
### **Step-by-Step Guide to Get Google Calendar API Credentials**
---
### **1️⃣ Create a Google Cloud Project**
1. Go to the **[Google Cloud Console](https://console.cloud.google.com/)**.
2. Click on the project dropdown (top-left) → **New Project**.
3. Enter a **Project Name** (e.g., "WhatsApp Bot Calendar").
4. Click **Create**.

---
### **2️⃣ Enable Google Calendar API**
1. Inside your **new project**, go to the **[Google API Library](https://console.cloud.google.com/apis/library)**.
2. Search for **Google Calendar API**.
3. Click **Enable**.

---
### **3️⃣ Create Service Account (For API Access)**
1. Open **[Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts)**.
2. Click **Create Service Account**.
3. **Service Account Name:** Give it a name (e.g., "Calendar Bot").
4. Click **Create and Continue**.
5. **Grant Role:** Select **Editor** or **Owner** (or `Cloud Functions Invoker` for limited access).
6. Click **Done**.

---
### **4️⃣ Generate API Credentials (JSON File)**
1. In the **Service Accounts** section, find your newly created service account.
2. Click on it → **Keys** tab → **Add Key** → **Create New Key**.
3. Choose **JSON**, then click **Create**.
4. A JSON file will download. **Keep it safe**—this is your credential file!

---
### **5️⃣ Share Google Calendar with Service Account**
1. Go to **[Google Calendar](https://calendar.google.com/)**.
2. Click on **Settings (⚙️) → Settings**.
3. Scroll to **"My Calendars"** and select the calendar you want to use.
4. Under **"Share with specific people"**, click **Add people**.
5. Enter the **service account email** (found in your JSON file).
6. Set permissions to **"Make changes to events"**.
7. Click **Send**.

---
### **6️⃣ Store Credentials in Your Python Project**
1. Open your `.env` file (or create one).
2. Add the following:
   ```
   GOOGLE_CALENDAR_CREDENTIALS='PASTE_YOUR_JSON_HERE'
   GOOGLE_CALENDAR_ID='your_calendar_id@gmail.com'
   ```
   - To find your `GOOGLE_CALENDAR_ID`:  
     - Go to Google Calendar settings.
     - Under **"Integrate Calendar"**, copy the **"Calendar ID"** (it looks like an email).

---
### **7️⃣ Install Google API Client in Python**
Run the following command to install the required library:
```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

---
### **8️⃣ Use the Credentials in Your Code**
Now, update your Python code to use the credentials:
```python
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os
import json

# Load credentials
creds_json = json.loads(os.getenv("GOOGLE_CALENDAR_CREDENTIALS"))
credentials = service_account.Credentials.from_service_account_info(creds_json, scopes=["https://www.googleapis.com/auth/calendar"])

# Build the Google Calendar service
service = build("calendar", "v3", credentials=credentials)
```

