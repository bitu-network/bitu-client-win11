# file: src/cli/download/offpeak.py

from pathlib import Path
from datetime import datetime, timedelta
import json
import sys
import time

from lib.net.vid_download import download_url_files


CONFIG_FILE = Path(__file__).with_name("offpeak.json")


def parse_time(s: str):
    return datetime.strptime(s, "%H:%M").time()


def load_config():
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_config(start, end):
    CONFIG_FILE.write_text(
        json.dumps(
            {"start_time": start, "end_time": end},
            indent=4
        ),
        encoding="utf-8"
    )


def resolve_schedule():
    args = sys.argv[1:]

    cfg = load_config()

    if len(args) >= 2:
        start, end = args[0], args[1]
        save_config(start, end)
        return start, end

    if cfg.get("start_time") and cfg.get("end_time"):
        return cfg["start_time"], cfg["end_time"]

    start = input("Start time (HH:MM): ").strip()
    end = input("End time (HH:MM): ").strip()

    save_config(start, end)
    return start, end


def next_time(t):
    now = datetime.now()
    target = now.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)

    if target <= now:
        target += timedelta(days=1)

    return target


def sleep_until(dt):
    seconds = (dt - datetime.now()).total_seconds()
    if seconds > 0:
        print(f"Sleeping until {dt:%Y-%m-%d %H:%M:%S}")
        time.sleep(seconds)


def download_all(cwd: Path):
    # files = list(cwd.glob("*.url"))
    files = list(cwd.rglob("*.url"))

    if not files:
        print("No .url files found.")
        return

    print(f"Downloading {len(files)} file(s)...")
    download_url_files(files, outdir=cwd)
    print("Done.")


def main():
    start_s, end_s = resolve_schedule()

    start_t = parse_time(start_s)
    end_t = parse_time(end_s)

    cwd = Path.cwd()

    print(f"CWD: {cwd}")
    print(f"Off-peak: {start_s} → {end_s}")

    while True:
        start_dt = next_time(start_t)
        sleep_until(start_dt)

        print(f"Off-peak started: {datetime.now():%H:%M:%S}")
        download_all(cwd)

        end_dt = start_dt.replace(hour=end_t.hour, minute=end_t.minute)

        if end_dt <= start_dt:
            end_dt += timedelta(days=1)

        sleep_until(end_dt)

        print(f"Off-peak ended: {datetime.now():%H:%M:%S}")


if __name__ == "__main__":
    main()