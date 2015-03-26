#!/bin/sh

# Receive messages from "System Of Record" via default 'direct' exchange.
# Publish to temporary queues - as specified by (unknown) clients - via default 'fanout' exchange.
export SETTINGS="config.DevelopmentConfig"
export INCOMING_QUEUE_HOSTNAME="amqp://guest:guest@localhost:5672//"
export INCOMING_QUEUE="system_of_record"
export OUTGOING_QUEUE_HOSTNAME="amqp://guest:guest@localhost:5672//"
export OUTGOING_QUEUE="register_publisher"
