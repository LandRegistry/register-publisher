from .server import run
import threading

# Run the flask app in a new thread.
process_thread = threading.Thread(name='register_publisher', target=run)
process_thread.setDaemon(True)
process_thread.start()
