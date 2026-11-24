#!/usr/bin/env python3
"""Heat Wave BD — data script.

Fetches the ECMWF IFS 0.25 forecast for all 64 district towns from
Open-Meteo in ONE call, applies the BMD heat wave rule to each day, and
writes one JSON file for the app to read.

BMD rule (by daily maximum temperature):
  level 0  তাপপ্রবাহ নেই          tmax < 36.0
  level 1  মৃদু তাপপ্রবাহ          36.0 - 37.9
  level 2  মাঝারি তাপপ্রবাহ        38.0 - 39.9
  level 3  তীব্র তাপপ্রবাহ         40.0 - 41.9
  level 4  অতি তীব্র তাপপ্রবাহ     tmax >= 42.0

Run:  python3 fetch_forecast.py [output_path]
Default output: ./forecast.json beside this script.
Uses the https_proxy environment variable when one is set (test VM);
on a normal server it connects directly. No API key is needed.
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = "ecmwf_ifs025"
DAYS = 15
FETCH_DAYS = 16  # ask for one extra day, then trim incomplete tail days
TZ = ZoneInfo("Asia/Dhaka")


def level_for(tmax):
    if tmax is None:
        return None
    if tmax < 36.0:
        return 0
    if tmax < 38.0:
        return 1
    if tmax < 40.0:
        return 2
    if tmax < 42.0:
        return 3
    return 4


def opener():
    proxy = os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY")
    if proxy:
        return urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    return urllib.request.build_opener()


def fetch(districts):
    lats = ",".join(str(d["lat"]) for d in districts)
    lons = ",".join(str(d["lon"]) for d in districts)
    q = urllib.parse.urlencode({
        "latitude": lats,
        "longitude": lons,
        "daily": "temperature_2m_max,apparent_temperature_max,"
                 "relative_humidity_2m_mean",
        "models": MODEL,
        "forecast_days": FETCH_DAYS,
        "timezone": "Asia/Dhaka",
    })
    url = f"https://api.open-meteo.com/v1/forecast?{q}"
    with opener().open(url, timeout=120) as r:
        data = json.load(r)
    if isinstance(data, dict):  # single-location shape, safety net
        data = [data]
    return data


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        HERE, "forecast.json")
    districts = json.load(open(os.path.join(HERE, "districts.json"),
                               encoding="utf-8"))["districts"]
    raw = fetch(districts)
    assert len(raw) == len(districts), (len(raw), len(districts))

    # ECMWF daily values need a full calendar day of model steps. The last
    # 1-2 days of a run can be incomplete (null) and the boundary moves
    # with the 6-hour run cycle. Trim trailing days that are null for any
    # district, and cap at DAYS. The JSON carries the true day count.
    total_days = len(raw[0]["daily"]["time"])
    complete = total_days
    while complete > 0 and any(
            loc["daily"]["temperature_2m_max"][complete - 1] is None
            for loc in raw):
        complete -= 1
    complete = min(complete, DAYS)
    assert complete >= 10, f"only {complete} complete days"
    print(f"Fetched {total_days} days, complete days kept: {complete}")
    for loc in raw:
        for key in loc["daily"]:
            loc["daily"][key] = loc["daily"][key][:complete]

    out_districts = []
    for d, loc in zip(districts, raw):
        daily = loc["daily"]
        days = []
        for i, date in enumerate(daily["time"]):
            tmax = daily["temperature_2m_max"][i]
            days.append({
                "date": date,
                "tmax": tmax,
                "feels": daily["apparent_temperature_max"][i],
                "humidity": daily["relative_humidity_2m_mean"][i],
                "level": level_for(tmax),
            })
        out_districts.append({
            "id": d["id"],
            "name_en": d["name_en"],
            "name_bn": d["name_bn"],
            "division_en": d["division_en"],
            "division_bn": d["division_bn"],
            "lat": d["lat"],
            "lon": d["lon"],
            "days": days,
        })

    out = {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "timezone": "Asia/Dhaka",
        "source": "Open-Meteo",
        "model": MODEL,
        "forecast_days": complete,
        "districts": out_districts,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"OK: wrote {out_path}")
    print(f"Districts: {len(out_districts)}, days each: "
          f"{len(out_districts[0]['days'])}, generated_at: "
          f"{out['generated_at']}")


if __name__ == "__main__":
    main()
