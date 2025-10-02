import unittest
from unittest.mock import patch, mock_open, MagicMock
import os
import tempfile
import logging
from app.services.openai_service import generate_meet_link, extract_event_details, upload_file_response


class TestOpenAIServiceLogging(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures."""
        self.logger = logging.getLogger('app.services.openai_service')

    @patch('app.services.openai_service.logger')
    def test_generate_meet_link_logs_file_read_success(self, mock_logger):
        """Test that generate_meet_link logs successful file read."""
        mock_file_content = "https://meet.google.com/abc-defg-hij\nhttps://meet.google.com/klm-nopq-rst\n"

        with patch('builtins.open', mock_open(read_data=mock_file_content)) as mock_file:
            result = generate_meet_link()

            # Verify logging calls
            mock_logger.info.assert_any_call("generate_meet_link called with provider: google")
            mock_logger.debug.assert_any_call("Attempting to read meet_links.txt")
            mock_logger.info.assert_any_call("Retrieved Meet link from file: https://meet.google.com/abc-defg-hij")
            mock_logger.debug.assert_any_call("Remaining links in file: 1")
            mock_logger.debug.assert_any_call("Successfully updated meet_links.txt with remaining links")

            # Verify file operations
            mock_file.assert_called_with("meet_links.txt", "r+")
            handle = mock_file()
            handle.readlines.assert_called_once()
            handle.seek.assert_called_once_with(0)
            handle.writelines.assert_called_once()
            handle.truncate.assert_called_once()

    @patch('app.services.openai_service.logger')
    def test_generate_meet_link_logs_file_not_found(self, mock_logger):
        """Test that generate_meet_link logs file not found and falls back to API."""
        with patch('builtins.open', side_effect=FileNotFoundError):
            with patch('app.services.openai_service.service_account') as mock_sa:
                # Mock the API fallback
                mock_service = MagicMock()
                mock_sa.Credentials.from_service_account_info.return_value = MagicMock()
                with patch('app.services.openai_service.build', return_value=mock_service):
                    mock_event = {
                        'conferenceData': {
                            'entryPoints': [{'uri': 'https://meet.google.com/test'}]
                        }
                    }
                    mock_service.events().insert().execute.return_value = mock_event

                    result = generate_meet_link()

                    # Verify logging calls
                    mock_logger.info.assert_any_call("generate_meet_link called with provider: google")
                    mock_logger.debug.assert_any_call("Attempting to read meet_links.txt")
                    mock_logger.warning.assert_any_call("meet_links.txt not found. Falling back to API.")
                    mock_logger.info.assert_any_call("Falling back to API to generate new Meet link")
                    mock_logger.info.assert_any_call("Successfully generated Meet link via API: https://meet.google.com/test")

    @patch('app.services.openai_service.logger')
    def test_generate_meet_link_logs_empty_file_fallback(self, mock_logger):
        """Test that generate_meet_link logs empty file and falls back to API."""
        with patch('builtins.open', mock_open(read_data="")):
            with patch('app.services.openai_service.service_account') as mock_sa:
                mock_service = MagicMock()
                mock_sa.Credentials.from_service_account_info.return_value = MagicMock()
                with patch('app.services.openai_service.build', return_value=mock_service):
                    mock_event = {
                        'conferenceData': {
                            'entryPoints': [{'uri': 'https://meet.google.com/test'}]
                        }
                    }
                    mock_service.events().insert().execute.return_value = mock_event

                    result = generate_meet_link()

                    mock_logger.warning.assert_any_call("meet_links.txt is empty. Falling back to API.")

    @patch('app.services.openai_service.logger')
    def test_extract_event_details_logs_success(self, mock_logger):
        """Test that extract_event_details logs successful extraction."""
        with patch('app.services.openai_service.get_openai_client') as mock_client:
            mock_response = MagicMock()
            mock_response.choices[0].message.content = "Title: Test Event\nDate: 2024-01-01\nTime: 10:00 AM\nLocation: Office\nNotes: Test notes"
            mock_client.return_value.chat.completions.create.return_value = mock_response

            result = extract_event_details("Schedule a test event")

            mock_logger.info.assert_any_call("Starting event details extraction from message")
            mock_logger.debug.assert_any_call("Input message: Schedule a test event")
            mock_logger.debug.assert_any_call("Making OpenAI API call for event extraction")
            mock_logger.info.assert_any_call("LLM extracted text: Title: Test Event\nDate: 2024-01-01\nTime: 10:00 AM\nLocation: Office\nNotes: Test notes")
            mock_logger.info.assert_any_call("Successfully extracted event details: {'title': 'Test Event', 'date': '2024-01-01', 'time': '10:00 AM', 'location': 'Office', 'notes': 'Test notes'}")

    @patch('app.services.openai_service.logger')
    def test_extract_event_details_logs_error(self, mock_logger):
        """Test that extract_event_details logs API errors."""
        with patch('app.services.openai_service.get_openai_client') as mock_client:
            mock_client.return_value.chat.completions.create.side_effect = Exception("API Error")

            result = extract_event_details("Schedule an event")

            mock_logger.error.assert_called_with("OpenAI API error while extracting event details: API Error", exc_info=True)

    @patch('app.services.openai_service.logger')
    def test_upload_file_response_logs_success(self, mock_logger):
        """Test that upload_file_response logs successful upload."""
        with patch('app.services.openai_service.authenticate') as mock_auth:
            mock_service = MagicMock()
            mock_auth.return_value = mock_service
            mock_service.files().create().execute.return_value = {'id': 'test_file_id'}

            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(b"test content")
                temp_file_path = temp_file.name

            try:
                result = upload_file_response(temp_file_path)

                mock_logger.info.assert_any_call(f"Starting file upload: {temp_file_path}")
                mock_logger.debug.assert_any_call("Authenticating with Google Drive")
                mock_logger.debug.assert_any_call("Creating media upload object")
                mock_logger.debug.assert_any_call("Executing file upload to Google Drive")
                mock_logger.info.assert_any_call(f"Successfully uploaded file {os.path.basename(temp_file_path)} with ID: test_file_id")
            finally:
                os.unlink(temp_file_path)

    @patch('app.services.openai_service.logger')
    def test_upload_file_response_logs_error(self, mock_logger):
        """Test that upload_file_response logs upload errors."""
        with patch('app.services.openai_service.authenticate', side_effect=Exception("Auth failed")):
            result = upload_file_response("/nonexistent/file.txt")

            mock_logger.error.assert_called_with("Error uploading file /nonexistent/file.txt: Auth failed", exc_info=True)


if __name__ == '__main__':
    unittest.main()