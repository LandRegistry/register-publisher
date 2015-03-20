#!/bin/python

import os
import kombu
from collections import namedtuple

class Config(object):
    """ Get parameters from environment, or defaults if not specified. """

    # Flask DEBUG setting - not used.
    DEBUG = False

    # Logging.
    LOG_THRESHOLD_LEVEL = os.getenv('LOG_THRESHOLD_LEVEL', 'ERROR')                 # Base threshold logging level.

    # AMQP.
    default_hostname = "amqp://guest:guest@localhost:5672//"
    INCOMING_QUEUE_HOSTNAME = os.getenv('INCOMING_QUEUE_HOSTNAME', default_hostname)# RabbitMQ IP address
    OUTGOING_QUEUE_HOSTNAME = os.getenv('OUTGOING_QUEUE_HOSTNAME', default_hostname)# RabbitMQ IP address
    INCOMING_QUEUE = os.getenv('INCOMING_QUEUE', 'INCOMING_QUEUE')                  # SOR to RP queue name
    OUTGOING_QUEUE = os.getenv('OUTGOING_QUEUE', 'OUTGOING_QUEUE')                  # Default outgoing queue name

    # RabbitMQ Exchange default values:
    #   delivery_mode: '2' (persistent messages)
    #   durable: True (exchange remains 'active' on server re-start)
    INCOMING_EXCHANGE = kombu.Exchange(type="direct")
    OUTGOING_EXCHANGE = kombu.Exchange(type="fanout")

    # Collections
    Configuration = namedtuple("Configuration", ['hostname', 'exchange', 'queue'])
    INCOMING_CFG = Configuration(hostname=INCOMING_QUEUE_HOSTNAME, exchange=INCOMING_EXCHANGE, queue=INCOMING_QUEUE)
    OUTGOING_CFG = Configuration(hostname=OUTGOING_QUEUE_HOSTNAME, exchange=OUTGOING_EXCHANGE, queue=OUTGOING_QUEUE)

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
