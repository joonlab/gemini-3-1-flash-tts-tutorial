"""Gemini 3.1 Flash TTS - Script/_index.json 일괄 합성 메인.

흐름:
1) Script/_index.json 읽기
2) 시나리오마다 tts_input → Audio/{filename_base}.wav
3) 결과를 Audio/_generation_log.json 에 기록
"""
import json
import time
from datetime import datetime
from pathlib import Path

from utils import MODEL_ID, generate_tts, get_client


SCRIPT_INDEX = Path(__file__).resolve().parent.parent / "Script" / "_index.json"
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "Script"
AUDIO_DIR = Path(__file__).resolve().parent.parent / "Audio"
LOG_PATH = AUDIO_DIR / "_generation_log.json"


def _read_text_for_scenario(scenario: dict) -> str:
    """시나리오의 합성 입력 텍스트를 결정.

    우선순위:
      1. scenario['tts_input'] (인라인 문자열)
      2. scenario['script_file'] (Script/ 내 파일명) → 파일 내용
      3. scenario['filename_base'] + '.txt' (Script/ 내) → 파일 내용
    """
    if scenario.get("tts_input"):
        return scenario["tts_input"]

    candidates = []
    if scenario.get("script_file"):
        candidates.append(SCRIPT_DIR / scenario["script_file"])
    if scenario.get("filename_base"):
        candidates.append(SCRIPT_DIR / f"{scenario['filename_base']}.txt")

    for c in candidates:
        if c.exists():
            return c.read_text(encoding="utf-8").strip()

    raise RuntimeError(
        f"시나리오 #{scenario.get('no')} 에서 입력 텍스트를 찾을 수 없습니다: {scenario}"
    )


def main():
    if not SCRIPT_INDEX.exists():
        raise SystemExit(f"_index.json 이 존재하지 않습니다: {SCRIPT_INDEX}")

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    index = json.loads(SCRIPT_INDEX.read_text(encoding="utf-8"))
    scenarios = index.get("scenarios") or index.get("items") or index
    if not isinstance(scenarios, list):
        raise SystemExit("_index.json 구조가 예상과 다릅니다 (scenarios 배열 필요)")

    client = get_client()
    started_at = datetime.now().isoformat()
    results = []
    success = 0
    failed = 0
    total = len(scenarios)

    for i, sc in enumerate(scenarios, 1):
        no = sc.get("no", i)
        filename_base = sc.get("filename_base") or f"{no:02d}_unnamed"
        voice = sc.get("voice") or sc.get("voice_name") or "Kore"
        out_path = AUDIO_DIR / f"{filename_base}.wav"

        try:
            text = _read_text_for_scenario(sc)
        except Exception as e:  # noqa: BLE001
            print(f"[{i}/{total}] {filename_base} - 입력 텍스트 로드 실패: {e}")
            results.append({
                "no": no,
                "filename": filename_base,
                "status": "failed",
                "duration_sec": 0,
                "file_size_bytes": 0,
                "error": f"input_load: {e}",
                "elapsed_api_ms": 0,
            })
            failed += 1
            continue

        print(f"[{i}/{total}] {filename_base} - generating (voice={voice})...", flush=True)
        ok, dur, size, err, ms = generate_tts(client, text, voice, out_path)

        if ok:
            print(f"    OK ({dur:.1f}s, {size/1024:.1f}KB, api {ms}ms)")
            success += 1
            results.append({
                "no": no,
                "filename": filename_base,
                "status": "success",
                "duration_sec": round(dur, 2),
                "file_size_bytes": size,
                "error": None,
                "elapsed_api_ms": ms,
            })
        else:
            print(f"    FAIL: {err}")
            failed += 1
            results.append({
                "no": no,
                "filename": filename_base,
                "status": "failed",
                "duration_sec": 0,
                "file_size_bytes": 0,
                "error": err,
                "elapsed_api_ms": ms,
            })

        if i < total:
            time.sleep(2.0)

    completed_at = datetime.now().isoformat()
    log = {
        "model_id": MODEL_ID,
        "started_at": started_at,
        "completed_at": completed_at,
        "results": results,
        "summary": {"total": total, "success": success, "failed": failed},
    }
    LOG_PATH.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== Generation Complete ===")
    print(f"Total: {total}, Success: {success}, Failed: {failed}")
    print(f"Log: {LOG_PATH}")


if __name__ == "__main__":
    main()
