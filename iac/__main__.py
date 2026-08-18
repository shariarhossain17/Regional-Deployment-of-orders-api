import json
import pulumi
import pulumi_aws as aws

# Configuration
config = pulumi.Config()
project_name = "orders-api-capstone"
environment = "prod"
key_name = config.get("key_name") or "capstone-key"
session_nonce = config.get("session_nonce")
student_token = config.get("student_token") or "student"
instance_type = config.get("instance_type") or "t2.micro"
common_tags = {
    "Project": "capstone-orders-api",
    "Environment": environment,
    "ManagedBy": "Pulumi",
}

def instance_tags(name: str) -> dict:
    tags = {**common_tags, "Name": name}
    if session_nonce:
        tags["AssessmentNonce"] = session_nonce
    return tags

#=============================================================================
# STEP 1: VPCs
#=============================================================================

app_vpc = aws.ec2.Vpc(
    f"{project_name}-app-vpc",
    cidr_block="10.20.0.0/16",
    enable_dns_support=True,
    enable_dns_hostnames=True,
    tags={**common_tags, "Name": "app-vpc"},
)

egress_vpc = aws.ec2.Vpc(
    f"{project_name}-egress-vpc",
    cidr_block="10.30.0.0/16",
    enable_dns_support=True,
    enable_dns_hostnames=True,
    tags={**common_tags, "Name": "egress-vpc"},
)

#=============================================================================
# STEP 2: Subnets
#=============================================================================

# app-vpc public — bastion + nginx. Two AZs as the brief requires.
public_subnet = aws.ec2.Subnet(
    f"{project_name}-public-a",
    vpc_id=app_vpc.id,
    cidr_block="10.20.1.0/24",
    availability_zone="ap-southeast-1a",
    map_public_ip_on_launch=True,
    tags={**common_tags, "Name": "public-a"},
)

public_subnet_b = aws.ec2.Subnet(
    f"{project_name}-public-b",
    vpc_id=app_vpc.id,
    cidr_block="10.20.2.0/24",
    availability_zone="ap-southeast-1b",
    map_public_ip_on_launch=True,
    tags={**common_tags, "Name": "public-b"},
)

app_subnet_a = aws.ec2.Subnet(
    f"{project_name}-private-app-a",
    vpc_id=app_vpc.id,
    cidr_block="10.20.10.0/24",
    availability_zone="ap-southeast-1a",
    tags={**common_tags, "Name": "private-app-a"},
)

app_subnet_b = aws.ec2.Subnet(
    f"{project_name}-private-app-b",
    vpc_id=app_vpc.id,
    cidr_block="10.20.11.0/24",
    availability_zone="ap-southeast-1b",
    tags={**common_tags, "Name": "private-app-b"},
)

data_subnet = aws.ec2.Subnet(
    f"{project_name}-private-data-a",
    vpc_id=app_vpc.id,
    cidr_block="10.20.20.0/24",
    availability_zone="ap-southeast-1a",
    tags={**common_tags, "Name": "private-data-a"},
)

# egress-vpc: NAT lives in public. TGW attachment must NOT share that subnet.
# Same-subnet NAT+TGW with 0.0.0.0/0 → NAT loops the NAT's own internet path.
egress_public_subnet = aws.ec2.Subnet(
    f"{project_name}-egress-public-a",
    vpc_id=egress_vpc.id,
    cidr_block="10.30.1.0/24",
    availability_zone="ap-southeast-1a",
    map_public_ip_on_launch=True,
    tags={**common_tags, "Name": "egress-public-a"},
)

egress_tgw_subnet = aws.ec2.Subnet(
    f"{project_name}-egress-tgw-a",
    vpc_id=egress_vpc.id,
    cidr_block="10.30.10.0/24",
    availability_zone="ap-southeast-1a",
    tags={**common_tags, "Name": "egress-tgw-a"},
)

#=============================================================================
# STEP 3: Gateways and Transit Gateway
#=============================================================================

app_igw = aws.ec2.InternetGateway(
    f"{project_name}-app-igw",
    vpc_id=app_vpc.id,
    tags={**common_tags, "Name": "app-igw"},
)
egress_igw = aws.ec2.InternetGateway(
    f"{project_name}-egress-igw",
    vpc_id=egress_vpc.id,
    tags={**common_tags, "Name": "egress-igw"},
)

