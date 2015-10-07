    #!/bin/python

import os
import kombu
from collections import namedtuple

class Config(object):
    """ Get parameters from environment, or defaults if not specified. """

    # Flask DEBUG setting - not used.
    DEBUG = False
    OUTGOING_QUEUE_HOSTNAME = os.getenv('OUTGOING_QUEUE_HOSTNAME', "amqp://mqpublisher:mqpublisherpassword@localhost:5672/")   # RabbitMQ IP address


class DevelopmentConfig(Config):
    LOG_THRESHOLD_LEVEL = os.getenv('LOG_THRESHOLD_LEVEL', 'DEBUG')
