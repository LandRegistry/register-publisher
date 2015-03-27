#!/bin/sh

# Receive messages from "System Of Record" via default 'direct' exchange.
# Publish to temporary queues - as specified by (unknown) clients - via default 'fanout' exchange.
export SETTINGS="config.DevelopmentConfig"
