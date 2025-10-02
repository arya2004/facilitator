import logging
from flask import current_app, jsonify
import json
import requests
import os
from app.services.openai_service import generate_response
import re

WHATSAPP_ACCESS_TOKEN = os.getenv("ACCESS_TOKEN") 


def log_http_response(response):
    logging.info(f"Status: {response.status_code}")
    logging.info(f"Content-type: {response.headers.get('content-type')}")
    logging.info(f"Body: {response.text}")


def get_text_message_input(recipient, text):
    return json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
    )


# def generate_response(response):
#     # Return text in uppercase
#     return response.upper()


def send_message(data):
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
    }

    url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{current_app.config['PHONE_NUMBER_ID']}/messages"

    try:
        response = requests.post(
            url, data=data, headers=headers, timeout=10
        )  # 10 seconds timeout as an example
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
    except requests.Timeout:
        logging.error("Timeout occurred while sending message")
        return jsonify({"status": "error", "message": "Request timed out"}), 408
    except (
        requests.RequestException
    ) as e:  # This will catch any general request exception
        logging.error(f"Request failed due to: {e}")
        return jsonify({"status": "error", "message": "Failed to send message"}), 500
    else:
        # Process the response as normal
        log_http_response(response)
        return response


def process_text_for_whatsapp(text):
    # Remove brackets
    pattern = r"\【.*?\】"
    # Substitute the pattern with an empty string
    text = re.sub(pattern, "", text).strip()

    # Pattern to find double asterisks including the word(s) in between
    pattern = r"\*\*(.*?)\*\*"

    # Replacement pattern with single asterisks
    replacement = r"*\1*"

    # Substitute occurrences of the pattern with the replacement
    whatsapp_style_text = re.sub(pattern, replacement, text)

    return whatsapp_style_text

import os
import tempfile
import logging
import requests

def download_whatsapp_document(document):
    """
    Downloads the attached document using WhatsApp's media API and saves it temporarily.
    If 'media_url' is not provided, the function will use the media ID to request the media URL.
    """
    try:
        file_name = document.get("filename")
        media_url = document.get("media_url")
        if not media_url:
            # Fallback: use the media ID to fetch the URL from WhatsApp's API.
            media_id = document.get("id")
            if not media_id:
                logging.error("No media_url or media ID provided in the document payload.")
                return None
            whatsapp_access_token = os.getenv("ACCESS_TOKEN")
            media_api_url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{media_id}"
            headers = {"Authorization": f"Bearer {whatsapp_access_token}"}
            r = requests.get(media_api_url, headers=headers)
            if r.status_code == 200:
                media_data = r.json()
                media_url = media_data.get("url")
            else:
                logging.error(f"Failed to retrieve media URL for media ID {media_id}, status code: {r.status_code}")
                return None

        headers = {"Authorization": f"Bearer {os.getenv('ACCESS_TOKEN')}"}
        response = requests.get(media_url, headers=headers)
        if response.status_code != 200:
            logging.error(f"Failed to download media from {media_url}, status code: {response.status_code}")
            return None

        temp_dir = tempfile.gettempdir()
        local_file_path = os.path.join(temp_dir, file_name)
        with open(local_file_path, "wb") as file:
            file.write(response.content)
        logging.info(f"File downloaded and saved to {local_file_path}")
        return local_file_path

    except Exception as e:
        logging.error(f"Error downloading document: {e}")
        return None

def _extract_message_context(body):
    """
    Extracts user and message information from the webhook body.

    Args:
        body: The webhook request body from WhatsApp

    Returns:
        tuple: (wa_id, name, message) containing user ID, name, and message object
    """
    wa_id = body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
    name = body["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]
    message = body["entry"][0]["changes"][0]["value"]["messages"][0]
    return wa_id, name, message


def _handle_text_message(message, wa_id, name):
    """
    Handles incoming text messages.

    Args:
        message: The message object containing text
        wa_id: WhatsApp ID of the sender
        name: Name of the sender

    Returns:
        str: Generated response text
    """
    message_body = message["text"]["body"]
    logging.info(f"Processing text message: {message_body}")
    return generate_response(message_body, wa_id, name, local_file_path=None)


def _handle_document_message(message, wa_id, name):
    """
    Handles incoming document messages.

    Args:
        message: The message object containing document
        wa_id: WhatsApp ID of the sender
        name: Name of the sender

    Returns:
        str: Generated response text
    """
    local_file_path = download_whatsapp_document(message["document"])
    message_body = message["document"].get("caption", "")
    logging.info(f"Processing document message with caption: {message_body}")
    return generate_response(message_body, wa_id, name, local_file_path=local_file_path)


def _send_whatsapp_response(response_text):
    """
    Sends a formatted response back to WhatsApp.

    Args:
        response_text: The response text to send
    """
    formatted_response = process_text_for_whatsapp(response_text)
    data = get_text_message_input(current_app.config["RECIPIENT_WAID"], formatted_response)
    send_message(data)


def process_whatsapp_message(body):
    """
    Processes an incoming WhatsApp message.

    Delegates to appropriate handler based on message type (text or document).

    Args:
        body: The webhook request body from WhatsApp
    """
    wa_id, name, message = _extract_message_context(body)

    if "document" in message:
        response = _handle_document_message(message, wa_id, name)
    else:
        response = _handle_text_message(message, wa_id, name)

    _send_whatsapp_response(response)


def is_valid_whatsapp_message(body):
    """
    Check if the incoming webhook event has a valid WhatsApp message structure.
    """
    return (
        body.get("object")
        and body.get("entry")
        and body["entry"][0].get("changes")
        and body["entry"][0]["changes"][0].get("value")
        and body["entry"][0]["changes"][0]["value"].get("messages")
        and body["entry"][0]["changes"][0]["value"]["messages"][0]
    )
