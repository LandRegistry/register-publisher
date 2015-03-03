#!/bin/bash

dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $dir

virtualenv -p python3 ~/venvs/register-publisher
source ~/venvs/register-publisher/bin/activate

pip install -r requirements.txt

#Set environment variable in supervisord according to deploying environment (default to development)
case "$DEPLOY_ENVIRONMENT" in
  development)
  SETTINGS="config.DevelopmentConfig"
  ;;
  test)
  SETTINGS="config.PreviewConfig"
  ;;
  preproduction)
  SETTINGS="config.PreproductionConfig"
  ;;
  production)
  SETTINGS="config.ProductionConfig"
  ;;
  *)
  SETTINGS="config.DevelopmentConfig"
  ;;
esac

echo "Adding register-publisherto supervisord..."
cat > /etc/supervisord.d/register-publisher.ini << EOF
[program:registerpublisher]
command=$HOME/venvs/register-publisher/bin/python run.py
directory=$dir
autostart=true
autorestart=true
user=$USER
environment=SETTINGS="$SETTINGS",INCOMING_QUEUE="system_of_record"
EOF
