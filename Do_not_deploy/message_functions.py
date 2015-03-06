from kombu import Connection, Exchange, Queue

#Gets the next message from target queue.  Returns the signed JSON.
def get_last_incoming_queue_message(show_output):
    #: By default messages sent to exchanges are persistent (delivery_mode=2),
    #: and queues and exchanges are durable.
    exchange = Exchange()
    connection = Connection('amqp://guest:guest@localhost:5672//')

    # Create/access a queue bound to the connection.
    queue = Queue('OUTGOING_QUEUE',
                  exchange,
                  routing_key='OUTGOING_QUEUE')(connection)
    queue.declare()

    message = queue.get()

    if message:
        signature = message.body
        message.ack() #acknowledges message, ensuring its removal.
        if show_output:
            print (signature)
        return signature

    else:
        if show_output:
            print ("no message")
        return ("no message")


def remove_all_messages(show_output):
    while True:
        queue_message = get_last_incoming_queue_message(False)
        if queue_message == 'no message':
            break

