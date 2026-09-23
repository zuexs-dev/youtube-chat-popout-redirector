# ytchat

A permanent URL for any YouTube channel's live chat.

YouTube live chat URLs include the video ID (`live_chat?v=<id>`), so they change with every stream. ytchat gives each channel a fixed address that always opens the chat of whatever that channel is streaming now:

```
https://ytchat.example.com/@SomeChannel  ->  youtube.com/live_chat?is_popout=1&dark_theme=1&v=<current stream>
```

This is useful anywhere you want a chat pane that "just works" every stream: [Ferdium](https://ferdium.org), Rambox, an OBS browser source, a kiosk display.

- Single file, Python standard library only. No API key.
- Works with live and scheduled (upcoming) streams.
- When the channel isn't live, it serves a small dark page that re-checks every 60 s, so the tab switches to the chat by itself once the stream starts.
- Always uses YouTube's dark chat theme.

## Routes

| Path | Result |
|---|---|
| `/@handle` | 302 to the channel's current live or scheduled chat, or the waiting page |
| `/channel/UC…` | Same, by channel ID |
| `/login` | 302 to Google sign-in (see [Signing in](#signing-in-to-chat)) |

## Run it

### Docker Compose

```
git clone https://github.com/zuexs-dev/youtube-chat-popout-redirector.git && cd youtube-chat-popout-redirector && docker compose up -d
```

### Plain Python

```
YTCHAT_PORT=8095 python3 ytchat.py
```

A systemd unit is in [`examples/ytchat.service`](examples/ytchat.service).

### Test

```
curl -s -o /dev/null -w "%{http_code} -> %{redirect_url}\n" http://127.0.0.1:8095/@SomeChannel
```

`302 -> https://www.youtube.com/live_chat?...` means the channel is live and the redirect works. `200` means the channel isn't live (you get the waiting page).

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `YTCHAT_HOST` | `0.0.0.0` | Listen address |
| `YTCHAT_PORT` | `8095` | Listen port |
| `YTCHAT_CACHE_TTL` | `60` | Seconds to cache each channel's lookup |
| `YTCHAT_RETRY` | `60` | Seconds between re-checks on the waiting page |

Put it behind a TLS reverse proxy for use outside your LAN. An nginx example is in [`examples/nginx.conf`](examples/nginx.conf). ytchat has no authentication, but it only ever returns redirects to YouTube.

## Using it in Ferdium

Sign in first, then point the service at the channel.

1. **Add new service → Custom Website**, URL `https://ytchat.example.com/login`.
2. Before saving, open **Advanced** and set:
   - **Enable Dark Mode:** off. Ferdium's Dark Reader fights YouTube's own dark theme and gives white text on white.
   - **User Agent** (otherwise Google refuses the sign-in):
     ```
     Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0
     ```
3. Sign in to Google inside the tab. It lands on youtube.com when done.
4. Edit the service and change the URL to `https://ytchat.example.com/@SomeChannel`.

Each Ferdium service has its own browser session, so every new chat service needs this once.

### Signing in to chat

Google blocks sign-in from embedded browsers such as Electron apps ("This browser or app may not be secure"). The Firefox user agent above usually gets around that. The **Sign in** button inside the chat opens a new window, which most wrapper apps send to your default browser, so the app's own session never gets the login. `/login` loads Google's sign-in page directly in the app's session instead.

## How it works

For `/@handle`, ytchat fetches `https://www.youtube.com/@handle/live`. When the channel is live or has a scheduled stream, that page's canonical URL is `watch?v=<id>` and it contains `"isLiveNow":true`, `"isLive":true` or `"isUpcoming":true`. ytchat then redirects to that video's popout chat. Otherwise it serves the waiting page.

Limitations:

- This relies on YouTube page markup, not an official API, so a YouTube change can break detection.
- With several scheduled streams, YouTube picks which one `/live` shows (usually the soonest).
- If the creator disables pre-stream chat, a scheduled stream shows YouTube's "chat is disabled" message until it goes live. Reload then.

## License

[MIT](LICENSE)
