"""Gemini 3.1 Flash TTS - TOPIK 다국어 혼합 해설 데모.

TOPIK 학습 콘텐츠처럼 한국어 본문 + 학습자 모국어 해설이 섞인 케이스를 합성한다.
하나의 voice가 여러 언어를 자연스럽게 발화할 수 있는지 확인한다.
"""
import time

from utils import get_client, generate_tts

DEMOS = [
    (
        "ko_en_mix",
        "Kore",
        "오늘의 표현은 '반갑습니다'입니다. In English, this means 'nice to meet you'. "
        "It is commonly used when meeting someone for the first time.",
    ),
    (
        "ko_vi_mix",
        "Charon",
        "오늘의 표현은 '감사합니다'입니다. Trong tiếng Việt, câu này có nghĩa là 'cảm ơn'. "
        "한국어 인사 중에서 가장 많이 쓰이는 표현 중 하나입니다.",
    ),
]


def main():
    client = get_client()
    for i, (label, voice, text) in enumerate(DEMOS, 1):
        out = f"../Audio/_demo_topik_{label}.wav"
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
