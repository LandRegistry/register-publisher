#!/bin/sh

export SETTINGS="config.TestConfig"

if [ -z "${INCOMING_QUEUE_HOSTNAME}" ]; then
  export INCOMING_QUEUE_HOSTNAME="amqp://guest:guest@localhost:5672//"
fi

if [ -z "${OUTGOING_QUEUE_HOSTNAME}" ]; then
  export OUTGOING_QUEUE_HOSTNAME="amqp://guest:guest@localhost:5672//"
fi

if [ -z "${INCOMING_QUEUE}" ]; then
  export INCOMING_QUEUE="INCOMING_QUEUE"
fi

if [ -z "${OUTGOING_QUEUE}" ]; then
  export OUTGOING_QUEUE="OUTGOING_QUEUE"
fi
