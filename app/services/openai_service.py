import os
import logging
import datetime
import re
import json
import pytz
import random
from dotenv import load_dotenv
from openai import OpenAI
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.errors import HttpError  # For more specific error handling
from googleapiclient.http import MediaFileUpload

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
SHARED_FOLDER_ID = os.getenv("SHARED_FOLDER_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_CALENDAR_CREDENTIALS = os.getenv("GOOGLE_CALENDAR_CREDENTIALS")
CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID")

# Initialize OpenAI Client (lazy initialization)
client = None

def get_openai_client():
    """Get or create OpenAI client with lazy initialization."""
    global client
    if client is None:
        client = OpenAI(api_key=OPENAI_API_KEY)
    return client

# Use the cost-efficient ChatCompletion model.
DEFAULT_MODEL = "gpt-4o-mini"

# Updated system prompt for more detailed extraction.
DEFAULT_SYSTEM_PROMPT = (
    "You are an AI assistant that extracts event and reminder details from messages. "
    "Your task is to identify the following details if provided: "
    "Title, Date (in YYYY-MM-DD), Time (in HH:MM AM/PM or indicate 'All Day' if not provided), "
    "Location, and Additional Notes. "
    "If any detail is missing, indicate 'Not provided'."
)

FOLDER_MAP = {
    "college_daa":    os.getenv("FOLDER_ID_COLLEGE_DAA"),
    "college_sdam":   os.getenv("FOLDER_ID_COLLEGE_SDAM"),
    "college_misc":   os.getenv("FOLDER_ID_COLLEGE_MISC"),
    "personal_docs":  os.getenv("FOLDER_ID_PERSONAL_DOCS"),
    "personal_misc":  os.getenv("FOLDER_ID_PERSONAL_MISC"),
}

def authenticate():
    """Authenticate to Google Drive using service account credentials."""
    service_account_info = json.loads(GOOGLE_CALENDAR_CREDENTIALS)
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/drive.file"]
    )
    return build("drive", "v3", credentials=credentials)

def extract_event_details(message_body):
    """Uses OpenAI to extract event details like title, date, time, location, and notes from the message."""
    logger.info("Starting event details extraction from message")
    logger.debug(f"Input message: {message_body}")

    prompt = (
        "Extract the following details from the message below:\n"
        "Title: <event title>\n"
        "Date: <YYYY-MM-DD> or 'Not provided'\n"
        "Time: <HH:MM AM/PM> or 'All Day' or 'Not provided'\n"
        "Location: <location> or 'Not provided'\n"
        "Notes: <additional notes> or 'Not provided'\n\n"
        f"Message: {message_body}"
    )

    try:
        logger.debug("Making OpenAI API call for event extraction")
        response = get_openai_client().chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        extracted_text = response.choices[0].message.content.strip()
        logger.info(f"LLM extracted text: {extracted_text}")

        # Extract details using regex
        title_match = re.search(r"Title:\s*(.+)", extracted_text)
        date_match = re.search(r"Date:\s*([\d]{4}-[\d]{2}-[\d]{2}|Not provided)", extracted_text)
        time_match = re.search(r"Time:\s*([\d:]+\s*[APMapm]+|All Day|Not provided)", extracted_text)
        location_match = re.search(r"Location:\s*(.+)", extracted_text)
        notes_match = re.search(r"Notes:\s*(.+)", extracted_text)

        event_details = {
            "title": title_match.group(1).strip() if title_match else "Not provided",
            "date": date_match.group(1).strip() if date_match and date_match.group(1) != "Not provided" else None,
            "time": time_match.group(1).strip() if time_match and time_match.group(1) not in ["Not provided"] else "All Day",
            "location": location_match.group(1).strip() if location_match else "Not provided",
            "notes": notes_match.group(1).strip() if notes_match else "Not provided"
        }
        logger.info(f"Successfully extracted event details: {event_details}")
        return event_details

    except Exception as e:
        logger.error(f"OpenAI API error while extracting event details: {e}", exc_info=True)
        return None

