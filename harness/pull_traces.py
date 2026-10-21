"""Pull real customer traces from Confident AI and save them for error analysis."""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

API = "https://api.confident-ai.com/v1/traces"
HEADERS = {"CONFIDENT_API_KEY": os.environ["CONFIDENT_API_KEY"]}


def customer_traces(since):
    cursor = None
    while True:
        params = {"cursor": cursor} if cursor else {}
        page = requests.get(API, headers=HEADERS, params=params, timeout=30)
        page = page.json()["data"]
        for t in page["traces"]:
            if t["startTime"] < since:
                return  # traces come newest first
            if t["name"] == "support-bot" and "customer" in (t["tags"] or []):
                trace = requests.get(f"{API}/{t['uuid']}", headers=HEADERS, timeout=30)
                yield trace.json()["data"]
        cursor = page["nextCursor"]
        if not cursor:
            return


def search_results(trace):
    for s in trace["spans"]:
        if s["name"] == "retrieve-docs":
            return s["retrievalContext"]
    return []


if __name__ == "__main__":
    hours = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    rows = [
        {
            "trace": t["uuid"],
            "input": t["input"],
            "output": t["output"],
            "search_results": search_results(t),
            "topic": (t.get("labels") or {}).get("Topics", {}).get("label"),
        }
        for t in customer_traces(since.strftime("%Y-%m-%dT%H:%M:%S.000Z"))
    ]
    json.dump(rows, open("traces.json", "w"), indent=2)
    print(f"Saved {len(rows)} customer traces to traces.json")
