# Gemini 3.1 Flash TTS Tutorial

> Google **Gemini 3.1 Flash TTS Preview** 모델로 만든 72개 다국어/다감정 음성 합성 튜토리얼 + Audio Profile 일관성 4단계(v0/v1/v2/v3 DSP) 비교 실험 (7개 언어 전체)

**Live Demo**: https://joonlab.github.io/gemini-3-1-flash-tts-tutorial/

## 개요

- **모델**: `gemini-3.1-flash-tts-preview` (Google AI Studio · `google-genai` SDK)
- **시나리오**: 72개 (10개 카테고리)
- **언어**: 8개 — 한국어 · English · 日本語 · 中文 · Tiếng Việt · Русский · Oʻzbek* · ខ្មែរ* (* 실험적)
- **Voice**: Kore / Puck / Charon / Zephyr / Leda (전체 30+ voice 중 5개 사용)
- **총 오디오**: ~300분 / ~825 MB

## 카테고리 구성

| 카테고리 | 설명 | 시나리오 수 |
|---|---|---|
| `basic` | 8개 언어 기본 인사·자기소개 | 8 |
| `emotion` | `[whispers]`, `[excited]` 등 인라인 태그 + 자연어 prefix 감정 제어 | 6 |
| `voice_compare` | 동일 한국어 텍스트로 4개 voice 비교 | 4 |
| `parameter` | style instruction 변경에 따른 톤 변화 (뉴스앵커/동화구연자) | 2 |
| `topik_mixed` | TOPIK 학습자(외국어 화자)에게 한국어 문법·어휘를 해당 언어로 설명 | 7 |
| `topik_long` | TOPIK 28-34 종합 레슨 (10분 분량 × 7개 언어) — Advanced Prompt 구조 (v0) | 7 |
| `consistency_test` | Audio Profile 일관성 4전략 비교 (Advanced Prompt / Same prefix / Multi-speaker / Chunk merge) | 17 |
| `topik_long_chunked` | 5섹션 청크 분할 + 300ms 무음 병합 — 장문 일관성 전략 (v1) | 7 |
| `topik_long_optimized` | duration 균등 분할 + Multi-speaker + Loudnorm + Crossfade — 최적화 전략 (v2) | 7 |
| `topik_long_v3_dsp` | **v2 청크에 F0 정규화 + Spectral envelope matching DSP — 일관성 강화 (v3)** | **7** |
| **합계** | | **72** |

## Audio Profile 일관성 4가지 전략

장문 다국어 강의 음성에서 화자의 톤·페이스가 일관되게 유지되도록 4가지 전략을 비교 실험:

1. **Advanced Prompt** — 시스템 prompt에 화자 페르소나/스타일 명시
2. **Same prefix** — 모든 청크에 동일한 prefix 문장 삽입
3. **Multi-speaker** — multi-speaker 모드를 single-speaker 용도로 활용
4. **Chunk merge** — 5개 섹션으로 분할 생성 후 300ms 무음 병합

## 🔬 v0/v1/v2/v3 4-way 비교 실험 (7개 언어 전체)

10분 분량 TOPIK 종합 레슨에서 드리프트가 의심된 **7개 언어(EN/JA/ZH/VI/RU/UZ\*/KM\*)** 모두에 대해 단계적 최적화 결과를 비교 (\* = 실험적):

### v0 single (단일 요청)
- 시나리오 #28~#34 — 7개 언어
- 전체 스크립트를 한 번에 단일 TTS 요청으로 합성

### v1 chunked (5섹션 단락 분할 + 300ms 무음)
- 시나리오 #52~#58 — 7개 언어
- 5개 섹션으로 분할 생성 후 300ms 무음 삽입 병합
- 단락 길이 편차 큼 (39~200초, 5배 차이)

### v2 optimized (균등 분할 + Multi-speaker + Loudnorm + Crossfade)
- 시나리오 #59 (EN/Charon), #60 (VI/Puck), #61 (KM/Leda), #62 (JA/Leda), #63 (ZH/Kore), #64 (RU/Zephyr), #65 (UZ/Charon)
- **3가지 전략 결합**:
  1. Duration 균등 분할 (~90초/청크, v1의 5배 편차 해소)
  2. Multi-speaker mode (dummy 2nd speaker로 안정화)
  3. 음량 정규화(`ffmpeg loudnorm -23 LUFS`) + 무음 트림 + 100ms 코사인 크로스페이드 병합
- 28개 청크 모두 loudnorm 적용 · `INVALID_ARGUMENT` 에러 0건

## 🎚 v3 DSP 일관성 보정

