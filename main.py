import os
import json
import asyncio
import edge_tts
import pygame
import speech_recognition as sr
from dotenv import load_dotenv
from openai import OpenAI

# 1. Load Environment Variables
load_dotenv()

# 2. Initialize Audio Systems
pygame.mixer.init()
VOICE = "en-US-AvaNeural"
AUDIO_FILE = "aura_voice.mp3"
recognizer = sr.Recognizer()

def speak(text):
    """Generates audio from text and plays it aloud."""
    async def _generate_and_play():
        communicate = edge_tts.Communicate(text, VOICE)
        await communicate.save(AUDIO_FILE)
        
        pygame.mixer.music.load(AUDIO_FILE)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
            
        pygame.mixer.music.unload()

    try:
        asyncio.run(_generate_and_play())
    except Exception as e:
        print(f"[Voice Output Error]: {e}")

def listen():
    """Listens to the microphone and converts speech to text."""
    with sr.Microphone() as source:
        print("\n🎤 Listening... Speak now:")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            print("⚡ Processing speech...")
            text = recognizer.recognize_google(audio)
            print(f"You (Spoken): {text}")
            return text
        except sr.WaitTimeoutError:
            print("[System]: Listening timed out. Try speaking again or type your message.")
            return None
        except sr.UnknownValueError:
            print("[System]: Could not understand audio.")
            return None
        except sr.RequestError as e:
            print(f"[Speech Error]: Service error: {e}")
            return None

# 3. Connect to Groq API
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ.get("GROQ_API_KEY")
)

MODEL_NAME = "openai/gpt-oss-120b"

# 4. Load Memory Context
try:
    with open('user_profile.json', 'r') as f:
        user_profile_data = json.load(f)
except FileNotFoundError:
    user_profile_data = {}

system_prompt = f"""
You are AURA (Advanced Personal Assistant), running locally for De Great.
User Context:
- Name: {user_profile_data.get('master_profile', {}).get('name', 'De Great')}
- Brand: {user_profile_data.get('photography_context', {}).get('brand_name', 'GREAT LENZ')}

Keep responses conversational, concise, and clear so they sound natural when spoken aloud.
Assist De Great with his engineering projects, GREAT LENZ photography concepts, and Physics preparation.
"""

# 5. Interactive Full Voice Loop
if __name__ == "__main__":
    print("==========================================")
    print("       AURA CORE SYSTEM INITIALIZED       ")
    print("==========================================")
    print(f"Active Model: {MODEL_NAME}")
    print("Press Ctrl+C to stop.\n")
    
    speak("AURA system online. Listening, De Great.")

    while True:
        # 1. Listen via microphone first
        user_say = listen()
        
        # 2. Fallback to typed input if mic did not catch anything
        if not user_say:
            user_say = input("\nYou (Type or press Enter to retry mic): ")
            if not user_say.strip():
                continue

        if user_say.lower() in ['quit', 'exit']:
            speak("Shutting down AURA core systems. Goodbye, De Great.")
            print("Shutting down AURA...")
            break
            
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_say}
                ],
                temperature=0.7,
            )
            
            reply_text = response.choices[0].message.content
            print(f"\nAURA: {reply_text}\n")
            
            speak(reply_text)
            
        except Exception as e:
            print(f"\nAURA Error: {e}\n")