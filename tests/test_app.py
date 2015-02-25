#!/bin/python
import os
import json
import unittest
import time
import datetime
from multiprocessing import Process
from application import server
from flask import Flask

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

#: This can be the callback applied when a message is received - i.e. "consume()" case.
def handle_message(body, message):
    logger.info('Received message: {}'.format(body))
    logger.info(' properties: {}'.format(message.properties))
    logger.info(' delivery_info: {}'.format(message.delivery_info))
    message.ack()


class TestRegisterPublisher(unittest.TestCase):

    def setUp(self):
        """ Establish connection and other resources; prepare """

        with server.setup_connection() as connection:

            # Ensure that message broker is alive
            self.assertEqual(connection.connected, True)

            queue = server.setup_queue(connection, name=server.INCOMING_QUEUE, exchange=server.incoming_exchange)
            queue.purge()

            queue = server.setup_queue(connection, name=server.OUTGOING_QUEUE, exchange=server.outgoing_exchange)
            queue.purge()

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


    @unittest.skip("Ignore")
    def test_incoming_queue(self):
        """ Basic check of 'incoming' message via default direct exchange """

        exchange = server.incoming_exchange
        queue_name = server.INCOMING_QUEUE

        with server.setup_connection() as connection:
            producer = server.setup_producer(connection, exchange=exchange)
            producer.publish(body=self.message, routing_key=queue_name)
            logger.info("Put message, exchange: {}, {}".format(self.message, exchange))

       # Wait a bit - one second should be long enough.
        time.sleep(1)

        with server.setup_connection() as connection:
            consumer = server.setup_consumer(connection, exchange=exchange, queue_name=queue_name)
            queue = consumer.queues[0]
            message = queue.get()
            logger.info("Got message, queue: {}, {}".format(message.body, queue.name))

            queue.delete()

            if message:
                handle_message(message.body, message)
                self.assertEqual(self.message, message.payload)
            else:
                self.fail("No message received")


    # N.B.: this test reverses the default 'producer' and 'consumer' targets.
    def test_end_to_end(self):
        """ Send message from dummy "System Of Record", then consume and check it. """

        # Execute 'run()' as a separate process.
        server_run = Process(target=server.run)
        server_run.start()

        # Send a message to 'incoming' exchange - i.e. as if from SoR.
        exchange=server.incoming_exchange
        with server.setup_producer(exchange=exchange) as producer:
            producer.publish(body=self.message, routing_key=server.INCOMING_QUEUE)
            logger.info(self.message)

       # Wait a bit - one second should be long enough.
        server_run.join(timeout=1)
        server_run.terminate()

        # Consume (poll) message from outgoing exchange.
        time.sleep(10)
        exchange=server.outgoing_exchange
        queue_name=server.OUTGOING_QUEUE
        with server.setup_consumer(exchange=exchange, queue_name=queue_name) as consumer:

            queue = consumer.queues[0]

            message = queue.get()
            logger.info("Got message, queue: {}, {}".format(message.body, queue.name))

            if message:
                handle_message(message.body, message)
                self.assertEqual(self.message, message.payload)
            else:
                self.fail("No message received")

