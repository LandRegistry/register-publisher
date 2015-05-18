#!/bin/bash

dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $dir
source ~/venvs/register-publisher/bin/activate

#Set environment variable in supervisord according to deploying environment (default to development)
case "$DEPLOY_ENVIRONMENT" in
  development)
  SUPERVISOR_ENV="SETTINGS=\"config.DevelopmentConfig\""
  ;;
  preview)
  SUPERVISOR_ENV="SETTINGS=\"config.PreviewConfig\""
  ;;
  release)
  SUPERVISOR_ENV="SETTINGS=\"config.ReleaseConfig\""
  ;;
  preproduction)
  SUPERVISOR_ENV="SETTINGS=\"config.PreProductionConfig\""
  ;;
  production)
  SUPERVISOR_ENV="SETTINGS=\"config.ProductionConfig\""
  ;;
  *)
  SUPERVISOR_ENV="SETTINGS=\"config.DevelopmentConfig\""
  ;;
esac

if [ -n "$INCOMING_QUEUE_HOSTNAME" ]; then
  SUPERVISOR_ENV="$SUPERVISOR_ENV,INCOMING_QUEUE_HOSTNAME=\"$INCOMING_QUEUE_HOSTNAME\""
fi

if [ -n "$INCOMING_QUEUE" ]; then
  SUPERVISOR_ENV="$SUPERVISOR_ENV,INCOMING_QUEUE=\"$INCOMING_QUEUE\""
fi

if [ -n "$OUTGOING_QUEUE_HOSTNAME" ]; then
  SUPERVISOR_ENV="$SUPERVISOR_ENV,OUTGOING_QUEUE_HOSTNAME=\"$OUTGOING_QUEUE_HOSTNAME\""
fi

if [ -n "$OUTGOING_QUEUE" ]; then
  SUPERVISOR_ENV="$SUPERVISOR_ENV,OUTGOING_QUEUE=\"$OUTGOING_QUEUE\""
fi

echo "Adding register-publisher to supervisord..."
cat > /etc/supervisord.d/register-publisher.ini << EOF
[program:registerpublisher]
command=$HOME/venvs/register-publisher/bin/python run.py
directory=$dir
autostart=true
autorestart=true
user=$USER
environment=$SUPERVISOR_ENV
stopasgroup=true
EOF
