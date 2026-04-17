"""
Тесты для RequestID middleware.
"""
from django.test import TestCase, Client


class RequestIDMiddlewareTest(TestCase):

    def setUp(self):
        self.client = Client()

    def test_response_has_request_id_header(self):
        response = self.client.get('/')
        self.assertIn('X-Request-ID', response)
        self.assertTrue(len(response['X-Request-ID']) > 0)

    def test_custom_request_id_is_preserved(self):
        response = self.client.get('/', HTTP_X_REQUEST_ID='custom-123')
        self.assertEqual(response['X-Request-ID'], 'custom-123')

    def test_generated_request_id_is_12_chars(self):
        response = self.client.get('/')
        rid = response['X-Request-ID']
        self.assertEqual(len(rid), 12)
