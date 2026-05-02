# Gemini 3.1 Flash TTS Tutorial

> Google **Gemini 3.1 Flash TTS Preview** 모델로 만든 58개 다국어/다감정 음성 합성 튜토리얼 + Audio Profile 일관성 전략 비교 실험

**Live Demo**: https://joonlab.github.io/gemini-3-1-flash-tts-tutorial/

## 개요

- **모델**: `gemini-3.1-flash-tts-preview` (Google AI Studio · `google-genai` SDK)
- **시나리오**: 58개 (8개 카테고리)
- **언어**: 8개 — 한국어 · English · 日本語 · 中文 · Tiếng Việt · Русский · Oʻzbek* · ខ្មែរ* (* 실험적)
- **Voice**: Kore / Puck / Charon / Zephyr / Leda (전체 30+ voice 중 5개 사용)
- **총 오디오**: ~152분 / ~417 MB

## 카테고리 구성

| 카테고리 | 설명 | 시나리오 수 |
|---|---|---|
| `basic` | 8개 언어 기본 인사·자기소개 | 8 |
| `emotion` | `[whispers]`, `[excited]` 등 인라인 태그 + 자연어 prefix 감정 제어 | 6 |
| `voice_compare` | 동일 한국어 텍스트로 4개 voice 비교 | 4 |
| `parameter` | style instruction 변경에 따른 톤 변화 (뉴스앵커/동화구연자) | 2 |
| `topik_mixed` | TOPIK 학습자(외국어 화자)에게 한국어 문법·어휘를 해당 언어로 설명 | 7 |
| `topik_long` | TOPIK 28-34 종합 레슨 (10분 분량 × 7개 언어) — Advanced Prompt 구조 | 7 |
| `consistency_test` | Audio Profile 일관성 4전략 비교 (Advanced Prompt / Same prefix / Multi-speaker / Chunk merge) | 17 |
| `topik_long_chunked` | 5섹션 청크 분할 + 300ms 무음 병합 — 장문 일관성 전략 | 7 |
| **합계** | | **58** |

## Audio Profile 일관성 4가지 전략

장문 다국어 강의 음성에서 화자의 톤·페이스가 일관되게 유지되도록 4가지 전략을 비교 실험:

1. **Advanced Prompt** — 시스템 prompt에 화자 페르소나/스타일 명시
2. **Same prefix** — 모든 청크에 동일한 prefix 문장 삽입
3. **Multi-speaker** — multi-speaker 모드를 single-speaker 용도로 활용
4. **Chunk merge** — 5개 섹션으로 분할 생성 후 300ms 무음 병합

## 로컬에서 실행하기

```bash
git clone https://github.com/joonlab/gemini-3-1-flash-tts-tutorial.git
cd gemini-3-1-flash-tts-tutorial
python3 -m http.server 8000
# http://localhost:8000/ 접속
```

## TTS 재합성하기

```bash
cd code
pip install -r requirements.txt
export GEMINI_PAID_API_KEY=your_key_here
python3 run_all.py
```

특정 시나리오만 재생성하려면:

```bash
python3 regenerate_subset.py --no 1,5,12
python3 regenerate_subset.py --category emotion
```

## 폴더 구조

```
.
├── index.html              # 단일 페이지 대시보드 진입점
├── styles.css              # Raycast 영감 다크 테마
├── app.js                  # 라우팅 + 카드 렌더링
├── data.json               # 통합 메타데이터 (시나리오 + 코드 본문 인라인)
├── audio/                  # 58개 .wav (24kHz / 16-bit / mono PCM) + chunks/
├── script/                 # 시나리오 스크립트 원문
├── code/                   # TTS 생성 Python 코드 (google-genai SDK)
├── research/               # 연구·조사 자료
├── gemini_tts_test_mapping.xlsx
└── README.md
```

## 디자인 시스템

- **배경**: `#07080a` (near-black blue)
- **서피스**: `#101111`
- **강조 (Raycast Red)**: `#FF6363`
- **블루 / 그린 / 옐로 / 골드** 보조색 사용
- **폰트**: Inter (Google Fonts) + Geist Mono + Noto Sans KR
- **카드 그림자**: double-ring (`outer 1px` + `inset 1px`)

## 기술 스택

- **Frontend**: Vanilla HTML/CSS/JS (프레임워크 없음)
- **Backend (TTS 생성)**: Python 3 + `google-genai` SDK
- **재시도 전략**: utils.py 강건한 exponential backoff
- **호스팅**: GitHub Pages (정적)

## 가격 정보

- Free Tier: 무료 (입력 데이터가 모델 개선에 사용됨)
- Paid Tier:
  - Input (text): **$1 / 1M tokens**
  - Output (audio): **$20 / 1M tokens**
  - 분당: **~$0.03 / minute**
- 58개 시나리오 / ~152분 → 약 $4.5

## 라이선스

MIT

## 만든 사람

joonlab + Claude Code (Agent Teams 협업)
