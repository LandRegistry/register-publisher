# All this module does is create a test queue connect to a direct and fanout exchange.

import kombu
import flask
import os

os.environ['SETTINGS'] = "config.DevelopmentConfig"

app = flask.Flask(__name__)
app.config.from_object(os.environ.get('SETTINGS'))

direct_exchange = kombu.Exchange(type="direct")
fanout_exchange = kombu.Exchange(type="topic", name="amq.fanout")

connection = kombu.Connection(app.config['OUTGOING_QUEUE_HOSTNAME'])

queue = kombu.Queue('test_queue', direct_exchange, routing_key='test_queue')(connection)
queue.declare()
queue.bind_to(fanout_exchange, '#')

message = queue.get()
if message:
    print('ok')

