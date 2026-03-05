# URL Shortener TUI

A terminal-based URL shortener with a built-in HTTP redirect server, built with [Textual](https://textual.textualize.io/).

## Features

- **Create** shortened URLs with random or custom short codes
- **List** all URLs in a searchable data table
- **View** full details, click counts, and creation dates
- **Edit** and **delete** URLs with confirmation dialogs
- **Built-in redirect server** — handles `GET /<code>` → 301 redirect
- **Settings** — configurable port, base URL, server toggle
- **Universal Help** (`h`) — available from main workflows with all operations documented
- **Secure** — uses `secrets.choice()` for cryptographically random codes
- **Persistent** — pluggable storage backend via repository interface
- **Backends** — SQLite (default), PostgreSQL, or MySQL via `DB_BACKEND`
- **Clipboard** — copies short URLs to clipboard (via pyperclip, with fallback)

## Quick Start (uv-first)

```bash
# 1) Install dependencies and create .venv
uv sync --dev

# 2) Run the TUI
uv run python run.py
```

## Development Workflow

```bash
# Run tests
uv run python -m pytest -q

# Optional TUI smoke run (Ctrl+Q to exit)
uv run python run.py
```

## Keyboard Shortcuts

| Key      | Action           |
|----------|------------------|
| `n`      | Create new URL   |
| `Enter`  | View URL details |
| `d`      | Delete URL       |
| `/`      | Search/filter    |
| `Esc`    | Clear search / close modal |
| `s`      | Settings         |
| `h`      | Help (all operations) |
| `r`      | Refresh list     |
| `q`      | Quit             |
| `Ctrl+Q` | Quit             |

## Terminal Theme & Font Guidance

- The app ships with a **modern high-contrast dark theme** tuned for readability.
- Recommended font (optional): **Nerd Font Mono** (for cleaner symbol alignment).
- Any readable monospaced font works; Nerd Mono is *not required*.

## Architecture

See `architecture.mmd` for the Mermaid architecture diagram (domain/service/repository boundary + SQLite/PostgreSQL/MySQL adapters + TUI/redirect interactions).

Render options:
- Mermaid Live: paste file contents into https://mermaid.live
- CLI: `npx @mermaid-js/mermaid-cli -i architecture.mmd -o architecture.svg`

## Data Storage & Backend Selection

Default backend is SQLite (`DB_BACKEND=sqlite`).

```bash
# SQLite (default)
DB_BACKEND=sqlite URL_SHORTENER_DATA_DIR=/tmp/my-urls uv run python run.py

# PostgreSQL
DB_BACKEND=postgres POSTGRES_DSN='postgresql://user:pass@localhost:5432/urlshortener' uv run python run.py

# MySQL
DB_BACKEND=mysql MYSQL_DSN='mysql://user:pass@localhost:3306/urlshortener' uv run python run.py
```

Optional backend dependencies:
```bash
uv sync --extra postgres
uv sync --extra mysql
```

## Redirect Server

By default, an HTTP redirect server starts on port **8080**. When someone visits `http://localhost:8080/<code>`, they're redirected (301) to the original URL, and the click count is incremented.

Change the port and base URL in Settings (`s`).

## Docker Profiles

`docker-compose.yml` includes backend-specific profiles:

```bash
# SQLite
docker compose --profile sqlite up --build

# PostgreSQL
docker compose --profile postgres up --build

# MySQL
docker compose --profile mysql up --build
```

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
