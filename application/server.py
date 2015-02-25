#!/bin/python
import os
import logging
import stopit
import kombu
from flask import Flask
from kombu.common import maybe_declare
from amqp import AccessRefused

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
OUTGOING_QUEUE = app.config['OUTGOING_QUEUE']
RP_HOSTNAME = app.config['RP_HOSTNAME']
incoming_exchange = kombu.Exchange(type="direct", durable=True)
outgoing_exchange = kombu.Exchange(type="fanout")

# Set up root logger
def setup_logger(name=__name__):
    ll = app.config['LOG_LEVEL']
    FORMAT = "[%(asctime)s %(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s"
    filename = "{}.log".format(name)
    logging.basicConfig(filename=filename, format=FORMAT, level=ll)

    logger = logging.getLogger(name)

    return logger

logger = setup_logger()

# RabbitMQ connection/channel; default user/password.
def setup_connection(exchange=None):
    """ Attempt connection, with timeout. """

    # Attempt connection in a separate thread, as (implied) 'connect' call hangs if permissions not set etc.
    with stopit.ThreadingTimeout(10) as to_ctx_mgr:
        assert to_ctx_mgr.state == to_ctx_mgr.EXECUTING

        connection = kombu.Connection(hostname=RP_HOSTNAME)
        connection.connect()

    if to_ctx_mgr.state == to_ctx_mgr.TIMED_OUT:
        err_msg = "Connection unavailable: {}".format(RP_HOSTNAME)
        raise RuntimeError(err_msg)


    logger.info("URI: {}".format(connection.as_uri()))

    # Bind/Declare exchange on broker if necessary.
    if exchange is not None:
        exchange.maybe_bind(connection)
        maybe_declare(exchange, connection)

    return connection


# Producer, for 'outgoing' exchange by default.
def setup_producer(connection=None, exchange=outgoing_exchange, serializer='json'):

    channel = setup_connection(exchange) if connection is None else connection
    logger.info("channel: {}".format(channel))
    logger.info("exchange: {}".format(exchange))

    producer = kombu.Producer(channel, exchange=exchange, serializer=serializer)

    return producer


# Consumer, for 'incoming' queue by default.
def setup_consumer(connection=None, exchange=incoming_exchange, queue_name=INCOMING_QUEUE, callback=None):
    """ Create consumer with single queue and callback """

    channel = setup_connection(exchange) if connection is None else connection
    logger.info("channel: {}".format(channel))
    logger.info("exchange: {}".format(exchange))
    logger.info("queue: {}".format(queue_name))

    queue = setup_queue(channel, name=queue_name, exchange=exchange)
    logger.info("queue: {}".format(queue.name))

    consumer = kombu.Consumer(channel, queues=queue, callbacks=[callback], accept=['json'])

    return consumer


def setup_queue(channel, name=None, exchange=incoming_exchange, key=None):
    """ Return bound queue """

    if name is None or exchange is None:
        raise RuntimeError("setup_queue: queue/exchange name required!")

    routing_key = name if key is None else key
    queue = kombu.Queue(name=name, exchange=exchange, routing_key=routing_key)
    queue.maybe_bind(channel)
    ##queue.auto_delete = True

    # VIP: ensure that queue is declared!
    # [IMO, this should have been done by default via the 'bind' operation].
    try:
        queue.declare()
    except AccessRefused:
        pass

    logger.info("queue name, exchange, key: {}, {}, {}".format(name, exchange, routing_key))

    return queue


def run():

    # Producer for outgoing (default) exchange.
    producer = setup_producer()

    # This is used to consume messages from the "System of Record", then forward them to the outside world.
    # @TO DO: This may unpack incoming messages, then pack them again when forwarding; consider 'on_message()' instead.
    # ['body' is decoded content, 'message' is the packet as a whole].
    def process_message(body, message):
        ''' Forward messages from the 'System of Record' to the outside world '''

        logger.info("RECEIVED MSG - delivery_info: {}".format(message.delivery_info))
        message.ack()

        # Forward message to outgoing exchange.
        producer.publish(body=body, routing_key=OUTGOING_QUEUE)

    # Create consumer with default exchange/queue.
    consumer = setup_consumer(callback=process_message)
    consumer.consume()

    # Loop "forever", as a service.
    while True:
        try:
            consumer.connection.drain_events()
        except Exception as e:
            logger.error(e)
            break

    # Graceful degradation.
    producer.close()
    consumer.cancel()


if __name__ == "__main__":
    print("This module should be executed as a separate Python process")
