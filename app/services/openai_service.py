import os
import logging
import datetime
import re
import pytz
import random
from dotenv import load_dotenv
from openai import OpenAI
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.errors import HttpError  # For more specific error handling

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_CALENDAR_CREDENTIALS = os.getenv("GOOGLE_CALENDAR_CREDENTIALS")
CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID")

# Initialize OpenAI Client
client = OpenAI(api_key=OPENAI_API_KEY)

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

def extract_event_details(message_body):
    """Uses OpenAI to extract event details like title, date, time, location, and notes from the message."""
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
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        extracted_text = response.choices[0].message.content.strip()
        logging.info(f"LLM extracted text: {extracted_text}")

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
        return event_details

    except Exception as e:
        logging.error(f"OpenAI API error while extracting event details: {e}")
        return None

def schedule_google_calendar_event(event_details):
    """Schedules an event in Google Calendar and returns event details."""
    try:
        credentials = service_account.Credentials.from_service_account_info(
            eval(GOOGLE_CALENDAR_CREDENTIALS),
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
                except Exception as parse_error:
                    logging.error(f"Error parsing date and time: {parse_error}")
                    return None
            else:
                start = {"date": event_details["date"]}
                end = {"date": event_details["date"]}
        else:
            logging.error("No valid date provided in event details.")
            return None

        event = {
            "summary": event_details["title"],
            "location": event_details["location"] if event_details["location"] != "Not provided" else "",
            "description": event_details["notes"] if event_details["notes"] != "Not provided" else "",
            "start": start,
            "end": end,
            "reminders": {"useDefault": True}
        }

        created_event = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        return {
            "title": event_details["title"],
            "date": event_details["date"],
            "time": event_details["time"],
            "location": event_details["location"],
            "notes": event_details["notes"],
            "event_link": created_event.get("htmlLink")
        }

    except HttpError as http_err:
        logging.error(f"Google Calendar API HTTP error: {http_err.resp.status} - {http_err.content}")
        return None
    except Exception as e:
        logging.error(f"Google Calendar API error: {e}")
        return None

def generate_meet_link(random_mode: bool = True) -> str:
    """
    Overloaded function for generating a Google Meet link.
    
    - When `random_mode` is True (default), it reads a text file "meet_links.txt" located at the project root, 
      picks a random link from newline-separated values, and returns it.
    - When `random_mode` is False, it uses Google services (via the Calendar API) to generate a Meet link.
    """
    if random_mode:
        try:
            with open("meet_links.txt", "r") as file:
                links = [line.strip() for line in file if line.strip()]
            if links:
                chosen_link = random.choice(links)
                return chosen_link
            else:
                logging.error("No meet links available in meet_links.txt")
                return "No Meet links available."
        except Exception as e:
            logging.error(f"Error reading meet links file: {e}")
            return "Error retrieving Meet link."
    else:
        # Use Google services (using Calendar API) to create a dummy event and extract the Meet link.
        try:
            credentials = service_account.Credentials.from_service_account_info(
                eval(GOOGLE_CALENDAR_CREDENTIALS),
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
                return meet_link
            else:
                logging.error("No Meet link found in the created event.")
                return "No Meet link generated."
        except HttpError as http_err:
            logging.error(f"Google Meet generation HTTP error: {http_err}")
            return "Error generating Google Meet link using Google API."
        except Exception as e:
            logging.error(f"Google Meet generation error: {e}")
            return "Error generating Google Meet link."

def generate_response(message_body, wa_id, name):
    """
    Processes the incoming message by first checking the intent (using OpenAI API).
    Depending on the intent, this function either schedules a Google Calendar event or returns a Meet link.
    
    For the purpose of this demo:
      - If intent is 'meet', it returns a Meet link (using the random/text file version).
      - If intent is 'calendar', it extracts event details and schedules the event.
      - Future intents can be added accordingly.
    """
    # 1. Check intent using OpenAI (meet link vs calendar event)
    intent_prompt = (
        "Determine if the following message is requesting a Google Meet link generation "
        "or scheduling a Google Calendar event. Respond with only one word: 'meet' or 'calendar'.\n\n"
        f"Message: {message_body}"
    )
    try:
        intent_response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": intent_prompt}],
            temperature=0
        )
        intent = intent_response.choices[0].message.content.strip().lower()
    except Exception as e:
        logging.error(f"Error determining intent: {e}")
        return "Could not determine the intent of your message."

    # 2. Branch logic based on intent
    if intent == "meet":
        # For demo purposes, use the overloaded function in its random link mode.
        meet_link = generate_meet_link()  # defaults to random_mode=True
        response_message = f"🔗 **Google Meet Link:** {meet_link}"
        logging.info(f"Generated Meet link response: {response_message}")
        return response_message

    elif intent == "calendar":
        event_details = extract_event_details(message_body)
        if not event_details or not event_details.get("date"):
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
        else:
            response_message = "Failed to schedule the event in Google Calendar. Please try again."

        logging.info(f"Scheduled event response: {response_message}")
        return response_message

    else:
        logging.error("Unrecognized intent from the message.")
        return "Sorry, I did not understand your request. Please try again with a valid instruction."

