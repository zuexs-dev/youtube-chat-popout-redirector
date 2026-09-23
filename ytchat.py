#!/usr/bin/env python3
"""ytchat: a permanent URL for any YouTube channel's live chat.

GET /@handle          -> 302 to the channel's current live (or scheduled) popout chat
GET /channel/UC...    -> same, by channel ID
GET /login            -> 302 to Google sign-in, so an embedded browser session can chat

When the channel isn't live, a small page re-checks every RETRY seconds, so an
app tab (Ferdium, OBS browser source, etc.) switches to the chat by itself once
the stream starts. Python standard library only.
"""
import html
import os
import re
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LISTEN = (os.environ.get("YTCHAT_HOST", "0.0.0.0"), int(os.environ.get("YTCHAT_PORT", "8095")))
CACHE_TTL = int(os.environ.get("YTCHAT_CACHE_TTL", "60"))  # seconds to cache a lookup per channel
RETRY = int(os.environ.get("YTCHAT_RETRY", "60"))          # seconds between re-checks on the "not live" page

PATH_RE = re.compile(r"^/(@[A-Za-z0-9._-]{3,30}|channel/UC[A-Za-z0-9_-]{22})/?$")
CANON_RE = re.compile(r'<link rel="canonical" href="https://www\.youtube\.com/watch\?v=([A-Za-z0-9_-]{11})"')
LIVE_MARKERS = ('"isLiveNow":true', '"isLive":true', '"isUpcoming":true')
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Cookie": "SOCS=CAI; CONSENT=YES+",  # skip the EU consent interstitial
}
LOGIN_URL = "https://accounts.google.com/ServiceLogin?service=youtube&continue=https%3A%2F%2Fwww.youtube.com%2F"
_cache = {}


def find_live(chan):
    """Return the live (or upcoming) video ID for a channel, or None."""
    now = time.time()
    hit = _cache.get(chan)
    if hit and now - hit[0] < CACHE_TTL:
        return hit[1]
    req = urllib.request.Request(f"https://www.youtube.com/{chan}/live", headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as r:
        page = r.read().decode("utf-8", "replace")
    m = CANON_RE.search(page)
    vid = m.group(1) if m and any(k in page for k in LIVE_MARKERS) else None
    _cache[chan] = (now, vid)
    return vid


def wait_page(title, msg):
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta http-equiv="refresh" content="{RETRY}"><title>{title}</title>
<style>body{{background:#0f0f0f;color:#aaa;font:15px system-ui,sans-serif;
display:grid;place-items:center;height:100vh;margin:0;text-align:center}}</style>
</head><body><div>{msg}<br><small>Re-checking every {RETRY}s</small></div></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body="", location=None):
        data = body.encode()
        self.send_response(code)
        if location:
            self.send_header("Location", location)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path.rstrip("/") == "/login":  # sign-in inside the Ferdium service session
            return self._send(302, location=LOGIN_URL)
        m = PATH_RE.match(path)
        if not m:
            return self._send(404, wait_page("ytchat", "Use /@channelhandle"))
        chan = m.group(1)
        safe = html.escape(chan)
        try:
            vid = find_live(chan)
        except Exception as e:  # network/HTTP error from YouTube
            self.log_error("lookup %s failed: %s", chan, e)
            return self._send(502, wait_page(safe, f"Couldn't reach YouTube for {safe}"))
        if vid:
            return self._send(302, location=f"https://www.youtube.com/live_chat?is_popout=1&dark_theme=1&v={vid}")
        return self._send(200, wait_page(safe, f"{safe} isn't live right now"))


if __name__ == "__main__":
    print(f"ytchat listening on {LISTEN[0]}:{LISTEN[1]}", flush=True)
    ThreadingHTTPServer(LISTEN, Handler).serve_forever()
