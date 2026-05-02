"""Gemini 3.1 Flash TTS - 감정/스타일 태그 데모."""
import time

from utils import get_client, generate_tts

DEMOS = [
    ("excited", "Leda", "[excited] 와! 드디어 해냈어요! 정말 믿기지 않아요!"),
    ("whisper", "Zephyr", "[whispers] 아무한테도 말하지 마. 이건 우리만의 비밀이야."),
    ("sad", "Charon", "[sad] 그날 이후로 모든 게 변해버렸어요. 다시 돌아갈 수 없겠죠."),
    ("cheerful_prefix", "Puck", "Say cheerfully: 오늘 날씨가 정말 좋네요! 산책하기 딱 좋은 날이에요."),
]


def main():
    client = get_client()
    for i, (label, voice, text) in enumerate(DEMOS, 1):
        out = f"../Audio/_demo_emotion_{label}.wav"
        print(f"[{i}/{len(DEMOS)}] {label} (voice={voice}) → {out}")
        ok, dur, size, err, ms = generate_tts(client, text, voice, out)
        if ok:
            print(f"    OK ({dur:.1f}s, {size/1024:.1f}KB)")
        else:
            print(f"    FAIL: {err}")
        if i < len(DEMOS):
            time.sleep(2.0)


if __name__ == "__main__":
    main()
