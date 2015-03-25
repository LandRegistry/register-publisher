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
from logger.setup_logging import setup_logging

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
app.config.from_object(os.getenv('SETTINGS', "config.ProductionConfig"))

incoming_cfg = app.config['INCOMING_CFG']
outgoing_cfg = app.config['OUTGOING_CFG']

# Constraints, etc.
MAX_RETRIES = app.config['MAX_RETRIES']

LOG_NAME = "Register-Publisher"

# Logger-independent output to 'stderr'.
# def echo(message):
#     print('\n' + message, file=sys.stderr)

# Set up logger
def setup_logger(name=__name__):

    # Standard LR configuration.
    setup_logging()

    # Specify base logging threshold level.
    ll = app.config['LOG_THRESHOLD_LEVEL']
    logger = logging.getLogger(name)
    logger.setLevel(ll)

    return logger

logger = setup_logger(LOG_NAME)

log_threshold_level_name = logging.getLevelName(logger.getEffectiveLevel())


# RabbitMQ connection; default user/password.
def setup_connection(queue_hostname, confirm_publish=True):
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

        connection = kombu.Connection(hostname=queue_hostname, transport_options={'confirm_publish': confirm_publish})
        app.logger.info(queue_hostname)

        connection.connect()

    if to_ctx_mgr.state == to_ctx_mgr.TIMED_OUT:
        err_msg = "Connection unavailable: {}".format(queue_hostname)
        raise RuntimeError(err_msg)

    logger.info("URI: {}".format(connection.as_uri()))

    return connection


# RabbitMQ channel.
def setup_channel(queue_hostname, exchange=None, connection=None):
    """ Get a channel and bind exchange to it. """

    assert exchange is not None
    logger.info("exchange: {}".format(exchange))

    if connection is None:
        channel = setup_connection(queue_hostname).channel()
    else:
        channel = connection.channel()

    # Bind/Declare exchange on broker if necessary.
    exchange.maybe_bind(channel)
    maybe_declare(exchange, channel)

    logger.debug('channel_id: {}'.format(channel.channel_id))

    return channel


# Get Producer, for 'outgoing' exchange and JSON "serializer" by default.
def setup_producer(cfg=outgoing_cfg, serializer='json'):

    channel = setup_channel(cfg.hostname, exchange=cfg.exchange)

    # Make sure that outgoing queue exists!
    setup_queue(channel, cfg=cfg)

    # Publish message to given queue.
    producer = kombu.Producer(channel, exchange=cfg.exchange, routing_key=cfg.queue, serializer=serializer)

    logger.debug('channel_id: {}'.format(producer.channel.channel_id))
    logger.debug('exchange: {}'.format(producer.exchange.name))
    logger.debug('routing_key: {}'.format(producer.routing_key))
    logger.debug('serializer: {}'.format(producer.serializer))

    return producer


# Consumer, for 'incoming' queue by default.
def setup_consumer(cfg=incoming_cfg, callback=None):
    """ Create consumer with single queue and callback """

    channel = setup_channel(cfg.hostname, cfg.exchange)
    logger.info("queue_name: {}".format(cfg.queue))

    # A consumer needs a queue, so create one (if necessary).
    queue = setup_queue(channel, cfg=cfg)

    consumer = kombu.Consumer(channel, queues=queue, callbacks=[callback], accept=['json'])

    logger.debug('channel_id: {}'.format(consumer.channel.channel_id))
    logger.debug('queue(s): {}'.format(consumer.queues))

    return consumer


def setup_queue(channel, cfg=None, key=None, durable=True):
    """ Return bound queue, "durable" by default """

    if cfg is None:
        raise RuntimeError("setup_queue: configuration 'cfg' required!")

    routing_key = cfg.queue if key is None else key
    queue = kombu.Queue(name=cfg.queue, exchange=cfg.exchange, routing_key=routing_key, durable=durable)
    queue.maybe_bind(channel)

    # VIP: ensure that queue is declared! If it isn't, we can send message to queue but they die, silently :-(
    # [IMO, this should have been done by default via the 'bind' operation].
    try:
        queue.declare()
    # 'AccessRefused' raised by kombu if queue already declared.
    except AccessRefused:
        pass

    logger.info("queue name, exchange, routing_key: {}, {}, {}".format(queue.name, cfg.exchange, routing_key))

    return queue


# This is executed as a separate process by unit tests; cannot refer to 'INCOMING_QUEUE' etc. in that case.
def run():
    """ "System of Record" to "Feeder" re-publisher. """

    logger = setup_logger(LOG_NAME)

    def errback(exc, interval):
            """ Callback for use with 'ensure/autoretry'. """

            logger.error('Error: {}'.format(exc))
            logger.info('Retry in {} seconds.'.format(interval))

    def ensure(connection, instance, method, *args, **kwargs):
        """ Retries 'method' if it raises connection or channel error.

            Error is re-raised if 'max_retries' exceeded.

        """
        logger.debug("instance: {}, method: {}".format(instance.__class__, method))
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

        logger.audit("Pull from incoming queue: {}".format(message.delivery_info))

        # Forward message to outgoing exchange, with retry management.
        logger.audit("Push to outgoing queue: {}".format(message.delivery_info))
        ensure(producer.connection, producer, 'publish', body)
        logger.audit("Acknowledged Push (implied): {}".format(message.delivery_tag))

        # Acknowledge message only after publish(); if that fails, message is still in queue.
        message.ack()
        logger.audit("Acknowledged Pull: {}".format(message.delivery_tag))


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
            logger.exception("{}: {}".format(err_line_no, str(e)))

            # If we ignore the problem, perhaps it will go away ...
            time.sleep(10)

    # Graceful degradation.
    producer.close()
    consumer.close()


if __name__ == "__main__":
    print("This module should be executed as a separate Python process")