def schedule_google_calendar_event(event_details):
    """Schedules an event in Google Calendar and returns event details."""
    logger.info("Starting Google Calendar event scheduling")
    logger.debug(f"Event details: {event_details}")

    try:
        logger.debug("Authenticating with Google Calendar API")
        credentials = service_account.Credentials.from_service_account_info(
            json.loads(GOOGLE_CALENDAR_CREDENTIALS),
            scopes=["https://www.googleapis.com/auth/calendar"]
        )
        service = build("calendar", "v3", credentials=credentials)

        if event_details["date"]:
            # If a specific time is provided, parse and format it to the required ISO 8601 format.
            if event_details["time"] != "All Day":
                try:
                    # Assuming time is in "HH:MM AM/PM" format. Combine with date.
                    combined_str = f"{event_details['date']} {event_details['time']}"
                    dt = datetime.datetime.strptime(combined_str, "%Y-%m-%d %I:%M %p")

                    # Set IST timezone
                    ist = pytz.timezone("Asia/Kolkata")
                    dt_ist = ist.localize(dt)  # Localize to IST

                    # Format it as per Google Calendar API requirements
                    event_datetime = dt_ist.strftime("%Y-%m-%dT%H:%M:%S%z")  # Keeps timezone offset

                    start = {"dateTime": event_datetime, "timeZone": "Asia/Kolkata"}
                    end = {"dateTime": event_datetime, "timeZone": "Asia/Kolkata"}
                    logger.debug(f"Parsed event datetime: {event_datetime}")
                except Exception as parse_error:
                    logger.error(f"Error parsing date and time: {parse_error}", exc_info=True)
                    return None
            else:
                start = {"date": event_details["date"]}
                end = {"date": event_details["date"]}
                logger.debug("Event is all-day")
        else:
            logger.error("No valid date provided in event details.")
            return None

        event = {
            "summary": event_details["title"],
            "location": event_details["location"] if event_details["location"] != "Not provided" else "",
            "description": event_details["notes"] if event_details["notes"] != "Not provided" else "",
            "start": start,
            "end": end,
            "reminders": {"useDefault": True}
        }

        logger.debug("Inserting event into Google Calendar")
        created_event = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        event_link = created_event.get("htmlLink")
        logger.info(f"Successfully scheduled event: {event_details['title']} - {event_link}")

        return {
            "title": event_details["title"],
            "date": event_details["date"],
            "time": event_details["time"],
            "location": event_details["location"],
            "notes": event_details["notes"],
            "event_link": event_link
        }

    except HttpError as http_err:
        logger.error(f"Google Calendar API HTTP error: {http_err.resp.status} - {http_err.content}")
        return None
    except Exception as e:
        logger.error(f"Google Calendar API error: {e}", exc_info=True)
        return None

def generate_meet_link(provider="google"):
    """
    Generate a Google Meet link by reading from meet_links.txt or creating via API.

    This function attempts to read a Meet link from a local file first, removing the used link
    from the file. If the file is empty or doesn't exist, it falls back to generating a new
    Meet link via the Google Calendar API.

    Args:
        provider (str): The meeting provider. Currently only supports "google".

    Returns:
        str: A Google Meet link URL

    Logging:
        - INFO: Function entry with provider, successful link retrieval/generation
        - DEBUG: File operations, API calls, remaining links count
        - WARNING: File not found, empty file (with fallback to API)
        - ERROR: File access errors, API failures with full exception details
    """
    logger.info(f"generate_meet_link called with provider: {provider}")

    if provider == "google":
        try:
            logger.debug("Attempting to read meet links file")
            meet_links_path = os.getenv("MEET_LINKS_FILE_PATH", "meet_links.txt")
            with open(meet_links_path, "r+") as f:
                links = [line.strip() for line in f if line.strip()]
                if links:
                    # deterministic: use and remove the first link
                    link = links.pop(0)
                    logger.info(f"Retrieved Meet link from file: {link}")
                    logger.debug(f"Remaining links in file: {len(links)}")

                    f.seek(0)
                    f.truncate(0)
                    for l in links:
                        f.write(l + "\n")
                    logger.debug("Successfully updated meet links file with remaining links")
                    return link
                else:
                    logger.warning(f"{meet_links_path} is empty. Falling back to API.")
        except FileNotFoundError:
            logger.warning("meet links file not found. Falling back to API.")
        except PermissionError as e:
            logger.error(f"Permission denied when accessing meet links file: {e}")
        except IOError as e:
            logger.error(f"IO error when reading meet links file: {e}")
        except Exception as e:
            logger.error(f"Unexpected error reading meet links file: {e}", exc_info=True)

        # Fallback to creating a dummy event if the file is empty or doesn't exist
        logger.info("Falling back to API to generate new Meet link")
        try:
            credentials = service_account.Credentials.from_service_account_info(
                json.loads(GOOGLE_CALENDAR_CREDENTIALS),
                scopes=["https://www.googleapis.com/auth/calendar"]
            )
            service = build("calendar", "v3", credentials=credentials)
            now = datetime.datetime.utcnow()
            event = {
                'summary': 'Temporary Google Meet Event',
                'description': 'Generated Google Meet link.',
                'start': {
                    'dateTime': now.isoformat() + 'Z'
                },
                'end': {
                    'dateTime': (now + datetime.timedelta(minutes=30)).isoformat() + 'Z'
                },
                'conferenceData': {
                    'createRequest': {
                        'requestId': str(random.randint(100000, 999999)),  # simple random id
                        'conferenceSolutionKey': {
                            'type': 'hangoutsMeet'
                        }
                    }
                }
            }
            created_event = service.events().insert(
                calendarId=CALENDAR_ID,
                body=event,
                conferenceDataVersion=1
            ).execute()
            # Extract the Meet link
            meet_link = created_event.get('conferenceData', {}).get('entryPoints', [{}])[0].get('uri', None)
            if meet_link:
                logger.info(f"Successfully generated Meet link via API: {meet_link}")
                return meet_link
            else:
                logger.error("No Meet link found in the created event.")
                return "No Meet link generated."
        except HttpError as http_err:
            logger.error(f"Google Meet generation HTTP error: {http_err}")
            return "Error generating Google Meet link using Google API."
        except Exception as e:
            logger.error(f"Google Meet generation error: {e}")
            return "Error generating Google Meet link."



