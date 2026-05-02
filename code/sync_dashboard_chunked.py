"""topik_long_chunked 시나리오 (52~58)의 audio/script를 dashboard/로 동기화."""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT_DIR = ROOT / "Script"
AUDIO_DIR = ROOT / "Audio"
DASHBOARD = ROOT / "dashboard"
DASH_AUDIO = DASHBOARD / "audio"
DASH_SCRIPT = DASHBOARD / "script"

TARGETS = list(range(52, 59))


def main():
    DASH_AUDIO.mkdir(parents=True, exist_ok=True)
    DASH_SCRIPT.mkdir(parents=True, exist_ok=True)

    copied_audio = 0
    copied_script = 0
    for src_audio in AUDIO_DIR.glob("*.wav"):
        try:
            no = int(src_audio.name.split("_", 1)[0])
        except ValueError:
            continue
        if no in TARGETS:
            dst = DASH_AUDIO / src_audio.name
            shutil.copy2(src_audio, dst)
            copied_audio += 1
            print(f"audio: {src_audio.name}")

    for src_script in SCRIPT_DIR.glob("*.txt"):
        try:
            no = int(src_script.name.split("_", 1)[0])
        except ValueError:
            continue
        if no in TARGETS:
            dst = DASH_SCRIPT / src_script.name
            shutil.copy2(src_script, dst)
            copied_script += 1
            print(f"script: {src_script.name}")

    print(f"\nsynced audio={copied_audio} script={copied_script}")


if __name__ == "__main__":
    main()
