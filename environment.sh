#!/bin/sh

# Receive messages from "System Of Record" via default 'direct' exchange.
# Publish to temporary queues - as specified by (unknown) clients - via default 'fanout' exchange.

export SETTINGS="config.DevelopmentConfig"

# The following are not used, for now.
export RP_INCOMING_EXCHG_NAME=""
export RP_INCOMING_EXCHG_TYPE="direct"
export RP_OUTGOING_EXCHG_NAME=""                # Must be named if of type 'direct'
export RP_OUTGOING_EXCHG_TYPE="fanout"
