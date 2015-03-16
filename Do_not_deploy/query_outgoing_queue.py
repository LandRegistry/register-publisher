from kombu import Connection, Exchange, Queue
from flask import Flask
import os

app = Flask(__name__)
app.config.from_object(os.environ.get('SETTINGS'))

@app.route("/getnextqueuemessage")
#Gets the next message from target queue.  Returns the signed JSON.
def get_last_queue_message():
    #: By default messages sent to exchanges are persistent (delivery_mode=2),
    #: and queues and exchanges are durable.
    exchange = Exchange()
    connection = Connection(app.config['OUTGOING_QUEUE_HOSTNAME'])

    # Create/access a queue bound to the connection.
    queue = Queue(app.config['OUTGOING_QUEUE'],
                  exchange,
                  routing_key=app.config['OUTGOING_QUEUE'])(connection)
    queue.declare()

    message = queue.get()

    if message:
        signature = message.body
        message.ack() #acknowledges message, ensuring its removal.
        return signature
    else:
        return "no message"



@app.route("/removeallmessages")
#Gets the next message from target queue.  Returns the signed JSON.
def remove_all_messages():
    while True:
        queue_message = get_last_incoming_queue_message()
        if queue_message == 'no message':
            break
    return "done", 202


@app.route("/")
def check_status():
    return "Everything is OK"