def upload_file_response(file_path, mime_type="text/plain", folder_id=SHARED_FOLDER_ID):
    """
    Uploads the file located at file_path to Google Drive,
    and returns a response message with a link to the uploaded file.
    """
    logger.info(f"Starting file upload: {file_path}")
    logger.debug(f"MIME type: {mime_type}, Folder ID: {folder_id}")

    try:
        logger.debug("Authenticating with Google Drive")
        service = authenticate()
        file_name = os.path.basename(file_path)
        metadata = {"name": file_name}
        if folder_id:
            metadata["parents"] = [folder_id]
            logger.debug(f"Uploading to folder: {folder_id}")

        logger.debug("Creating media upload object")
        media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)

        logger.debug("Executing file upload to Google Drive")
        uploaded_file = service.files().create(
            body=metadata,
            media_body=media,
            fields="id, parents"
        ).execute()

        file_id = uploaded_file["id"]
        logger.info(f"Successfully uploaded file {file_name} with ID: {file_id}")

        response_message = f"✅ File uploaded. File link: https://drive.google.com/file/d/{file_id}/view"
        if folder_id:
            response_message += f"\n📁 File was uploaded into folder: https://drive.google.com/drive/folders/{folder_id}"
        return response_message

    except Exception as e:
        logger.error(f"Error uploading file {file_path}: {e}", exc_info=True)
        return f"Error uploading file: {e}"


