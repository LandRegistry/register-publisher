#!/bin/python
import os
import json
import unittest
import time
import datetime
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
logger = server.setup_logger(__name__)

# Basic test data.
def make_message():
    dt=str(datetime.datetime.now())
    return json.dumps(dt.split())


class TestRegisterPublisher(unittest.TestCase):

    def setUp(self):
        """ Establish connection and other resources """

        # Ensure that message broker is alive
        with server.setup_connection() as connection:
            self.assertEqual(connection.connected, True)

        self.message = make_message()


    @unittest.skip("Not wanted")
    def test_simple_queue(self):
        """ Basic check of message send/get via 'simple' interface """

        with server.setup_connection() as connection:
            with connection.SimpleQueue('simple_queue') as queue:
                queue.put(self.message)
                logger.info("Sent message: {}".format(self.message))

        # Wait a bit - one second should be long enough.
        time.sleep(1)

        with server.setup_connection() as connection:
            with connection.SimpleQueue('simple_queue') as queue:
                message = queue.get(block=True, timeout=1)
                logger.info("Received: {}".format(message.payload))
                message.ack()

        self.assertEqual(self.message, message.payload)


    def test_incoming_queue(self):
        """ Basic check of 'incoming' message via default direct exchange """

        exchange = server.incoming_exchange
        queue_name = server.INCOMING_QUEUE

        with server.setup_connection() as connection:
            producer, queue = server.setup_producer(connection, exchange=exchange, queue_name=queue_name)
            producer.publish(body=self.message,routing_key=queue.routing_key)

        with server.setup_connection() as connection:
            consumer, queue = server.setup_consumer(connection, exchange=exchange, queue_name=queue_name)

            #: This can be the callback applied when a message is received.
            def handle_message(body, message):
                logger.info('Received message: {}'.format(body))
                logger.info(' properties: {}'.format(message.properties))
                logger.info(' delivery_info: {}'.format(message.delivery_info))
                message.ack()

            message = queue.get()

            queue.delete()

            if message:
                handle_message(message.body, message)
                self.assertEqual(self.message, message.payload)
            else:
                self.fail("No message received")

    # Send message from dummy "System Of Record", then consume and check it.
    @unittest.skip("Not ready")
    def test_end_to_end(self):

        json_data = make_message()

        # Send a message to 'incoming' exchange - i.e. as if from SoR.
        with server.setup_connection() as connection:
            producer = server.setup_producer(connection, exchange=server.incoming_exchange)
            producer.publish(body=json_data)
            logger.info(json_data)

        # Wait a bit - one second should be long enough.
        time.sleep(1)

        # Consume (poll) message from outgoing exchange.
        queue = server.setup_queue(self.connection, name="outgoing_queue", exchange=server.outgoing_exchange)
        message = queue.get(no_ack=True, accept=['json'])

        assert message.body == json_data
