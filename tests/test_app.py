#!/bin/python
import os
import json
import unittest
import time
import datetime
import stopit
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
    dt = str(datetime.datetime.now())
    return json.dumps(dt.split())


class TestRegisterPublisher(unittest.TestCase):
    #: This can be the callback applied when a message is received - i.e. "consume()" case.
    def handle_message(self, body, message):
        # Note: 'body' may have been pickled, so refer to 'payload' instead.
        logger.info('Received message: {}'.format(message.payload))
        logger.info(' properties: {}'.format(message.properties))
        logger.info(' delivery_info: {}'.format(message.delivery_info))
        message.ack()

        self.payload = message.payload

    def setUp(self):
        """ Establish connection and other resources; prepare """

        with server.setup_connection(server.OUTGOING_QUEUE_HOSTNAME) as outgoing_connection:
            # Ensure that message broker is alive
            self.assertEqual(outgoing_connection.connected, True)

            # We also need relevant queues established before publishing to exchange!
            queue = server.setup_queue(outgoing_connection, name=server.OUTGOING_QUEUE,
                                       exchange=server.outgoing_exchange)
            queue.purge()

        with server.setup_connection(server.INCOMING_QUEUE_HOSTNAME) as incoming_connection:
            # Ensure that message broker is alive
            self.assertEqual(incoming_connection.connected, True)

            # We also need relevant queues established before publishing to exchange!
            queue = server.setup_queue(incoming_connection, name=server.INCOMING_QUEUE,
                                       exchange=server.incoming_exchange)
            queue.purge()

        # Message to be sent.
        self.message = make_message()

        # Corresponding 'payload' of message received.
        self.payload = None

    def tearDown(self):
        with server.setup_connection(server.INCOMING_QUEUE_HOSTNAME) as incoming_connection:
            # Need a connection to delete the queues.
            self.assertEqual(incoming_connection.connected, True)

            queue = server.setup_queue(incoming_connection, name=server.INCOMING_QUEUE,
                                       exchange=server.incoming_exchange)
            queue.delete()

        with server.setup_connection(server.OUTGOING_QUEUE_HOSTNAME) as outgoing_connection:
            # Need a connection to delete the queues.
            self.assertEqual(outgoing_connection.connected, True)

            queue = server.setup_queue(outgoing_connection, name=server.OUTGOING_QUEUE,
                                       exchange=server.outgoing_exchange)
            queue.delete()


    def test_incoming_queue(self):
        """ Basic check of 'incoming' message via default direct exchange """

        exchange = server.incoming_exchange
        queue_name = server.INCOMING_QUEUE

        with server.setup_connection(server.INCOMING_QUEUE_HOSTNAME) as connection:
            producer = server.setup_producer(connection, exchange=exchange)
            producer.publish(body=self.message, routing_key=queue_name)
            logger.info("Put message, exchange: {}, {}".format(self.message, exchange))

            # Wait a bit - one second should be long enough.
        time.sleep(1)

        with server.setup_connection(server.INCOMING_QUEUE_HOSTNAME) as connection:
            consumer = server.setup_consumer(connection, exchange=exchange, queue_name=queue_name)
            queue = consumer.queues[0]
            message = queue.get()
            logger.info("Got message, queue: {}, {}".format(message.body, queue.name))

            queue.delete()

            if message:
                self.handle_message(message.body, message)

            self.assertEqual(self.message, self.payload)

        # N.B.: this test reverses the default 'producer' and 'consumer' targets.


    def test_end_to_end(self):
        """ Send message from dummy "System Of Record", then consume and check it. """

        # Execute 'run()' as a separate process.
        server_run = Process(target=server.run)
        server_run.start()

        # Send a message to 'incoming' exchange - i.e. as if from SoR.
        exchange = server.incoming_exchange
        with server.setup_producer(exchange=exchange) as producer:
            producer.publish(body=self.message, routing_key=server.INCOMING_QUEUE)
            logger.info(self.message)

            # Wait a bit - one second should be long enough.
        server_run.join(timeout=1)
        server_run.terminate()

        # Consume (poll) message from outgoing exchange.
        exchange = server.outgoing_exchange
        queue_name = server.OUTGOING_QUEUE
        callback = self.handle_message

        with server.setup_consumer(exchange=exchange, queue_name=queue_name, callback=callback) as consumer:

            # 'consume' may be a misnomer here - it just initiates the consumption process, I believe.
            consumer.consume()

            # Execute 'drain_events()' loop in a time-out thread, in case it gets stuck.
            with stopit.ThreadingTimeout(10) as to_ctx_mgr:
                assert to_ctx_mgr.state == to_ctx_mgr.EXECUTING

                try:
                    consumer.connection.drain_events()
                except Exception as e:
                    logger.error(e)

            if to_ctx_mgr.state == to_ctx_mgr.TIMED_OUT:
                logger.error("Message not consumed!")

        self.assertEqual(self.message, self.payload)
