import os
import json
import traceback
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from pydantic import BaseModel
from typing import List
from dotenv import load_dotenv

import tools
from models import Base, Doctor

# ===== SETUP =====

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

DATABASE_URL = "postgresql+psycopg2://admin:admin@localhost:5432/doctor_app"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

conversation_history = {}

AVAILABLE_TOOLS = {
    "get_doctor_schedule": tools.get_doctor_schedule,
    "book_appointment": tools.book_appointment,
    "get_appointment_summary": tools.get_appointment_summary,
    "list_all_doctors": tools.list_all_doctors,
    "find_doctor_by_symptom": tools.find_doctor_by_symptom,
}

# ===== FASTAPI APP =====

VERCEL_FRONTEND_URL = "https://your-vercel-app-name.vercel.app"

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", VERCEL_FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DoctorResponse(BaseModel):
    id: int
    name: str
    specialization: str
    class Config: from_attributes = True

class BookingRequest(BaseModel):
    doctor_name: str
    date: str
    time: str
    email: str
    symptoms: str | None = None

# --- API ENDPOINTS ---
@app.get("/.well-known/mcp.json")
async def get_mcp_manifest():
    return FileResponse("mcp.json", media_type="application/json")

@app.get("/doctors", response_model=List[DoctorResponse])
async def get_all_doctors():
    db = SessionLocal()
    try:
        return db.query(Doctor).all()
    finally:
        db.close()

@app.post("/book")
async def book_appointment_from_form(booking: BookingRequest):
    db = SessionLocal()
    try:
        result = tools.book_appointment(
            db=db,
            doctor_name=booking.doctor_name,
            patient_email=booking.email,
            date=booking.date,
            time=booking.time,
            symptoms=booking.symptoms
        )
        return {"reply": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        session_id = data.get("session_id")
        user_message = data.get("message")

        if not session_id or not user_message:
            raise HTTPException(status_code=400, detail="session_id and message are required.")

        with open("mcp.json", "r") as f:
            mcp_schema = json.load(f)

        agent_model = genai.GenerativeModel(
            model_name='gemini-2.5-flash', # As requested
            tools=mcp_schema['tools'],
            system_instruction="""You are a smart and friendly AI assistant for booking doctor appointments. Your tools are powerful and can understand natural language dates like "tomorrow afternoon" or "next Friday". Trust the tools and pass the user's conversational input directly to them.

            **Workflow for Checking Availability:**
            1. When a user asks for a doctor's availability, you MUST use the `get_doctor_schedule` tool.
            2. After you receive the list of available times from the tool, you MUST analyze that list yourself to answer the user's specific question (e.g., filter for "afternoon" slots).
            
            **Booking Rule:**
            When calling `book_appointment`, if the user wants 'any' doctor, you MUST use the exact string 'any' for the 'doctor_name' parameter."""
        )

        # === Manual History Management ===
        if session_id not in conversation_history:
            conversation_history[session_id] = []
        
        conversation_history[session_id].append({'role': 'user', 'parts': [user_message]})
        
        response = agent_model.generate_content(conversation_history[session_id])
        
        if not response.candidates:
            return {"reply": "I'm sorry, I couldn't generate a response. The request may have been blocked. Please try rephrasing your message."}

        response_part = response.candidates[0].content.parts[0]
        conversation_history[session_id].append({'role': 'model', 'parts': [response_part]})

        if hasattr(response_part, 'function_call') and response_part.function_call:
            function_call = response_part.function_call
            function_name = function_call.name
            
            if function_name in AVAILABLE_TOOLS:
                args = {key: value for key, value in function_call.args.items()}
                db = SessionLocal()
                tool_function = AVAILABLE_TOOLS[function_name]
                tool_result = tool_function(db=db, **args)
                db.close()
                
                function_response_part = {
                    "function_response": {
                        "name": function_name,
                        "response": {"result": tool_result},
                    }
                }
                conversation_history[session_id].append({'role': 'function', 'parts': [function_response_part]})

                response = agent_model.generate_content(conversation_history[session_id])
                
                if not response.candidates:
                    return {"reply": "I'm sorry, I received a result from the tool but couldn't process it. Please try again."}

                final_response_part = response.candidates[0].content.parts[0]
                conversation_history[session_id].append({'role': 'model', 'parts': [final_response_part]})
            else:
                reply = f"Error: The model tried to call a function named '{function_name}' which is not available."
                return {"reply": reply}

        reply = response.text
        return {"reply": reply}

    except Exception as e:
        print("An error occurred in /chat:")
        traceback.print_exc()
        # === NEW: Better error handling for rate limits ===
        if "ResourceExhausted" in str(e):
             return {"reply": "I'm experiencing high traffic right now. Please wait a minute and try again."}
        # === END OF NEW HANDLING ===
        return {"reply": f"An unexpected server error occurred."}
