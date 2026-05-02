"""topik_long_chunked: 28~34의 본문을 5섹션으로 분할 → 각 청크 TTS → 300ms 무음 병합.

매핑:
  28 → 52 (en/Charon)
  29 → 53 (ja/Leda)
  30 → 54 (zh/Kore)
  31 → 55 (vi/Puck)
  32 → 56 (ru/Zephyr)
  33 → 57 (uz/Charon, 실험적)
  34 → 58 (km/Leda, 실험적)
"""
import json
import os
import re
import sys
import time
import wave
from datetime import datetime
from pathlib import Path

from utils import (
    get_client,
    generate_tts,
    get_wav_duration_sec,
    get_file_size,
    merge_wavs_with_silence,
)

ROOT = Path(__file__).resolve().parent.parent
SCRIPT_DIR = ROOT / "Script"
AUDIO_DIR = ROOT / "Audio"
DASHBOARD_DIR = ROOT / "dashboard"
INDEX_PATH = SCRIPT_DIR / "_index.json"
LOG_PATH = AUDIO_DIR / "_generation_log.json"
TMP_CHUNK_DIR = ROOT / "code" / "tmp_chunks"
DASHBOARD_CHUNK_DIR = DASHBOARD_DIR / "audio" / "chunks"

# source no → new no, target lang label, voice
MAPPING = [
    (28, 52, "English", "Charon", "en", False),
    (29, 53, "Japanese", "Leda", "ja", False),
    (30, 54, "Mandarin", "Kore", "zh", False),
    (31, 55, "Vietnamese", "Puck", "vi", False),
    (32, 56, "Russian", "Zephyr", "ru", False),
    (33, 57, "Uzbek", "Charon", "uz", True),
    (34, 58, "Khmer", "Leda", "km", True),
]

CHUNK_LABELS = ["a", "b", "c", "d", "e"]


def split_5_sections(tts_input: str):
    """헤더 + 6단락 본문을 (header, [5 chunks])로 반환.

    본문 6단락(도입/인사/자기소개/문법/실용/마무리)을 5섹션으로 합칠 때
    마지막 두 단락(실용 + 마무리)을 묶어 1개 섹션으로 처리.
    """
    paragraphs = [p.strip() for p in tts_input.split("\n\n") if p.strip()]
    if len(paragraphs) < 6:
        raise RuntimeError(f"expected at least 6 paragraphs (1 header + 5+ body), got {len(paragraphs)}")

    header = paragraphs[0]
    body = paragraphs[1:]

    # 본문이 정확히 6단락이면 마지막 둘을 묶어 5섹션
    if len(body) == 6:
        sections = [body[0], body[1], body[2], body[3], body[4] + "\n\n" + body[5]]
    elif len(body) == 5:
        sections = body[:]
    else:
        # 길이 기반 자동 분할: 5등분
        text = "\n\n".join(body)
        # split into sentences by punctuation
        boundaries = []
        for m in re.finditer(r"[.。។!?][\s\n]", text):
            boundaries.append(m.end())
        if len(boundaries) < 4:
            raise RuntimeError(f"not enough sentence boundaries (got {len(boundaries)})")
        target_pos = [int(len(text) * x / 5) for x in (1, 2, 3, 4)]
        cuts = []
        for tp in target_pos:
            best = min(boundaries, key=lambda b: abs(b - tp))
            cuts.append(best)
        cuts = sorted(set(cuts))
        sections = []
        prev = 0
        for c in cuts:
            sections.append(text[prev:c].strip())
            prev = c
        sections.append(text[prev:].strip())
        if len(sections) != 5:
            raise RuntimeError(f"split_5_sections produced {len(sections)} sections")

    return header, sections


def build_chunk_prompt(header: str, chunk_body: str) -> str:
    """헤더(byte-단위 동일) + 빈 줄 + 청크 본문."""
    return f"{header}\n\n{chunk_body}"


