#!/bin/bash
set -e

# Script: download_cert.sh
# Downloads the Amazon DocumentDB certificate bundle (global-bundle.pem)
# Ensure script is executable:
# chmod 755 downloadcert.sh

log() {
  local level="INFO"
  if [ "$#" -gt 1 ]; then
    level="$1"
    shift
  fi
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] [${level}] $1"
}

error_exit() {
  log "ERROR" "$1"
  exit 1
}

log "Downloading Amazon DocumentDB certificate..."

# Check if curl is installed
command -v curl >/dev/null 2>&1 || error_exit "curl is required but not installed"

CERT_URL="https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem"
CERT_FILE="global-bundle.pem"

MAX_RETRIES=3
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
  if curl -s -f -o "${CERT_FILE}" "${CERT_URL}"; then
    break
  else
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
      log "WARN" "Download attempt ${RETRY_COUNT} failed. Retrying in 5 seconds..."
      sleep 5
    else
      error_exit "Failed to download certificate after ${MAX_RETRIES} attempts"
    fi
  fi
done

# Verify the certificate was downloaded correctly
if [ ! -s "${CERT_FILE}" ]; then
  error_exit "Downloaded certificate file is empty"
fi

if ! grep -q "BEGIN CERTIFICATE" "${CERT_FILE}"; then
  error_exit "Downloaded file does not appear to be a valid certificate"
fi

# Set appropriate permissions
chmod 644 "${CERT_FILE}"

log "Certificate bundle downloaded and verified"