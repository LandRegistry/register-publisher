#!/bin/bash

dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $dir

virtualenv -p python3 ~/venvs/register-publisher
source ~/venvs/register-publisher/bin/activate

pip install -r requirements.txt

#Set environment variable in supervisord according to deploying environment (default to development)
case "$DEPLOY_ENVIRONMENT" in
  development)
  SUPERVISOR_ENV="SETTINGS=\"config.DevelopmentConfig\""
  ;;
  test)
  SUPERVISOR_ENV="SETTINGS=\"config.PreviewConfig\""
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

INCOMING_QUEUE_HOSTNAME="amqp://mqsor:mqsorpassword@localhost:5672/"
INCOMING_QUEUE="system_of_record"
OUTGOING_QUEUE_HOSTNAME="amqp://mqsor:mqsorpassword@192.168.39.22:5672/"
OUTGOING_QUEUE="OUTGOING_QUEUE"

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

echo "Adding register-publisherto supervisord..."
cat > /etc/supervisord.d/register-publisher.ini << EOF
[program:registerpublisher]
command=$HOME/venvs/register-publisher/bin/python run.py
directory=$dir
autostart=true
autorestart=true
user=$USER
environment=$SUPERVISOR_ENV
EOF
