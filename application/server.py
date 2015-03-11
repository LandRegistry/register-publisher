#!/bin/python
import os
import sys
import logging
import logging.handlers
import stopit
import kombu
import time
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
app.config.from_object(os.getenv('SETTINGS', "config.DevelopmentConfig"))

# Routing key is same as queue name in "default direct exchange" case; exchange name is blank.
INCOMING_QUEUE = app.config['INCOMING_QUEUE']
OUTGOING_QUEUE = app.config['OUTGOING_QUEUE']
RP_HOSTNAME = app.config['RP_HOSTNAME']

# Relevant Exchange default values:
#   delivery_mode: '2' (persistent messages)
#   durable: True (exchange remains 'active' on server re-start)
incoming_exchange = kombu.Exchange(type="direct")
outgoing_exchange = kombu.Exchange(type="fanout")

# Constraints, etc.
MAX_RETRIES = app.config['MAX_RETRIES']


# Logger-independent output to 'stderr'.
def echo(message):
    print('\n' + message, file=sys.stderr)

# Set up logger
def setup_logger(name=__name__):

    # Specify base logging threshold level.
    ll = app.config['LOG_THRESHOLD_LEVEL']
    logger = logging.getLogger(name)
    logger.setLevel(ll)

    # Formatter for log records.
    FORMAT = "%(asctime)s %(filename)-12.12s#%(lineno)-5.5s %(funcName)-20.20s %(message)s"
    formatter = logging.Formatter(FORMAT)

    # Add 'timed rotating' file handler, for DEBUG-level messages or above.
    # WARNING: do not use RotatingFileHandler, as this may result in a "ResourceWarning: unclosed file" fault!
    filename = "{}.log".format(name)
    file_handler = logging.handlers.TimedRotatingFileHandler(filename, when='D')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

    # Add 'console' handler, for errors only.
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.ERROR)
    logger.addHandler(stream_handler)

    return logger

logger = setup_logger('Register-Publisher')

log_threshold_level_name = logging.getLevelName(logger.getEffectiveLevel())
echo("LOG_THRESHOLD_LEVEL = {}".format(log_threshold_level_name))


# RabbitMQ connection; default user/password.
def setup_connection(hostname=RP_HOSTNAME, confirm_publish=True):
    """ Attempt connection, with timeout.

    'confirm_publish' refers to the "Confirmation Model", with the broker as client to a publisher.

    This can be for asynchronous operation, in which case channel.confirm_select() is called,
    or for synchronous operation, which employs channel.basic_publish() in a blocking way; note
    that this call is invoked via the Producer.publish() method, rather than being invoked directly.

    Asynchronous mode does not seem to be well-supported however and the blocking approach is simpler,
    so we will adopt that even though the performance may suffer.

    See the "2013-09-04 02:39 P.M UTC" entry of http://amqp.readthedocs.org/en/latest/changelog.html for details.

    """

    # Run-time checks.
    assert type(confirm_publish) is bool

    logger.debug("confirm_publish: {}".format(confirm_publish))

    # Attempt connection in a separate thread, as (implied) 'connect' call may hang if permissions not set etc.
    with stopit.ThreadingTimeout(10) as to_ctx_mgr:
        assert to_ctx_mgr.state == to_ctx_mgr.EXECUTING

        connection = kombu.Connection(hostname=hostname, transport_options={'confirm_publish': confirm_publish})
        app.logger.info(hostname)
        connection.connect()

    if to_ctx_mgr.state == to_ctx_mgr.TIMED_OUT:
        err_msg = "Connection unavailable: {}".format(RP_HOSTNAME)
        raise RuntimeError(err_msg)

    logger.info("URI: {}".format(connection.as_uri()))

    return connection


# RabbitMQ channel.
def setup_channel(exchange=None, connection=None):
    """ Get a channel and bind exchange to it. """

    assert exchange is not None
    logger.info("exchange: {}".format(exchange))

    channel = setup_connection().channel() if connection is None else connection.channel

    # Bind/Declare exchange on broker if necessary.
    exchange.maybe_bind(channel)
    maybe_declare(exchange, channel)

    return channel


