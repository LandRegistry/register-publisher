import unittest
from application import server
from application.server import app
import os
import mock

class TestSequenceFunctions(unittest.TestCase):

    def setUp(self):
        app.config.from_object(os.environ.get('SETTINGS'))
        self.app = server.app.test_client()

    @mock.patch('application.server.get_queue_count')
    def test_outgoingcount_endpoint(self, mock_count):
        def fake_count(queue):
            return "25"
        mock_count.side_effect = fake_count
        self.assertEqual(self.app.get('/outgoingcount').status, '200 OK')
        self.assertEqual(self.app.get('/outgoingcount').data.decode("utf-8"), "25")

    @mock.patch('application.server.get_queue_count')
    def test_incomingcount_endpoint(self, mock_count):
        def fake_count(queue):
            return "12"
        mock_count.side_effect = fake_count
        self.assertEqual(self.app.get('/incomingcount').status, '200 OK')
        self.assertEqual(self.app.get('/incomingcount').data.decode("utf-8"), "12")

    def test_index(self):
        self.assertEqual(self.app.get('/').status, '200 OK')
        self.assertEqual(self.app.get('/').data.decode("utf-8"), 'register publisher flask service running')