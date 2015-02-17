import os
from flask import Flask
from kombu import Exchange, Queue, BrokerConnection, Consumer, Producer
from kombu.common import maybe_declare
from kombu.log import get_logger
from kombu.utils.debug import setup_logging

'''
Register-Publisher: forwards messages from the System of Record to the outside world, via AMQP "broadcast".

* AMQP defines four type of exchange, one of which is 'fanout'; that enables clients to subscribe on an 'ad hoc' basis.
* RabbitMQ etc. should have default exchanges in place; 'amq.fanout' for example.
* The "System of Record" (SoR) could publish directly to a fanout exchange and indeed used to do so.
* A separate "Register-Publisher" (RP) module is required to isolate the SoR from the outside world.
* Thus the SoR publishes to the RP via a 'direct' exchange, which in turn forwards the messages to the fanout exchange.

See http://www.rabbitmq.com/blog/2010/10/19/exchange-to-exchange-bindings for an alternative arrangement, which may be
unique to RabbitMQ. This might avoid the unpack/pack issue of 'process_message()' but it does not permit logging etc.

'''

# Flask is invoked here mostly to get the configuration values in a consistent manner!
# It is also useful for testing however.
app = Flask(__name__)
app.config.from_object(os.environ.get('SETTINGS'))

# Set up root logger
ll = app.config('LOG_LEVEL')
setup_logging(loglevel=ll, loggers=[''])
logger = get_logger(__name__)

# Routing key is same as queue name in "default direct exchange" case; exchange name is blank.
SOR_TO_RP_QUEUE = os.environ['SOR_TO_RP_QUEUE']
RP_HOSTNAME = os.environ['RP_HOSTNAME']
incoming_exchange = Exchange(type="direct", durable=True)
incoming_queue = Queue(SOR_TO_RP_QUEUE, exchange=incoming_exchange)
outgoing_exchange = Exchange(type="fanout")

def run():

    # RabbitMQ connection & channel; default user/password.
    # ['connection' is via TCP or the like. 'channel' is a "virtual connection"].
    connection = BrokerConnection(hostname=RP_HOSTNAME, userid="guest", password="guest", virtual_host="/")
    channel = connection.channel()

    # Producer: could get one from pool instead.
    producer = Producer(channel, exchange=outgoing_exchange, serializer='json')

    # Create exchange on broker if necessary.
    maybe_declare(outgoing_exchange, producer.channel)

    # This is used to consume messages from the "System of Record", then forward them to the outside world.
    # @TO DO: This may unpack incoming messages, then pack them again when forwarding; consider 'on_message()' instead.
    # ['body' is decoded content, 'message' is the packet as a whole].
    def process_message(body, message):
        ''' Forward messages from the 'System of Record' to the outside world '''

        logger.info("RECEIVED MSG - delivery_info: %r" % message.delivery_info)
        message.ack()

        # Forward message to 'fanout' exchange.
        producer.publish(payload=body)

    consumer = Consumer(channel, incoming_queue, callbacks=[process_message], accept=['json'])
    ##consumer.consume()

    # Create exchange on broker if necessary.
    maybe_declare(incoming_exchange, consumer.channel)


    # Loop "forever", as a service.
    while True:
        try:
            connection.drain_events()
        except Exception as e:
            logger.error(e)
            break

    # Graceful degradation.
    connection.close()
    channel.close()
    producer.close()
    consumer.close()

if __name__ == "__main__":
    print("This module should be executed as a separate Python process")

run()
