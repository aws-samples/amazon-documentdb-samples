#!/usr/bin/env bash
# ────────────────────────────────────────────────────────────────────────────
# Media Asset Workbench - Cleanup Script
# Tears down all resources created by deploy.sh.
# Usage: ./cleanup.sh
# ────────────────────────────────────────────────────────────────────────────
set -euo pipefail
export AWS_PAGER=""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ ! -f "${SCRIPT_DIR}/config.env" ]; then
  echo "ERROR: config.env not found. Nothing to clean up." >&2
  exit 1
fi

source "${SCRIPT_DIR}/config.env"

: "${STACK_NAME:?STACK_NAME not set in config.env}"
: "${AWS_REGION:?AWS_REGION not set in config.env}"
: "${BUCKET_NAME:?BUCKET_NAME not set in config.env}"

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
DEPLOY_BUCKET="${STACK_NAME}-deploy-${ACCOUNT_ID}-${AWS_REGION}"

echo "=== Media Asset Workbench Cleanup ==="
echo "Stack:         ${STACK_NAME}"
echo "Region:        ${AWS_REGION}"
echo "Asset Bucket:  ${BUCKET_NAME}"
echo "Deploy Bucket: ${DEPLOY_BUCKET}"
echo ""
read -p "Are you sure you want to delete everything? (y/N) " -n 1 -r
echo ""
[[ $REPLY =~ ^[Yy]$ ]] || { echo "Cancelled."; exit 0; }

# ── 1. Empty the asset bucket (versioned) ─────────────────────────────────────
echo "--- Emptying asset bucket: ${BUCKET_NAME}"
aws s3 rm "s3://${BUCKET_NAME}" --recursive --region "${AWS_REGION}" 2>/dev/null || true

echo "    Deleting object versions..."
aws s3api list-object-versions --bucket "${BUCKET_NAME}" --region "${AWS_REGION}" \
  --query '{Objects: Versions[].{Key:Key,VersionId:VersionId}}' --output json 2>/dev/null \
  | aws s3api delete-objects --bucket "${BUCKET_NAME}" --delete file:///dev/stdin --region "${AWS_REGION}" > /dev/null 2>&1 || true

echo "    Deleting delete markers..."
aws s3api list-object-versions --bucket "${BUCKET_NAME}" --region "${AWS_REGION}" \
  --query '{Objects: DeleteMarkers[].{Key:Key,VersionId:VersionId}}' --output json 2>/dev/null \
  | aws s3api delete-objects --bucket "${BUCKET_NAME}" --delete file:///dev/stdin --region "${AWS_REGION}" > /dev/null 2>&1 || true

echo "    Asset bucket emptied"

# ── 2. Delete S3 Files filesystem (if created) ────────────────────────────────
echo "--- Checking for S3 Files filesystem..."
FS_ID=$(aws s3files list-file-systems \
  --bucket "arn:aws:s3:::${BUCKET_NAME}" \
  --query "fileSystems[0].fileSystemId" \
  --output text --region "${AWS_REGION}" 2>/dev/null || echo "")

if [ -n "${FS_ID}" ] && [ "${FS_ID}" != "None" ]; then
  echo "    Deleting mount targets for filesystem: ${FS_ID}"
  # Get all mount target IDs and delete them
  MT_IDS=$(aws s3files list-mount-targets \
    --file-system-id "${FS_ID}" \
    --query "mountTargets[].mountTargetId" \
    --output text --region "${AWS_REGION}" 2>/dev/null || echo "")
  for MT_ID in ${MT_IDS}; do
    aws s3files delete-mount-target --mount-target-id "${MT_ID}" --region "${AWS_REGION}" 2>/dev/null || true
  done
  echo "    Waiting for mount targets to be deleted..."
  sleep 30
  echo "    Deleting filesystem: ${FS_ID}"
  aws s3files delete-file-system --file-system-id "${FS_ID}" --region "${AWS_REGION}" 2>/dev/null || true
else
  echo "    No S3 Files filesystem found"
fi

# ── 3. Delete the CloudFormation stack ─────────────────────────────────────────
echo "--- Deleting CloudFormation stack: ${STACK_NAME}"
aws cloudformation delete-stack --stack-name "${STACK_NAME}" --region "${AWS_REGION}"
echo "    Waiting for stack deletion..."
aws cloudformation wait stack-delete-complete --stack-name "${STACK_NAME}" --region "${AWS_REGION}" 2>/dev/null || true
echo "    Stack deleted"

# ── 4. Delete the deployment bucket ───────────────────────────────────────────
echo "--- Deleting deploy bucket: ${DEPLOY_BUCKET}"
aws s3 rb "s3://${DEPLOY_BUCKET}" --force --region "${AWS_REGION}" 2>/dev/null || true
echo "    Deploy bucket deleted"

echo ""
echo "============================================================"
echo "  Cleanup complete!"
echo "============================================================"
echo ""
echo "  Don't forget to:"
echo "  - Remove the /etc/hosts entry for DocumentDB:"
echo "    sudo sed -i '' '/${DOCDB_ENDPOINT:-docdb}/d' /etc/hosts"
echo "  - Close any open SSM port forward sessions"
echo "============================================================"
