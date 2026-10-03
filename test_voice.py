import pyttsx3

engine = pyttsx3.init()

# Get available system voices
voices = engine.getProperty('voices')

# Set to female voice (Index 1 is usually Microsoft Zira on Windows)
engine.setProperty('voice', voices[1].id)
engine.setProperty('rate', 180)

engine.say("AURA vocal audio sub-system online, De Great. Voice profile updated.")
engine.runAndWait()