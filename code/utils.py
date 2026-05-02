"""Gemini 3.1 Flash TTS 공용 유틸리티"""
import os
import random
import time
import wave
from pathlib import Path

from google import genai
from google.genai import types


MODEL_ID = "gemini-3.1-flash-tts-preview"

# Retry 정책 (call_with_retry 참고)
RETRY_BACKOFFS = [5, 15, 30, 60, 120]
RETRY_MAX_ATTEMPTS = 5
RETRY_RATE_LIMIT_MAX_HITS = 3
RETRY_FATAL_TOKENS = (
    "401",
    "403",
    "PERMISSION_DENIED",
    "INVALID_ARGUMENT",
    "API key not valid",
)
RETRY_RATE_LIMIT_TOKENS = ("429", "RESOURCE_EXHAUSTED")


def get_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_PAID_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_PAID_API_KEY 환경변수가 설정되어 있지 않습니다. "
            "export GEMINI_PAID_API_KEY=... 후 다시 실행해 주세요."
        )
    return genai.Client(api_key=api_key)


def wave_file(filename, pcm, channels: int = 1, rate: int = 24000, sample_width: int = 2) -> None:
    """PCM 바이트를 .wav 파일로 저장."""
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(filename), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)


def get_wav_duration_sec(filename) -> float:
    with wave.open(str(filename), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / float(rate) if rate else 0.0


def get_file_size(filename) -> int:
    try:
        return os.path.getsize(filename)
    except OSError:
        return 0


def call_with_retry(fn, *args, max_attempts: int = RETRY_MAX_ATTEMPTS, label: str = "tts", **kwargs):
    """
    재시도 정책:
    - max_attempts 회 (기본 5)
    - backoff: 5s → 15s → 30s → 60s → 120s + jitter (0~30%)
    - 4xx (401/403/INVALID_ARGUMENT/PERMISSION_DENIED): 즉시 raise (재시도 무의미)
    - 429 (RESOURCE_EXHAUSTED): 90+jitter 초 sleep, attempt counter 증가 X (단 누적 3회 초과 시 raise)
    - 5xx + Empty response (FinishReason.OTHER/RECITATION/PROHIBITED_CONTENT) + 네트워크: 일반 backoff
    """
    rate_limit_hits = 0
    last_exc = None

    attempt = 0
    while attempt < max_attempts:
        try:
            return fn(*args, **kwargs)
        except Exception as e:  # noqa: BLE001
            last_exc = e
            err_str = str(e)
            err_upper = err_str.upper()

            # 1) 영구 실패 - 즉시 raise
            if any(tok in err_upper for tok in (t.upper() for t in RETRY_FATAL_TOKENS)):
                raise

            # 2) Rate limit - attempt 증가시키지 않고 긴 sleep
            if any(tok in err_upper for tok in RETRY_RATE_LIMIT_TOKENS):
                rate_limit_hits += 1
                if rate_limit_hits > RETRY_RATE_LIMIT_MAX_HITS:
                    raise
                wait = 90 + random.randint(0, 30)
                print(
                    f"    [{label}] rate-limit hit #{rate_limit_hits}, sleep {wait}s: {err_str[:120]}"
                )
                time.sleep(wait)
                continue

            # 3) Transient (5xx, Empty response, 네트워크 등) - 일반 backoff
            if attempt + 1 >= max_attempts:
                raise
            backoff = RETRY_BACKOFFS[min(attempt, len(RETRY_BACKOFFS) - 1)]
            wait = backoff + random.uniform(0, backoff * 0.3)
            print(
                f"    [{label}] {attempt + 1}/{max_attempts} fail: {err_str[:120]}, sleep {wait:.0f}s"
            )
            time.sleep(wait)
            attempt += 1

    # 도달 불가 영역 (안전망)
    if last_exc is not None:
        raise last_exc
    raise RuntimeError(f"call_with_retry exhausted without exception (label={label})")


def _validate_wav(out_path) -> None:
    """생성된 wav가 유효한지 (size > 1KB + wave.open 가능) 검증."""
    p = Path(out_path)
    size = p.stat().st_size if p.exists() else 0
    if size < 1024:
        raise RuntimeError(f"Generated wav too small: {size}B path={p}")
    try:
        with wave.open(str(p), "rb") as wf:
            if wf.getnframes() <= 0:
                raise RuntimeError(f"Generated wav has 0 frames: {p}")
    except wave.Error as e:
        raise RuntimeError(f"Generated wav not readable ({e}): {p}") from e


def generate_tts(
    client: genai.Client,
    text: str,
    voice_name: str,
    out_path,
    max_retries: int = RETRY_MAX_ATTEMPTS,
    sleep_between: float = 2.0,
):
    """TTS 합성 → wav 저장. (success, duration_sec, file_size, error_msg, elapsed_ms) 반환.

    호환 유지: signature 그대로. max_retries 기본값만 3 → 5로 상향.
    """
    def _do():
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice_name
                        )
                    )
                ),
            ),
        )
        cand = response.candidates[0] if response.candidates else None
        if cand is None or cand.content is None or not cand.content.parts:
            raise RuntimeError(
                f"Empty response (finish_reason={getattr(cand, 'finish_reason', None)})"
            )
        data = cand.content.parts[0].inline_data.data
        wave_file(out_path, data)
        _validate_wav(out_path)
        return data

    start = time.time()
    try:
        call_with_retry(_do, max_attempts=max_retries, label=f"tts/{voice_name}")
    except Exception as e:  # noqa: BLE001
        elapsed_ms = int((time.time() - start) * 1000)
        return False, 0.0, 0, str(e), elapsed_ms

    elapsed_ms = int((time.time() - start) * 1000)
    duration = get_wav_duration_sec(out_path)
    size = get_file_size(out_path)
    return True, duration, size, None, elapsed_ms


