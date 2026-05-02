"""Gemini 3.1 Flash TTS - 다국어 지원 데모.

공식 지원 6개 + 미지원 추정 2개를 시도하여 동작 차이를 비교한다.
미지원 언어는 PROHIBITED_CONTENT 또는 부정확한 합성이 발생할 수 있다.
"""
import time

from utils import get_client, generate_tts

DEMOS = [
    # (lang, voice, label, text, supported)
    ("ko", "Kore", "korean", "안녕하세요. 만나서 반갑습니다.", True),
    ("en", "Puck", "english", "Hello, nice to meet you.", True),
    ("ja", "Leda", "japanese", "こんにちは。はじめまして。", True),
    ("zh", "Charon", "chinese", "你好,很高兴见到你。", True),
    ("vi", "Zephyr", "vietnamese", "Xin chào, rất vui được gặp bạn.", True),
    ("ru", "Kore", "russian", "Здравствуйте, приятно познакомиться.", True),
    ("uz", "Puck", "uzbek_unsupported", "Salom, tanishganimdan xursandman.", False),
    ("km", "Leda", "khmer_unsupported", "សួស្តី, រីករាយដែលបានជួប.", False),
]


def main():
    client = get_client()
    for i, (lang, voice, label, text, supported) in enumerate(DEMOS, 1):
        out = f"../Audio/_demo_multilingual_{lang}_{label}.wav"
        tag = "지원" if supported else "미지원(테스트)"
        print(f"[{i}/{len(DEMOS)}] {lang} {tag} (voice={voice}) → {out}")
        ok, dur, size, err, ms = generate_tts(client, text, voice, out)
        if ok:
            print(f"    OK ({dur:.1f}s, {size/1024:.1f}KB)")
        else:
            print(f"    FAIL: {err}")
        if i < len(DEMOS):
            time.sleep(2.0)


if __name__ == "__main__":
    main()
