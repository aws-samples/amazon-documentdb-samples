#!/bin/bash
# ────────────────────────────────────────────────────────────────────────────
# S3 Files mount + worker startup script.
# Run this on the EC2 instance after the CloudFormation stack is deployed.
# It is also embedded in the CF UserData for first-boot; re-run if needed.
# ────────────────────────────────────────────────────────────────────────────
set -euo pipefail
export PATH="/usr/local/bin:$PATH"

BUCKET_NAME="${BUCKET_NAME:?Set BUCKET_NAME}"
AWS_REGION="${AWS_REGION:-us-east-1}"
SUBNET_ID="${SUBNET_ID:?Set SUBNET_ID (PublicSubnet1 from CF outputs)}"
SECURITY_GROUP_ID="${SECURITY_GROUP_ID:?Set SECURITY_GROUP_ID (MountTargetSGId from CF outputs)}"
S3FILES_ROLE_ARN="${S3FILES_ROLE_ARN:?Set S3FILES_ROLE_ARN (S3FilesRoleArn from CF outputs)}"
MOUNT_PATH="/mnt/assets"
BUCKET_ARN="arn:aws:s3:::${BUCKET_NAME}"

echo "=== Installing system packages ==="
dnf install -y nfs-utils jq python3.11 python3.11-pip unzip

# Install/update AWS CLI v2 (s3files requires a recent version)
if ! aws s3files help &>/dev/null; then
  echo "Updating AWS CLI v2..."
  curl -sL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o /tmp/awscliv2.zip
  unzip -qo /tmp/awscliv2.zip -d /tmp
  /tmp/aws/install --update
  rm -rf /tmp/aws /tmp/awscliv2.zip
  # Ensure the new version is on PATH
  ln -sf /usr/local/bin/aws /usr/bin/aws
  hash -r
  echo "AWS CLI: $(aws --version)"
fi

# Install amazon-efs-utils (required for mount -t s3files)
if ! command -v mount.s3files &>/dev/null; then
  echo "Installing amazon-efs-utils..."
  dnf install -y amazon-efs-utils 2>/dev/null || \
    { curl -s https://amazon-efs-utils.aws.com/efs-utils-installer.sh | sh -s -- --install; }
  echo "amazon-efs-utils installed"
fi

# ffmpeg is not in AL2023 default repos — install static build
if ! command -v ffmpeg &>/dev/null; then
  echo "Installing ffmpeg (static build)..."
  curl -sL https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz -o /tmp/ffmpeg.tar.xz
  tar -xf /tmp/ffmpeg.tar.xz -C /tmp
  cp /tmp/ffmpeg-*-amd64-static/ffmpeg /usr/local/bin/
  cp /tmp/ffmpeg-*-amd64-static/ffprobe /usr/local/bin/
  rm -rf /tmp/ffmpeg* 
  echo "ffmpeg installed: $(ffmpeg -version | head -1)"
fi

echo "=== Deploying worker code ==="
if [ ! -f /opt/worker/worker.py ]; then
  mkdir -p /opt/worker
  aws s3 cp "s3://${BUCKET_NAME}/worker.tar.gz" /tmp/worker.tar.gz \
    --region "${AWS_REGION}"
  tar -xzf /tmp/worker.tar.gz -C /opt/worker
else
  echo "Worker code already deployed"
fi

echo "=== Downloading RDS CA bundle for DocumentDB TLS ==="
curl -sL https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem \
  -o /etc/ssl/certs/rds-combined-ca-bundle.pem

echo "=== Installing Python dependencies ==="
pip3.11 install -r /opt/worker/requirements.txt

echo "=== Setting up S3 Files filesystem ==="
# S3 Files creates a managed NFS endpoint backed by your S3 bucket.
# Your data stays in S3; the worker sees it as a regular filesystem.

# 1. Create the S3 Files filesystem (idempotent — skip if exists)
FS_ID=$(aws s3files list-file-systems \
  --bucket "${BUCKET_ARN}" \
  --query "fileSystems[0].fileSystemId" \
  --output text --region "${AWS_REGION}" 2>/dev/null || echo "None")

if [ -z "${FS_ID}" ] || [ "${FS_ID}" = "None" ]; then
  echo "Creating S3 Files filesystem for bucket: ${BUCKET_NAME}"
  FS_ID=$(aws s3files create-file-system \
    --bucket "${BUCKET_ARN}" \
    --role-arn "${S3FILES_ROLE_ARN}" \
    --region "${AWS_REGION}" \
    --query 'fileSystemId' \
    --output text)
  echo "Created filesystem: ${FS_ID}"
  # Wait for filesystem to become available
  echo "Waiting for filesystem to be available..."
  for i in $(seq 1 30); do
    FS_STATE=$(aws s3files get-file-system \
      --file-system-id "${FS_ID}" \
      --query "status" \
      --output text --region "${AWS_REGION}" 2>/dev/null || echo "CREATING")
    [ "${FS_STATE}" = "available" ] && break
    echo "  State: ${FS_STATE} (attempt $i/30)"
    sleep 10
  done
else
  echo "Using existing filesystem: ${FS_ID}"
fi

# 2. Create a mount target in the worker's subnet
MT_IP=$(aws s3files list-mount-targets \
  --file-system-id "${FS_ID}" \
  --query "mountTargets[?subnetId=='${SUBNET_ID}'].ipv4Address" \
  --output text --region "${AWS_REGION}" 2>/dev/null || echo "")

if [ -z "${MT_IP}" ] || [ "${MT_IP}" = "None" ]; then
  echo "Creating mount target in subnet ${SUBNET_ID}"
  MT_IP=$(aws s3files create-mount-target \
    --file-system-id "${FS_ID}" \
    --subnet-id "${SUBNET_ID}" \
    --security-groups "${SECURITY_GROUP_ID}" \
    --region "${AWS_REGION}" \
    --query 'ipv4Address' \
    --output text)
  echo "Mount target IP: ${MT_IP}"

  # Wait for mount target to become available
  echo "Waiting for mount target to be available..."
  for i in $(seq 1 60); do
    STATE=$(aws s3files list-mount-targets \
      --file-system-id "${FS_ID}" \
      --query "mountTargets[0].status" \
      --output text --region "${AWS_REGION}")
    [ "${STATE}" = "available" ] && break
    echo "  State: ${STATE} (attempt $i/60)"
    sleep 10
  done
else
  echo "Using existing mount target: ${MT_IP}"
fi

# 3. Mount via S3 Files mount helper
echo "=== Mounting S3 Files at ${MOUNT_PATH} ==="
mkdir -p "${MOUNT_PATH}"
mount -t s3files "${FS_ID}":/ "${MOUNT_PATH}"

# Persist across reboots
FSTAB_ENTRY="${FS_ID}:/ ${MOUNT_PATH} s3files _netdev 0 0"
grep -qF "${FS_ID}" /etc/fstab || echo "${FSTAB_ENTRY}" >> /etc/fstab

echo "Mount successful: $(df -h ${MOUNT_PATH})"

# 4. Start the worker service
echo "=== Starting maw-worker service ==="
systemctl daemon-reload
systemctl enable maw-worker
systemctl restart maw-worker
systemctl status maw-worker

echo "=== Setup complete ==="
echo "S3 Files filesystem: ${FS_ID}"
echo "Mount target IP:     ${MT_IP}"
echo "Mount path:          ${MOUNT_PATH}"
echo "Worker service:      systemctl status maw-worker"
echo ""
df -h "${MOUNT_PATH}"
echo ""
ls "${MOUNT_PATH}"
