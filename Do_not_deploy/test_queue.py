# All this module does is create a test queue connect to a direct and fanout exchange.

import kombu
import flask
import os

os.environ['SETTINGS'] = "config.DevelopmentConfig"

app = flask.Flask(__name__)
app.config.from_object(os.environ.get('SETTINGS'))

topic_exchange = kombu.Exchange(type="topic", name="amq.topic")

connection = kombu.Connection(app.config['OUTGOING_QUEUE_HOSTNAME'])

queue = kombu.Queue('test_queue_1', topic_exchange, routing_key='test_queue_1')(connection)
queue.declare()

queue = kombu.Queue('test_queue_2', topic_exchange, routing_key='test_queue_2')(connection)
queue.declare()

queue = kombu.Queue('test_queue_3', topic_exchange, routing_key='test_queue_3')(connection)
queue.declare()

queue = kombu.Queue('test_queue_4', topic_exchange, routing_key='test_queue_4')(connection)
queue.declare()


message = queue.get()
if message:
    print('ok')

