# Regional Deployment of orders-api

Pulumi (Python) deploys the orders-api capstone stack in **ap-southeast-1** (Asia Pacific, Singapore).

## Submission order (required)

The grader checks git history. Do this in this order, and do not skip a push:

1. Deploy and collect screenshots into `evidence/`.
2. **Commit and push `evidence/` first.**
3. Tear down AWS resources (`pulumi destroy`).
4. **Then** fill `teardown.txt` and commit/push it.

`teardown.txt` must be pushed **after** the `evidence/` commit. Do not commit them together.

## 1. Deploy

```bash
cd iac
source venv/bin/activate
pulumi up
```

Region is already set: `aws:region: ap-southeast-1`.

## 2. Evidence commit (before teardown)

Put console screenshots / proof into `evidence/` (VPC, subnets, TGW, NAT, EC2, routing). Then:

```bash
git add evidence/
git commit -m "Add assessment evidence"
git push origin main
```

Confirm the push succeeded before destroying anything.

## 3. Teardown (only after evidence is on GitHub)

```bash
cd iac
source venv/bin/activate
pulumi destroy --yes
```

Paste the destroy output into `teardown.txt`.

## 4. teardown.txt commit (after destroy)

```bash
git add teardown.txt
git commit -m "Add teardown confirmation"
git push origin main
```
