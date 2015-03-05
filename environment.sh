#!/bin/sh

# Receive messages from "System Of Record" via default 'direct' exchange.
# Publish to temporary queues - as specified by (unknown) clients - via default 'fanout' exchange.
export SETTINGS="config.DevelopmentConfig"
export RP_HOSTNAME="amqp://guest:guest@localhost:5672//"
export INCOMING_QUEUE="system_of_record"
export OUTGOING_QUEUE="feeder"

# The following are not used, for now.
export RP_INCOMING_EXCHG_NAME=""
export RP_INCOMING_EXCHG_TYPE="direct"
export RP_OUTGOING_EXCHG_NAME=""                # Must be named if of type 'direct'
export RP_OUTGOING_EXCHG_TYPE="fanout"
