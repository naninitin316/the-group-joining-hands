# The Group of Joining Hands — setup

A modular web ecosystem built on the Python standard library (no framework),
vanilla JS/CSS on the front end, and SQLite for storage.

## Running it

```bash
python3 server.py
```

Then open http://localhost:8080. No dependency install is needed for the server
itself — `requirements.txt` covers optional extras only (Google sign-in
verification and the PDF/deck generators).

## Configuration

Copy `.env.example` to `.env` and fill it in.

`SECRET_KEY` and `JWT_SECRET` are **mandatory when `APP_ENV=production`** — the
server refuses to start without them rather than falling back to a shared
default. In development it generates a random secret per boot, which means
sessions end when you restart.

Generate each secret separately:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

## The database is not in this repository

`database/database.db` is gitignored. It holds real accounts and password
hashes and must not be published. The schema is created automatically on first
boot, so a fresh checkout will initialise its own empty database.

## Background theme assets

The theme picker ships 13 themes that render from pure CSS with no external
files. A further 24 legacy themes exist in the code but reference `.mp4` and
image files under `themes/` that are not in the repository; their buttons are
hidden via a clearly marked block in `static/css/styles.css` (section 15).
Upload the media and delete that block to restore them.

## Security notes

A security review was carried out on this codebase. Fixed since: path traversal
in the asset routes, hard-coded signing keys, credentialed CORS to any origin,
unbounded request bodies, a permissive Content Security Policy, rate limiting
applied to a single endpoint, and HTML served without cache directives.

One item remains open by choice: `script-src` still allows `'unsafe-inline'`
because `templates/index.html` relies on inline event handlers. Removing it
requires migrating those to `addEventListener`.
