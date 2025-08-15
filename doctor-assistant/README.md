Smart Doctor Appointment Assistant
🧠 Overview

This project is a full-stack web application that acts as an intelligent assistant for booking and managing doctor appointments. It leverages a Large Language Model (LLM) as an AI agent that can dynamically discover and invoke backend tools to fulfill user requests in natural language.

The core of the project is its agentic architecture, built using the Model Context Protocol (MCP). The AI agent can understand conversational prompts, decide which tools to use (e.g., check availability, book an appointment), maintain conversation context, and interact with external services like Google Calendar and email notifications.
✨ Features Implemented

This project successfully implements all the core requirements of the assignment:

    Scenario 1: Patient Appointment Scheduling

        Natural Language Processing: Patients can book appointments using conversational language (e.g., "I need to see a doctor tomorrow afternoon for a fever").

        Agentic Tool Use: The LLM dynamically chooses the correct backend tool (get_doctor_schedule, book_appointment, etc.) based on the user's intent.

        Database Integration: The agent checks a PostgreSQL database for doctor availability and saves new appointments.

        External API Integration (Mocked): The system simulates scheduling appointments on Google Calendar and sending confirmation emails to patients.

        Conversation Continuity: The assistant maintains context across multiple turns, allowing for follow-up questions and clarifications.

    Scenario 2: Doctor Summary Reports

        Natural Language Queries: Doctors can request summaries of their schedule (e.g., "how many appointments do I have today?").

        Dynamic Symptom Queries: The summary tool can dynamically filter appointments based on patient symptoms (e.g., "how many patients with fever?").

        Dashboard Interface: A dedicated "Doctor Dashboard" provides a user-friendly button-based interface for triggering common reports.

        Alternative Notification Channel (Mocked): Summary reports simulate being sent via a Slack notification, demonstrating a different communication channel.

    Technical Implementation

        MCP Architecture: The backend exposes its tools via a /.well-known/mcp.json manifest, allowing for dynamic discovery.

        Full-Stack Fluency: A React frontend communicates with a FastAPI backend, which in turn interacts with a PostgreSQL database and external APIs.

        Modular Code Structure: The code is organized logically, with a clear separation between the web server (main.py), business logic (tools.py), and database models (models.py).

🛠️ Tech Stack

    Frontend: React.js (with Vite)

    Backend: FastAPI (Python)

    Database: PostgreSQL

    LLM / AI Agent: Google Gemini (gemini-2.5-flash)

    Core Libraries:

        google-generativeai for LLM interaction

        SQLAlchemy for database ORM

        dateparser for robust natural language date parsing

🚀 Setup and Installation

1. Clone the Repository

git clone <https://github.com/sand33p312/Smart-Doctor-Appointment-Assistant.git>

2. Backend Setup (Python)

    Create and activate a virtual environment:

    python -m venv .venv
    source .venv/bin/activate

    Install the required Python packages:

    pip install -r requirements.txt

    (Note: You will need to create a requirements.txt file using pip freeze > requirements.txt)

    Database: Ensure you have PostgreSQL running and create a database named doctor_app. Update the DATABASE_URL in main.py if your credentials are different.

    API Key: Open main.py and replace "YOUR_GEMINI_API_KEY" with your actual Google AI Studio API key.

3. Frontend Setup (React)

    Navigate to the frontend directory:

    cd doctor-assistant

    Install the required Node.js packages:

    npm install

▶️ How to Run the Application

You will need to run the backend and frontend servers in two separate terminals.

1. Run the Backend Server

    From the project's root directory (with your virtual environment activated):

    uvicorn main:app --reload

    The backend will be running at http://127.0.0.1:8000.

2. Run the Frontend Server

    From the doctor-assistant directory:

    npm run dev

    The frontend will be running at http://localhost:5173.

3. Seed the Database

    Before the first use, populate the database with sample data by running the seed script from the root directory:

    python seed.py

Now, you can open http://localhost:5173 in your browser to use the application.
📋 Sample Prompts to Demonstrate Functionality

Patient Prompts (in the Chat Assistant):

    "I want to check Dr. Ahuja’s availability for Friday afternoon."

    "I have a fever, who should I see?"

    "Can you book me an appointment with any doctor tomorrow at 10 AM? My email is test@example.com."

Doctor Prompts (in the Chat or Dashboard):

    "how many appointments do I have today for Dr. Priya Sharma?"

    "how many patients visited yesterday?"

    "how many patients with headache"