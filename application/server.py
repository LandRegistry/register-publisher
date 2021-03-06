#!/bin/python
import os
import sys
import pwd
import re
import logging
import logging.handlers
import stopit
import kombu
import time
from flask import Flask
from kombu.common import maybe_declare
from amqp import AccessRefused
from python_logging.setup_logging import setup_logging


"""
Register-Publisher: forwards messages from the System of Record to the outside world, via AMQP "topic broadcast".

* AMQP defines four type of exchange, one of which is 'topic'; that enables clients to subscribe on an 'ad hoc' basis.
* RabbitMQ etc. should have default exchanges in place; 'amq.fanout' for example.
* The "System of Record" (SoR) could publish directly to a fanout exchange and indeed used to do so.
* A separate "Register-Publisher" (RP) module is required to isolate the SoR from the outside world.
* Thus the SoR publishes to the RP via a 'direct' exchange, which in turn forwards the messages to a 'topic' exchange.

See http://www.rabbitmq.com/blog/2010/10/19/exchange-to-exchange-bindings for an alternative arrangement, which may be
unique to RabbitMQ. This might avoid the unpack/pack issue of 'process_message()' but it does not permit logging etc.
More importantly perhaps, this package acts as a proxy publisher for the System of Record - i.e. security/isolation.


"""

app = Flask(__name__)
app.config.from_object(os.getenv('SETTINGS', "config.DevelopmentConfig"))

incoming_cfg = app.config['INCOMING_CFG']
outgoing_cfg = app.config['OUTGOING_CFG']

incoming_count_cfg = app.config['INCOMING_COUNT_CFG']
outgoing_count_cfg = app.config['OUTGOING_COUNT_CFG']

# Constraints, etc.
MAX_RETRIES = app.config['MAX_RETRIES']

LOG_NAME = "RP"

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

    logger.debug(queue_hostname)
    logger.debug("confirm_publish: {}".format(confirm_publish))

    # Attempt connection in a separate thread, as (implied) 'connect' call may hang if permissions not set etc.
    with stopit.ThreadingTimeout(10) as to_ctx_mgr:
        assert to_ctx_mgr.state == to_ctx_mgr.EXECUTING

        connection = kombu.Connection(hostname=queue_hostname, transport_options={'confirm_publish': confirm_publish})

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
def setup_producer(cfg=outgoing_cfg, serializer='json', set_queue=True):
    """ Create a Producer, with a corresponding queue if required. """

    assert type(set_queue) is bool

    logger.debug("cfg: {}".format(cfg))

    channel = setup_channel(cfg.hostname, exchange=cfg.exchange)

    # Publishing is to an exchange but we need a queue to store messages *before* publication.
    # Note that Consumers should really be responsible for (their) queues.
    queue = None
    if set_queue:
        queue = setup_queue(channel, cfg=cfg)

    # Publish message; the default message *routing* key is the outgoing queue name.
    producer = kombu.Producer(channel, exchange=cfg.exchange, routing_key=cfg.queue, serializer=serializer)

    logger.debug('channel_id: {}'.format(producer.channel.channel_id))
    logger.debug('exchange: {}'.format(producer.exchange.name))
    logger.debug('routing_key: {}'.format(producer.routing_key))
    logger.debug('serializer: {}'.format(producer.serializer))

    # Track queue, for debugging purposes.
    producer._queue = queue

    return producer


# Consumer, for 'incoming' queue by default.
def setup_consumer(cfg=incoming_cfg, callback=None):
    """ Create consumer with single queue and callback """

    logger.debug("cfg: {}".format(cfg))

    channel = setup_channel(cfg.hostname, cfg.exchange)
    logger.info("queue_name: {}".format(cfg.queue))

    # A consumer needs a queue, so create one (if necessary).
    queue = setup_queue(channel, cfg=cfg)

    consumer = kombu.Consumer(channel, queues=queue, callbacks=[callback], accept=['json'])

    logger.debug('channel_id: {}'.format(consumer.channel.channel_id))
    logger.debug('queue(s): {}'.format(consumer.queues))

    return consumer


