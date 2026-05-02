# Gemini 3.1 Flash TTS - 조사 결과 (2026-05-03)

## 1. 모델 정보
- **모델 ID**: `gemini-3.1-flash-tts-preview` (Preview 단계)
- **대안 모델**: `gemini-2.5-flash-preview-tts`, `gemini-2.5-pro-preview-tts`
- **공식 문서**: https://ai.google.dev/gemini-api/docs/speech-generation

## 2. SDK / 인증
- **Python 패키지**: `google-genai >= 1.74.0`
- **설치**: `pip install -U google-genai`
- **인증 환경변수**: `GEMINI_API_KEY` 또는 `GOOGLE_API_KEY` (이 프로젝트에선 `GEMINI_PAID_API_KEY` 환경변수 값을 직접 전달)

## 3. 사용 가능 Voice (30개)
대표 5개 (튜토리얼에서 사용):
- **Kore** (Firm) — 안정적인 단단한 톤
- **Puck** (Upbeat) — 발랄하고 경쾌
- **Charon** (Informative) — 정보 전달용 차분한 톤
- **Zephyr** (Bright) — 밝고 또렷
- **Leda** (Youthful) — 젊고 활기

전체 목록: Zephyr, Puck, Charon, Kore, Fenrir, Leda, Orus, Aoede, Callirrhoe, Autonoe, Enceladus, Iapetus, Umbriel, Algieba, Despina, Erinome, Algenib, Rasalgethi, Laomedeia, Achernar, Alnilam, Schedar, Gacrux, Pulcherrima, Achird, Zubenelgenubi, Vindemiatrix, Sadachbia, Sadaltager, Sulafat

## 4. 언어 지원
**공식 지원 80여개 언어**. 사용자 요청 8개 언어 중:

| 언어 | 코드 | 공식 지원 |
|------|------|----------|
| 한국어 | ko | ✅ |
| 영어 | en | ✅ |
| 일본어 | ja | ✅ |
| 중국어(Mandarin) | cmn | ✅ |
| 베트남어 | vi | ✅ |
| 러시아어 | ru | ✅ |
| **우즈벡어** | uz | ❌ 미지원 |
| **크메르어** | km | ❌ 미지원 |

**언어 감지**: 별도 파라미터 없음. **입력 텍스트 자체에서 자동 감지**.
**미지원 언어 처리 (사용자 지시)**: 언어 지정 없이 해당 언어 텍스트 그대로 입력하여 실험적 시도 (품질 보장 X).

## 5. 출력 오디오 포맷
- 인코딩: **PCM, 24kHz, 16-bit, mono, signed little-endian**
- WAV 변환은 Python `wave` 모듈 사용

## 6. 감정 / 스타일 제어
1. **자연어 prefix**: `"Say cheerfully: 안녕하세요"`
2. **인라인 오디오 태그** (대괄호, 영어로): `[whispers]`, `[excited]`, `[sad]`, `[laughs]`, `[crying]`, `[shouting]`, `[very fast]` 등
3. **고급 구조화 프롬프트**: Audio Profile / Scene / Director's Notes / Transcript 섹션 분리
4. **Multi-speaker 가이드**: prompt header에 명시 (최대 2명)

## 7. 제약
- **Text-only 입력 → Audio 전용 출력**
- **Context window 32k tokens**
- **Streaming 미지원** (실시간은 Live API 사용)
- **긴 출력은 drift** — 수 분 이상 텍스트는 chunking 필수
- **Random 500 에러** — retry 로직 필수
- **PROHIBITED_CONTENT** — 모호한 prompt 방지 위해 "Read the following text aloud:" 같은 명시 prefix 권장

## 8. Rate Limit / 가격
- **Preview 모델**은 GA 모델보다 RPM 제한이 더 빡빡함 (구체 수치 미공개, AI Studio에서 확인)
- Free tier: 무료 (학습 데이터로 활용됨)
- Paid tier:
  - Input text: $1.00 / 1M tokens
  - Output audio: $20.00 / 1M tokens (≈ $0.03/분)

## 9. Single Speaker 코드 예제

```python
from google import genai
from google.genai import types
import wave, os

def wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)

client = genai.Client(api_key=os.environ["GEMINI_PAID_API_KEY"])
response = client.models.generate_content(
    model="gemini-3.1-flash-tts-preview",
    contents="[excitedly] 안녕하세요! 멋진 하루죠?",
    config=types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name='Leda')
            )
        )
    ),
)
data = response.candidates[0].content.parts[0].inline_data.data
wave_file("out.wav", data)
```

## 10. Multi-Speaker 코드 예제

```python
from google.genai import types

prompt = """TTS the following conversation between Joe and Jane:
Joe: How's it going today Jane?
Jane: Not too bad, how about you?"""

response = client.models.generate_content(
    model="gemini-3.1-flash-tts-preview",
    contents=prompt,
    config=types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                speaker_voice_configs=[
                    types.SpeakerVoiceConfig(
                        speaker='Joe',
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name='Kore'))),
                    types.SpeakerVoiceConfig(
                        speaker='Jane',
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name='Puck'))),
                ]
            )
        )
    ),
)
```

## Sources
- [Gemini API - Speech generation (TTS)](https://ai.google.dev/gemini-api/docs/speech-generation)
- [google-genai PyPI](https://pypi.org/project/google-genai/)
- [Gemini API Pricing](https://ai.google.dev/pricing)
