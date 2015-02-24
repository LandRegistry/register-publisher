#!/bin/python

import os
import logging
import stopit
import kombu
from flask import Flask
from kombu.common import maybe_declare

"""
Register-Publisher: forwards messages from the System of Record to the outside world, via AMQP "broadcast".

* AMQP defines four type of exchange, one of which is 'fanout'; that enables clients to subscribe on an 'ad hoc' basis.
* RabbitMQ etc. should have default exchanges in place; 'amq.fanout' for example.
* The "System of Record" (SoR) could publish directly to a fanout exchange and indeed used to do so.
* A separate "Register-Publisher" (RP) module is required to isolate the SoR from the outside world.
* Thus the SoR publishes to the RP via a 'direct' exchange, which in turn forwards the messages to a 'fanout' exchange.

See http://www.rabbitmq.com/blog/2010/10/19/exchange-to-exchange-bindings for an alternative arrangement, which may be
unique to RabbitMQ. This might avoid the unpack/pack issue of 'process_message()' but it does not permit logging etc.
More importantly perhaps, this package acts as a proxy publisher for the System of Record - i.e. security/isolation.
"""

# Flask is invoked here purely to get the configuration values in a consistent manner!
app = Flask(__name__)
app.config.from_object(os.environ.get('SETTINGS'))

# Routing key is same as queue name in "default direct exchange" case; exchange name is blank.
INCOMING_QUEUE = app.config['INCOMING_QUEUE']
RP_HOSTNAME = app.config['RP_HOSTNAME']
incoming_exchange = kombu.Exchange(type="direct", durable=True)
outgoing_exchange = kombu.Exchange(type="fanout")

# Set up root logger
def setup_logger(name=__name__):
    ll = app.config['LOG_LEVEL']
    FORMAT = "[%(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s"
    logging.basicConfig(format=FORMAT, level=ll)

    logger = logging.getLogger(name)

    return logger

logger = setup_logger()

# Helper functions, mostly to aid testing.
def setup_connection():
    """
    Attempt connection, with timeout.
    """

    # Attempt connection in a separate thread, as (implied) 'connect' call hangs if permissions not set etc.
    with stopit.ThreadingTimeout(10) as to_ctx_mgr:
        assert to_ctx_mgr.state == to_ctx_mgr.EXECUTING

        connection = kombu.Connection(hostname=RP_HOSTNAME)
        connection.connect()

    if to_ctx_mgr.state == to_ctx_mgr.TIMED_OUT:
        err_msg = "Connection unavailable: {}".format(RP_HOSTNAME)
        raise RuntimeError(err_msg)


    logger.info("setup_connection(): {}".format(connection.as_uri()))

    return connection


def setup_producer(connection, exchange=outgoing_exchange, serializer='json'):

    producer = kombu.Producer(connection, exchange=exchange, serializer=serializer)

    # Create exchange on broker if necessary.
    maybe_declare(exchange, producer.channel)

    return producer


def setup_consumer(connection, callback=None):
    """ Create consumer with single queue and callback.
    """

    queue = setup_queue(connection, INCOMING_QUEUE, exchange=incoming_exchange)

    # Create exchange on broker if necessary.
    maybe_declare(queue.exchange, connection)

    consumer = kombu.Consumer(connection, queues=queue, callbacks=[callback], accept=['json'])

    return consumer


def setup_queue(connection, name="", exchange=None):
    """
    Return bound queue.
    """

    unbound_queue = kombu.Queue(name=name, exchange=exchange)
    bound_queue = unbound_queue(connection)
    bound_queue.declare()

    return bound_queue


def run():

    # RabbitMQ connection/channel; default user/password.
    connection = setup_connection()

    # Producer for outgoing (default) exchange.
    producer = setup_producer(connection)

    # This is used to consume messages from the "System of Record", then forward them to the outside world.
    # @TO DO: This may unpack incoming messages, then pack them again when forwarding; consider 'on_message()' instead.
    # ['body' is decoded content, 'message' is the packet as a whole].
    def process_message(body, message):
        ''' Forward messages from the 'System of Record' to the outside world '''

        logger.info("RECEIVED MSG - delivery_info: {}".format(message.delivery_info))
        message.ack()

        # Forward message to outgoing exchange.
        producer.publish(body=body)

    # Create consumer with default queue.
    consumer = setup_consumer(connection, callback=process_message)


    # Loop "forever", as a service.
    while True:
        try:
            connection.drain_events()
        except Exception as e:
            logger.error(e)
            break

    # Graceful degradation.
    connection.close()
    producer.close()
    consumer.cancel()

if __name__ == "__main__":
    print("This module should be executed as a separate Python process")
