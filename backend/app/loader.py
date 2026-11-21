"""Single place that reads the dataset and does type cleaning."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


def data_dir() -> Path:
    env = os.environ.get("DATA_DIR")
    if env:
        return Path(env)
    # backend/app/loader.py -> repo root / data
    return Path(__file__).resolve().parents[2] / "data"


@dataclass
class Data:
    wo: pd.DataFrame
    complaints: pd.DataFrame
    wards: pd.DataFrame
    roads: pd.DataFrame
    rate_card: pd.DataFrame
    contractors: pd.DataFrame
    rain: pd.DataFrame
    accidents: pd.DataFrame
    traffic: pd.DataFrame
    hotspots: pd.DataFrame
    facilities: pd.DataFrame
    localities: pd.DataFrame
    dir: Path


def load() -> Data:
    d = data_dir()
    rd = lambda n: pd.read_csv(d / n)  # noqa: E731

    wo = rd("work_orders.csv")
    for c in ("assigned_at", "work_started_at", "completed_at"):
        wo[c] = pd.to_datetime(wo[c])
    wo["linked_complaint_ids"] = wo["linked_complaint_ids"].fillna("")
    wo["reopened"] = wo["reopened_within_30d"].eq("Y")

    complaints = rd("complaints.csv")
    complaints["received_at"] = pd.to_datetime(complaints["received_at"])

    rain = rd("rainfall_daily.csv")
    rain["date"] = pd.to_datetime(rain["date"])

    acc = rd("accidents.csv")
    acc["occurred_at"] = pd.to_datetime(acc["occurred_at"])

    return Data(
        wo=wo,
        complaints=complaints,
        wards=rd("wards.csv"),
        roads=rd("roads.csv"),
        rate_card=rd("rate_card.csv"),
        contractors=rd("contractors.csv"),
        rain=rain,
        accidents=acc,
        traffic=rd("traffic.csv"),
        hotspots=rd("flood_hotspots.csv"),
        facilities=rd("facilities.csv"),
        localities=rd("localities.csv"),
        dir=d,
    )
