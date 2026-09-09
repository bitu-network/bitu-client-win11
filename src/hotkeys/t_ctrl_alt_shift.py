# file: src/hotkeys/t_ctrl_alt_shift.py
# Tags selected video files or video shortcuts with their duration by prepending a formatted duration label to the filename. 


import sys
from apps.explorer import get_active_explorer_info
from lib.video_utils import is_video, duration_seconds, format_duration
from lib.fs.filename_utils import prepend_tag
from lib.fs.lnk_utils import resolve_lnk_target

TAG_SEPARATOR = "."

# ---------------- helpers ----------------


def log(msg: str):
    print(msg, file=sys.stderr, flush=True)


# ---------------- main ----------------

folder, selected = get_active_explorer_info()
if not folder or not selected:
    raise SystemExit

for item in selected:
    p = item
    if not p.exists():
        log(f"Item does not exist: {p}")
        continue

    log(f"Processing: {p}")

    # direct video
    if is_video(p):
        dur = duration_seconds(p)
        if dur:
            prepend_tag(p, format_duration(dur))
        continue

    # .lnk to video
    if p.suffix.lower() == ".lnk":
        target = resolve_lnk_target(p)

        if target and is_video(target):
            dur = duration_seconds(target)
            if dur:
                prepend_tag(p, format_duration(dur))
        else:
            # fallback: only tag if the .lnk itself is intended as a video
            if is_video(p):
                prepend_tag(p, "[video]")
        continue

    log(f"Skipped (not a video or .lnk): {p}")
