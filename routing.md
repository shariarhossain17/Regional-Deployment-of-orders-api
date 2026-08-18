# Routing

Every extra route we created (VPC local routes exist automatically). One sentence on purpose, one on deletion.

## app-public-rt (public-a 10.20.1.0/24, public-b 10.20.2.0/24)

| Destination | Target | What it does | If you delete it |
|---|---|---|---|
| 0.0.0.0/0 | app-vpc IGW | Lets bastion SSH and Nginx serve port 80 from the internet. | You cannot reach EDGE_IP or the bastion; harness SSH to nginx fails. |

## app-private-rt (private-app-a 10.20.10.0/24, private-app-b 10.20.11.0/24, private-data-a 10.20.20.0/24)

No IGW. No NAT in this VPC.

| Destination | Target | What it does | If you delete it |
|---|---|---|---|
| 0.0.0.0/0 | Transit Gateway | Sends all non-VPC traffic to the shared egress VPC. | `pip`/`yum` on app and DB hang; `checkip` fails; Lambda cannot reach S3/SES. |

Same-VPC app→DB uses the automatic `10.20.0.0/16 → local` route. Deleting that is not possible without replacing the VPC; if it were gone, `/orders` would fail while `/health` still passed.

## egress-public-rt (egress-public-a 10.30.1.0/24 — NAT lives here)

| Destination | Target | What it does | If you delete it |
|---|---|---|---|
| 0.0.0.0/0 | egress-vpc IGW | NAT translated packets leave to the internet. | NAT has no path out; app egress times out even if TGW is healthy. |
| 10.20.0.0/16 | Transit Gateway | Return path: after NAT, replies go back to app-vpc. | Outbound SYNs work, replies blackhole; `checkip` hangs. This is the TGW return path. |

## egress-tgw-rt (egress-tgw-a 10.30.10.0/24 — TGW attachment lives here)

| Destination | Target | What it does | If you delete it |
|---|---|---|---|
| 0.0.0.0/0 | NAT Gateway | Packets arriving from TGW are sent to NAT for SNAT. | Traffic reaches egress VPC and dies on the attachment subnet. |

Do not point this table at the IGW and do not put the TGW attachment in the NAT subnet: `0.0.0.0/0 → NAT` on the NAT's own subnet loops the NAT.

## capstone-tgw-rt (Transit Gateway route table)

Both VPC attachments are associated and both propagate.

| Destination | Target | What it does | If you delete it |
|---|---|---|---|
| 0.0.0.0/0 (static) | egress VPC attachment | Default: workload internet goes to egress-vpc. | TGW has no default; app `0.0.0.0/0` hits TGW and blackholes. |
| 10.20.0.0/16 (propagated) | app VPC attachment | NAT return and any spoke-to-spoke to app-vpc. | Return path from NAT fails; isolation of app CIDR from TGW. |
| 10.30.0.0/16 (propagated) | egress VPC attachment | TGW can forward into egress-vpc CIDR. | Attachment-local routing in egress can fail depending on overlap with 0.0.0.0/0. |

## Why NAT and TGW ENI are split

First apply put the egress TGW attachment in `egress-public-a` with `0.0.0.0/0 → NAT`. That is the generic “NAT subnet” pattern and it is wrong here: the NAT Gateway itself needs `0.0.0.0/0 → IGW`. Split: attachment in `10.30.10.0/24`, NAT in `10.30.1.0/24`.
