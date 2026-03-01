# URL Shortener TUI

A terminal-based URL shortener with a built-in HTTP redirect server, built with [Textual](https://textual.textualize.io/).

## Features

- **Create** shortened URLs with random or custom short codes
- **List** all URLs in a searchable data table
- **View** full details, click counts, and creation dates
- **Edit** and **delete** URLs with confirmation dialogs
- **Built-in redirect server** — handles `GET /<code>` → 301 redirect
- **Settings** — configurable port, base URL, server toggle
- **Secure** — uses `secrets.choice()` for cryptographically random codes
- **Persistent** — SQLite database with WAL mode for safe concurrent access
- **Clipboard** — copies short URLs to clipboard (via pyperclip, with fallback)

## Quick Start

```bash
# Create a virtual environment
python3 -m venv .venv

# Install dependencies into the venv interpreter
.venv/bin/python -m pip install -r requirements.txt

# Run the app
.venv/bin/python run.py
```

## Test / Validation Steps

```bash
# Install test dependency
.venv/bin/python -m pip install pytest

# Run test suite
.venv/bin/python -m pytest -q

# Optional TUI smoke run (Ctrl+Q to exit)
.venv/bin/python run.py
```

Current automated coverage includes:
- import/startup smoke checks
- create/list/detail/edit/delete/search/settings core flows (database-backed)
- redirect server behavior (`GET /<code>` => `301`, missing code => `404`, click increment)
- `run.py` launcher wiring

## Keyboard Shortcuts

| Key     | Action           |
|---------|------------------|
| `n`     | Create new URL   |
| `Enter` | View URL details |
| `d`     | Delete URL       |
| `/`     | Search/filter    |
| `Esc`   | Clear search     |
| `s`     | Settings         |
| `r`     | Refresh list     |
| `q`     | Quit             |

## Architecture

```
┌─────────────────────────────────┐
│       Textual TUI App           │
│  ┌──────────┐  ┌────────────┐  │
│  │ URL List  │  │ Create URL │  │
│  │ Screen    │  │ Modal      │  │
│  ├──────────┤  ├────────────┤  │
│  │ Detail   │  │ Settings   │  │
│  │ Modal    │  │ Modal      │  │
│  └──────────┘  └────────────┘  │
│        │                        │
│   ┌────┴─────┐                 │
│   │ SQLite   │ (WAL mode)     │
│   └────┬─────┘                 │
│        │                        │
│  ┌─────┴──────────┐           │
│  │ Redirect Server │ (daemon) │
│  │ (http.server)   │          │
│  └────────────────┘           │
└─────────────────────────────────┘
```

## Data Storage

The SQLite database is stored at `~/.local/share/url-shortener/urls.db`.

Override with the `URL_SHORTENER_DATA_DIR` environment variable:
```bash
URL_SHORTENER_DATA_DIR=/tmp/my-urls python run.py
```

## Redirect Server

By default, an HTTP redirect server starts on port **8080**. When someone visits `http://localhost:8080/<code>`, they're redirected (301) to the original URL, and the click count is incremented.

Change the port and base URL in Settings (`s`).

### Running Behind a Reverse Proxy

For production use (even on a LAN), front the redirect server with nginx or Caddy for TLS:

```nginx
server {
    listen 443 ssl;
    server_name short.example.com;
    location / {
        proxy_pass http://127.0.0.1:8080;
    }
}
```

## Notes

- **Clipboard on headless systems:** `pyperclip` requires X11/Wayland. Over SSH without display, clipboard copy won't work — the app will show the URL for manual copying.
- **Raspberry Pi:** Fully compatible. All dependencies are pure Python — no native extensions needed.

## License

MIT
