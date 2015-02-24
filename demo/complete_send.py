"""
Example producer that sends a single message and exits.
You can use `complete_receive.py` to receive the message sent.
"""
from kombu import Connection, Producer, Exchange, Queue

#: By default messages sent to exchanges are persistent (delivery_mode=2),
#: and queues and exchanges are durable.

exchange = Exchange()
connection = Connection('amqp://guest:guest@localhost:5672//')

# Create (if necessary) a queue bound to the connection.
queue = Queue('kombu_demo', exchange, routing_key='kombu_demo')(connection)
queue.declare()

with connection as conn:

    #: Producers are used to publish messages.
    #: a default exchange and routing key can also be specified
    #: as arguments the Producer, but we rather specify this explicitly
    #: at the publish call.
    producer = Producer(conn)

    #: Publish the message using the json serializer (which is the default),
    #: and zlib compression. The kombu consumer will automatically detect
    #: encoding, serialization and compression used and decode accordingly.
    producer.publish({'hello': 'world'}, exchange=exchange, routing_key='kombu_demo',  serializer='json')


