#!/bin/bash

: "${AWS_ACCESS_KEY_ID:?Need to set AWS_ACCESS_KEY_ID non-empty}"
: "${AWS_SECRET_ACCESS_KEY:?Need to set AWS_SECRET_ACCESS_KEY non-empty}"
: "${AWS_DEFAULT_REGION:?Need to set AWS_DEFAULT_REGION non-empty}"

CONTAINER_NAME=run_shell_documentdb_lambda_layers_python

trap "docker-compose -f docker-compose.yml rm --force $CONTAINER_NAME" SIGINT SIGTERM
docker-compose -f docker-compose.yml build --no-cache $CONTAINER_NAME && \
  docker-compose -f docker-compose.yml up $CONTAINER_NAME
docker-compose -f docker-compose.yml rm --force $CONTAINER_NAME