# Get Producer, for 'outgoing' exchange and JSON "serializer" by default.
def setup_producer(exchange=outgoing_exchange, queue_name=OUTGOING_QUEUE, serializer='json'):

    channel = setup_channel(exchange=exchange)

    # Make sure that outgoing queue exists!
    setup_queue(channel, name=queue_name, exchange=exchange)

    # Publish message to given queue.
    producer = kombu.Producer(channel, exchange=exchange, routing_key=queue_name, serializer=serializer)

    return producer


# Consumer, for 'incoming' queue by default.
def setup_consumer(exchange=incoming_exchange, queue_name=INCOMING_QUEUE, callback=None):
    """ Create consumer with single queue and callback """

    channel = setup_channel(exchange=exchange)
    logger.info("queue_name: {}".format(queue_name))

    # A consumer needs a queue, so create one (if necessary).
    queue = setup_queue(channel, name=queue_name, exchange=exchange)

    consumer = kombu.Consumer(channel, queues=queue, callbacks=[callback], accept=['json'])

    return consumer


def setup_queue(channel, name=None, exchange=incoming_exchange, key=None, durable=True):
    """ Return bound queue, "durable" by default """

    if name is None or exchange is None:
        raise RuntimeError("setup_queue: queue/exchange name required!")

    routing_key = name if key is None else key
    queue = kombu.Queue(name=name, exchange=exchange, routing_key=routing_key, durable=durable)
    queue.maybe_bind(channel)

    # VIP: ensure that queue is declared! If it isn't, we can send message to queue but they die, silently :-(
    # [IMO, this should have been done by default via the 'bind' operation].
    try:
        queue.declare()
    # 'AccessRefused' raised by kombu if queue already declared.
    except AccessRefused:
        pass

    logger.info("queue name, exchange, routing_key: {}, {}, {}".format(queue.name, exchange, routing_key))

    return queue


def run():
    """ "System of Record" to "Feeder" re-publisher. """

    def errback(exc, interval):
            """ Callback for use with 'ensure/autoretry'. """

            logger.error('Error: {}'.format(exc))
            logger.info('Retry in {} seconds.'.format(interval))

    def ensure(connection, instance, method, *args, **kwargs):
        """ Retries 'method' if it raises connection or channel error.

            Error is re-raised if 'max_retries' exceeded.

        """
        _method = getattr(instance, method)
        _wrapper = connection.ensure(instance, _method, errback=errback, max_retries=MAX_RETRIES)

        _wrapper(*args, **kwargs)

    # Handler (callback) for consumer.
    def process_message(body, message):
        """ Forward messages from the 'System of Record' to the outside world

        'body' is decoded content, 'message' is the packet as a whole.

        N.B.:
          This will unpack incoming messages, then pack them again when forwarding.
          'on_message()' doesn't really help, because publish() requires a message body.

        """

        logger.info("RECEIVED MSG - delivery_info: {}".format(message.delivery_info))

        # Forward message to outgoing exchange, with retry management.
        ensure(producer.connection, producer, 'publish', body)

        # Acknowledge message only after publish(); if that fails, message is still in queue.
        message.ack()


    # Producer for outgoing exchange.
    producer = setup_producer()

    # Create consumer with incoming exchange/queue.
    consumer = setup_consumer(callback=process_message)
    consumer.consume()

    # Loop "forever", as a service.
    # N.B.: if there is a serious network failure or the like then this will keep logging errors!
    while True:
        try:
            # "Wait for a single event from the server".
            # consumer.connection.drain_events()
            ensure(consumer.connection, consumer.connection, 'drain_events')

        # Permit an explicit abort.
        except KeyboardInterrupt:
            logger.error("KeyboardInterrupt received!")
            break
        # Trap (log) everything else.
        except Exception as e:
            err_line_no = sys.exc_info()[2].tb_lineno
            logger.error("{}: {}".format(err_line_no, str(e)))

            # If we ignore the problem, perhaps it will go away ...
            time.sleep(10)

    # Graceful degradation.
    producer.close()
    consumer.close()


if __name__ == "__main__":
    print("This module should be executed as a separate Python process")
