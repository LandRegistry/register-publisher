#!/bin/python

import os

class Config(object):
    DEBUG = False
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'ERROR')
    INCOMING_QUEUE_HOSTNAME = os.getenv('INCOMING_QUEUE_HOSTNAME', "amqp://guest:guest@localhost:5672//")   # RabbitMQ IP address
    OUTGOING_QUEUE_HOSTNAME = os.getenv('OUTGOING_QUEUE_HOSTNAME', "amqp://guest:guest@localhost:5672//")   # RabbitMQ IP address
    INCOMING_QUEUE = os.getenv('INCOMING_QUEUE', 'INCOMING_QUEUE')                  # SOR to RP queue name
    OUTGOING_QUEUE = os.getenv('OUTGOING_QUEUE', 'OUTGOING_QUEUE')                  # Default outgoing queue name

class DevelopmentConfig(Config):
    DEBUG = True
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG')

class PreviewConfig(Config):
    DEBUG = True
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

class PreProductionConfig(Config):
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

class ProductionConfig(Config):
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
