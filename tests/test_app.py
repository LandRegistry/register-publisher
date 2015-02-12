import unittest
from application import server
from application.server import app
from application.server import build_system_of_record_json_string
from application.server import return_signed_data
import os

import mock

TEST_TITLE = '{"titleno": "DN1"}'
TEST_SIGNATURE = "b6vjrGcLzq97_2D5h286TkRu_Kf0GonPDsndkGjhtrTBlHKIcF5H18hu635VEork_kr811ZS7B-4FuaCQFk6CvIQpNhxaMxI7m56HRQnj8ZsRSkX74xEKQUqf3k26ZdkODWJVsKyd_grJ39tfwMvJJb9V5REpRa8qXGr1eXgK4gEqwmo2fkow_W8q_yqMTTm9jOuVeFaqCQzAJBFUEWgkuTLRd91Wm8MlF4RhG_w1YktGzVath3tvaiTXNfiyfZbzPu9viotpP81gsFpWw6xocrUDbKhhXw2rm0BU2NvqSMXJ3X1qZs-VZibnWRJNNyt3sFapDojlDs99cL_uQ2aBQ"
VERIFY_DATA = '{"sig" : "b6vjrGcLzq97_2D5h286TkRu_Kf0GonPDsndkGjhtrTBlHKIcF5H18hu635VEork_kr811ZS7B-4FuaCQFk6CvIQpNhxaMxI7m56HRQnj8ZsRSkX74xEKQUqf3k26ZdkODWJVsKyd_grJ39tfwMvJJb9V5REpRa8qXGr1eXgK4gEqwmo2fkow_W8q_yqMTTm9jOuVeFaqCQzAJBFUEWgkuTLRd91Wm8MlF4RhG_w1YktGzVath3tvaiTXNfiyfZbzPu9viotpP81gsFpWw6xocrUDbKhhXw2rm0BU2NvqSMXJ3X1qZs-VZibnWRJNNyt3sFapDojlDs99cL_uQ2aBQ", "data":{"titleno" : "DN1"}}'

class TestSequenceFunctions(unittest.TestCase):

    def setUp(self):
        app.config.from_object(os.environ.get('SETTINGS'))
        self.app = server.app.test_client()

    def test_server(self):
        self.assertEqual((self.app.get('/')).status, '200 OK')

    def test_build_system_of_record_json_string(self):
        test_string = build_system_of_record_json_string({"a":"1"}, {"b":"2" })
        self.assertEqual('{"sig": {"b": "2"}, "data": {"a": "1"}}', test_string)

    def test_return_signed_data(self):
        signed_string = return_signed_data(TEST_TITLE)
        self.assertEqual(signed_string, TEST_SIGNATURE)

    def test_sign_route(self):
        headers = {'content-Type': 'application/json'}
        response = self.app.post('/sign', data = TEST_TITLE, headers = headers)
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.data, TEST_SIGNATURE)

    def test_verify_route(self):
        headers = {'content-Type': 'application/json'}
        response = self.app.post('/verify', data = VERIFY_DATA, headers = headers)
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.data, "verified")

    @mock.patch('requests.post')
    @mock.patch('requests.Response')
    def test_insert_route(self, mock_response, mock_post):
        mock_response.text = "row inserted"
        mock_post.return_value = mock_response
        headers = {'content-Type': 'application/json'}
        response = self.app.post('/insert', data = TEST_TITLE, headers = headers)
        self.assertEqual(response.data, "row inserted")



