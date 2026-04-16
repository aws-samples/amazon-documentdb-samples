#!/usr/bin/env bash
# ────────────────────────────────────────────────────────────────────────────
# Media Asset Workbench - Deploy Script
# Usage: ./deploy.sh [--region us-east-1] [--stack media-asset-workbench]
# Requires: aws CLI v2, tar
# ────────────────────────────────────────────────────────────────────────────
set -euo pipefail
export AWS_PAGER=""

STACK_NAME="${STACK_NAME:-media-asset-workbench}"
AWS_REGION="${AWS_REGION:-us-east-1}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Load config.env if present
[ -f "${SCRIPT_DIR}/config.env" ] && source "${SCRIPT_DIR}/config.env"

: "${KEY_PAIR_NAME:?Set KEY_PAIR_NAME in config.env}"
: "${MY_IP:?Set MY_IP in config.env (your public IP, e.g. 1.2.3.4/32)}"

echo "=== Media Asset Workbench Deploy ==="
echo "Stack:  ${STACK_NAME}"
echo "Region: ${AWS_REGION}"
echo ""

# ── 1. Create deployment S3 bucket (if needed) ────────────────────────────────
DEPLOY_BUCKET="${STACK_NAME}-deploy-$(aws sts get-caller-identity --query Account --output text)-${AWS_REGION}"
echo "--- Ensuring deploy bucket: ${DEPLOY_BUCKET}"
aws s3api head-bucket --bucket "${DEPLOY_BUCKET}" > /dev/null 2>&1 || \
  aws s3 mb "s3://${DEPLOY_BUCKET}" --region "${AWS_REGION}"

# ── 2. Package and upload worker code ─────────────────────────────────────────
echo "--- Packaging worker"
WORKER_TAR=$(mktemp /tmp/worker-XXXXXX.tar.gz)
trap "rm -f ${WORKER_TAR}" EXIT
tar -czf "${WORKER_TAR}" -C "${SCRIPT_DIR}/worker" .
aws s3 cp "${WORKER_TAR}" "s3://${DEPLOY_BUCKET}/worker.tar.gz" --region "${AWS_REGION}"
echo "    Worker packaged and uploaded"

# ── 3. Deploy/update CloudFormation stack ────────────────────────────────────
echo "--- Deploying CloudFormation stack"
aws cloudformation deploy \
  --stack-name "${STACK_NAME}" \
  --template-file "${SCRIPT_DIR}/infrastructure/cloudformation.yaml" \
  --region "${AWS_REGION}" \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    KeyPairName="${KEY_PAIR_NAME}" \
    MyIP="${MY_IP}" \
  --no-fail-on-empty-changeset

echo "    Stack deployed"

# ── 4. Fetch outputs ──────────────────────────────────────────────────────────
echo "--- Fetching stack outputs"
OUTPUTS=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME}" \
  --region "${AWS_REGION}" \
  --query 'Stacks[0].Outputs' \
  --output json)

get_output() {
  echo "${OUTPUTS}" | python3 -c "
import json, sys
outputs = json.load(sys.stdin)
key = sys.argv[1]
for o in outputs:
    if o['OutputKey'] == key:
        print(o['OutputValue'])
" "$1"
}

BUCKET_NAME=$(get_output BucketName)
DOCDB_ENDPOINT=$(get_output DocDBEndpoint)
WORKER_IP=$(get_output WorkerPublicIP)
WORKER_INSTANCE_ID=$(get_output WorkerInstanceId)
DOCDB_CLUSTER=$(get_output DocDBClusterIdentifier)
DOCDB_SECRET_ARN=$(get_output DocDBSecretArn)
SUBNET_ID=$(get_output SubnetId)
SECURITY_GROUP_ID=$(get_output MountTargetSGId)
S3FILES_ROLE_ARN=$(get_output S3FilesRoleArn)

# ── 4b. Copy worker code to asset bucket (EC2 pulls from here on first boot) ──
echo "--- Copying worker code to asset bucket"
aws s3 cp "s3://${DEPLOY_BUCKET}/worker.tar.gz" "s3://${BUCKET_NAME}/worker.tar.gz" --region "${AWS_REGION}"
echo "    Worker code copied"

