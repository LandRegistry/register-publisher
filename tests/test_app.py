#!/bin/python
import sys; sys.path.insert(0, 'c:\\Users\\User\\register-publisher')
import json
import unittest
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

class Application(object):
    """ Mimic Process calls, for logging purposes. """

    def __init__(self, target=server.run):
        self.target = target
        self.process = None

    def start(self):
        self.process = Process(target=self.target)

        logger.debug("Starting '{}' as a separate process.".format(self.target))
        self.process.start()

    def join(self, timeout=None):
        self.process.join(timeout=timeout)
        logger.debug("'{}' completed.".format(self.target))

    def terminate(self):
        self.process.terminate()
        logger.debug("'{}' terminated.".format(self.target))

# N.B.: these tests may reverse the default 'producer' and 'consumer' targets.
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
                consumer.close()

    def reset(self):
        """ Clear the decks. """

        with server.setup_connection() as connection:

            # Need a connection to delete the queues.
            self.assertEqual(connection.connected, True)

            queue = server.setup_queue(connection, name=server.INCOMING_QUEUE, exchange=server.incoming_exchange)
            queue.purge()
            queue.delete()

            queue = server.setup_queue(connection, name=server.OUTGOING_QUEUE, exchange=server.outgoing_exchange)
            queue.purge()
            queue.delete()

    def setUp(self):
        """ Establish connection and other resources; prepare """

        self.app = Application()

        test_title = self.id().split(sep='.')[-1]
        server.echo(test_title)

        # Ensure that message broker is alive, etc.
        self.reset()

        self.message = None             # Message to be sent.
        self.payload = None             # Corresponding 'payload' of message received.

        # Execute 'server.run()' as a separate process.
        self.app.start()

    def tearDown(self):

        # N.B.: app needs to be terminated before queues can be deleted!
        self.app.terminate()

        self.reset()

    def test_incoming_queue(self):
        """ Basic check of 'incoming' message via default direct exchange """

        # We don't need the app to be running for this test.
        self.app.terminate()

        self.message = make_message()

        producer = server.setup_producer(exchange=server.incoming_exchange, queue_name=server.INCOMING_QUEUE)
        producer.publish(body=self.message)
        logger.info("Put message, exchange: {}, {}".format(self.message, producer.exchange))

        producer.close()

        self.consume()

        self.assertEqual(self.message, self.payload)

    def test_broken_connection(self):
        """ Attempt 'publish' via closed connection, which is subsequently restored. """

        self.message = make_message()

        # Send a message to 'incoming' exchange - i.e. as if from SoR.
        with server.setup_producer(exchange=server.incoming_exchange, queue_name=server.INCOMING_QUEUE) as producer:

            # Kill connection to broker.
            producer.connection.close()

            producer.publish(body=self.message)

        # Block (wait) until app times out or terminates.
        self.app.join(timeout=5)
        logger.info("'server.run()' completed")

        # Consume message from outgoing exchange.
        self.consume(exchange=server.outgoing_exchange, queue_name=server.OUTGOING_QUEUE)

        self.assertEqual(self.message, self.payload)

    def test_stored_message(self):
        """ Store message from dummy "System Of Record", then consume later and check it. """

        self.app.terminate()

        self.message = make_message()

        # Send a message to 'incoming' exchange - i.e. as if from SoR.
        with server.setup_producer(exchange=server.incoming_exchange, queue_name=server.INCOMING_QUEUE) as producer:
            producer.publish(body=self.message)
            logger.debug(self.message)

        self.app.start()

        # Kill application; wait long enough for message to be stored.
        # N.B.: 1 second may be insufficient, for a full coverage check during testing.
        self.app.join(timeout=5)
        logger.info("'server.run()' completed")

        # Consume message from outgoing exchange.
        self.consume(exchange=server.outgoing_exchange, queue_name=server.OUTGOING_QUEUE)

        self.assertEqual(self.message, self.payload)

    def test_end_to_end(self, count=1):
        """ Send message from dummy "System Of Record", then consume and check it. """

        # Send a message to 'incoming' exchange - i.e. as if from SoR.
        with server.setup_producer(exchange=server.incoming_exchange, queue_name=server.INCOMING_QUEUE) as producer:
            for n in range(count):

                # Message to be sent.
                self.message = make_message()

                producer.publish(body=self.message)
                logger.debug(self.message)

                # Consume message from outgoing exchange, via callback.
                self.consume(exchange=server.outgoing_exchange, queue_name=server.OUTGOING_QUEUE)

                self.assertEqual(self.message, self.payload)

        # Wait long enough for all messages to be processed.
        self.app.join(timeout=(count // 10) + 1)

    def test_multiple_end_to_end(self):
        """ Check many messages. """

        self.test_end_to_end(100)

if __name__ == '__main__':
    unittest.main()
