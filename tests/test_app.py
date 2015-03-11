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

        with server.setup_consumer(exchange=exchange, queue_name=queue_name, callback=self.handle_message) as consumer:

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

    def reset(self):
        """ Clear the decks. """

        with server.setup_connection() as connection:

            # Need a connection to delete the queues.
            self.assertEqual(connection.connected, True)

            queue = server.setup_queue(connection, name=server.INCOMING_QUEUE, exchange=server.incoming_exchange)
            queue.delete()

            queue = server.setup_queue(connection, name=server.OUTGOING_QUEUE, exchange=server.outgoing_exchange)
            queue.delete()

    def setUp(self):
        """ Establish connection and other resources; prepare """

        test_title = self.id().split(sep='.')[-1]
        server.echo(test_title)

        # Ensure that message broker is alive, etc.
        self.reset()

        self.message = None             # Message to be sent.
        self.payload = None             # Corresponding 'payload' of message received.

    def tearDown(self):

        self.reset()

    def test_incoming_queue(self):
        """ Basic check of 'incoming' message via default direct exchange """

        self.message = make_message()

        exchange = server.incoming_exchange
        queue_name = server.INCOMING_QUEUE

        producer = server.setup_producer(exchange=exchange, queue_name=queue_name)
        producer.publish(body=self.message, routing_key=queue_name)
        logger.info("Put message, exchange: {}, {}".format(self.message, exchange))

        producer.close()

        self.consume()

        self.assertEqual(self.message, self.payload)

    # N.B.: this test reverses the default 'producer' and 'consumer' targets.
    def test_stored_message(self):
        """ Send message from dummy "System Of Record", then consume and check it. """

        self.message = make_message()

        # Execute 'run()' as a separate process.
        logger.info("Starting 'server.run()' with timeout")
        server_run = Process(target=server.run)
        server_run.start()

        # Send a message to 'incoming' exchange - i.e. as if from SoR.
        with server.setup_producer(exchange=server.incoming_exchange, queue_name=server.INCOMING_QUEUE) as producer:
            producer.publish(body=self.message, routing_key=server.INCOMING_QUEUE)
            logger.debug(self.message)

        # Kill application; wait long enough for message to be stored.
        # N.B.: 1 second may be insufficient, for a full coverage check during testing.
        server_run.join(timeout=5)
        logger.info("'server.run()' completed")
        server_run.terminate()
        logger.info("'server.run()' terminated")

        # Consume message from outgoing exchange.
        self.consume(exchange=server.outgoing_exchange, queue_name=server.OUTGOING_QUEUE)

        self.assertEqual(self.message, self.payload)

    def test_end_to_end(self, count=1):
        """ Send message from dummy "System Of Record", then consume and check it. """

        server_run = Process(target=server.run)
        server_run.start()

        # Send a message to 'incoming' exchange - i.e. as if from SoR.
        with server.setup_producer(exchange=server.incoming_exchange, queue_name=server.INCOMING_QUEUE) as producer:
            for n in range(count):

                # Message to be sent.
                self.message = make_message()

                producer.publish(body=self.message, routing_key=server.INCOMING_QUEUE)
                logger.debug(self.message)

                # Consume message from outgoing exchange, via callback.
                self.consume(exchange=server.outgoing_exchange, queue_name=server.OUTGOING_QUEUE)

                self.assertEqual(self.message, self.payload)

        # Wait long enough for all messages to be processed.
        server_run.join(timeout=(count // 10) + 1)
        logger.info("'server.run()' completed")
        server_run.terminate()
        logger.info("'server.run()' terminated")

    def test_multiple_end_to_end(self):
        """ Check many messages. """

        self.test_end_to_end(100)

if __name__ == '__main__':
    unittest.main()
