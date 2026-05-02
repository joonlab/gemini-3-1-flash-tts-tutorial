"""TOPIK long lesson 28~34 병렬 생성. 단일 요청, max_retries=3."""
import json
import os
import sys
import time
import wave
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from google import genai
from google.genai import types

ROOT = Path(__file__).resolve().parent.parent
SCRIPT_DIR = ROOT / "Script"
AUDIO_DIR = ROOT / "Audio"
INDEX_PATH = SCRIPT_DIR / "_index.json"
LOG_PATH = AUDIO_DIR / "_generation_log.json"
MODEL_ID = "gemini-3.1-flash-tts-preview"


def wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(filename), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)


def generate_one(client, sc, max_retries=3):
    no = sc["no"]
    text = sc["tts_input"]
    voice = sc["voice"]
    out_path = AUDIO_DIR / f"{sc['filename_base']}.wav"
    last_err = None
    for attempt in range(1, max_retries + 1):
        t0 = time.time()
        try:
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                        )
                    ),
                ),
            )
            cand = response.candidates[0] if response.candidates else None
            if cand is None or cand.content is None or not cand.content.parts:
                raise RuntimeError(f"Empty response (finish_reason={getattr(cand, 'finish_reason', None)})")
            data = cand.content.parts[0].inline_data.data
            wave_file(out_path, data)
            elapsed_ms = int((time.time() - t0) * 1000)
            with wave.open(str(out_path)) as wf:
                duration = wf.getnframes() / wf.getframerate()
            size = out_path.stat().st_size
            print(f"  [{no}] OK voice={voice} dur={duration:.1f}s size={size//1024}KB ms={elapsed_ms}", flush=True)
            return {
                "no": no,
                "filename": sc["filename_base"],
                "status": "success",
                "duration_sec": round(duration, 2),
                "file_size_bytes": size,
                "error": None,
                "elapsed_api_ms": elapsed_ms,
            }
        except Exception as e:
            last_err = str(e)
            elapsed_ms = int((time.time() - t0) * 1000)
            print(f"  [{no}] attempt {attempt}/{max_retries} FAIL ms={elapsed_ms}: {last_err[:160]}", flush=True)
            if attempt < max_retries:
                time.sleep(60)
    return {
        "no": no,
        "filename": sc["filename_base"],
        "status": "failed",
        "duration_sec": 0.0,
        "file_size_bytes": 0,
        "error": last_err,
        "elapsed_api_ms": 0,
    }


def main(target_nos):
    api_key = os.environ.get("GEMINI_PAID_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_PAID_API_KEY not set")
        sys.exit(1)
    client = genai.Client(api_key=api_key)

    with INDEX_PATH.open(encoding="utf-8") as f:
        index = json.load(f)
    with LOG_PATH.open(encoding="utf-8") as f:
        log = json.load(f)

    by_no = {s["no"]: s for s in index["scenarios"]}
    targets = [by_no[n] for n in target_nos if n in by_no]
    print(f"Targets: {[s['no'] for s in targets]}", flush=True)

    results = []
    # 순차 처리 + 30초 sleep (rate limit 회피, 메모리 기반 정책)
    for i, sc in enumerate(targets):
        if i > 0:
            time.sleep(30)
        results.append(generate_one(client, sc))

    # 로그 갱신
    by_no_log = {r["no"]: i for i, r in enumerate(log["results"])}
    for r in results:
        if r["no"] in by_no_log:
            log["results"][by_no_log[r["no"]]] = r
        else:
            log["results"].append(r)

    log["completed_at"] = datetime.utcnow().isoformat() + "Z"
    log["summary"] = {
        "total": len(log["results"]),
        "success": sum(1 for r in log["results"] if r["status"] == "success"),
        "failed": sum(1 for r in log["results"] if r["status"] != "success"),
    }
    with LOG_PATH.open("w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

    fails = [r for r in results if r["status"] != "success"]
    print(f"\nThis batch: success={sum(1 for r in results if r['status']=='success')}, failed={len(fails)}", flush=True)
    if fails:
        for f_ in fails:
            print(f"  FAIL [{f_['no']}]: {f_['error']}", flush=True)
    print(f"Overall log summary: {log['summary']}")


if __name__ == "__main__":
    nos = [int(x) for x in sys.argv[1:]] if len(sys.argv) > 1 else [28, 29, 30, 31, 32, 33, 34]
    main(nos)
