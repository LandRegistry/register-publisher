#!/bin/python

import os


class Config(object):
    """ Get parameters from environment, or defaults if not specified. """

    # Flask DEBUG setting - not used.
    DEBUG = False

    # Logging.
    LOG_THRESHOLD_LEVEL = os.getenv('LOG_THRESHOLD_LEVEL', 'ERROR')                 # Base threshold logging level.

    # AMQP.
    RP_HOSTNAME = os.getenv('RP_HOSTNAME', "amqp://guest:guest@localhost:5672//")   # RabbitMQ IP address
    INCOMING_QUEUE = os.getenv('INCOMING_QUEUE', 'INCOMING_QUEUE')                  # SOR to RP queue name
    OUTGOING_QUEUE = os.getenv('OUTGOING_QUEUE', 'OUTGOING_QUEUE')                  # Default outgoing queue name

    # Kombu.
    MAX_RETRIES = os.getenv('MAX_RETRIES', 10)                                      # # Maximum 'ensure' limit.

class DevelopmentConfig(Config):
    LOG_THRESHOLD_LEVEL = os.getenv('LOG_THRESHOLD_LEVEL', 'DEBUG')

class TestConfig(Config):
    LOG_THRESHOLD_LEVEL = os.getenv('LOG_THRESHOLD_LEVEL', 'INFO')

class PreviewConfig(Config):
    LOG_THRESHOLD_LEVEL = os.getenv('LOG_THRESHOLD_LEVEL', 'INFO')

class PreProductionConfig(Config):
    LOG_THRESHOLD_LEVEL = os.getenv('LOG_THRESHOLD_LEVEL', 'INFO')

class ProductionConfig(Config):
    LOG_THRESHOLD_LEVEL = os.getenv('LOG_THRESHOLD_LEVEL', 'INFO')
