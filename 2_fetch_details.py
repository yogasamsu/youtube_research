#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube Video Detail Fetcher - Descriptive Analysis Version (v6 - English Labels)

Uses bilingual keywords for matching but outputs standardized English tags for academic use.
"""

import os
import re
import argparse
import requests
import time
try:
    import pandas as pd
except Exception as e:
    raise SystemExit("Please install pandas: pip install -U pandas") from e

API_KEY = os.getenv("YOUTUBE_API_KEY")
BASE_URL = "https://www.googleapis.com/youtube/v3"

AI_KEYWORDS = [
    "ai generated", "ai video", "text-to-video", "sora", "runway gen-3", "runwayml",
    "pika labs", "gen-3", "midjourney", "luma ai", "google veo", "veo3",
    "synthesia", "heygen", "kaiber", "stable video diffusion", "d-id",
    "hailuo", "kling", "nano-banana", "gpt", "chatgpt", "elevenlabs"
]

# Bilingual keyword lists for broad matching
KREATIF_TERMS = ['short film', 'music video', 'animation', 'story', 'art', 'movie', 'song', 'fiction', 'cerita', 'film pendek', 'video musik']
EDUKASI_TERMS = ['tutorial', 'how to', 'guide', 'masterclass', 'lesson', 'course', 'explained', 'walkthrough', 'create', 'cara membuat', 'cara pakai', 'panduan', 'belajar', 'tips']
ULASAN_TERMS = ['review', 'news', 'update', 'demo', 'vs', 'versus', 'hands-on', 'first look', 'analysis', 'report', 'reaction', 'ulasan', 'berita']
EKSPERIMEN_TERMS = ['experiment', 'test', 'challenge', 'prompt', 'showcase', 'uji coba']


# --- Helper functions (no changes) ---
def _get(url, params, max_retries=5, backoff=1.6):
    params = dict(params or {}); params["key"] = API_KEY
    for attempt in range(max_retries):
        try:
            r = requests.get(url, params=params, timeout=30)
            if r.status_code == 200: return r.json()
            if r.status_code in (403, 429, 500, 503):
                time.sleep(int(backoff ** attempt) + 1); continue
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}. Retrying...")
            time.sleep(int(backoff ** attempt) + 1)
    raise RuntimeError(f"Failed after {max_retries} retries.")

def chunked(iterable, n):
    buf = [];
    for x in iterable:
        buf.append(x)
        if len(buf) == n: yield buf; buf = []
    if buf: yield buf

def to_int(x, default=0):
    try: return int(x)
    except: return default

def get_video_details(video_ids):
    rows = []; url = f"{BASE_URL}/videos"
    for i, batch in enumerate(chunked(video_ids, 50)):
        print(f"  > Fetching details for batch {i+1}...")
        params = {"part": "snippet,statistics,contentDetails", "id": ",".join(batch)}
        data = _get(url, params)
        for it in data.get("items", []):
            sn = it.get("snippet", {}) or {}; st = it.get("statistics", {}) or {}; cd = it.get("contentDetails", {}) or {}
            tags = sn.get("tags") or []
            rows.append({
                "videoId": it.get("id"), "publishedAt": sn.get("publishedAt"),
                "channelId": sn.get("channelId"), "channelTitle": sn.get("channelTitle"),
                "title": sn.get("title"), "description": sn.get("description"),
                "tags": "|".join(tags) if tags else "", "categoryId": sn.get("categoryId"),
                "duration": cd.get("duration"), "viewCount": to_int(st.get("viewCount")),
                "likeCount": to_int(st.get("likeCount")), "commentCount": to_int(st.get("commentCount")),
                "url": f"https://www.youtube.com/watch?v={it.get('id')}"
            })
        time.sleep(0.1)
    return rows

# ========== CLASSIFICATION FUNCTION UPDATED TO RETURN ENGLISH LABELS ==========
def klasifikasi_konten_dengan_tag(row) -> str:
    tags = []
    text_corpus = " ".join([
        str(row.get("title") or ""),
        str(row.get("description") or "")
    ]).lower()

    if any(term in text_corpus for term in KREATIF_TERMS):
        tags.append('creative_work')
    if any(term in text_corpus for term in EDUKASI_TERMS):
        tags.append('education_tutorial')
    if any(term in text_corpus for term in ULASAN_TERMS):
        tags.append('review_news')
    if any(term in text_corpus for term in EKSPERIMEN_TERMS):
        tags.append('experiment')

    is_ai_keyword_present = any(keyword in text_corpus for keyword in AI_KEYWORDS)
    if not tags and is_ai_keyword_present:
        tags.append('general_ai_content')
        
    if not tags:
        return 'Irrelevant'
    
    return "|".join(sorted(tags))
# ========== END OF UPDATE ==========

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input_file", type=str, default="out/video_ids.txt", help="File containing video IDs.")
    ap.add_argument("--output_file", type=str, default="out/videos_ai_deskriptif.csv", help="Single output file for descriptive analysis.")
    args = ap.parse_args()
    if not os.path.exists(args.input_file):
        raise SystemExit(f"Error: Input file not found at {args.input_file}.")
    with open(args.input_file, 'r') as f:
        video_ids = [line.strip() for line in f if line.strip()]
    print(f"[*] Found {len(video_ids)} video IDs in {args.input_file}.")
    details = get_video_details(video_ids)
    if not details:
        print("No details were fetched. Exiting.")
        return
    df = pd.DataFrame(details)
    print("[*] Classifying videos with bilingual keywords and English tags...")
    df["content_tags"] = df.apply(klasifikasi_konten_dengan_tag, axis=1) # Using a new column name
    df.to_csv(args.output_file, index=False, encoding='utf-8-sig')
    print(f"\n[*] Success! Saved {len(df)} classified videos to {args.output_file}")
    print("\nDistribution of content tags (Top 10):")
    # Explode tags for accurate value counting
    print(df['content_tags'].str.split('|').explode().value_counts().head(10))

if __name__ == "__main__":
    main()