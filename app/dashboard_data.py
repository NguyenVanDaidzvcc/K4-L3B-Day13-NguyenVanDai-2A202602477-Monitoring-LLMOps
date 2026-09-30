from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def read_log_file(path: Path) -> tuple[pd.DataFrame, int]:
    records: list[dict] = []
    skipped = 0

    if not path.exists():
        return pd.DataFrame(columns=["event", "ts"]), skipped

    with path.open("r", encoding="utf-8") as log_file:
        for line in log_file:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue
            if not isinstance(record, dict):
                skipped += 1
                continue
            records.append(record)

    frame = pd.DataFrame.from_records(records)
    if frame.empty:
        return pd.DataFrame(columns=["event", "ts"]), skipped

    if "ts" not in frame:
        frame["ts"] = pd.NaT
    frame["ts"] = pd.to_datetime(frame["ts"], utc=True, errors="coerce")
    invalid_timestamps = int(frame["ts"].isna().sum())
    skipped += invalid_timestamps
    frame = frame.dropna(subset=["ts"]).sort_values("ts").reset_index(drop=True)
    return frame, skipped


def select_window(frame: pd.DataFrame, minutes: int) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    latest = frame["ts"].max()
    start = latest - pd.Timedelta(minutes=minutes)
    return frame.loc[frame["ts"] >= start].copy()