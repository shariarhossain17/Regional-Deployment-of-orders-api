# AI log

Required by Part 1. Each entry: what was asked, what it said, what I did, why if modified or rejected.

## 1. Pulumi venv / Python 3.8

**Asked:** `sudo apt install python3.8-venv` failed.

**It said:** Debian 12 has Python 3.11; use `python3 -m venv`.

**Did:** Accepted. Used 3.11 venv in `iac/`.

## 2. Region

**Asked:** Put everything in Singapore / ap-southeast.

**It said:** Use `ap-southeast-1`, not `ap-south-east`. Lookup AMI in-region.

**Did:** Accepted. Stack region `ap-southeast-1`.

## 3. Copy private key onto the bastion

**Asked:** How to scp `capstone-key.pem` to the bastion like a tutorial.

**It said:** Copy the key and chmod 400, then ssh from bastion to app.

**Did:** Rejected for submission. Brief: if `~/.ssh` on the bastion contains a private key, access scores zero. Reach private hosts with ProxyJump / `ProxyCommand` from the laptop (same pattern as `collect-evidence.sh`). Agent forwarding without `ssh-add` also failed; did not copy the key to fix it.

## 4. AssessmentNonce at instance create

**Asked:** `session_nonce` NameError; later IAM `ec2:RunInstances` explicit deny.

**It said:** Default a fake nonce tag; then: Poridhi deny may be the extra tag or `t3.micro` / Ubuntu AMI.

**Did:** Modified. No nonce until the instructor issues it (tag update later). `t2.micro` + Amazon Linux 2. Fake nonce at launch was rejected because it blocked `RunInstances`.

## 5. Centralized egress / NAT + TGW same subnet

**Asked:** Implement networking in Pulumi.

**It said (generic):** Put NAT and TGW attachment together; default route to NAT.

**Did:** Rejected that layout. NAT's subnet must use `0.0.0.0/0 → IGW`. Attachment subnet uses `0.0.0.0/0 → NAT`. Return: `10.20.0.0/16 → TGW` on the NAT subnet. First apply's `RouteAlreadyExists` / `Resource.AlreadyAssociated` came from leftover default TGW association — used a dedicated TGW route table plus explicit association/propagation.

## 6. Lambda placement

**Asked:** How to reach private DB and S3/SES.

**It said:** Obvious options include Lambda outside the VPC, or a NAT in app-vpc, or public subnets.

**Did:** Rejected those. Outside VPC cannot hit private-data. NAT in app-vpc breaks the audit rule. Public subnet Lambda still has no public IP and still needs NAT. Lambda sits in private-app with **app-sg** so DB SG still references only the app SG id. Egress is TGW → shared NAT, same as the instances.

## 7. Lambda IAM

**Asked:** What permissions.

**It said:** Scoped `s3:PutObject` on the token prefix; SES on the email identity; attach `AWSLambdaVPCAccessExecutionRole`.

**Did:** Accepted. Rejected `s3:*` on `*`. First SES policy used `region:*:identity/email` and AccessDenied; replaced with account `914115115438` and `identity/shariarhossain23@gmail.com` on the execution role actually used by the function.

## 8. Appendix A schema vs existing table

**Asked:** Why recreate DB; Lambda `column customer does not exist`.

**It said:** Do not rebuild the EC2; `DROP`/`CREATE` the `orders` table to Appendix A (500 rows).

**Did:** Accepted the table change, rejected a new DB instance. Later `permission denied for table orders` — GRANT to `postgres`/`orders` because the table was created as the postgres superuser.

## 9. systemd credentials

**Asked:** Password must not show in `systemctl cat` / `ps aux`.

**It said:** Fetch from SSM, or source a file inside a wrapper, not `Environment=` / `EnvironmentFile=` (those appear in `systemctl show -p Environment`).

**Did:** Accepted wrapper + env file outside the unit. Did not put secrets on the gunicorn command line.

## 10. Evidence / teardown order

**Asked:** Commit teardown.

**It said:** Do not commit teardown before `evidence/`; git history is graded.

**Did:** Accepted. `teardown.txt` stays empty until after evidence is pushed and `pulumi destroy` has run.
