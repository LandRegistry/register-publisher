import os
import pwd
from application import app
import yaml


#Exceptions are handled silently, so logging doesn't impair the app.

def linux_user():
    try:
        return pwd.getpwuid(os.geteuid()).pw_name
    except Exception as err:
        return "failed to get user: %s" % err


def client_ip(request):
    try:
        return request.remote_addr
    except Exception as err:
        return "failed to get client ip: %s" % err


def log_dir(log_type):
    try:
        path = app.config['LOGGING_PATH']
        if os.path.exists(path):
            with open(path, 'rt') as f:
                config = yaml.load(f.read())
                return config['handlers'][log_type + '_file_handler']['filename']
    except Exception as err:
        return "failed to get log path: %s" % err