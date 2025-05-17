# Facilitator

Transforming conversations into actions for simpler and more productive work.

## Goals

* **Simplify Scheduling & Document Organization:**
  Streamline the process of scheduling events and organizing documents within Google Suite.
* **Automate Task Management:**
  Convert WhatsApp messages into actionable tasks within Google Suite, ensuring nothing falls through the cracks.
* **Enhance User Productivity:**
  Provide timely reminders and notifications to keep users on top of their deadlines and meetings.

## System Architecture

![System Architecture](docs/system_architecture.png)

Facilitator uses a secure, modular architecture to bridge WhatsApp and Google Suite services, automating actions based on natural language messages.

* **WhatsApp Client:** Users send multilingual, end-to-end encrypted messages.
* **Ngrok Ingress & Webhook Endpoint:** Receives messages/media securely and forwards them to the backend.
* **Private Subnet & Flask Server:** Handles message intent detection and routes requests to appropriate services.
* **AI-Driven Services:** Uses OpenAI to analyze context, automate event scheduling, meeting link generation, and file handling.
* **Google Cloud Platform:** Integrates with Google Calendar and Drive APIs via a service account to create events, store documents, and more.
* **Monitoring:** Uses OpenTelemetry and Grafana for logging and system monitoring.

## Objectives

### Simplified Scheduling and Document Organization

* **Meet Link Generation:**
  Automatically generate and share Google Meet links directly from WhatsApp messages.
* **Smart Folder Allocation:**
  Automatically categorize and store forwarded documents into Google Drive folders based on content type.
* **Task Scheduling:**
  Automate the scheduling of tasks such as project deadlines, assignments, and follow-ups.

### Automated Task Management

* **Message Context Analysis:**
  Uses AI to analyze WhatsApp messages, extracting actionable insights like deadlines, reminders, and more.
* **Action Execution:**
  Converts extracted insights into Google Calendar events, task lists, or reminders.

### Key Features

* **Google Meet Link Generation**
* **Smart Folder Allocation**
* **Automated Task Scheduling**
* **AI-Driven Message Context Analysis**
* **Seamless Integration with Google Suite** (Calendar, Drive, etc.)

## Getting Started

### Prerequisites

* Python 3.x
* API credentials:

  * **Google Calendar API** (service account)
  * **Google Suite APIs** (Drive, etc.)
  * **OpenAI API** key
* Environment variables set up (via `.env`):

  * `OPENAI_API_KEY`
  * `GOOGLE_CALENDAR_CREDENTIALS`
  * `GOOGLE_CALENDAR_ID`

### Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/arya2004/facilitator.git
   cd facilitator
   ```
2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```
3. **Set up environment variables:**
   Create a `.env` file in the root directory and add your credentials.

### Running the Project

```bash
python run.py
```

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your improvements.

## License

This project is licensed under the [MIT License](LICENSE).

