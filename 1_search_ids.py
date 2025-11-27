#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube ID Searcher - Quota-Efficient Script (v2)

Performs a consolidated search to gather video IDs and saves them to a file.
Includes the ability to filter by a specific video category.
"""
\
import os
import time
import argparse
import requests
from datetime import datetime, timedelta, timezone

API_KEY = os.getenv("YOUTUBE_API_KEY")
BASE_URL = "https://www.googleapis.com/youtube/v3"

# Default keywords if no query is provided via command line
AI_KEYWORDS = [
    "ai generated", "ai video", "text-to-video", "sora", "runway gen-3",
    "pika labs", "gen-3", "midjourney video", "luma ai", "google veo",
    "synthesia", "heygen", "kaiber", "stable video diffusion", "d-id"
]

def to_iso8601_day_start(dstr):
    return f"{dstr}T00:00:00Z"

def _get(url, params, max_retries=5, backoff=1.6):
    params = dict(params or {}); params["key"] = API_KEY
    for attempt in range(max_retries):
        try:
            r = requests.get(url, params=params, timeout=30)
            if r.status_code == 200: return r.json()
            if r.status_code in (403, 429, 500, 503):
                print(f"Warning: Received status code {r.status_code}. Retrying in {int(backoff ** attempt) + 1}s...")
                time.sleep(int(backoff ** attempt) + 1)
                continue
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}. Retrying...")
            time.sleep(int(backoff ** attempt) + 1)
    raise RuntimeError(f"Failed after {max_retries} retries.")

def search_and_save_ids(args):
    url = f"{BASE_URL}/search"
    params = {
        "part": "id",
        "q": args.query,
        "type": "video",
        "maxResults": 50,
        "order": "relevance"
    }
    if args.start_date:
        params["publishedAfter"] = to_iso8601_day_start(args.start_date)
    else:
        start_dt = datetime.now(timezone.utc) - timedelta(days=args.days)
        params["publishedAfter"] = start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    if args.lang: params["relevanceLanguage"] = args.lang
    if args.region: params["regionCode"] = args.region
    if args.category_id: params["videoCategoryId"] = args.category_id

    found_ids = set()
    next_token = None
    
    pages = (args.max_results + 49) // 50
    estimated_cost = pages * 100
    print(f"[*] Estimated quota cost for search: {pages} pages * 100 units = {estimated_cost} units.")

    while len(found_ids) < args.max_results:
        if next_token:
            params["pageToken"] = next_token
        
        data = _get(url, params)
        
        for item in data.get("items", []):
            video_id = item.get("id", {}).get("videoId")
            if video_id:
                found_ids.add(video_id)
        
        print(f"  > Found {len(found_ids)} unique video IDs so far...")
        
        next_token = data.get("nextPageToken")
        if not next_token:
            print("[*] Reached the end of search results.")
            break
        time.sleep(0.1)

    with open(args.output_file, 'w') as f:
        for vid in list(found_ids)[:args.max_results]:
            f.write(f"{vid}\n")
    
    print(f"\n[*] Success! Saved {len(list(found_ids)[:args.max_results])} video IDs to {args.output_file}")

def main():
    ap = argparse.ArgumentParser()
    default_query = " | ".join([f'"{k}"' for k in AI_KEYWORDS])
    ap.add_argument("--query", type=str, default=default_query, help="Search query. Use '|' as OR.")
    ap.add_argument("--max_results", type=int, default=500, help="Total video IDs to find.")
    ap.add_argument("--days", type=int, default=90, help="Lookback period in days.")
    ap.add_argument("--start_date", type=str, default=None, help="YYYY-MM-DD (overrides --days).")
    ap.add_argument("--lang", type=str, default=None, help="e.g., en or id")
    ap.add_argument("--region", type=str, default=None, help="e.g., US, ID")
    ap.add_argument("--category_id", type=str, default=None, help="Filter search by YouTube video category ID.")
    ap.add_argument("--output_file", type=str, default="out/video_ids.txt")
    args = ap.parse_args()

    if not API_KEY:
        raise SystemExit("Please set env var YOUTUBE_API_KEY")

    os.makedirs(os.path.dirname(args.output_file), exist_ok=True)
    
    search_and_save_ids(args)

if __name__ == "__main__":
    main()