"""Gemini 3.1 Flash TTS - Single Speaker 기본 예제."""
from utils import get_client, wave_file, MODEL_ID
from google.genai import types

client = get_client()

response = client.models.generate_content(
    model=MODEL_ID,
    contents="안녕하세요! Gemini 3.1 Flash TTS 튜토리얼에 오신 것을 환영합니다.",
    config=types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Kore")
            )
        ),
    ),
)

data = response.candidates[0].content.parts[0].inline_data.data
wave_file("../Audio/_demo_basic.wav", data)
print("완료: ../Audio/_demo_basic.wav")
