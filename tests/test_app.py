import os
import unittest
import unittest.mock
from application import server
from application.server import app


class TestSequenceFunctions(unittest.TestCase):

    def setUp(self):
        app.config.from_object(os.environ.get('SETTINGS'))
        self.app = server.app.test_client()

    def test_server(self):
        self.assertEqual((self.app.get('/')).status, '200 OK')


    @mock.patch('requests.post')
    @mock.patch('requests.Response')
    def test_insert_route(self, mock_response, mock_post):
        mock_response.text = "row inserted"
        mock_post.return_value = mock_response
        headers = {'content-Type': 'application/json'}
        response = self.app.post('/insert', data = TEST_TITLE, headers = headers)
        self.assertEqual(response.data, "row inserted")



