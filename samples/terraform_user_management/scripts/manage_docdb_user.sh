#!/bin/bash
set -e

# Script: manage_docdb_user.sh
# Manages DocumentDB users (create/delete) with proper role management
# Required environment variables:
#   DOCDB_HOST - DocumentDB cluster endpoint
#   DOCDB_PORT - DocumentDB port (usually 27017)
#   DOCDB_USER - Admin username
#   DOCDB_PASSWORD - Admin password
#   USERNAME - User to create/delete
#   ACTION - Operation to perform (create/delete)
#   USER_PASSWORD - Password for new user (required for create)
#   ROLES - JSON array of roles (required for create)
#
# Ensure script is executable:
# chmod 755 manage_docdb_user.sh

# Define log file location with secure permissions
LOG_DIR="/tmp/docdb_user_management"
LOG_FILE="${LOG_DIR}/user_operations.log"
OPERATION_ID=$(uuidgen || date +%s)

setup_logging() {
  mkdir -p "${LOG_DIR}"
  touch "${LOG_FILE}"
  chmod 600 "${LOG_FILE}"
  chmod 700 "${LOG_DIR}"
}

log() {
  local level="INFO"
  if [ "$#" -gt 1 ]; then
    level="$1"
    shift
  fi
  local timestamp=$(date +'%Y-%m-%d %H:%M:%S')
  local message="[${timestamp}] [${level}] [OP:${OPERATION_ID}] $1"
  
  echo "${message}"
  echo "${message}" >> "${LOG_FILE}"
}

setup_logging

error_exit() {
  local message="$1"
  local exit_code=1
  
  if [ "$#" -gt 1 ]; then
    exit_code="$2"
  fi
  
  log "ERROR" "${message}"
  exit "${exit_code}"
}

validate_env() {
  local required_vars=("DOCDB_HOST" "DOCDB_PORT" "DOCDB_USER" "USERNAME" "ACTION")
  
  for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
      error_exit "Required environment variable ${var} is not set" 2
    fi
  done
  
  if [ "${ACTION}" == "create" ] && [ -z "${USER_PASSWORD}" ]; then
    error_exit "USER_PASSWORD is required for create operations" 3
  fi
  
  if [ "${ACTION}" == "create" ] && [ -z "${ROLES}" ]; then
    error_exit "ROLES are required for create operations" 4
  fi
  
  log "Environment validation completed"
}

check_prerequisites() {
  log "Checking prerequisites..."
  
  command -v mongosh >/dev/null 2>&1 || error_exit "mongosh is required but not installed" 5
  
  if [ ! -f global-bundle.pem ]; then
    error_exit "SSL certificate not found" 6
  fi
  
  if ! grep -q "BEGIN CERTIFICATE" global-bundle.pem; then
    error_exit "Invalid SSL certificate" 7
  fi
  
  log "Prerequisites verified"
}

test_connection() {
  local masked_host="${DOCDB_HOST%%.*}*****"
  log "Testing database connection to ${masked_host}:${DOCDB_PORT}..."
  
  if ! mongosh --host $DOCDB_HOST:$DOCDB_PORT \
    --username $DOCDB_USER \
    --password $DOCDB_PASSWORD \
    --tls \
    --tlsCAFile global-bundle.pem \
    --authenticationMechanism SCRAM-SHA-1 \
    --eval "db.adminCommand('ping')" &>/dev/null; then
    error_exit "Database connection failed" 8
  fi
  
  log "Database connection successful"
}

check_user_exists() {
  local log_tmp="/tmp/user_check_$$.log"
  
  log "Verifying user existence..." >> "${log_tmp}"
  
  local result=$(mongosh --host $DOCDB_HOST:$DOCDB_PORT \
    --username $DOCDB_USER \
    --password $DOCDB_PASSWORD \
    --tls \
    --tlsCAFile global-bundle.pem \
    --authenticationMechanism SCRAM-SHA-1 \
    --quiet \
    --eval 'try { 
      const user = db.getSiblingDB("admin").getUser("'"${USERNAME}"'");
      if (user && user.user === "'"${USERNAME}"'") {
        print("true");
      } else {
        print("false");
      }
    } catch(e) { 
      print("false");
    }' 2>/dev/null || echo "false")
  
  cat "${log_tmp}" >> "${LOG_FILE}"
  rm -f "${log_tmp}"
  
  echo "${result}" | tr -d '[:space:]'
}

manage_user() {
  local user_exists=$(check_user_exists)
  
  if [ "${user_exists}" = "true" ]; then
    log "Updating existing user roles..."
    
    mongosh --host $DOCDB_HOST:$DOCDB_PORT \
      --username $DOCDB_USER \
      --password $DOCDB_PASSWORD \
      --tls \
      --tlsCAFile global-bundle.pem \
      --authenticationMechanism SCRAM-SHA-1 \
      --eval 'db.getSiblingDB("admin").updateUser("'"${USERNAME}"'", {
        roles: '"${ROLES}"'
      })'
      
    log "Role update completed successfully"
  else
    log "Creating new user..."
    mongosh --host $DOCDB_HOST:$DOCDB_PORT \
      --username $DOCDB_USER \
      --password $DOCDB_PASSWORD \
      --tls \
      --tlsCAFile global-bundle.pem \
      --authenticationMechanism SCRAM-SHA-1 \
      --eval 'db.getSiblingDB("admin").createUser({
        user: "'"${USERNAME}"'",
        pwd: "'"${USER_PASSWORD}"'",
        roles: '"${ROLES}"'
      })'
      
    log "User creation completed successfully"
  fi
}

delete_user() {
  log "Initiating user deletion process..."
  
  local user_exists=$(check_user_exists)
  
  if [ "${user_exists}" = "true" ]; then
    log "Executing deletion..."
    
    local delete_result=$(mongosh --host $DOCDB_HOST:$DOCDB_PORT \
      --username $DOCDB_USER \
      --password $DOCDB_PASSWORD \
      --tls \
      --tlsCAFile global-bundle.pem \
      --authenticationMechanism SCRAM-SHA-1 \
      --quiet \
      --eval 'try { 
        const result = db.getSiblingDB("admin").dropUser("'"${USERNAME}"'");
        if (result.ok === 1) {
          print("success");
        } else {
          print("failed: " + JSON.stringify(result));
          quit(1);
        }
      } catch(e) { 
        print("error: " + e.message); 
        quit(1); 
      }' 2>/dev/null)
    
    if [ "${delete_result}" != "success" ]; then
      error_exit "Failed to delete user" 11
    fi
    
    if [ "$(check_user_exists)" = "true" ]; then
      error_exit "User still exists after deletion attempt" 11
    fi
    
    log "Deletion completed successfully"
  else
    log "WARN" "No deletion needed - user does not exist"
  fi
}

main() {
  log "Starting operation ${OPERATION_ID}"
  validate_env
  check_prerequisites
  test_connection
  
  case "${ACTION}" in
    create)
      manage_user
      ;;
    delete)
      delete_user
      ;;
    *)
      error_exit "Invalid ACTION specified" 12
      ;;
  esac
  
  log "Operation ${OPERATION_ID} completed successfully"
}

main