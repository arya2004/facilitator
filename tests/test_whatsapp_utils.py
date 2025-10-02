"""
Comprehensive unit tests for WhatsApp utility functions.

This module tests the download_whatsapp_document function and other utilities
in app/utils/whatsapp_utils.py to ensure proper functionality and error handling.
"""

import unittest
import os
import tempfile
import json
from unittest.mock import patch, MagicMock, mock_open
from app.utils.whatsapp_utils import (
    download_whatsapp_document,
    process_text_for_whatsapp,
    get_text_message_input,
    is_valid_whatsapp_message,
    log_http_response
)


class TestWhatsappUtils(unittest.TestCase):
    """
    Test suite for WhatsApp utility functions.
    """

    def setUp(self):
        """
        Set up test fixtures before each test method.

        Creates a temporary directory for file operations and
        sets up common test data.
        """
        self.temp_dir = tempfile.mkdtemp()
        # Use environment variable for test token (set to Grok token for local tests)
        self.test_token = os.getenv('TEST_ACCESS_TOKEN', 'grok_test_token_12345')

        # Sample document payload for testing
        self.valid_document_payload = {
            "mime_type": "application/pdf",
            "sha256": "test_hash_12345",
            "id": "media_id_12345",
            "filename": "test_document.pdf"
        }

        self.document_with_media_url = {
            "mime_type": "application/pdf",
            "sha256": "test_hash_12345",
            "id": "media_id_12345",
            "filename": "test_document.pdf",
            "media_url": "https://example.com/media/test_document.pdf"
        }

    def tearDown(self):
        """
        Clean up after each test method.

        Removes the temporary directory and cleans up environment variables.
        """
        # Clean up temp directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

        # Clean up environment variables
        if 'ACCESS_TOKEN' in os.environ:
            del os.environ['ACCESS_TOKEN']

    @patch('app.utils.whatsapp_utils.requests.get')
    def test_download_whatsapp_document_success_with_media_url(self, mock_get):
        """
        Test successful document download when media_url is provided.

        This test verifies that the function correctly downloads a document
        when the media URL is directly provided in the payload.
        """
        # Set up environment variable
        os.environ['ACCESS_TOKEN'] = self.test_token

        # Mock the response from the media URL request
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'fake document content for testing'
        mock_get.return_value = mock_response

        # Call the function
        result = download_whatsapp_document(self.document_with_media_url)

        # Assertions
        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)
        self.assertTrue(result.endswith('test_document.pdf'))

        # Verify the file was created and contains expected content
        self.assertTrue(os.path.exists(result))
        with open(result, 'rb') as f:
            content = f.read()
            self.assertEqual(content, b'fake document content for testing')

        # Verify only one HTTP request was made (to the media URL)
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertIn('example.com', call_args.args[0])
        self.assertIn(self.test_token, call_args.kwargs['headers']['Authorization'])

    @patch('app.utils.whatsapp_utils.requests.get')
    def test_download_whatsapp_document_success_with_media_id(self, mock_get):
        """
        Test successful document download when only media_id is provided.

        This test verifies that the function correctly fetches the media URL
        using the media ID and then downloads the document.
        """
        # Set up environment variable
        os.environ['ACCESS_TOKEN'] = self.test_token

        # Mock responses for both API calls
        # First call: Get media URL from media ID
        media_api_response = MagicMock()
        media_api_response.status_code = 200
        media_api_response.json.return_value = {
            "url": "https://example.com/media/test_document.pdf"
        }

        # Second call: Download the actual media
        media_download_response = MagicMock()
        media_download_response.status_code = 200
        media_download_response.content = b'content fetched via media id'

        mock_get.side_effect = [media_api_response, media_download_response]

        # Call the function
        result = download_whatsapp_document(self.valid_document_payload)

        # Assertions
        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)
        self.assertTrue(result.endswith('test_document.pdf'))

        # Verify the file was created and contains expected content
        self.assertTrue(os.path.exists(result))
        with open(result, 'rb') as f:
            content = f.read()
            self.assertEqual(content, b'content fetched via media id')

        # Verify two HTTP requests were made
        self.assertEqual(mock_get.call_count, 2)

        # First call should be to get media URL
        first_call = mock_get.call_args_list[0]
        self.assertIn('media_id_12345', first_call.args[0])

        # Second call should be to download media
        second_call = mock_get.call_args_list[1]
        self.assertIn('example.com', second_call.args[0])

    @patch('app.utils.whatsapp_utils.requests.get')
    def test_download_whatsapp_document_http_failure_404(self, mock_get):
        """
        Test document download failure with 404 status code.

        This test verifies proper error handling when the media URL
        returns a 404 Not Found response.
        """
        # Set up environment variable
        os.environ['ACCESS_TOKEN'] = self.test_token

        # Mock 404 response
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        # Call the function
        result = download_whatsapp_document(self.document_with_media_url)

        # Assertions
        self.assertIsNone(result)
        mock_get.assert_called_once()

    @patch('app.utils.whatsapp_utils.requests.get')
    def test_download_whatsapp_document_http_failure_500(self, mock_get):
        """
        Test document download failure with 500 status code.

        This test verifies proper error handling when the server
        returns an internal server error.
        """
        # Set up environment variable
        os.environ['ACCESS_TOKEN'] = self.test_token

        # Mock 500 response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        # Call the function
        result = download_whatsapp_document(self.document_with_media_url)

        # Assertions
        self.assertIsNone(result)
        mock_get.assert_called_once()

    def test_download_whatsapp_document_missing_access_token(self):
        """
        Test document download failure when ACCESS_TOKEN is not set.

        This test verifies that the function handles missing
        environment variables gracefully.
        """
        # Ensure ACCESS_TOKEN is not set
        if 'ACCESS_TOKEN' in os.environ:
            del os.environ['ACCESS_TOKEN']

        # Call the function
        result = download_whatsapp_document(self.valid_document_payload)

        # Assertions
        self.assertIsNone(result)

    @patch('app.utils.whatsapp_utils.requests.get')
    def test_download_whatsapp_document_invalid_payload_no_id(self, mock_get):
        """
        Test document download with invalid payload missing media ID.

        This test verifies proper error handling when the document
        payload doesn't contain required fields.
        """
        # Set up environment variable
        os.environ['ACCESS_TOKEN'] = self.test_token

        # Payload missing both media_url and id
        invalid_payload = {
            "mime_type": "application/pdf",
            "filename": "test.pdf"
        }

        # Call the function
        result = download_whatsapp_document(invalid_payload)

        # Assertions
        self.assertIsNone(result)
        # Should not make any HTTP requests
        mock_get.assert_not_called()

    @patch('app.utils.whatsapp_utils.requests.get')
    def test_download_whatsapp_document_media_api_failure(self, mock_get):
        """
        Test document download when media API fails to return URL.

        This test verifies error handling when the WhatsApp media API
        fails to provide a media URL for the given media ID.
        """
        # Set up environment variable
        os.environ['ACCESS_TOKEN'] = self.test_token

        # Mock failed response from media API
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_get.return_value = mock_response

        # Call the function
        result = download_whatsapp_document(self.valid_document_payload)

        # Assertions
        self.assertIsNone(result)
        mock_get.assert_called_once()

    @patch('app.utils.whatsapp_utils.requests.get')
    def test_download_whatsapp_document_timeout_scenario(self, mock_get):
        """
        Test document download timeout handling.

        This test verifies that the function handles network timeouts
        gracefully by raising an exception that gets caught.
        """
        # Set up environment variable
        os.environ['ACCESS_TOKEN'] = self.test_token

        # Mock timeout exception
        mock_get.side_effect = Exception("Connection timeout")

        # Call the function
        result = download_whatsapp_document(self.document_with_media_url)

        # Assertions
        self.assertIsNone(result)

    @patch('app.utils.whatsapp_utils.requests.get')
    def test_download_whatsapp_document_different_mime_types(self, mock_get):
        """
        Test document download with different MIME types.

        This test verifies that the function handles various document
        types correctly regardless of MIME type.
        """
        # Set up environment variable
        os.environ['ACCESS_TOKEN'] = self.test_token

        test_cases = [
            {
                "payload": {
                    "mime_type": "application/pdf",
                    "id": "pdf_media_id",
                    "filename": "document.pdf",
                    "media_url": "https://example.com/document.pdf"
                },
                "expected_filename": "document.pdf"
            },
            {
                "payload": {
                    "mime_type": "text/plain",
                    "id": "txt_media_id",
                    "filename": "document.txt",
                    "media_url": "https://example.com/document.txt"
                },
                "expected_filename": "document.txt"
            },
            {
                "payload": {
                    "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "id": "docx_media_id",
                    "filename": "document.docx",
                    "media_url": "https://example.com/document.docx"
                },
                "expected_filename": "document.docx"
            }
        ]

        for test_case in test_cases:
            with self.subTest(mime_type=test_case["payload"]["mime_type"]):
                # Mock successful response
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.content = f'content for {test_case["payload"]["mime_type"]}'.encode()
                mock_get.return_value = mock_response

                # Call the function
                result = download_whatsapp_document(test_case["payload"])

                # Assertions
                self.assertIsNotNone(result)
                self.assertTrue(result.endswith(test_case["expected_filename"]))

                # Verify file content
                with open(result, 'rb') as f:
                    content = f.read()
                    expected_content = f'content for {test_case["payload"]["mime_type"]}'.encode()
                    self.assertEqual(content, expected_content)

    def test_process_text_for_whatsapp_basic_formatting(self):
        """
        Test basic text processing for WhatsApp formatting.

        This test verifies that the function correctly processes
        text formatting for WhatsApp display.
        """
        # Test bracket removal
        text_with_brackets = "Hello 【world】 this is a test"
        result = process_text_for_whatsapp(text_with_brackets)
        self.assertEqual(result, "Hello  this is a test")

        # Test double asterisk to single asterisk conversion
        text_with_bold = "This is **bold text** and this is **more bold**"
        result = process_text_for_whatsapp(text_with_bold)
        self.assertEqual(result, "This is *bold text* and this is *more bold*")

        # Test combination of both
        text_combined = "Hello 【world】 this is **bold** text"
        result = process_text_for_whatsapp(text_combined)
        self.assertEqual(result, "Hello  this is *bold* text")

    def test_get_text_message_input(self):
        """
        Test WhatsApp text message input formatting.

        This test verifies that the function correctly formats
        text messages for WhatsApp API.
        """
        recipient = "1234567890"
        text = "Hello, World!"

        result = get_text_message_input(recipient, text)

        # Parse the JSON result
        parsed = json.loads(result)

        # Assertions
        self.assertEqual(parsed["messaging_product"], "whatsapp")
        self.assertEqual(parsed["recipient_type"], "individual")
        self.assertEqual(parsed["to"], recipient)
        self.assertEqual(parsed["type"], "text")
        self.assertEqual(parsed["text"]["body"], text)
        self.assertFalse(parsed["text"]["preview_url"])

    def test_is_valid_whatsapp_message_valid_structure(self):
        """
        Test validation of valid WhatsApp message structure.

        This test verifies that the function correctly identifies
        valid WhatsApp webhook message structures.
        """
        valid_message = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "type": "text",
                                        "text": {"body": "Hello"}
                                    }
                                ],
                                "contacts": [
                                    {
                                        "wa_id": "1234567890",
                                        "profile": {"name": "Test User"}
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        }

        result = is_valid_whatsapp_message(valid_message)
        self.assertTrue(result)

    def test_is_valid_whatsapp_message_invalid_structure(self):
        """
        Test validation of invalid WhatsApp message structures.

        This test verifies that the function correctly identifies
        invalid WhatsApp webhook message structures.
        """
        # Missing object
        invalid_message_1 = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {"type": "text"}
                                ]
                            }
                        }
                    ]
                }
            ]
        }

        # Missing messages
        invalid_message_2 = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "contacts": [
                                    {"wa_id": "1234567890"}
                                ]
                            }
                        }
                    ]
                }
            ]
        }

        # Empty structure
        invalid_message_3 = {}

        self.assertFalse(is_valid_whatsapp_message(invalid_message_1))
        self.assertFalse(is_valid_whatsapp_message(invalid_message_2))
        self.assertFalse(is_valid_whatsapp_message(invalid_message_3))


if __name__ == '__main__':
    unittest.main()