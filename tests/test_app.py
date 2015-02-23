#!/bin/python
import os
import json
import unittest
import time
from application import server
from flask import Flask
from kombu.log import get_logger
from kombu.utils.debug import setup_logging

"""
Test Register-Publisher on an 'ad hoc' basis or automatically (pytest).
Pretend to be "System Of Record" publisher.
"""

# Flask is used here purely for configuration purposes.
app = Flask(__name__)
app.config.from_object(os.environ.get('SETTINGS'))

# Set up root logger
ll = app.config['LOG_LEVEL']
setup_logging(loglevel=ll, loggers=[''])
logger = get_logger(__name__)

# Basic test data.
json_data = json.dumps([1,2,3,{'4': 5, '6': 7}], separators=(',', ':'))

class TestRegisterPublisher(unittest.TestCase):

    def setUp(self):
        """ Establish connection and other resources """

        # Ensure that message broker is alive
        connection = server.setup_connection()
        self.assertEqual(connection.connected, True)

        self.connection = connection

    # Send message from dummy "System Of Record", then consume and check it.
    def test_end_to_end(self):

        # Send a message to 'incoming' exchange - i.e. as if from SoR.
        producer = server.setup_producer(self.connection, exchange=server.incoming_exchange)
        producer.publish(body=json_data)

        logger.info("TEST - producer(): {}".format(len(json_data)))

        # Wait a bit - one second should be long enough.
        time.sleep(1)

        # Consume (poll) message from outgoing exchange.
        queue = server.setup_queue(self.connection, name="outgoing_queue", exchange=server.outgoing_exchange)
        message = queue.get(no_ack=True, accept=['json'])

        assert message.body == json_data

    def tearDown(self):
        self.connection.close()
