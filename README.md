# SociaMate

# SociaMate

SociaMate is a tool that transforms your social media group messages into an intelligent notification console.  
It helps you quickly catch up on conversations without reading line-by-line, ensuring you never miss fun events, important updates, or relevant discussions.

## Core Features

1. **Conversation Summarization**  
   Automatically summarizes group chats into concise, readable formats.

2. **Calendar Event Creation**  
   Extracts important dates and suggests adding them to your calendar.

3. **Important Message Highlights**  
   Flags critical or highly relevant messages for quick attention.

4. **Reply Suggestions**  
   Offers AI-powered draft replies based on the conversation context.

---

## Technology Stack

- **Frontend:** React (Next.js 14 with App Router)
- **Backend:** FastAPI (Python)
- **Parsing:** PapaParse for CSV parsing
- **UI Styling:** Tailwind CSS

---

## Setup Instructions

### Backend (FastAPI)

1. Navigate to the `backend` directory:

   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:

   ```bash
   python3 -m venv venv
   source venv/bin/activate    # Mac/Linux
   .\venv\Scripts\activate     # Windows
   ```

3. Install Python dependencies:

   ```bash
   pip install -r requirements.txt
   ```

6. create a .env that includes your hugging face token ```"HF_TOKEN = XXX"```

5. Start the FastAPI server:

   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

### Frontend (React / Next.js)

1. Navigate to the `frontend` directory:

   ```bash
   cd frontend
   ```

2. Install Node.js dependencies:

   ```bash
   npm install
   ```

   This will install all necessary packages including:

   - next
   - react
   - papaparse
   - tailwindcss

3. Start the development server:

   ```bash
   npm run dev
   ```

4. Open your browser and navigate to:

   ```
   http://localhost:3000
   ```

---

## Example Screenshot


Example placeholder:

![Console Example](frontend/public/screenshot/screenshot/example-ui.png)
---

## Future Improvements

- Add conversation chunk selection before summarization
- Add drag-and-drop upload support
- Implement event extraction and calendar integration
- Implement "important message" classification
- Implement suggested reply generator
- Improve backend concurrency and queue handling

---