# ── 5. Write config.env ───────────────────────────────────────────────────────
echo "--- Writing config.env"
cat > "${SCRIPT_DIR}/config.env" << ENV
AWS_REGION=${AWS_REGION}
STACK_NAME=${STACK_NAME}
BUCKET_NAME=${BUCKET_NAME}
DOCDB_ENDPOINT=${DOCDB_ENDPOINT}
DOCDB_CLUSTER=${DOCDB_CLUSTER}
DOCDB_SECRET_ARN=${DOCDB_SECRET_ARN}
WORKER_IP=${WORKER_IP}
WORKER_INSTANCE_ID=${WORKER_INSTANCE_ID}
KEY_PAIR_NAME=${KEY_PAIR_NAME}
MY_IP=${MY_IP}
CA_BUNDLE_PATH=${SCRIPT_DIR}/rds-combined-ca-bundle.pem
SUBNET_ID=${SUBNET_ID}
SECURITY_GROUP_ID=${SECURITY_GROUP_ID}
S3FILES_ROLE_ARN=${S3FILES_ROLE_ARN}
ENV

# ── 6. Download RDS CA bundle for local DocumentDB TLS ────────────────────────
echo "--- Downloading RDS CA bundle"
curl -sL https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem \
  -o "${SCRIPT_DIR}/rds-combined-ca-bundle.pem"
echo "    CA bundle saved to rds-combined-ca-bundle.pem"

echo ""
echo "============================================================"
echo "  Deploy complete!"
echo "============================================================"
echo ""
echo "  S3 Bucket:       ${BUCKET_NAME}"
echo "  DocumentDB:      ${DOCDB_ENDPOINT}"
echo "  Worker IP:       ${WORKER_IP}"
echo "  Worker ID:       ${WORKER_INSTANCE_ID}"
echo "  DocDB Cluster:   ${DOCDB_CLUSTER}"
echo ""
echo "  NEXT STEPS:"
echo ""
echo "  1. Generate and upload sample data (on your laptop):"
echo "     ./generate-sample-data.sh"
echo "     aws s3 sync ./sample-data/ s3://${BUCKET_NAME}/sample-packs/ --region ${AWS_REGION}"
echo ""
echo "  2. Set up S3 Files (run on your local machine — executes userdata.sh remotely):"
echo "     chmod 400 ~/.ssh/${KEY_PAIR_NAME}.pem   # or ./${KEY_PAIR_NAME}.pem if key is here"
echo "     ssh -i ~/.ssh/${KEY_PAIR_NAME}.pem ec2-user@${WORKER_IP} \\"
echo "       \"sudo BUCKET_NAME=${BUCKET_NAME} AWS_REGION=${AWS_REGION} \\"
echo "        SUBNET_ID=${SUBNET_ID} SECURITY_GROUP_ID=${SECURITY_GROUP_ID} \\"
echo "        S3FILES_ROLE_ARN=${S3FILES_ROLE_ARN} bash /opt/worker/userdata.sh\""
echo ""
echo "  3. Before running the UI, open the DocumentDB tunnel:"
echo "     # Add to /etc/hosts (one-time, remove after teardown):"
echo "     echo '127.0.0.1 ${DOCDB_ENDPOINT}' | sudo tee -a /etc/hosts"
echo ""
echo "     # Open SSM port forward (keep this terminal open while using the UI):"
echo "     aws ssm start-session \\"
echo "       --target ${WORKER_INSTANCE_ID} \\"
echo "       --region ${AWS_REGION} \\"
echo "       --document-name AWS-StartPortForwardingSessionToRemoteHost \\"
echo "       --parameters 'host=${DOCDB_ENDPOINT},portNumber=27017,localPortNumber=27017'"
echo ""
echo "  4. Start the local UI (new terminal on your laptop):"
echo "     cd ui && pip install -r requirements.txt"
echo "     uvicorn app:app --reload --port 8080"
echo "     Then open http://127.0.0.1:8080 in your browser"
echo ""
echo "  5. Stop DocumentDB when done to save cost:"
echo "     aws docdb stop-db-cluster --db-cluster-identifier ${DOCDB_CLUSTER} --region ${AWS_REGION}"
echo ""
echo "  6. Tear down everything:"
echo "     ./cleanup.sh"
echo "============================================================"
