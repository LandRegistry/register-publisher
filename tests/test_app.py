#!/bin/python
import os
import json
import unittest
import time
from application import server
from flask import Flask
from kombu import Exchange, Queue, Connection, Consumer, Producer
from kombu.common import maybe_declare

"""
Test Register-Publisher on an 'ad hoc' basis or automatically (pytest).
Pretend to be "System Of Record" publisher.
"""

# Flask is used here purely for configuration purposes.
app = Flask(__name__)
app.config.from_object(os.environ.get('SETTINGS'))

# Set up root logger
ll = app.config['LOG_LEVEL']

# Basic test data.
json_data = json.dumps([1,2,3,{'4': 5, '6': 7}], separators=(',', ':'))

class TestRegisterPublisher(unittest.TestCase):

    def setUp(self):
        """ Establish connection and other resources """

        # Ensure that message broker is alive
        connection, channel = server.setup_connection()
        self.connection = connection

        self.assertEqual(self.connection.connected, True)

        self.producer = server.setup_producer(channel, exchange=server.incoming_exchange)

    # Send message from dummy "System Of Record", then consume and check it.
    def test_end_to_end(self):

        # Send a message to 'incoming' exchange - i.e. as if from SoR.
        self.producer.publish(payload=json_data)

        # Wait a bit - one second should be long enough.
        time.sleep(1)

        # Consume (poll) message from outgoing exchange.
        queue = Queue(name="outgoing_queue", exchange=server.outgoing_exchange)
        message = queue.get(no_ack=True, accept=['json'])

        assert message.body == json_data

    def tearDown(self):
        self.connection.close()
        self.producer.close()