def generate_response(message_body, wa_id, name, local_file_path=None):
    """
    Processes the incoming message by checking its intent using the OpenAI API.
    Depending on the intent, this function will:
      - If intent is 'upload' and a local_file_path is provided, upload that file to Google Drive.
      - If intent is 'meet', return a Google Meet link.
      - If intent is 'calendar', extract event details and schedule a calendar event.
      - If intent is 'feedback' or 'suggestion', acknowledge the feedback.
    """
    logger.info(f"Processing message from {name} (WA ID: {wa_id})")
    logger.debug(f"Message content: {message_body}")
    logger.debug(f"Local file path: {local_file_path}")

    # 1) Expanded intent prompt to include feedback/suggestion and multilingual support
    intent_prompt = (
        "Determine if the following message (in any language) is requesting:\n"
        "- a Google Meet link ('meet'),\n"
        "- scheduling a Google Calendar event ('calendar'),\n"
        "- uploading a file to Google Drive ('upload'),\n"
        "- or is providing a suggestion/feedback ('feedback').\n"
        "Respond with exactly one word: meet, calendar, upload, or feedback.\n\n"
        f"Message: {message_body}"
    )

    try:
        logger.debug("Determining message intent via OpenAI")
        intent_response = get_openai_client().chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": intent_prompt}],
            temperature=0
        )
        intent = intent_response.choices[0].message.content.strip().lower()
        logger.info(f"Detected intent: {intent}")
    except Exception as e:
        logger.error(f"Error determining intent: {e}", exc_info=True)
        return "Could not determine the intent of your message."

    # 2) Handle feedback/suggestion intents
    if intent == "feedback":
        return "Understood—thank you for your feedback. We’ll keep improving!"

    # 3) Handle file uploads
    if intent == "upload":
        logger.info("Processing file upload intent")
        if local_file_path is None:
            logger.warning("Upload intent detected but no file path provided")
            return "No file available for upload. Please attach a file."

        # Determine target folder based on file name via OpenAI
        file_name = os.path.basename(local_file_path)
        logger.debug(f"Determining folder for file: {file_name}")

        folder_prompt = (
            f"You have a file named '{file_name}'. "
            "Please choose the correct upload folder based on these categories:\n"
            "- college_daa: materials related to Design and Analysis of Algorithms.\n"
            "- college_sdam: materials related to Software Design and Modelling.\n"
            "- college_misc: any other college study–related materials.\n"
            "- personal_docs: personal documents like license, passport, ID, etc.\n"
            "- personal_misc: any other personal files.\n"
            "Respond with exactly one of: college_daa, college_sdam, college_misc, personal_docs, personal_misc."
        )

        try:
            logger.debug("Querying OpenAI for folder determination")
            folder_resp = get_openai_client().chat.completions.create(
                model=DEFAULT_MODEL,
                messages=[{"role": "user", "content": folder_prompt}],
                temperature=0
            )
            folder_key = folder_resp.choices[0].message.content.strip()
            folder_id = FOLDER_MAP.get(folder_key)
            if folder_id is None:
                logger.warning(f"Unrecognized folder key '{folder_key}', using default.")
                folder_id = None  # falls back to shared or default folder in upload call
            else:
                logger.info(f"Determined folder: {folder_key} -> {folder_id}")
        except Exception as e:
            logger.error(f"Error determining folder: {e}", exc_info=True)
            folder_id = None

        # Set MIME type based on extension
        ext = os.path.splitext(local_file_path)[1].lower()
        mime_type = "text/plain" if ext == ".txt" else "application/octet-stream"
        logger.debug(f"Set MIME type: {mime_type}")

        # Call your upload helper
        response_message = upload_file_response(
            file_path=local_file_path,
            mime_type=mime_type,
            folder_id=folder_id
        )
        logger.info(f"File upload response: {response_message}")
        return response_message

    # 4) Handle Google Meet link requests
    if intent == "meet":
        logger.info("Processing Meet link request")
        meet_link = generate_meet_link()  # defaults to random_mode=True
        response_message = f"🔗 **Google Meet Link:** {meet_link}"
        logger.info(f"Generated Meet link response: {response_message}")
        return response_message

    # 5) Handle Calendar events
    if intent == "calendar":
        logger.info("Processing calendar event scheduling")
        event_details = extract_event_details(message_body)
        if not event_details or not event_details.get("date"):
            logger.warning("Failed to extract valid event details from message")
            return "Could not extract valid event details. Please provide a clear date for the reminder."

        scheduled_event = schedule_google_calendar_event(event_details)
        if scheduled_event:
            response_message = (
                f"📅 **Reminder Scheduled**\n\n"
                f"**Title:** {scheduled_event['title']}\n"
                f"**Date:** {scheduled_event['date']}\n"
                f"**Time:** {scheduled_event['time']}\n"
                f"**Location:** {scheduled_event['location']}\n"
                f"**Notes:** {scheduled_event['notes']}\n"
                f"🔗 [View in Google Calendar]({scheduled_event['event_link']})"
            )
            logger.info("Successfully scheduled calendar event")
        else:
            response_message = "Failed to schedule the event in Google Calendar. Please try again."
            logger.error("Failed to schedule calendar event")
        logger.info(f"Scheduled event response: {response_message}")
        return response_message

    # 6) Fallback for anything else
    logger.error(f"Unrecognized intent '{intent}' from the message.")
    return "Sorry, I did not understand your request. Please try again with a valid instruction."