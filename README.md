# orders-api capstone

Two VPCs in **ap-southeast-1**, joined only by a Transit Gateway (no peering). Workload subnets have no IGW or NAT of their own. Internet for app, database installs, and Lambda exits through the shared egress VPC NAT.

## Paths

1. **Inbound** — user → Nginx public IP (`public-a`) → app-a / app-b (`:5000`).
2. **App → database** — private-app → private-data, same VPC, local route; DB SG allows only the app SG on 5432.
3. **App → internet** — private-app `0.0.0.0/0` → TGW → egress-tgw-a → NAT → IGW. Return: NAT subnet `10.20.0.0/16` → TGW.
4. **Lambda → database** — Lambda ENIs in private-app + app SG → same 5432 rule. Lambda → S3/SES uses path (3).

## Subnets

| Name | CIDR | Route table |
|---|---|---|
| public-a | 10.20.1.0/24 | app-public-rt (`0.0.0.0/0` → app IGW) |
| public-b | 10.20.2.0/24 | app-public-rt |
| private-app-a | 10.20.10.0/24 | app-private-rt (`0.0.0.0/0` → TGW) |
| private-app-b | 10.20.11.0/24 | app-private-rt |
| private-data-a | 10.20.20.0/24 | app-private-rt |
| egress-public-a | 10.30.1.0/24 | egress-public-rt (`0.0.0.0/0` → egress IGW, `10.20.0.0/16` → TGW) |
| egress-tgw-a | 10.30.10.0/24 | egress-tgw-rt (`0.0.0.0/0` → NAT) |

NAT and the TGW attachment are **not** in the same subnet. Same-subnet NAT+TGW with default-to-NAT loops the NAT's own internet path.

## Rebuild

```bash
cd iac
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pulumi stack select dev
pulumi config set aws:region ap-southeast-1
pulumi up
```

Key pair name defaults to `capstone-key`. After apply, configure Postgres, systemd `orders-api`, Nginx upstreams, and the Lambda (`orders-api-nightly-dump`) on the live instances. SSH to private hosts with ProxyJump from your laptop — do not copy a private key onto the bastion.

## Evidence then teardown (git order)

1. Tag both app instances `AssessmentNonce=<instructor nonce>`.
2. Set Lambda env `SESSION_NONCE` to the same value; invoke once so SES subject contains it.
3. `./collect-evidence.sh` (see script header for env vars).
4. Read `evidence/08-egress.txt` — app-a must equal the egress NAT EIP.
5. `git add evidence && git commit && git push`
6. `cd iac && pulumi destroy --yes`
7. Paste destroy output into `teardown.txt`, commit and push **separately**.
