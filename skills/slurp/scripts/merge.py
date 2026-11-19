#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Merge staged recordings of one conversation (a meeting split across files) into one.

Runs after transcribe.py, before diarize.py. Each part must already be staged by
transcribe.py (`/tmp/slurp/<id>/{audio.mp3,transcript.json}`). Writes
`/tmp/slurp/<id1>+<id2>[+...]/` holding:

  audio.mp3        the parts in time order, with silence filling the gap between them, so
                   every segment time below points at its real audio (diarize.py slices by it)
  transcript.json  one transcript: recorder_id `<id1>+<id2>`, recorded_at of the first part,
                   each part's segments shifted by its start offset from the first and tagged
                   with `part` (1-based), and a `parts` list [{recorder_id, sha256, offset_s,
                   duration_s}]

Gaps come from the recorder ids, which have minute precision, so a gap is good to about a
minute (the same precision every recorder note's wall clock already has). A gap that comes
out negative (the next part "starts" before the previous one ends) is clamped to zero.

The merged note's frontmatter carries `recorder_id: <id1>+<id2>`; transcribe.py splits it
on `+`, so every part is reported `transcribed` on later runs.

    merge.py /tmp/slurp/261119_1402 /tmp/slurp/261119_1439

stdout: the merged staging dir.
stderr: progress.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

STAGING = Path("/tmp/slurp")
SR = 16000  # diarize.py resamples to 16 kHz mono anyway; whisper isn't re-run on this audio


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("staging_dirs", type=Path, nargs="+", help="two or more transcribe.py staging dirs")
    ap.add_argument("--out", type=Path, help="merged staging dir (default: /tmp/slurp/<id1>+<id2>...)")
    args = ap.parse_args()
    if len(args.staging_dirs) < 2:
        ap.error("need at least two staging dirs")

    parts = []
    for d in args.staging_dirs:
        t = json.loads((d / "transcript.json").read_text())
        if not t.get("recorded_at_local") or not t.get("duration_s"):
            log(f"{d}: transcript.json has no recorded_at_local/duration_s; can't place it in time")
            return 1
        parts.append((datetime.fromisoformat(t["recorded_at_local"]), d, t))
    parts.sort(key=lambda p: p[0])

    first_at, _, first = parts[0]
    rid = "+".join(t["recorder_id"] for _, _, t in parts)
    out = args.out or STAGING / rid
    out.mkdir(parents=True, exist_ok=True)

    segments, meta, gaps = [], [], []
    end = 0.0  # end of the previous part, in merged seconds
    for i, (at, d, t) in enumerate(parts, 1):
        offset = max((at - first_at).total_seconds(), end)
        gaps.append(offset - end)
        for s in t["segments"]:
            segments.append({**s, "start": round(s["start"] + offset, 2), "end": round(s["end"] + offset, 2), "part": i})
        meta.append({"recorder_id": t["recorder_id"], "sha256": t.get("sha256"),
                     "offset_s": round(offset, 3), "duration_s": t["duration_s"]})
        log(f"{t['recorder_id']}: part {i} at +{offset:.0f}s ({t['duration_s']:.0f}s, gap before {gaps[-1]:.0f}s)")
        end = offset + t["duration_s"]

    # [a1][s2][a2][s3][a3]... ; s_i is gaps[i-1] seconds of silence before part i (none before part 1)
    cmd = ["ffmpeg", "-v", "error", "-y"]
    for _, d, _ in parts:
        cmd += ["-i", str(d / "audio.mp3")]
    chains, labels = [], []
    for i in range(len(parts)):
        if i:
            chains.append(f"anullsrc=r={SR}:cl=mono,atrim=duration={gaps[i]:.3f}[s{i}]")
            labels.append(f"[s{i}]")
        chains.append(f"[{i}:a]aresample={SR},aformat=channel_layouts=mono[a{i}]")
        labels.append(f"[a{i}]")
    chains.append(f"{''.join(labels)}concat=n={len(labels)}:v=0:a=1[out]")
    audio = out / "audio.mp3"
    cmd += ["-filter_complex", ";".join(chains), "-map", "[out]", "-c:a", "libmp3lame", "-q:a", "4", str(audio)]
    log(f"{rid}: joining audio...")
    subprocess.run(cmd, check=True)

    payload = {
        "recorder_id": rid,
        "recorded_at_local": first["recorded_at_local"],
        "recorded_at_utc": first["recorded_at_utc"],
        "duration_s": round(end, 3),
        "model": first["model"],
        "language": first.get("language"),
        "parts": meta,
        "segments": segments,
    }
    tj = out / "transcript.json"
    tmp = tj.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(tj)
    log(f"{rid}: {len(segments)} segments, {end:.0f}s")
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
