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
RP_HOSTNAME = app.config('RP_HOSTNAME')
INCOMING_QUEUE = app.config('INCOMING_QUEUE')

# Basic test data.
json_data = json.dumps([1,2,3,{'4': 5, '6': 7}], separators=(',', ':'))

class TestRegisterPublisher(unittest.TestCase):

    def setUp(self):
        """ Ensure that message broker is alive """

        connection, channel = server.setup_connection()
        self.connection = connection
        self.channel = channel

        self.assertEqual(self.connection.connected, True)

    # Send message from dummy "System Of Record", then consume and check it.
    def test_End_To_End(self):
        incoming_exchange = server.incoming_exchange
        incoming_queue = server.incoming_queue
        outgoing_exchange = server.outgoing_exchange

        channel = self.channel

        # Send a message to 'incoming' exchange - i.e. as if from SoR.
        producer = server.setup_producer(channel, exchange=incoming_exchange)

        producer.publish(payload=json_data)

        # Wait a bit - one second should be long enough.
        time.sleep(1)

        # Consume (poll) message from outgoing exchange.
        queue = Queue(name="outgoing_queue", exchange=outgoing_exchange)
        message = queue.get(no_ack=True, accept=['json'])

        self.assertEqual(message, json_data)

    def tearDown(self):
        self.connection.close()

if __name__ == '__main__':
    unittest.main()
