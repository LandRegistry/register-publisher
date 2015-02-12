import os

class Config(object):
    DEBUG = False
    SYSTEM_OF_RECORD = os.environ['SYSTEM_OF_RECORD']

class DevelopmentConfig(Config):
    DEBUG = True

class TestConfig(Config):
    DEBUG = True
