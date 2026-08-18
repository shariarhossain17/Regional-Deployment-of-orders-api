# Source this from the repo root, then run ./collect-evidence.sh
#   source ./evidence-env.sh
#   export SESSION_NONCE='instructor-nonce'
#   ./collect-evidence.sh

export STUDENT_TOKEN=student
export DUMP_BUCKET=orders-api-capstone-dump-bucket-c514480
export SSH_KEY=~/.ssh/capstone-key.pem
export BASTION_IP=13.228.27.177
export EDGE_IP=54.251.71.221
export APP_A_IP=10.20.10.51
export APP_B_IP=10.20.11.77
export DB_IP=10.20.20.239
export DB_PORT=5432
export LAMBDA_NAME=orders-api-nightly-dump
export TGW_RT_ID=tgw-rtb-0ce02f7e8600c335c
export PULUMI_DIR=./iac