def generate_tts_multispeaker(
    client: genai.Client,
    text: str,
    speaker_voice_pairs,
    out_path,
    max_retries: int = RETRY_MAX_ATTEMPTS,
):
    """Multi-speaker TTS 합성. speaker_voice_pairs = [(speaker_name, voice_name), ...]."""
    speaker_configs = [
        types.SpeakerVoiceConfig(
            speaker=spk,
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
            ),
        )
        for spk, voice in speaker_voice_pairs
    ]

    def _do():
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                        speaker_voice_configs=speaker_configs
                    )
                ),
            ),
        )
        cand = response.candidates[0] if response.candidates else None
        if cand is None or cand.content is None or not cand.content.parts:
            raise RuntimeError(
                f"Empty response (finish_reason={getattr(cand, 'finish_reason', None)})"
            )
        data = cand.content.parts[0].inline_data.data
        wave_file(out_path, data)
        _validate_wav(out_path)
        return data

    label = "multi/" + "+".join(v for _, v in speaker_voice_pairs)
    start = time.time()
    try:
        call_with_retry(_do, max_attempts=max_retries, label=label)
    except Exception as e:  # noqa: BLE001
        elapsed_ms = int((time.time() - start) * 1000)
        return False, 0.0, 0, str(e), elapsed_ms

    elapsed_ms = int((time.time() - start) * 1000)
    duration = get_wav_duration_sec(out_path)
    size = get_file_size(out_path)
    return True, duration, size, None, elapsed_ms


def merge_wavs(input_paths, output_path) -> float:
    """동일 포맷(채널/샘플레이트/샘플폭) wav 파일들을 frame-단위로 단순 concat. duration 반환."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    params = None
    all_frames = []
    for p in input_paths:
        with wave.open(str(p), "rb") as wf:
            cur = wf.getparams()
            if params is None:
                params = cur
            else:
                if (
                    cur.nchannels != params.nchannels
                    or cur.sampwidth != params.sampwidth
                    or cur.framerate != params.framerate
                ):
                    raise RuntimeError(
                        f"wav format mismatch: {p} {cur} vs base {params}"
                    )
            all_frames.append(wf.readframes(cur.nframes))
    if params is None:
        raise RuntimeError("merge_wavs: empty input list")
    with wave.open(str(output_path), "wb") as wo:
        wo.setnchannels(params.nchannels)
        wo.setsampwidth(params.sampwidth)
        wo.setframerate(params.framerate)
        for fr in all_frames:
            wo.writeframes(fr)
    return get_wav_duration_sec(output_path)


def merge_wavs_with_silence(input_paths, output_path, silence_ms: int = 300) -> float:
    """동일 포맷 wav 파일들을 사이에 무음을 끼워 concat. duration 반환."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    params = None
    frames_list = []
    for p in input_paths:
        with wave.open(str(p), "rb") as wf:
            cur = wf.getparams()
            if params is None:
                params = cur
            else:
                if (
                    cur.nchannels != params.nchannels
                    or cur.sampwidth != params.sampwidth
                    or cur.framerate != params.framerate
                ):
                    raise RuntimeError(
                        f"wav format mismatch: {p} {cur} vs base {params}"
                    )
            frames_list.append(wf.readframes(cur.nframes))
    if params is None:
        raise RuntimeError("merge_wavs_with_silence: empty input list")
    silence_frames = int(params.framerate * silence_ms / 1000)
    silence_bytes = b"\x00" * silence_frames * params.sampwidth * params.nchannels
    with wave.open(str(output_path), "wb") as wo:
        wo.setnchannels(params.nchannels)
        wo.setsampwidth(params.sampwidth)
        wo.setframerate(params.framerate)
        for i, fr in enumerate(frames_list):
            wo.writeframes(fr)
            if i < len(frames_list) - 1:
                wo.writeframes(silence_bytes)
    return get_wav_duration_sec(output_path)
