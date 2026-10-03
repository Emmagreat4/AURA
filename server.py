import os
import json
import asyncio
from datetime import datetime, timedelta
import edge_tts
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI
from apscheduler.schedulers.asyncio import AsyncIOScheduler

load_dotenv()

app = FastAPI(title="AURA AI Core")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ.get("GROQ_API_KEY")
)

MODEL_NAME = "openai/gpt-oss-120b"

subscriptions = []
tasks = []

scheduler = AsyncIOScheduler()

try:
    with open('user_profile.json', 'r') as f:
        user_profile_data = json.load(f)
except FileNotFoundError:
    user_profile_data = {}

system_prompt = f"""
You are AURA (Advanced Personal Assistant), running for De Great.
User Context:
- Name: {user_profile_data.get('master_profile', {}).get('name', 'De Great')}
- Brand: {user_profile_data.get('photography_context', {}).get('brand_name', 'GREAT LENZ')}

Keep responses conversational, concise, professional, and direct for voice playback.
Do not use any emojis in your responses under any circumstances.
Assist De Great with engineering projects, GREAT LENZ photography concepts, task schedules, and Physics preparation.
When the user asks you to set a task, reminder, or timer, call the schedule_task tool.
"""

tools = [
    {
        "type": "function",
        "function": {
            "name": "schedule_task",
            "description": "Schedules a task or timer given a title and a duration in seconds.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "The title or description of the task"},
                    "run_in_seconds": {"type": "integer", "description": "Duration in seconds from now until execution"}
                },
                "required": ["title", "run_in_seconds"]
            }
        }
    }
]

class ChatPayload(BaseModel):
    message: str

class TaskPayload(BaseModel):
    title: str
    run_in_seconds: int

class TTSPayload(BaseModel):
    text: str

def trigger_task_alert(task_title: str):
    print(f"[AURA TASK EXECUTION]: Task due -> {task_title}")

@app.on_event("startup")
async def start_scheduler():
    scheduler.start()

@app.get("/")
async def serve_hud():
    return FileResponse("static/index.html")

@app.get("/manifest.json")
async def serve_manifest():
    return FileResponse("static/manifest.json")

@app.get("/sw.js")
async def serve_sw():
    return FileResponse("static/sw.js")

@app.post("/api/chat")
async def chat_endpoint(payload: ChatPayload):
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": payload.message}
            ],
            tools=tools,
            tool_choice="auto",
            temperature=0.7,
        )

        response_message = response.choices[0].message
        scheduled_task = None

        if response_message.tool_calls:
            for tool_call in response_message.tool_calls:
                if tool_call.function.name == "schedule_task":
                    args = json.loads(tool_call.function.arguments)
                    title = args.get("title", "Task")
                    seconds = int(args.get("run_in_seconds", 10))

                    task_id = f"task_{len(tasks) + 1}"
                    execution_time = datetime.now() + timedelta(seconds=seconds)

                    scheduler.add_job(
                        trigger_task_alert,
                        'date',
                        run_date=execution_time,
                        args=[title],
                        id=task_id
                    )

                    task_entry = {
                        "id": task_id,
                        "title": title,
                        "execution_time": execution_time.strftime("%H:%M:%S"),
                        "status": "scheduled"
                    }
                    tasks.append(task_entry)
                    scheduled_task = {"title": title, "run_in_seconds": seconds}
                    reply_text = f"Task registered: \"{title}\" scheduled on server for {seconds} seconds."
        else:
            reply_text = response_message.content

        audio_url = None
        try:
            audio_filename = "aura_response.mp3"
            audio_path = os.path.join("static", audio_filename)
            communicate = edge_tts.Communicate(reply_text, "en-US-AvaNeural")
            await communicate.save(audio_path)
            audio_url = f"/static/{audio_filename}"
        except Exception as tts_err:
            print(f"[Voice Output Warning]: {tts_err}")

        return {
            "text": reply_text,
            "audio_url": audio_url,
            "scheduled_task": scheduled_task
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tts")
async def tts_endpoint(payload: TTSPayload):
    try:
        audio_filename = "aura_alert.mp3"
        audio_path = os.path.join("static", audio_filename)
        communicate = edge_tts.Communicate(payload.text, "en-US-AvaNeural")
        await communicate.save(audio_path)
        return {"audio_url": f"/static/{audio_filename}"}
    except Exception as e:
        print(f"[TTS Warning]: {e}")
        return {"audio_url": None}

@app.post("/api/tasks/schedule")
async def schedule_task(payload: TaskPayload):
    task_id = f"task_{len(tasks) + 1}"
    execution_time = datetime.now() + timedelta(seconds=payload.run_in_seconds)
    
    scheduler.add_job(
        trigger_task_alert,
        'date',
        run_date=execution_time,
        args=[payload.title],
        id=task_id
    )

    task_entry = {
        "id": task_id,
        "title": payload.title,
        "execution_time": execution_time.strftime("%H:%M:%S"),
        "status": "scheduled"
    }
    tasks.append(task_entry)

    return {"status": "Task scheduled successfully", "task": task_entry}

@app.get("/api/tasks")
async def get_tasks():
    return {"tasks": tasks}