#!/bin/python

import os


class Config(object):
    DEBUG = False

    # Logging parameters.
    LOG_THRESHOLD_LEVEL = os.getenv('LOG_THRESHOLD_LEVEL', 'ERROR')                 # Base threshold logging level.

    # AMQP parameters.
    RP_HOSTNAME = os.getenv('RP_HOSTNAME', "amqp://guest:guest@localhost:5672//")   # RabbitMQ IP address
    INCOMING_QUEUE = os.getenv('INCOMING_QUEUE', 'INCOMING_QUEUE')                  # SOR to RP queue name
    OUTGOING_QUEUE = os.getenv('OUTGOING_QUEUE', 'OUTGOING_QUEUE')                  # Default outgoing queue name

class DevelopmentConfig(Config):
    DEBUG = True
    LOG_THRESHOLD_LEVEL = os.getenv('LOG_THRESHOLD_LEVEL', 'DEBUG')

class TestConfig(Config):
    DEBUG = False
    LOG_THRESHOLD_LEVEL = os.getenv('LOG_THRESHOLD_LEVEL', 'INFO')

class PreviewConfig(Config):
    DEBUG = True
    LOG_THRESHOLD_LEVEL = os.getenv('LOG_THRESHOLD_LEVEL', 'INFO')

class PreProductionConfig(Config):
    LOG_THRESHOLD_LEVEL = os.getenv('LOG_THRESHOLD_LEVEL', 'INFO')

class ProductionConfig(Config):
    LOG_THRESHOLD_LEVEL = os.getenv('LOG_THRESHOLD_LEVEL', 'INFO')
