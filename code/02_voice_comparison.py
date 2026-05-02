"""Gemini 3.1 Flash TTS - 같은 텍스트로 4개 voice 비교 데모."""
import time

from utils import get_client, generate_tts

TEXT = "안녕하세요. 오늘은 Gemini TTS의 다양한 음성을 비교해 보겠습니다."
VOICES = ["Kore", "Puck", "Charon", "Zephyr"]


def main():
    client = get_client()
    for i, voice in enumerate(VOICES, 1):
        out = f"../Audio/_demo_voice_{voice.lower()}.wav"
        print(f"[{i}/{len(VOICES)}] voice={voice} → {out}")
        ok, dur, size, err, ms = generate_tts(client, TEXT, voice, out)
        if ok:
            print(f"    OK ({dur:.1f}s, {size/1024:.1f}KB, api {ms}ms)")
        else:
            print(f"    FAIL: {err}")
        if i < len(VOICES):
            time.sleep(2.0)


if __name__ == "__main__":
    main()
