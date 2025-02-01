import os
import shelve
import logging
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(
    api_key=OPENAI_API_KEY,
)

# Use the cost-efficient ChatCompletion model.
DEFAULT_MODEL = "gpt-4o-mini"
# The system prompt now serves as the chatbot’s base instructions.
DEFAULT_SYSTEM_PROMPT = (
    "You are a clever yet mischievous cat assistant. "
    "You answer general-purpose questions but meow or 'mew' randomly in half of your responses. "
    "Be playful, occasionally aloof, and maintain your cat-like attitude. "
    "If you don't know the answer, casually suggest they consult a human, because, well... you're a cat."
)

def check_if_thread_exists(wa_id):
    """Retrieve the conversation history for a given wa_id from the shelf database."""
    with shelve.open("threads_db") as threads_shelf:
        return threads_shelf.get(wa_id)

def store_thread(wa_id, conversation_history):
    """Store or update the conversation history for a given wa_id."""
    with shelve.open("threads_db", writeback=True) as threads_shelf:
        threads_shelf[wa_id] = conversation_history

def generate_response(message_body, wa_id, name):
    """
    Handles the chatbot conversation using the ChatCompletion API.
    Maintains a conversation history per wa_id using shelve, starting with a system prompt.
    """
    conversation_history = check_if_thread_exists(wa_id)
    
    if conversation_history is None:
        logging.info(f"Creating new conversation thread for {name} with wa_id {wa_id}")
        conversation_history = [{"role": "system", "content": DEFAULT_SYSTEM_PROMPT}]
    else:
        logging.info(f"Retrieving existing conversation thread for {name} with wa_id {wa_id}")

    conversation_history.append({"role": "user", "content": message_body})

    try:
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=conversation_history,
            temperature=0.7
        )
    except Exception as e:
        logging.error(f"OpenAI API error: {e}")
        return "I'm sorry, but I'm having trouble responding at the moment."

    # Use the content attribute to get the assistant's reply.
    assistant_message = response.choices[0].message.content

    conversation_history.append({"role": "assistant", "content": assistant_message})
    store_thread(wa_id, conversation_history)

    logging.info(f"Generated message: {assistant_message}")
    return assistant_message
