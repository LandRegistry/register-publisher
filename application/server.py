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
app.config.from_object(os.environ.get('SETTINGS'))

# Routing key is same as queue name in "default direct exchange" case; exchange name is blank.
INCOMING_QUEUE = app.config['INCOMING_QUEUE']
OUTGOING_QUEUE = app.config['OUTGOING_QUEUE']
RP_HOSTNAME = app.config['RP_HOSTNAME']

# Relevant Exchange default values:
#   delivery_mode: '2' (persistent messages)
#   durable: True (exchange remains 'active' on server re-start)
incoming_exchange = kombu.Exchange(type="direct")
outgoing_exchange = kombu.Exchange(type="fanout")

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
def setup_connection(exchange=None):
    """ Attempt connection, with timeout.

    """

    logger.info("exchange: {}".format(exchange))

    # Attempt connection in a separate thread, as (implied) 'connect' call may hang if permissions not set etc.
    with stopit.ThreadingTimeout(10) as to_ctx_mgr:
        assert to_ctx_mgr.state == to_ctx_mgr.EXECUTING

        # N.B.: 'confirm_publish' refers to the "Confirmation Model", with the broker as client to a publisher.
        ## connection = kombu.Connection(hostname=RP_HOSTNAME, transport_options={'confirm_publish': confirm_publish})
        connection = kombu.Connection(hostname=RP_HOSTNAME)
        app.logger.info(RP_HOSTNAME)
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


# RabbitMQ channel.
def setup_channel(exchange=None, connection=None):

    channel = setup_connection(exchange).channel() if connection is None else connection.channel

    return channel


class Producer(kombu.Producer):
    """ Producer sub-class, using ASYNCHRONOUS "Confirmation Model" (aka "Publisher Acknowledgements").

    See: https://www.rabbitmq.com/confirms.html

    From http://amqp.readthedocs.org/en/latest/changelog.html:
    * There is now a new Connection confirm_publish that will force any basic_publish call to wait for confirmation.
    * Enabling publisher confirms like this degrades performance considerably, so use of 'confirm_select' is preferred.

    From https://pypi.python.org/pypi/amqp:
    * Channel.confirm_select() enables publisher confirms.
    * Channel.events['basic_ack'].append(my_callback) adds a callback to be called when a message is confirmed.
    * This callback is then called with the signature (delivery_tag, multiple)

    Overrides the 'publish' method of kombu.Producer class.
    """


    def __init__(self, channel, exchange=None, confirm=True, **kwargs):

        # Run-time checks.
        assert channel is not None
        assert exchange is not None
        assert type(confirm) is bool

        logger.debug("channel: {}".format(channel))
        logger.debug("exchange: {}".format(exchange))
        logger.debug("confirm: {}".format(confirm))

        # Use a set as a bag of distinct message identifiers.
        self.unacknowledged_messages = set()

        # Use "Confirmation Model", if specified.
        if confirm:

            def confirmation_callback(delivery_tag, multiple):
                """ Handle "Publisher Acknowledgement" from broker.

                Broker sends acknowledgement to a Publisher client - after receiving a corresponding ack. from a Consumer.

                Remove corresponding message id(s). from "Unacknowledged" list/set.

                Note that messages are persistent by default - i.e. they are saved by the broker, pending acknowledgement.


                From http://www.rabbitmq.com/amqp-0-9-1-reference.html#:

                'bit multiple':

                If set to 1, the delivery tag is treated as "up to and including", so that multiple messages can be
                acknowledged with a single method. If set to zero, the delivery tag refers to a single message.

                If the multiple field is 1, and the delivery tag is zero, this indicates acknowledgement of all
                outstanding messages.

                A message MUST not be acknowledged more than once. The receiving peer MUST validate that a non-zero
                delivery-tag refers to a delivered message, and raise a channel exception if this is not the case.
                """

                error = "confirmation_callback: "

                assert multiple in [0, 1]
                if multiple == 1:
                    error += "multiple-message acknowledgement not supported."
                    raise NotImplementedError(error)

                if delivery_tag in self.unacknowledged_messages:
                    self.unacknowledged_messages.remove(delivery_tag)
                else:
                    error += "delivery_tag '{}' to be removed not found in 'unacknowledged' set".format(delivery_tag)
                    raise RuntimeError(error)

            channel.confirm_select()
            channel.events['basic_ack'].add(confirmation_callback)

        ## TO DO: update a count (corresponding to 'delivery_tag' value, we hope) and add it to set. Clumsy.
        # Invoke parent class with full keyword arguments.
        super().__init__(channel, exchange=exchange, **kwargs)


    def publish(self, body=None, routing_key=None, **kwargs):
        """Publish message after noting id. in "Unacknowledged" set """

        # self.unacknowledged_messages.add(message.delivery_tag)
        super().publish(body, routing_key=routing_key, **kwargs)


# Get Producer, for 'outgoing' exchange and JSON "serializer" by default.
def setup_producer(exchange=outgoing_exchange, queue_name=OUTGOING_QUEUE, confirm=True):

    channel = setup_channel(exchange=exchange)
    logger.info("queue_name: {}".format(queue_name))

    # Make sure that outgoing queue exists!
    setup_queue(channel, name=queue_name, exchange=exchange)

    ## ASYNCHRONOUS 'Publisher Acknowledgements'. Not well-supported by Kombu/py-amqp.
    producer = Producer(channel, exchange=exchange, confirm=confirm)

    return producer


# Consumer, for 'incoming' queue by default.
def setup_consumer(exchange=incoming_exchange, queue_name=INCOMING_QUEUE, on_message=None):
    """ Create consumer with single queue and callback """

    channel = setup_channel(exchange=exchange)
    logger.info("queue_name: {}".format(queue_name))

    # A consumer needs a queue, so create one (if necessary).
    queue = setup_queue(channel, name=queue_name, exchange=exchange)

    consumer = kombu.Consumer(channel, queues=queue, on_message=on_message, accept=['json'])

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

    logger.info("queue name, exchange, key: {}, {}, {}".format(queue.name, exchange, routing_key))

    return queue


def run():

    # Producer for outgoing (default) exchange.
    producer = setup_producer()

    # This is used to consume messages from the "System of Record", then forward them to the outside world.
    # @TO DO: This may unpack incoming messages, then pack them again when forwarding; consider 'on_message()' instead.
    # ['body' is decoded content, 'message' is the packet as a whole].

    def process_message(message, exc):
        ''' Forward messages from the 'System of Record' to the outside world '''

        logger.info("RECEIVED MSG - delivery_info: {}".format(message.delivery_info))

        # Forward message to outgoing exchange.
        producer.publish(message=message, routing_key=OUTGOING_QUEUE)

        # Acknowledge message only after publish(); if that fails, message is still in queue.
        message.ack()

    # Create consumer with default exchange/queue.
    consumer = setup_consumer(on_message=process_message)
    consumer.consume()

    # Loop "forever", as a service.
    # N.B.: if there is a serious network failure or the like then this will keep logging errors!
    while True:
        try:
            # "Wait for a single event from the server".
            consumer.connection.drain_events()

        # Permit an explicit abort.
        except KeyboardInterrupt:
            logger.error("KeyboardInterrupt received!")
            break
        # Trap (log) everything else.
        except Exception as e:
            logger.error(e)

            # If we ignore the problem, perhaps it will go away ...
            time.sleep(10)

    # Graceful degradation.
    producer.close()
    consumer.close()


if __name__ == "__main__":
    print("This module should be executed as a separate Python process")
