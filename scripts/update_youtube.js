// scripts/update_youtube.js
// Node 20+ (built-in fetch). Appends the latest metrics to DATA_FILE.

import { readFileSync, writeFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname } from "node:path";

const API_KEY  = process.env.YT_API_KEY;
const VIDEO_ID = process.env.VIDEO_ID;
const DATA_FILE = process.env.DATA_FILE || "views2.json";

// Basic guards
if (!API_KEY)  throw new Error("Missing env YT_API_KEY.");
if (!VIDEO_ID) throw new Error("Missing env VIDEO_ID.");

// Fetch stats from YouTube Data API v3
const url = new URL("https://www.googleapis.com/youtube/v3/videos");
url.searchParams.set("part", "snippet,statistics");
url.searchParams.set("id", VIDEO_ID);
url.searchParams.set("key", API_KEY);

const res = await fetch(url, { method: "GET" });
if (!res.ok) {
  const text = await res.text();
  throw new Error(`YouTube API error: ${res.status} ${res.statusText}\n${text}`);
}
const data = await res.json();
if (!data.items || data.items.length === 0) {
  throw new Error("No video found for the provided VIDEO_ID.");
}

const item = data.items[0];
const now = new Date();

// Build record compatible with your file’s shape
const record = {
  timestamp: new Intl.DateTimeFormat("sv-SE", {
    timeZone: "America/Santiago",
    hour12: false,
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit"
  }).format(now).replace(" ", "T") + "-03:00", // keeps your style
  id: item.id,
  title: item.snippet?.title ?? "",
  viewCount: Number(item.statistics?.viewCount ?? 0),
  likeCount: Number(item.statistics?.likeCount ?? 0),
  commentCount: Number(item.statistics?.commentCount ?? 0)
};

// Ensure dir exists
const dir = dirname(DATA_FILE);
if (!existsSync(dir)) mkdirSync(dir, { recursive: true });

// Load existing JSON (array) or start fresh
let arr = [];
if (existsSync(DATA_FILE)) {
  try {
    const raw = readFileSync(DATA_FILE, "utf8");
    arr = JSON.parse(raw);
    if (!Array.isArray(arr)) arr = [];
  } catch {
    arr = [];
  }
}

// Optional: avoid duplicate rows if last viewCount & timestamp hour match
const last = arr[arr.length - 1];
const sameHour =
  last &&
  last.viewCount === record.viewCount &&
  last.likeCount === record.likeCount &&
  last.commentCount === record.commentCount;

// Append only when changed; you can drop this check if you prefer strict hourly rows
if (!sameHour) {
  arr.push(record);
  writeFileSync(DATA_FILE, JSON.stringify(arr, null, 2) + "\n", "utf8");
  console.log(`Appended metrics @ ${record.timestamp}`);
} else {
  console.log("No metric change detected; skipping append.");
}
