import os

class Config(object):
    DEBUG = False
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'ERROR')
    RP_HOSTNAME = os.getenv('RP_HOSTNAME', "amqp://guest:guest@localhost:5672//")   # RabbitMQ IP address
    SOR_TO_RP_QUEUE = os.getenv('SOR_TO_RP_QUEUE', 'SOR_TO_RP_QUEUE')                   # SOR to RP queue name

class DevelopmentConfig(Config):
    DEBUG = True
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG')

class TestConfig(Config):
    DEBUG = True
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
