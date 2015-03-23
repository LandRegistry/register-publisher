#!/bin/python

import os


class Config(object):
    """ Get parameters from environment, or defaults if not specified. """

    # Flask DEBUG setting - not used.
    DEBUG = False

    # Logging.
    LOG_THRESHOLD_LEVEL = os.getenv('LOG_THRESHOLD_LEVEL', 'ERROR')                 # Base threshold logging level.

    # Kombu.
    MAX_RETRIES = os.getenv('MAX_RETRIES', 10)                                      # # Maximum 'ensure' limit.

    INCOMING_QUEUE_HOSTNAME = os.getenv('INCOMING_QUEUE_HOSTNAME', "amqp://mqpublisher:mqpublisherpassword@localhost:5672/")   # RabbitMQ IP address
    OUTGOING_QUEUE_HOSTNAME = os.getenv('OUTGOING_QUEUE_HOSTNAME', "amqp://mqpublisher:mqpublisherpassword@localhost:5672/")   # RabbitMQ IP address
    INCOMING_QUEUE = os.getenv('INCOMING_QUEUE', 'system_of_record')                  # SOR to RP queue name
    OUTGOING_QUEUE = os.getenv('OUTGOING_QUEUE', 'register_publisher')                  # Default outgoing queue name
    
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
