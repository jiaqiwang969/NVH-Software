from openai import OpenAI
client = OpenAI()

audio_file= open("audio_2025-01-07_22-25-56.mp3", "rb")
transcription = client.audio.transcriptions.create(
    model="whisper-1", 
    file=audio_file
)

print(transcription.text)