nat_eip = aws.ec2.Eip(f"{project_name}-nat-eip", domain="vpc", tags={**common_tags, "Name": "egress-nat-eip"})
egress_nat = aws.ec2.NatGateway(
    f"{project_name}-egress-nat",
    allocation_id=nat_eip.id,
    subnet_id=egress_public_subnet.id,
    tags={**common_tags, "Name": "egress-nat"},
    opts=pulumi.ResourceOptions(depends_on=[egress_igw, nat_eip]),
)

# Custom TGW route table is required (associations + propagations in Pulumi).
# Disable the default RT so we do not double-associate.
transit_gateway = aws.ec2transitgateway.TransitGateway(
    f"{project_name}-tgw",
    description="Capstone Transit Gateway",
    default_route_table_association="disable",
    default_route_table_propagation="disable",
    tags={**common_tags, "Name": "capstone-tgw"},
)

app_tgw_attachment = aws.ec2transitgateway.VpcAttachment(
    f"{project_name}-app-tgw-attach",
    transit_gateway_id=transit_gateway.id,
    vpc_id=app_vpc.id,
    subnet_ids=[app_subnet_a.id, app_subnet_b.id],
    transit_gateway_default_route_table_association=False,
    transit_gateway_default_route_table_propagation=False,
    tags={**common_tags, "Name": "app-tgw-attach"},
)

egress_tgw_attachment = aws.ec2transitgateway.VpcAttachment(
    f"{project_name}-egress-tgw-attach",
    transit_gateway_id=transit_gateway.id,
    vpc_id=egress_vpc.id,
    subnet_ids=[egress_tgw_subnet.id],
    appliance_mode_support="enable",
    transit_gateway_default_route_table_association=False,
    transit_gateway_default_route_table_propagation=False,
    tags={**common_tags, "Name": "egress-tgw-attach"},
)

tgw_rt = aws.ec2transitgateway.RouteTable(
    f"{project_name}-tgw-rt",
    transit_gateway_id=transit_gateway.id,
    tags={**common_tags, "Name": "capstone-tgw-rt"},
)

aws.ec2transitgateway.RouteTableAssociation(
    f"{project_name}-tgw-assoc-app",
    transit_gateway_attachment_id=app_tgw_attachment.id,
    transit_gateway_route_table_id=tgw_rt.id,
)

aws.ec2transitgateway.RouteTableAssociation(
    f"{project_name}-tgw-assoc-egress",
    transit_gateway_attachment_id=egress_tgw_attachment.id,
    transit_gateway_route_table_id=tgw_rt.id,
)

# App CIDR must propagate so NAT return traffic can find 10.20.0.0/16.
aws.ec2transitgateway.RouteTablePropagation(
    f"{project_name}-tgw-prop-app",
    transit_gateway_attachment_id=app_tgw_attachment.id,
    transit_gateway_route_table_id=tgw_rt.id,
)

aws.ec2transitgateway.RouteTablePropagation(
    f"{project_name}-tgw-prop-egress",
    transit_gateway_attachment_id=egress_tgw_attachment.id,
    transit_gateway_route_table_id=tgw_rt.id,
)

# Workload internet: TGW sends 0.0.0.0/0 to the egress VPC attachment.
aws.ec2transitgateway.Route(
    f"{project_name}-tgw-default-to-egress",
    destination_cidr_block="0.0.0.0/0",
    transit_gateway_attachment_id=egress_tgw_attachment.id,
    transit_gateway_route_table_id=tgw_rt.id,
)

#=============================================================================
# STEP 4: VPC route tables
#=============================================================================

# public-* : users reach bastion/nginx. Not a workload egress path.
app_public_rt = aws.ec2.RouteTable(
    f"{project_name}-app-public-rt",
    vpc_id=app_vpc.id,
    tags={**common_tags, "Name": "app-public-rt"},
)
aws.ec2.Route(
    f"{project_name}-app-public-igw-route",
    route_table_id=app_public_rt.id,
    destination_cidr_block="0.0.0.0/0",
    gateway_id=app_igw.id,
)
aws.ec2.RouteTableAssociation(
    f"{project_name}-app-public-assoc",
    subnet_id=public_subnet.id,
    route_table_id=app_public_rt.id,
)
aws.ec2.RouteTableAssociation(
    f"{project_name}-app-public-b-assoc",
    subnet_id=public_subnet_b.id,
    route_table_id=app_public_rt.id,
)

