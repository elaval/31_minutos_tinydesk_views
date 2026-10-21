#!/usr/bin/env python3
"""Snapshot de estadísticas de todos los Tiny Desk Concerts en YouTube.

Reproduce el antiguo flujo de n8n: recorre la playlist oficial de NPR Music
"Tiny Desk Concerts", pide las estadísticas de cada video y guarda un JSON
con la misma forma que usaba el notebook (docs/allviews.html):

    [{"title", "publishedAt", "url", "viewCount", "likeCount", "commentCount", "videoId"}, ...]

`url` es la miniatura (default.jpg), como en el JSON original. Los conteos van
como string, igual que los entrega la API y como los guardaba n8n.

Solo usa la biblioteca estándar. Costo de cuota: ~1 unidad por cada 50 videos
(playlistItems + videos), unas 60 unidades por corrida sobre ~1.500 videos.

Uso:
    YT_API_KEY=... python3 scripts/snapshot_tinydesks.py [--out file.json]
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://www.googleapis.com/youtube/v3"
# "NPR Music Tiny Desk Concerts" en el canal de NPR Music.
DEFAULT_PLAYLIST = "PL1B627337ED6F55F0"


def get(endpoint, api_key, **params):
    params["key"] = api_key
    url = f"{API}/{endpoint}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=30) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"YouTube API error {e.code} en {endpoint}: {e.read().decode()}")


def playlist_video_ids(playlist_id, api_key):
    ids, token = [], None
    while True:
        params = {"part": "contentDetails", "playlistId": playlist_id, "maxResults": 50}
        if token:
            params["pageToken"] = token
        data = get("playlistItems", api_key, **params)
        ids += [it["contentDetails"]["videoId"] for it in data.get("items", [])]
        token = data.get("nextPageToken")
        if not token:
            break
    # La playlist puede repetir videos; conservar el orden de primera aparición.
    return list(dict.fromkeys(ids))


def video_records(ids, api_key):
    # Los videos privados o borrados no vuelven en videos.list: quedan fuera solos.
    records = []
    for i in range(0, len(ids), 50):
        data = get("videos", api_key, part="snippet,statistics", id=",".join(ids[i:i + 50]))
        for it in data.get("items", []):
            sn, st = it["snippet"], it.get("statistics", {})
            records.append({
                "title": sn["title"],
                "publishedAt": sn["publishedAt"],
                "url": sn.get("thumbnails", {}).get("default", {}).get("url", ""),
                "viewCount": st.get("viewCount", "0"),
                "likeCount": st.get("likeCount", "0"),
                "commentCount": st.get("commentCount", "0"),
                "videoId": it["id"],
            })
    return records


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--playlist", default=DEFAULT_PLAYLIST)
    p.add_argument("--out", default="file.json")
    args = p.parse_args()

    api_key = os.environ.get("YT_API_KEY")
    if not api_key:
        raise SystemExit("Falta la variable de entorno YT_API_KEY.")

    ids = playlist_video_ids(args.playlist, api_key)
    records = video_records(ids, api_key)
    records.sort(key=lambda r: r["publishedAt"], reverse=True)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False)
    print(f"{len(records)} videos ({len(ids) - len(records)} no disponibles) → {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
