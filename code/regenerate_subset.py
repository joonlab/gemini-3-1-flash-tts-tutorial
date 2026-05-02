"""
지정된 시나리오 번호만 재작성된 .txt에서 다시 읽어 _index.json 갱신 후 재생성.
사용: python regenerate_subset.py 12 14 21 22 23 24 25
"""
import json
import os
import sys
import time
import wave
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


def parse_script_file(path: Path):
    """METADATA 헤더와 본문을 파싱."""
    text = path.read_text(encoding="utf-8")
    meta = {}
    body_lines = []
    in_body = False
    for line in text.splitlines():
        if line.strip() == "# ---SCRIPT_BELOW---":
            in_body = True
            continue
        if in_body:
            body_lines.append(line)
        elif line.startswith("# ") and ":" in line:
            key, _, val = line[2:].partition(":")
            meta[key.strip()] = val.strip()
    body = "\n".join(body_lines).strip()
    return meta, body


def build_tts_input(meta: dict, body: str) -> str:
    si = meta.get("style_instruction") or ""
    if si and si.lower() not in {"none", "null", ""}:
        return f"{si}\n\n{body}"
    return body


def wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
    with wave.open(str(filename), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)


def generate_one(client, text: str, voice_name: str, out_path: Path, max_retries=3):
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
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
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
            return True, duration, out_path.stat().st_size, None, elapsed_ms
        except Exception as e:
            last_err = str(e)
            print(f"  attempt {attempt}/{max_retries} failed: {last_err[:120]}")
            if attempt < max_retries:
                time.sleep(60)
    return False, 0.0, 0, last_err, 0


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

    by_no_idx = {s["no"]: i for i, s in enumerate(index["scenarios"])}
    by_no_log = {r["no"]: i for i, r in enumerate(log["results"])}

    for no in target_nos:
        if no not in by_no_idx:
            print(f"  [{no}] not in index, skip")
            continue
        sc = index["scenarios"][by_no_idx[no]]
        script_path = Path(sc["script_path"])
        meta, body = parse_script_file(script_path)
        new_tts = build_tts_input(meta, body)
        sc["tts_input"] = new_tts
        sc["voice"] = meta.get("voice", sc["voice"])
        sc["emotion"] = meta.get("emotion", sc["emotion"])
        sc["style_instruction"] = meta.get("style_instruction") or None
        sc["description"] = meta.get("description", sc["description"])

        out_path = AUDIO_DIR / f"{sc['filename_base']}.wav"
        print(f"[{no}] {sc['filename_base']} -> {sc['voice']}")
        ok, dur, size, err, ms = generate_one(client, new_tts, sc["voice"], out_path)
        result = {
            "no": no,
            "filename": sc["filename_base"],
            "status": "success" if ok else "failed",
            "duration_sec": round(dur, 2),
            "file_size_bytes": size,
            "error": err,
            "elapsed_api_ms": ms,
        }
        if ok:
            print(f"  ok: {dur:.1f}s, {size//1024}KB, {ms}ms")
        else:
            print(f"  FAIL: {err}")
        if no in by_no_log:
            log["results"][by_no_log[no]] = result
        else:
            log["results"].append(result)
        time.sleep(2)

    with INDEX_PATH.open("w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    log["completed_at"] = datetime.utcnow().isoformat() + "Z"
    log["summary"] = {
        "total": len(log["results"]),
        "success": sum(1 for r in log["results"] if r["status"] == "success"),
        "failed": sum(1 for r in log["results"] if r["status"] != "success"),
    }
    with LOG_PATH.open("w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    print(f"\nSummary: {log['summary']}")


if __name__ == "__main__":
    nos = [int(x) for x in sys.argv[1:]] if len(sys.argv) > 1 else [12, 14, 21, 22, 23, 24, 25]
    main(nos)