# private-app-* and private-data-* : NO IGW, NO NAT in this VPC.
# 0.0.0.0/0 → Transit Gateway only.
app_private_rt = aws.ec2.RouteTable(
    f"{project_name}-app-private-rt",
    vpc_id=app_vpc.id,
    tags={**common_tags, "Name": "app-private-rt"},
)
aws.ec2.Route(
    f"{project_name}-app-private-tgw-route",
    route_table_id=app_private_rt.id,
    destination_cidr_block="0.0.0.0/0",
    transit_gateway_id=transit_gateway.id,
)
aws.ec2.RouteTableAssociation(
    f"{project_name}-app-a-assoc",
    subnet_id=app_subnet_a.id,
    route_table_id=app_private_rt.id,
)
aws.ec2.RouteTableAssociation(
    f"{project_name}-app-b-assoc",
    subnet_id=app_subnet_b.id,
    route_table_id=app_private_rt.id,
)
aws.ec2.RouteTableAssociation(
    f"{project_name}-data-assoc",
    subnet_id=data_subnet.id,
    route_table_id=app_private_rt.id,
)

# NAT's subnet: internet via IGW, return to app-vpc via TGW.
egress_public_rt = aws.ec2.RouteTable(
    f"{project_name}-egress-rt",
    vpc_id=egress_vpc.id,
    tags={**common_tags, "Name": "egress-public-rt"},
)
aws.ec2.Route(
    f"{project_name}-egress-public-igw-route",
    route_table_id=egress_public_rt.id,
    destination_cidr_block="0.0.0.0/0",
    gateway_id=egress_igw.id,
)
aws.ec2.Route(
    f"{project_name}-egress-public-return-route",
    route_table_id=egress_public_rt.id,
    destination_cidr_block="10.20.0.0/16",
    transit_gateway_id=transit_gateway.id,
)
aws.ec2.RouteTableAssociation(
    f"{project_name}-egress-assoc",
    subnet_id=egress_public_subnet.id,
    route_table_id=egress_public_rt.id,
)

# TGW attachment subnet: packets arriving from app-vpc go to the NAT.
egress_tgw_rt = aws.ec2.RouteTable(
    f"{project_name}-egress-tgw-rt",
    vpc_id=egress_vpc.id,
    tags={**common_tags, "Name": "egress-tgw-rt"},
)
aws.ec2.Route(
    f"{project_name}-egress-tgw-nat-route",
    route_table_id=egress_tgw_rt.id,
    destination_cidr_block="0.0.0.0/0",
    nat_gateway_id=egress_nat.id,
)
aws.ec2.RouteTableAssociation(
    f"{project_name}-egress-tgw-assoc",
    subnet_id=egress_tgw_subnet.id,
    route_table_id=egress_tgw_rt.id,
)

#=============================================================================
# STEP 5: Security Groups
#=============================================================================

bastion_sg = aws.ec2.SecurityGroup(
    f"{project_name}-bastion-sg",
    vpc_id=app_vpc.id,
    ingress=[aws.ec2.SecurityGroupIngressArgs(protocol="tcp", from_port=22, to_port=22, cidr_blocks=["0.0.0.0/0"])],
    egress=[aws.ec2.SecurityGroupEgressArgs(protocol="-1", from_port=0, to_port=0, cidr_blocks=["0.0.0.0/0"])],
    tags={**common_tags, "Name": "bastion-sg"},
)

nginx_sg = aws.ec2.SecurityGroup(
    f"{project_name}-nginx-sg",
    vpc_id=app_vpc.id,
    ingress=[aws.ec2.SecurityGroupIngressArgs(protocol="tcp", from_port=80, to_port=80, cidr_blocks=["0.0.0.0/0"])],
    egress=[aws.ec2.SecurityGroupEgressArgs(protocol="-1", from_port=0, to_port=0, cidr_blocks=["0.0.0.0/0"])],
    tags={**common_tags, "Name": "nginx-sg"},
)

app_sg = aws.ec2.SecurityGroup(
    f"{project_name}-app-sg",
    vpc_id=app_vpc.id,
    ingress=[
        aws.ec2.SecurityGroupIngressArgs(protocol="tcp", from_port=5000, to_port=5000, security_groups=[nginx_sg.id]),
        aws.ec2.SecurityGroupIngressArgs(protocol="tcp", from_port=22, to_port=22, security_groups=[bastion_sg.id]),
    ],
    egress=[aws.ec2.SecurityGroupEgressArgs(protocol="-1", from_port=0, to_port=0, cidr_blocks=["0.0.0.0/0"])],
    tags={**common_tags, "Name": "app-sg"},
)