def main():
    client = get_client()

    with INDEX_PATH.open(encoding="utf-8") as f:
        index = json.load(f)
    with LOG_PATH.open(encoding="utf-8") as f:
        log = json.load(f)

    by_no = {s["no"]: s for s in index["scenarios"]}

    TMP_CHUNK_DIR.mkdir(parents=True, exist_ok=True)
    DASHBOARD_CHUNK_DIR.mkdir(parents=True, exist_ok=True)

    new_scenarios = []
    new_logs = []
    error_count = 0
    retry_count = 0

    for src_no, new_no, lang_label, voice, lang_code, experimental in MAPPING:
        src = by_no.get(src_no)
        if src is None:
            print(f"[{new_no}] source {src_no} not found, skip", flush=True)
            continue

        header, sections = split_5_sections(src["tts_input"])
        print(f"\n[{new_no}] split: 5 sections, lengths={[len(s) for s in sections]}", flush=True)

        chunk_filename_base = f"{new_no}_topik_chunked_ko-{lang_code}_{voice.lower()}"
        chunk_paths = []
        chunk_records = []

        total_api_ms = 0
        all_ok = True
        for idx_chunk, body in enumerate(sections):
            label = CHUNK_LABELS[idx_chunk]
            tmp_path = TMP_CHUNK_DIR / f"{new_no}{label}.wav"
            prompt = build_chunk_prompt(header, body)
            print(f"  [{new_no}{label}] voice={voice} body_len={len(body)} … ", end="", flush=True)
            t0 = time.time()
            ok, dur, size, err, api_ms = generate_tts(
                client, prompt, voice, tmp_path, max_retries=3, sleep_between=2.0
            )
            wall_ms = int((time.time() - t0) * 1000)
            total_api_ms += api_ms
            if not ok:
                error_count += 1
                all_ok = False
                print(f"FAIL: {err[:120] if err else 'unknown'}", flush=True)
                chunk_records.append({
                    "label": label,
                    "status": "failed",
                    "error": err,
                    "elapsed_api_ms": api_ms,
                })
                break
            # wall_ms - api_ms 차이가 크면 재시도가 발생했음을 의미 (대략 60s sleep)
            if wall_ms - api_ms > 30_000:
                retry_count += 1
            chunk_paths.append(tmp_path)
            chunk_records.append({
                "label": label,
                "status": "success",
                "duration_sec": round(dur, 2),
                "file_size_bytes": size,
                "elapsed_api_ms": api_ms,
            })
            print(f"OK dur={dur:.1f}s {size//1024}KB ms={api_ms}", flush=True)
            # 청크 사이에 short sleep으로 rate limit 회피
            time.sleep(2)

        if not all_ok:
            new_scenarios.append({
                "no": new_no,
                "filename_base": chunk_filename_base,
                "category": "topik_long_chunked",
                "language": "mixed",
                "voice": voice,
                "emotion": src.get("emotion", "calm"),
                "style_instruction": src.get("style_instruction", ""),
                "description": f"TOPIK 종합 레슨 (Chunk 병합) - {lang_label} speaker용 - 5섹션 청크 분할 후 병합 (생성 실패)",
                "script_path": str(SCRIPT_DIR / f"{chunk_filename_base}.txt"),
                "tts_input": src["tts_input"],
                "sub_strategy": "chunked_5sections_300ms_silence",
                "source_scenario_no": src_no,
                "experimental": experimental,
                "chunk_records": chunk_records,
                "status": "failed",
            })
            new_logs.append({
                "no": new_no,
                "filename": chunk_filename_base,
                "status": "failed",
                "duration_sec": 0.0,
                "file_size_bytes": 0,
                "error": chunk_records[-1].get("error") if chunk_records else "unknown",
                "elapsed_api_ms": total_api_ms,
                "chunk_records": chunk_records,
            })
            continue

        # 5청크 → merge with 300ms silence
        merged_path = AUDIO_DIR / f"{chunk_filename_base}.wav"
        merged_dur = merge_wavs_with_silence(chunk_paths, merged_path, silence_ms=300)
        merged_size = get_file_size(merged_path)
        print(f"  [{new_no}] merged dur={merged_dur:.1f}s size={merged_size//1024}KB", flush=True)

        # 청크 .wav를 dashboard/audio/chunks/ 에 복사
        dashboard_chunk_paths = []
        for idx_chunk, src_chunk in enumerate(chunk_paths):
            label = CHUNK_LABELS[idx_chunk]
            dst = DASHBOARD_CHUNK_DIR / f"{new_no}{label}.wav"
            dst.write_bytes(src_chunk.read_bytes())
            dashboard_chunk_paths.append(f"audio/chunks/{new_no}{label}.wav")

        # 신규 script 파일 생성 (description만 갱신, 본문은 동일)
        script_text = src["tts_input"]
        # 헤더 메타 작성
        script_path = SCRIPT_DIR / f"{chunk_filename_base}.txt"
        script_meta = (
            f"# METADATA\n"
            f"# category: topik_long_chunked\n"
            f"# language: mixed\n"
            f"# voice: {voice}\n"
            f"# emotion: {src.get('emotion', 'calm')}\n"
            f"# style_instruction: {src.get('style_instruction', '')}\n"
            f"# description: TOPIK 종합 레슨 (Chunk 병합) - {lang_label} speaker용 - 5섹션 청크 분할 후 병합\n"
            f"# sub_strategy: chunked_5sections_300ms_silence\n"
            f"# source_scenario_no: {src_no}\n"
            f"# ---SCRIPT_BELOW---\n"
            f"{script_text}\n"
        )
        script_path.write_text(script_meta, encoding="utf-8")

        new_scenarios.append({
            "no": new_no,
            "filename_base": chunk_filename_base,
            "category": "topik_long_chunked",
            "language": "mixed",
            "voice": voice,
            "emotion": src.get("emotion", "calm"),
            "style_instruction": src.get("style_instruction", ""),
            "description": f"TOPIK 종합 레슨 (Chunk 병합) - {lang_label} speaker용 - 5섹션 청크 분할 후 병합",
            "script_path": str(script_path),
            "tts_input": src["tts_input"],
            "sub_strategy": "chunked_5sections_300ms_silence",
            "source_scenario_no": src_no,
            "experimental": experimental,
            "chunk_paths": dashboard_chunk_paths,
            "chunk_records": chunk_records,
            "audio_relative_path": f"audio/{chunk_filename_base}.wav",
            "audio_size_kb": merged_size // 1024,
            "duration_sec": round(merged_dur, 2),
            "elapsed_api_ms": total_api_ms,
        })
        new_logs.append({
            "no": new_no,
            "filename": chunk_filename_base,
            "status": "success",
            "duration_sec": round(merged_dur, 2),
            "file_size_bytes": merged_size,
            "error": None,
            "elapsed_api_ms": total_api_ms,
            "chunk_records": chunk_records,
        })

    # _index.json 갱신
    # categories는 단순 정수 카운트
    if "topik_long_chunked" not in index["categories"]:
        index["categories"]["topik_long_chunked"] = 0

    existing_nos = {s["no"] for s in index["scenarios"]}
    for sc in new_scenarios:
        if sc["no"] not in existing_nos:
            index["scenarios"].append(sc)
            if sc.get("status") != "failed":
                index["categories"]["topik_long_chunked"] += 1
        else:
            # replace
            for i, s in enumerate(index["scenarios"]):
                if s["no"] == sc["no"]:
                    index["scenarios"][i] = sc
                    break

    # total_scenarios 재계산
    index["total_scenarios"] = len(index["scenarios"])

    with INDEX_PATH.open("w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    # generation log 갱신
    by_no_log = {r["no"]: i for i, r in enumerate(log["results"])}
    for r in new_logs:
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

    print(f"\n=== Summary ===")
    print(f"new scenarios: {len(new_scenarios)}")
    print(f"errors: {error_count}, retries (60s sleep observed): {retry_count}")
    print(f"total_scenarios in index: {index['total_scenarios']}")
    print(f"topik_long_chunked count: {index['categories']['topik_long_chunked']}")


if __name__ == "__main__":
    main()
