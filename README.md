

# Facilitator

Transforming conversations into actions for simpler and more productive work.

## Goals

- **Simplify Scheduling & Document Organization:**  
  Streamline the process of scheduling events and organizing documents within Google Suite.
  
- **Automate Task Management:**  
  Convert WhatsApp messages into actionable tasks within Google Suite, ensuring nothing falls through the cracks.
  
- **Enhance User Productivity:**  
  Provide timely reminders and notifications to keep users on top of their deadlines and meetings.

## Objectives

### Simplified Scheduling and Document Organization

- **Meet Link Generation:**  
  Automatically generate and share Google Meet links directly from WhatsApp messages.

- **Smart Folder Allocation:**  
  Automatically categorize and store forwarded documents into appropriate Google Drive folders (e.g., PDFs, Sheets, PPTs) based on content type.

- **Task Scheduling:**  
  Facilitate the automated scheduling of tasks such as project deadlines, assignments, and follow-ups.

### Automated Task Management

- **Message Context Analysis:**  
  Utilize AI to analyze WhatsApp messages, extracting actionable insights such as deadlines, reminders, study materials, etc. The AI identifies key details like dates, times, participants, and action items.

- **Action Execution:**  
  Convert the extracted insights into actionable items such as creating Google Calendar events, task lists, or reminders.

### Key Features

- **Google Meet Link Generation:**  
  Automatically generate and share Google Meet links within WhatsApp conversations, ensuring seamless virtual meeting setup.

- **Smart Folder Allocation:**  
  Automatically organize and store forwarded documents into relevant Google Drive folders based on content type.

- **Automated Task Scheduling:**  
  Convert WhatsApp messages into scheduled tasks (e.g., project deadlines, assignments, follow-ups) in Google Suite.

- **Message Context Analysis:**  
  Implement AI to analyze messages and extract actionable insights to streamline workflow automation.  
  **Example:**  
  *User message:* "Reminder: Submit the project report by Monday at 5 PM."  
  *AI Output:* Detects the task ("Submit project report"), the deadline ("Next Monday at 5 PM"), and suggests adding it to the to-do list or setting a reminder.



- **Integration with Google Suite:**  
  Seamlessly integrate with Google Calendar, Google Drive, Google Sheets, Google Slides, and Google Docs to enable smooth automation and collaboration.

## Getting Started

### Prerequisites

- Python 3.x
- Necessary API credentials:
  - **Google Calendar API** credentials (service account)
  - **Google Suite APIs** credentials for Drive, Sheets, Slides, and Docs (if applicable)
  - **OpenAI API** key for AI-driven message analysis
- Environment variables set up (use a `.env` file):
  - `OPENAI_API_KEY`
  - `GOOGLE_CALENDAR_CREDENTIALS`
  - `GOOGLE_CALENDAR_ID`

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

3. **Set up your environment variables:**  
   Create a `.env` file in the root directory and add your credentials

### Running the Project

Execute the main script to start the integration service:

```bash
python run.py
```

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your improvements.

## License

This project is licensed under the [MIT License](LICENSE).
