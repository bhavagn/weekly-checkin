from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, List, Optional
import openai
import os
from datetime import datetime
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_root():
    return FileResponse("static/index.html")

# In-memory session storage
sessions: Dict[str, List[dict]] = {}

# System prompts
CHAT_SYSTEM_PROMPT = """You are an AI Assistant designed to help Customer Success Managers complete Weekly Client Check-ins through a natural, structured, and professional conversation.

Your objective is to collect specific information needed for weekly client engagement tracking.

Collect the following information one step at a time:

1. Client Name
2. Major Activities Completed This Week
3. Impact/Outcome of Activities
4. Meetings Conducted with Client
5. Risks, Blockers, or Escalations Observed
6. Implementation Progress Estimate (%)
7. Planned Activities for Next Week
8. Final Confirmation (any additional comments)

---

Strict Conversation Guidelines:

- Ask one topic at a time and wait for the user's response.
  
- If the user gives no response or gibberish (like "asdf", "ok", "..."):
  - Politely prompt once for clarification.
  - If still unclear after second attempt, acknowledge and move on.

- If the user gives a **valid but very short or vague** answer (e.g., "worked on sales", "issues discussed"):
  - Politely and **contextually** ask a follow-up question to deepen the information.
    - Example: If user says "issues discussed" → Follow-up: "Could you please elaborate on the issues that were discussed?"
    - Example: If user says "client meeting happened" → Follow-up: "Could you briefly summarize the key points discussed in the meeting?"
    - Example: If user says "some progress" → Follow-up: "Could you please estimate the current implementation progress percentage?"

- After one follow-up, accept whatever is answered and move to the next topic. Do not repeatedly ask.

- Maintain a professional, courteous, and concise tone.

- Never invent or assume information.

- Confirm if multiple answers are given voluntarily, then proceed.

- Follow the sequence strictly without skipping any step.

- If user says "no", "none", or "nothing" at any step (e.g., no meetings), record that explicitly.

---

Goal:

Your mission is to **gather complete, accurate, detailed, and contextually clarified Weekly Check-in data**  
while ensuring minimal user effort, maximum data richness, and a highly professional conversational experience."""

from datetime import datetime

def get_current_date_string():
    current_date = datetime.now()
    return current_date.strftime("%B %d, %Y")

SUMMARY_SYSTEM_PROMPT = f"""You are an AI Assistant summarizing a Weekly Client Check-in based on a completed structured conversation.

Summarize the details into the following JSON format:

{{
  'client': 'string',
  'date': '{get_current_date_string()}',  # Today's date is already provided here
  'last_week_activities': 'string',
  'impact_outcome': 'string',
  'meetings_with_client': 'Yes/No',
  'meeting_summary': 'string (if applicable)',
  'risk_blockers': 'string',
  'implementation_percentage': 'string (like 80%)',
  'next_week_activities': 'string'
}}

IMPORTANT: Use the exact date provided above ({get_current_date_string()}) in the summary. Do not modify or change this date."""

# Pydantic models
class SessionRequest(BaseModel):
    sessionId: str

class MessageRequest(BaseModel):
    sessionId: str
    message: str

# API endpoints
@app.post("/chat/start")
async def start_chat(request: SessionRequest):
    try:
        # Initialize new session with system message
        sessions[request.sessionId] = [
            {"role": "system", "content": CHAT_SYSTEM_PROMPT}
        ]
        
        # Get initial response from OpenAI
        response = await get_ai_response(request.sessionId)
        
        return {"status": "success", "message": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/message")
async def send_message(request: MessageRequest):
    try:
        if request.sessionId not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Append user message
        sessions[request.sessionId].append(
            {"role": "user", "content": request.message}
        )
        
        # Get AI response
        response = await get_ai_response(request.sessionId)
        
        return {"status": "success", "message": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/submit")
async def submit_chat(request: SessionRequest):
    try:
        if request.sessionId not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get conversation summary
        summary = await get_conversation_summary(request.sessionId)
        
        print(f"Sending to webhook: {summary}")
        
        # Send to webhook with detailed error handling
        try:
            webhook_response = requests.post(
                "https://n8n.ms.increff.com/webhook/weekly-checkin",
                json=summary,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            print(f"Webhook response status: {webhook_response.status_code}")
            print(f"Webhook response body: {webhook_response.text}")
            
            webhook_response.raise_for_status()
            
        except requests.exceptions.RequestException as e:
            print(f"Webhook error details: {str(e)}")
            if hasattr(e.response, 'text'):
                print(f"Error response body: {e.response.text}")
            raise HTTPException(
                status_code=502,
                detail={
                    "error": "Webhook delivery failed",
                    "message": str(e),
                    "summary": summary  # Return the summary even if webhook fails
                }
            )
        
        # Clean up session
        del sessions[request.sessionId]
        
        return {
            "status": "success",
            "summary": summary,
            "webhook_status": "delivered"
        }
    except Exception as e:
        print(f"General error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def get_ai_response(session_id: str) -> str:
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=sessions[session_id],
            temperature=0.7,
            max_tokens=500
        )
        
        assistant_message = response.choices[0].message.content
        sessions[session_id].append(
            {"role": "assistant", "content": assistant_message}
        )
        
        return assistant_message
    except Exception as e:
        raise Exception(f"OpenAI API error: {str(e)}")

async def get_conversation_summary(session_id: str) -> dict:
    try:
        # Create a new conversation for summary
        summary_messages = [
            {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
            {"role": "user", "content": str(sessions[session_id])}
        ]
        
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=summary_messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        summary_text = response.choices[0].message.content
        # Convert string to dictionary (assumes proper JSON response)
        import json
        return json.loads(summary_text.replace("'", '"'))
    except Exception as e:
        raise Exception(f"Summary generation failed: {str(e)}")