def setup_queue(channel=None, cfg=None, durable=True):
    """ Return bound queue, "durable" by default """

    if channel is None:
        raise RuntimeError("setup_queue: 'channel' required!")

    if cfg is None:
        raise RuntimeError("setup_queue: 'cfg' required!")

    logger.debug("cfg: {}".format(cfg))

    # N.B.: kombu mis-names the queue's Binding key as a Routing key!
    queue = kombu.Queue(name=cfg.queue, exchange=cfg.exchange, routing_key=cfg.binding_key, durable=durable)
    queue.maybe_bind(channel)

    # VIP: ensure that queue is declared! If it isn't, we can send messages to the queue but they die, silently :-(
    # Note: IMO, this should have been done by default via the 'bind' operation - and that by the class.
    try:
        queue.declare()
    # 'AccessRefused' raised by kombu if queue already declared.
    except AccessRefused:
        pass

    logger.info("queue name, exchange, binding_key: {}, {}, {}".format(queue.name, cfg.exchange, cfg.binding_key))

    return queue


def make_log_msg(log_message, log_level, message_header, hostname):
    #Constructs the message to submit to audit. Message header contains title number.
    msg = log_message + ' queue address is: %s. ' % hostname
    msg = msg + ' Signed in as: %s. ' % linux_user()
    msg = msg + ' Message header is: %s. ' % message_header
    msg = msg + ' Logged at: register-publisher/logs. '
    return msg


def get_message_header(mq_message):
    #contains the title number for audit
    try:
        return mq_message.properties['application_headers']
    except Exception as err:
        error_message = "message header not retrieved for message"
        logger.error(make_log_msg(error_message, 'error', 'no title', incoming_cfg.hostname))
        return error_message + str(err)


def linux_user():
    try:
        return pwd.getpwuid(os.geteuid()).pw_name
    except Exception as err:
        return "failed to get user: %s" % err


# This is executed as a separate process by unit tests; cannot refer to 'INCOMING_QUEUE' etc. in that case.
def run():
    """ "System of Record" to "Feeder" re-publisher. """

    logger = setup_logger(LOG_NAME + '.run')

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

        pull_message = " Pull from incoming queue: {}".format(message.delivery_info)
        logger.audit(make_log_msg(pull_message, 'debug', get_message_header(message), remove_username_password(incoming_cfg.hostname)))

        # Forward message to outgoing exchange, with retry management.
        outgoing_push_msg = " Push to outgoing queue: {}".format(message.delivery_info)
        logger.audit(make_log_msg(outgoing_push_msg, 'debug', get_message_header(message), remove_username_password(incoming_cfg.hostname)))

        ensure(producer.connection, producer, 'publish', body)
        acknowledge_push_message = "Push Acknowledged (implied): {}".format(message.delivery_tag)
        logger.audit(make_log_msg(acknowledge_push_message, 'debug', get_message_header(message), remove_username_password(outgoing_cfg.hostname)))

        # Acknowledge message only after publish(); if that fails, message is still in queue.
        message.ack()
        acknowledge_pull_message = "Acknowledged Pull: {}".format(message.delivery_tag)
        logger.audit(make_log_msg(acknowledge_pull_message, 'debug', get_message_header(message), remove_username_password(outgoing_cfg.hostname)))


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

def remove_username_password(endpoint_string):
    try:
        return re.sub('://[^:]+:[^@]+@', '://', endpoint_string)
    except:
        return "unknown endpoint"


if __name__ == "__main__":
    print("This module should be executed as a separate Python process")


@app.route("/outgoingcount")
def outgoing_count():
    jobs = get_queue_count(outgoing_count_cfg)
    return jobs, 200

@app.route("/incomingcount")
def incoming_count():
    jobs = get_queue_count(incoming_count_cfg)
    return jobs, 200

def get_queue_count(config):
    channel = setup_channel(config.hostname, exchange=config.exchange)
    try:
        name, jobs, consumers = channel.queue_declare(queue=config.queue, passive=True)
    finally:
        channel.close()
    return str(jobs)

@app.route("/")
def index():
    return 'register publisher flask service running', 200

