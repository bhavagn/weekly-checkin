# Weekly Check-in Chatbot

A FastAPI application that facilitates structured weekly client check-ins through a conversational interface.

## Features

- Structured conversation flow for weekly check-ins
- Professional and context-aware responses
- Modern, responsive UI
- Webhook integration for data submission
- OpenAI integration for natural language processing
- In-memory session management
- Automatic summarization
- Error handling for all endpoints

## Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment:
- Copy `.env` file and set your OpenAI API key:
```bash
OPENAI_API_KEY=your_openai_api_key_here
```

3. Run the development server:
```bash
uvicorn main:app --reload
```

4. Visit http://localhost:8000 in your browser

## API Endpoints

### 1. POST /chat/start
Starts a new chat session.
```json
{
    "sessionId": "unique_session_id"
}
```

### 2. POST /chat/message
Sends a message in an existing chat session.
```json
{
    "sessionId": "unique_session_id",
    "message": "user message"
}
```

### 3. POST /chat/submit
Submits and summarizes the chat session.
```json
{
    "sessionId": "unique_session_id"
}
```

## Deployment

### Deploy to Render

1. Create a new account on [Render](https://render.com)
2. Click "New +" and select "Web Service"
3. Connect your GitHub repository
4. Configure the service:
   - Name: weekly-checkin-bot
   - Environment: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add environment variable:
   - Key: OPENAI_API_KEY
   - Value: your_openai_api_key
6. Click "Create Web Service"

### Important Notes

- The application uses in-memory session storage, which means sessions will be cleared when the server restarts
- Make sure to set the OPENAI_API_KEY in your deployment environment
- The webhook URL can be configured in the code if needed

## API Documentation

Once deployed, visit `/docs` for the interactive API documentation.
