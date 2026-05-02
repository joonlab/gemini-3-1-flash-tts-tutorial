"""consistency_test 카테고리 16개 audio 생성 + Strategy 4 chunk merge.

사용:
    python generate_consistency.py
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))

from utils import (  # noqa: E402
    get_client,
    generate_tts,
    generate_tts_multispeaker,
    merge_wavs,
    get_wav_duration_sec,
    get_file_size,
)

SCRIPT_DIR = ROOT / "Script"
AUDIO_DIR = ROOT / "Audio"
INDEX_PATH = SCRIPT_DIR / "_index.json"
LOG_PATH = AUDIO_DIR / "_generation_log.json"


def main():
    client = get_client()
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    log = json.loads(LOG_PATH.read_text(encoding="utf-8"))
    by_no_log = {r["no"]: i for i, r in enumerate(log["results"])}

    targets = [s for s in index["scenarios"] if s.get("category") == "consistency_test"]
    targets.sort(key=lambda s: s["no"])
    print(f"Targets: {len(targets)} consistency scenarios")

    for sc in targets:
        no = sc["no"]
        base = sc["filename_base"]
        sub = sc.get("sub_strategy")
        voice = sc["voice"]
        text = sc["tts_input"]
        out_path = AUDIO_DIR / f"{base}.wav"
        print(f"\n[{no}] {base}  sub={sub}  voice={voice}")

        if sub == "s3_multi":
            # multi-speaker mode requires exactly 2 enabled voices.
            # Define a dummy 2nd speaker (Student=Charon) but only Teacher appears in transcript,
            # to test whether single-speaker consistency holds under multi-speaker config.
            ok, dur, size, err, ms = generate_tts_multispeaker(
                client, text, [("Teacher", voice), ("Student", "Charon")], out_path
            )
        else:
            ok, dur, size, err, ms = generate_tts(client, text, voice, out_path)

        result = {
            "no": no,
            "filename": base,
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
            by_no_log[no] = len(log["results"]) - 1

        time.sleep(2)

    # Strategy 4 chunk merge: 48 + 49 + 50 → 47_consistency_s4_long_merged.wav
    chunk_files = [AUDIO_DIR / f"{n}_consistency_s4_chunk{i}of3.wav" for n, i in [(48, 1), (49, 2), (50, 3)]]
    missing = [p for p in chunk_files if not p.exists()]
    merged_no = 51
    merged_base = "47_consistency_s4_long_merged"
    merged_path = AUDIO_DIR / f"{merged_base}.wav"
    if missing:
        print(f"\n[merge] skip merge - missing chunks: {missing}")
    else:
        print(f"\n[merge] merging 48+49+50 -> {merged_path.name}")
        try:
            dur = merge_wavs(chunk_files, merged_path)
            size = get_file_size(merged_path)
            merged_result = {
                "no": merged_no,
                "filename": merged_base,
                "status": "success",
                "duration_sec": round(dur, 2),
                "file_size_bytes": size,
                "error": None,
                "elapsed_api_ms": 0,
            }
            print(f"  merged ok: {dur:.1f}s, {size//1024}KB")
        except Exception as e:
            merged_result = {
                "no": merged_no,
                "filename": merged_base,
                "status": "failed",
                "duration_sec": 0.0,
                "file_size_bytes": 0,
                "error": str(e),
                "elapsed_api_ms": 0,
            }
            print(f"  merge FAIL: {e}")

        if merged_no in by_no_log:
            log["results"][by_no_log[merged_no]] = merged_result
        else:
            log["results"].append(merged_result)
            by_no_log[merged_no] = len(log["results"]) - 1

        # _index.json에 51번 항목 추가 (script_path: null)
        existing_nos = {s["no"] for s in index["scenarios"]}
        if merged_no not in existing_nos:
            index["scenarios"].append({
                "no": merged_no,
                "filename_base": merged_base,
                "category": "consistency_test",
                "language": "ko",
                "voice": "Kore",
                "emotion": "calm",
                "style_instruction": None,
                "sub_strategy": "s4_merged",
                "description": "Strategy 4 - 48+49+50 wav 병합 결과 (long single 47과 비교용)",
                "script_path": None,
                "tts_input": "[merged from 48+49+50, no separate transcript]",
            })
            index["categories"]["consistency_test"] = 17
            index["total_scenarios"] = len(index["scenarios"])

    # save
    INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    log["completed_at"] = datetime.utcnow().isoformat() + "Z"
    log["summary"] = {
        "total": len(log["results"]),
        "success": sum(1 for r in log["results"] if r["status"] == "success"),
        "failed": sum(1 for r in log["results"] if r["status"] != "success"),
    }
    LOG_PATH.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")

    consistency_results = [r for r in log["results"] if r["no"] >= 35]
    print(f"\n=== consistency_test summary ===")
    print(f"  total: {len(consistency_results)}")
    print(f"  success: {sum(1 for r in consistency_results if r['status']=='success')}")
    print(f"  failed: {sum(1 for r in consistency_results if r['status']=='failed')}")
    print(f"  log totals: {log['summary']}")


if __name__ == "__main__":
    main()