db_sg = aws.ec2.SecurityGroup(
    f"{project_name}-db-sg",
    vpc_id=app_vpc.id,
    ingress=[aws.ec2.SecurityGroupIngressArgs(protocol="tcp", from_port=5432, to_port=5432, security_groups=[app_sg.id])],
    egress=[aws.ec2.SecurityGroupEgressArgs(protocol="-1", from_port=0, to_port=0, cidr_blocks=["0.0.0.0/0"])],
    tags={**common_tags, "Name": "db-sg"},
)

#=============================================================================
# STEP 6: EC2 (already launched — networking only this pass)
#=============================================================================

amazon_linux_ami = aws.ec2.get_ami(
    most_recent=True,
    owners=["amazon"],
    filters=[
        aws.ec2.GetAmiFilterArgs(name="name", values=["amzn2-ami-hvm-*-x86_64-gp2"]),
        aws.ec2.GetAmiFilterArgs(name="virtualization-type", values=["hvm"]),
        aws.ec2.GetAmiFilterArgs(name="state", values=["available"]),
    ],
)
ami_id = amazon_linux_ami.id

private_depends = [
    app_tgw_attachment,
    egress_tgw_attachment,
    tgw_rt,
    egress_nat,
]

bastion = aws.ec2.Instance(
    f"{project_name}-bastion",
    ami=ami_id,
    instance_type=instance_type,
    key_name=key_name,
    subnet_id=public_subnet.id,
    vpc_security_group_ids=[bastion_sg.id],
    tags=instance_tags("bastion"),
)

nginx = aws.ec2.Instance(
    f"{project_name}-nginx",
    ami=ami_id,
    instance_type=instance_type,
    key_name=key_name,
    subnet_id=public_subnet.id,
    vpc_security_group_ids=[nginx_sg.id],
    tags=instance_tags("nginx-lb"),
)

db_instance = aws.ec2.Instance(
    f"{project_name}-db",
    ami=ami_id,
    instance_type=instance_type,
    key_name=key_name,
    subnet_id=data_subnet.id,
    vpc_security_group_ids=[db_sg.id],
    tags=instance_tags("database"),
    opts=pulumi.ResourceOptions(depends_on=private_depends),
)

app_a = aws.ec2.Instance(
    f"{project_name}-app-a",
    ami=ami_id,
    instance_type=instance_type,
    key_name=key_name,
    subnet_id=app_subnet_a.id,
    vpc_security_group_ids=[app_sg.id],
    tags=instance_tags("app-a"),
    opts=pulumi.ResourceOptions(depends_on=private_depends),
)

app_b = aws.ec2.Instance(
    f"{project_name}-app-b",
    ami=ami_id,
    instance_type=instance_type,
    key_name=key_name,
    subnet_id=app_subnet_b.id,
    vpc_security_group_ids=[app_sg.id],
    tags=instance_tags("app-b"),
    opts=pulumi.ResourceOptions(depends_on=private_depends),
)

#=============================================================================
# STEP 7: Placeholder automation (function itself comes later)
#=============================================================================

dump_bucket = aws.s3.Bucket(f"{project_name}-dump-bucket")

lambda_role = aws.iam.Role(
    f"{project_name}-lambda-role",
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Action": "sts:AssumeRole",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Effect": "Allow",
        }],
    }),
)

aws.iam.RolePolicy(
    f"{project_name}-lambda-policy",
    role=lambda_role.id,
    policy=pulumi.Output.all(dump_bucket.arn).apply(lambda args: json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {"Effect": "Allow", "Action": ["s3:PutObject"], "Resource": [f"{args[0]}/{student_token}/*"]},
            {"Effect": "Allow", "Action": ["ses:SendEmail", "ses:SendRawEmail"], "Resource": "*"},
            {"Effect": "Allow", "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"], "Resource": "*"},
        ],
    })),
)

#=============================================================================
# OUTPUTS
#=============================================================================

pulumi.export("bastion_ip", bastion.public_ip)
pulumi.export("edge_ip", nginx.public_ip)
pulumi.export("app_a_ip", app_a.private_ip)
pulumi.export("app_b_ip", app_b.private_ip)
pulumi.export("db_ip", db_instance.private_ip)
pulumi.export("nat_eip", nat_eip.public_ip)
pulumi.export("tgw_rt_id", tgw_rt.id)
pulumi.export("dump_bucket", dump_bucket.bucket)

