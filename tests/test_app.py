#!/bin/python
import sys; sys.path.insert(0, 'c:\\Users\\User\\register-publisher')
import json
import unittest
import time
import datetime
from multiprocessing import Process
from application import server

"""
Test Register-Publisher on an 'ad hoc' basis or automatically (pytest).
Pretend to be "System Of Record" publisher.
"""

# Set up root logger
logger = server.logger

# Basic test data.
def make_message():
    dt=str(datetime.datetime.now())
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

    def consume(self, exchange=server.incoming_exchange, queue_name=server.INCOMING_QUEUE):
        """ Get message via callback mechanism """

        callback = self.handle_message

        with server.setup_consumer(exchange=exchange, queue_name=queue_name, callback=callback) as consumer:

            # 'consume' may be a misnomer here - it just initiates the consumption process, I believe.
            consumer.consume()

            # Execute 'drain_events()' loop in a time-out thread, in case it gets stuck.
            logger.info("'drain_events()' with timeout")
            try:
                consumer.connection.drain_events(timeout=5)
            except Exception as e:
                logger.error(e)
            finally:
                consumer.cancel()
                consumer.close()

    def setUp(self):
        """ Establish connection and other resources; prepare """

        with server.setup_connection() as connection:

            # Ensure that message broker is alive
            self.assertEqual(connection.connected, True)

        # Message to be sent.
        self.message = make_message()

        # Corresponding 'payload' of message received.
        self.payload = None

    def tearDown(self):

        with server.setup_connection() as connection:

            # Need a connection to delete the queues.
            self.assertEqual(connection.connected, True)

            queue = server.setup_queue(connection, name=server.INCOMING_QUEUE, exchange=server.incoming_exchange)
            queue.delete()

            queue = server.setup_queue(connection, name=server.OUTGOING_QUEUE, exchange=server.outgoing_exchange)
            queue.delete()

    def test_incoming_queue(self):
        """ Basic check of 'incoming' message via default direct exchange """

        exchange = server.incoming_exchange
        queue_name = server.INCOMING_QUEUE

        # Check server with explicit connection.
        with server.setup_connection() as connection:
            producer = server.setup_producer(connection, exchange=exchange, queue_name=queue_name)
            producer.publish(body=self.message, routing_key=queue_name)
            logger.info("Put message, exchange: {}, {}".format(self.message, exchange))

            producer.close()

        self.consume()

        connection.close()

        self.assertEqual(self.message, self.payload)

    # N.B.: this test reverses the default 'producer' and 'consumer' targets.
    def test_end_to_end(self):
        """ Send message from dummy "System Of Record", then consume and check it. """

        # Execute 'run()' as a separate process.
        logger.info("Starting 'server.run()' with timeout")
        server_run = Process(target=server.run)
        server_run.start()

        # Send a message to 'incoming' exchange - i.e. as if from SoR.
        exchange=server.incoming_exchange
        queue_name=server.INCOMING_QUEUE
        with server.setup_producer(exchange=exchange, queue_name=queue_name) as producer:
            producer.publish(body=self.message, routing_key=server.INCOMING_QUEUE)
            logger.info(self.message)

        # Wait long enough for message to be picked up.
        # N.B.: 1 second may be insufficient, for a full coverage check during testing.
        server_run.join(timeout=5)
        logger.info("'server.run()' completed")
        server_run.terminate()
        logger.info("'server.run()' terminated")

        # Consume message from outgoing exchange.
        exchange=server.outgoing_exchange
        queue_name=server.OUTGOING_QUEUE
        self.consume(exchange=exchange, queue_name=queue_name)

        self.assertEqual(self.message, self.payload)


if __name__ == '__main__':
    unittest.main()
