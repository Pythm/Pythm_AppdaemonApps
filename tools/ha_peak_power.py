#!/usr/bin/env python3
"""Find the rated power of a device from its own power sensor in Home Assistant's history (read-only).

Used to fill `power:` (watts) in ElectricalManagement without asking the user, when the device has a power
sensor (a W sensor on the smart plug, floor thermostat or boiler relay).

Usage:
  python3 tools/ha_peak_power.py sensor.heater_power sensor.boiler_power [--days 30]

For every sensor it prints the highest value, the 99th percentile and the median of the values above half of
the highest ("plateau", what the device draws when it is on), and how many samples that is. A suggested
`power:` is the highest value rounded to the nearest 10 W. Use it only when the plateau is clearly visible
(several samples, max close to the plateau). If the sensor has no history, or the device never ran in the
period, say so and ask the user for the watts.

Only reads. Uses .local/ha_token and .local/ha_url (see ha_snapshot.py); the token is never printed.
Home Assistant only keeps history for its recorder period (often 10 days), and sensors excluded from the
recorder have none. Python 3.8+, standard library only.
"""
import argparse
import datetime as dt
import json
import os
import statistics
import subprocess
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL = os.path.join(ROOT, ".local")


def read(name):
    path = os.path.join(LOCAL, name)
    if not os.path.isfile(path):
        sys.exit(f"{path} is missing. Run tools/ha_snapshot.py --init and follow LLM_GUIDE.md first.")
    with open(path, encoding="utf-8") as f:
        return f.read().strip()


def main():
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("entities", nargs="+", help="power sensor entity ids (state in W)")
    ap.add_argument("--days", type=int, default=30, help="how far back to look (default 30)")
    args = ap.parse_args()
    r = subprocess.run(["git", "-C", ROOT, "check-ignore", "-q", os.path.join(LOCAL, "ha_token")])
    if r.returncode == 1:
        sys.exit("git does not ignore .local/ha_token. Fix .gitignore first (see ha_snapshot.py).")
    url, token = read("ha_url").rstrip("/"), read("ha_token")
    now = dt.datetime.now(dt.timezone.utc)
    start = (now - dt.timedelta(days=args.days)).isoformat()
    query = urllib.parse.urlencode({"filter_entity_id": ",".join(args.entities), "end_time": now.isoformat()})
    req = urllib.request.Request(f"{url}/api/history/period/{urllib.parse.quote(start)}?{query}",
                                 headers={"Authorization": "Bearer " + token})
    data = json.load(urllib.request.urlopen(req, timeout=180))
    found = set()
    for series in data:
        if not series:
            continue
        entity = series[0]["entity_id"]
        found.add(entity)
        values = []
        for s in series:
            try:
                values.append(float(s["state"]))
            except (TypeError, ValueError):
                pass
        if not values:
            print(f"{entity}: no numeric values")
            continue
        values.sort()
        top = values[-1]
        on = [v for v in values if v > 0.5 * top]
        first = series[0].get("last_changed", "")[:10]
        print(f"{entity}: samples {len(values)} from {first}, max {top:.0f} W, p99 {values[max(int(len(values) * 0.99) - 1, 0)]:.0f} W, "
              f"plateau (median of values above half of max) {statistics.median(on) if on else 0:.0f} W from {len(on)} samples, "
              f"suggested power: {round(top / 10) * 10}")
    for entity in args.entities:
        if entity not in found:
            print(f"{entity}: no history (excluded from the recorder, wrong id, or never changed). Ask the user.")


if __name__ == "__main__":
    main()