v2 청크에 한 단계 더 강화된 **DSP 후처리**를 적용한 **v3** 결과 (시나리오 **#66~#72**):

- **F0 pitch normalization** — pyworld dio/stonemask로 청크별 평균 F0를 추정한 뒤 1번째 청크(reference)에 맞춰 ratio 보정 (clamp 0.85~1.18)
- **Spectral envelope matching** — pyworld cheaptrick으로 spectral envelope을 ref-bias 50%로 매칭
- **재 trim + 재 loudnorm + 100ms crossfade** 병합

### v3 정량 결과 — 평균 f0_std 감소 **−44.3%**

| 언어 | f0_std before | f0_std after | 감소율 |
|---|---|---|---|
| Vietnamese (Puck) | 8.15 Hz | 2.42 Hz | **−70.3%** |
| Russian (Zephyr) | 11.65 Hz | 4.40 Hz | **−62.2%** |
| Khmer\* (Leda) | 10.77 Hz | 5.27 Hz | **−51.1%** |
| Uzbek\* (Charon) | 13.17 Hz | 6.63 Hz | **−49.6%** |
| Mandarin (Kore) | 7.62 Hz | 4.26 Hz | **−44.2%** |
| English (Charon) | 5.49 Hz | 3.54 Hz | **−35.5%** |
| Japanese (Leda) | 5.29 Hz | 5.44 Hz | −2.8% (이미 충분히 일관됨) |

### 핵심 결과 (duration 비교)

| 언어 | v0 single | v1 chunked | v2 optimized | v3 DSP ✨ | 청크 수 |
|---|---|---|---|---|---|
| English (Charon) | #28 | #52 | #59 — 641s | **#66 — 641s** | 6 |
| Japanese (Leda) | #29 | #53 | #62 — 615s | **#67 — 615s** | 7 |
| Mandarin (Kore) | #30 | #54 | #63 — 583s | **#68 — 583s** | 7 |
| Vietnamese (Puck) | #31 | #55 | #60 — 598s | **#69 — 598s** | 7 |
| Russian (Zephyr) | #32 | #56 | #64 — 629s | **#70 — 629s** | 7 |
| Uzbek\* (Charon) | #33 | #57 | #65 — 656s | **#71 — 656s** | 7 |
| Khmer\* (Leda) | #34 | #58 | #61 — 735s | **#72 — 734s** | 8 |

대시보드의 `topik_long_optimized` 또는 `topik_long_v3_dsp` 카테고리에서 v0/v1/v2/v3 7-row × 4-col 비교 청취 가능.

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

v2 최적화 전략 (균등 분할 + multi-speaker + 후처리)은 별도 스크립트로 처리:

```bash
# 균등 분할
python3 chunk_balanced.py --no 59
# Multi-speaker 합성
python3 generate_multispeaker.py --no 59
# 음량 정규화 + 크로스페이드 병합
python3 postprocess_merge.py --no 59
```

v3 DSP 후처리 (F0 정규화 + Spectral matching) 적용:

```bash
# v2 청크 + dsp_merge.py
python3 dsp_merge.py --no 66  # v2 #59 → v3 #66
```

## 폴더 구조

```
.
├── index.html              # 단일 페이지 대시보드 진입점
├── styles.css              # Raycast 영감 다크 테마
├── app.js                  # 라우팅 + 카드 렌더링 + v0/v1/v2/v3 4-way 비교 뷰
├── data.json               # 통합 메타데이터 (시나리오 + 코드 본문 인라인)
├── audio/                  # 72개 .wav (24kHz / 16-bit / mono PCM) + chunks/
├── script/                 # 시나리오 스크립트 원문
├── code/                   # TTS 생성 Python 코드 (google-genai SDK + DSP 후처리)
└── README.md
```

## 디자인 시스템

- **배경**: `#07080a` (near-black blue)
- **서피스**: `#101111`
- **강조 (Raycast Red)**: `#FF6363`
- **v3 DSP gold**: `#85714D`
- **블루 / 그린 / 옐로 / 골드** 보조색 사용
- **폰트**: Inter (Google Fonts) + Geist Mono + Noto Sans KR
- **카드 그림자**: double-ring (`outer 1px` + `inset 1px`)

## 기술 스택

- **Frontend**: Vanilla HTML/CSS/JS (프레임워크 없음)
- **Backend (TTS 생성)**: Python 3 + `google-genai` SDK
- **후처리**: ffmpeg (loudnorm -23 LUFS, silenceremove, acrossfade) + pyworld (F0/spectral DSP)
- **재시도 전략**: utils.py 강건한 exponential backoff
- **호스팅**: GitHub Pages (정적)

## 가격 정보

- Free Tier: 무료 (입력 데이터가 모델 개선에 사용됨)
- Paid Tier:
  - Input (text): **$1 / 1M tokens**
  - Output (audio): **$20 / 1M tokens**
  - 분당: **~$0.03 / minute**
- 72개 시나리오 / ~300분 → 약 $9

## 라이선스

MIT

## 만든 사람

joonlab + Claude Code (Agent Teams 협업)
