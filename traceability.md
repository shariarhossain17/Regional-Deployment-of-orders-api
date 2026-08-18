# Traceability

After `./collect-evidence.sh`, grep each third-column string in the named file. If a string is not in that file, replace it with the real `rtb-` / `tgw-` / EIP from your run — invented IDs cost more than a missing row.

Do not fill this table from memory. Open the evidence file, copy the value.

| Requirement | Evidence file | The specific value that proves it |
|---|---|---|
| Private subnets have no IGW or NAT route | evidence/03-route-tables.json | Route table tagged `Name=app-private-rt` associated with `10.20.10.0/24`, `10.20.11.0/24`, `10.20.20.0/24`; its `0.0.0.0/0` target is a `TransitGatewayId`, not `GatewayId` or `NatGatewayId` |
| Automatic VPC local route only for app CIDR on private RT | evidence/03-route-tables.json | `10.20.0.0/16` with `"GatewayId": "local"` on `app-private-rt` |
| TGW associations | evidence/05-tgw-attach.json and evidence/17-pulumi.json | Attachments named `app-tgw-attach` and `egress-tgw-attach`; Pulumi resources `orders-api-capstone-tgw-assoc-app` and `orders-api-capstone-tgw-assoc-egress` |
| TGW propagations | evidence/04-tgw-routes.json and evidence/17-pulumi.json | Active routes including propagated `10.20.0.0/16` to the app attachment; Pulumi `orders-api-capstone-tgw-prop-app` / `tgw-prop-egress` |
| Centralized egress (the line that matters) | evidence/08-egress.txt | App-a `curl checkip` output equals the NAT `PublicIp` listed in the same file (and in evidence/06-nat.json) |
| Return path from NAT to app-vpc | evidence/03-route-tables.json | Table tagged `egress-public-rt`: `10.20.0.0/16` → `TransitGatewayId`, and `0.0.0.0/0` → egress `GatewayId` (IGW), not NAT |
| TGW default to egress VPC | evidence/04-tgw-routes.json | `0.0.0.0/0` state `active` toward the egress attachment |
| Database isolation from public subnet | evidence/09-isolation.txt | Bastion probe of `DB_IP:5432` prints `CLOSED_OR_TIMEOUT` (not `OPEN`) |
| DB SG uses app SG id, not a CIDR | evidence/07-sgs.json | `db-sg` ingress `5432` `UserIdGroupPairs` references `app-sg` `GroupId`; no `CidrIp` for 5432 |
| Non-root service user | evidence/10-systemd.txt | Unit `User=ordersapi` and `ps` line not owned by `root` |
| Credentials not in systemd environment | evidence/10-systemd.txt | `systemctl show orders-api -p Environment` has no `DB_PASSWORD`; unit has no `Environment=` secret |
| Upstream failure detection | evidence/11-nginx.txt | `upstream` servers include `max_fails` and `fail_timeout` (not a bare `server` list) |
| Failover with no dropped requests | evidence/13-failover.txt | After stop on app-a, six `/whoami` HTTP codes are `200`; bodies are the remaining instance |
| Lambda network path (DB + AWS APIs) | evidence/14-lambda.json | `VpcConfig.SubnetIds` are private-app subnets; function has no public IP; role used for both VPC ENI and `s3:PutObject` |
| IAM scoping | evidence/14-lambda.json | Policy has `s3:PutObject` on `arn:aws:s3:::…/student/*` (or your token prefix), not `s3:*` on `*` |
| Session nonce on instances | evidence/02-inventory.json | Both app instances have tag `AssessmentNonce` equal to `evidence/00-manifest.txt` `session_nonce` |
| Session nonce in SES | instructor inbox + evidence/14-lambda.json | Lambda env `SESSION_NONCE`; email subject contains that nonce |
| Pulumi owns TGW routing | evidence/17-pulumi.json | Resources: Transit Gateway, both VPC attachments, TGW route table, associations, propagations, VPC `0.0.0.0/0` → TGW |

## How to paste real IDs after the harness

```bash
# examples — run these on the evidence files, then replace the third column
grep -n "app-private-rt" evidence/03-route-tables.json
grep -n "TransitGatewayId" evidence/03-route-tables.json
grep -n "PublicIp\|checkip" evidence/08-egress.txt
grep -n "CLOSED_OR_TIMEOUT\|OPEN" evidence/09-isolation.txt
grep -n "max_fails\|ordersapi\|Environment" evidence/10-systemd.txt evidence/11-nginx.txt
grep -n "PutObject\|s3:\\*" evidence/14-lambda.json
```
