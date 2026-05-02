# Gemini 3.1 Flash TTS 튜토리얼 코드

`gemini-3.1-flash-tts-preview` 모델로 Python에서 음성 합성을 수행하는 튜토리얼 예제 모음.

## 환경 설정

```bash
# 1) API 키 환경변수
export GEMINI_PAID_API_KEY=YOUR_KEY_HERE

# 2) 의존성 설치
pip install -r requirements.txt
```

`google-genai >= 1.74.0` 이상이 필요합니다.

## 빠른 실행

### 일괄 합성 (메인 워크플로)
```bash
cd code
python run_all.py
```
- `Script/_index.json` 의 시나리오를 모두 순회
- `Audio/{filename_base}.wav` 로 저장
- 결과 로그: `Audio/_generation_log.json`

### 개별 데모 스크립트
| 파일 | 설명 |
|------|------|
| `01_basic_single_speaker.py` | 가장 간단한 1인 합성 (Kore voice) |
| `02_voice_comparison.py` | Kore / Puck / Charon / Zephyr 비교 |
| `03_emotion_styles.py` | `[excited]`, `[whispers]` 등 감정 태그 |
| `04_multilingual.py` | 6개 지원 언어 + 2개 미지원 언어 비교 |
| `05_topik_mixed.py` | 한국어 + 학습자 모국어 혼합 해설 |

## 모델 / 음성 정보

- **모델 ID**: `gemini-3.1-flash-tts-preview`
- **출력 포맷**: PCM 24kHz / 16-bit / mono → `.wav` 변환
- **사용 voice**: Kore (Firm), Puck (Upbeat), Charon (Informative), Zephyr (Bright), Leda (Youthful)
- **공식 지원 언어 (튜토리얼 사용)**: ko, en, ja, zh, vi, ru
- **미지원 언어 (테스트 시도)**: uz (우즈베크어), km (크메르어)

미지원 언어는 합성이 거부되거나(`PROHIBITED_CONTENT`) 음질이 떨어질 수 있습니다.

## 주의 사항

- preview 모델은 5xx / 429 에러가 간헐적으로 발생하므로 `utils.generate_tts()`가 60초 sleep 후 최대 3회 재시도합니다.
- 요청 간 2초 sleep 이 적용됩니다.
- 32k token 컨텍스트 한도가 있으니 매우 긴 입력은 chunk 처리하세요.
- 스트리밍은 지원되지 않습니다 (필요 시 Live API 사용).
