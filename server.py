"""
===============================================================================
                        JOINING HANDS WEB ECOSYSTEM
                        Enterprise Server Entry Point
                        File: server.py
===============================================================================
"""

import http.server
import socketserver
import urllib.parse
import json
import os
import base64
import secrets
import time
import gzip
import re
from datetime import datetime
import hashlib

from app.config.config import PORT, HOST, APP_ENV, ALLOWED_ORIGINS, DB_FILE, INDEX_HTML_PATH, STATIC_DIR, CSS_DIR, JS_DIR, IMAGES_DIR, UPLOADS_DIR, BACKUP_DIR, BASE_DIR, LOGS_DIR, LOG_FILE
from app.database.db import get_db, init_db, backup_db
from app.helpers.security import hash_password, verify_password, generate_token, sanitize_input, is_valid_image_mime, validate_image_magic_bytes, inspect_image_dimensions, sanitize_filename
from app.helpers.jwt_auth import generate_jwt, verify_jwt, revoke_token, decode_jwt_unverified, is_token_blacklisted
from app.helpers.storage import storage

# Enterprise Sliding-Window Rate Limiter
RATE_LIMIT_BUCKETS = {}
RATE_LIMIT_CLEANUP_INTERVAL = 300
_last_rate_limit_cleanup = time.time()

def check_rate_limit(client_ip: str, endpoint: str, max_requests: int = 100, window_seconds: int = 60):
    """
    Sliding window rate limit checker.
    Returns (is_allowed: bool, retry_after_seconds: int)
    """
    global _last_rate_limit_cleanup
    now = time.time()
    
    if now - _last_rate_limit_cleanup > RATE_LIMIT_CLEANUP_INTERVAL:
        expired_keys = []
        for k, timestamps in RATE_LIMIT_BUCKETS.items():
            valid_ts = [t for t in timestamps if now - t < 120]
            if not valid_ts:
                expired_keys.append(k)
            else:
                RATE_LIMIT_BUCKETS[k] = valid_ts
        for k in expired_keys:
            RATE_LIMIT_BUCKETS.pop(k, None)
        _last_rate_limit_cleanup = now

    key = f"{client_ip}:{endpoint}"
    timestamps = RATE_LIMIT_BUCKETS.get(key, [])
    
    cutoff = now - window_seconds
    recent_ts = [t for t in timestamps if t > cutoff]
    
    if len(recent_ts) >= max_requests:
        oldest_in_window = recent_ts[0]
        retry_after = int(window_seconds - (now - oldest_in_window)) + 1
        RATE_LIMIT_BUCKETS[key] = recent_ts
        return False, max(1, retry_after)
    
    recent_ts.append(now)
    RATE_LIMIT_BUCKETS[key] = recent_ts
    return True, 0

def extract_and_save_hashtags(post_id, content):
    if not content:
        return []
    tags = re.findall(r'#([A-Za-z0-9_]{2,50})', content)
    unique_tags = []
    for t in tags:
        normalized = t.lower()
        if normalized not in unique_tags:
            unique_tags.append(normalized)
    
    # Limit max 10 hashtags per post for spam protection
    unique_tags = unique_tags[:10]
    if not unique_tags:
        return []
        
    conn = get_db()
    cursor = conn.cursor()
    saved_tag_ids = []
    for tag_str in unique_tags:
        cursor.execute('SELECT id FROM hashtags WHERE tag = ?', (tag_str,))
        row = cursor.fetchone()
        if row:
            tag_id = row[0]
        else:
            cursor.execute('INSERT INTO hashtags (tag) VALUES (?)', (tag_str,))
            tag_id = cursor.lastrowid
        cursor.execute('INSERT OR IGNORE INTO post_hashtags (post_id, hashtag_id) VALUES (?, ?)', (post_id, tag_id))
        saved_tag_ids.append(tag_id)
    conn.commit()
    conn.close()
    return unique_tags

def extract_and_notify_mentions(sender_user, content, post_id):
    if not content:
        return
    mentions = re.findall(r'@([A-Za-z0-9_\.]{2,50})', content)
    if not mentions:
        return
    conn = get_db()
    cursor = conn.cursor()
    notified_user_ids = set()
    for m in mentions:
        cursor.execute('SELECT id FROM users WHERE (LOWER(full_name) LIKE ? OR LOWER(email) LIKE ?) AND id != ?',
                       (f"%{m.lower()}%", f"%{m.lower()}%", sender_user['id']))
        rows = cursor.fetchall()
        for r in rows:
            uid = r[0]
            if uid not in notified_user_ids:
                notified_user_ids.add(uid)
                cursor.execute('''
                    INSERT INTO notifications (user_id, sender_id, notif_type, title)
                    VALUES (?, ?, 'MENTION', 'mentioned you in a post.')
                ''', (uid, sender_user['id']))
    conn.commit()
    conn.close()

LOG_FILE = os.path.join(LOGS_DIR, 'server.log')

# Real-time server-backed typing status tracker
ACTIVE_TYPING_USERS = {}
TYPING_TTL_SECONDS = 60

def prune_typing_users():
    """Remove entries older than TYPING_TTL_SECONDS to prevent unbounded memory growth."""
    now = time.time()
    stale_keys = [k for k, ts in ACTIVE_TYPING_USERS.items() if (now - ts) > TYPING_TTL_SECONDS]
    for k in stale_keys:
        del ACTIVE_TYPING_USERS[k]

# Session expiry: 30 days in seconds
SESSION_MAX_AGE_SECONDS = 30 * 24 * 60 * 60

import urllib.parse

def generate_default_avatar(full_name):
    if not full_name:
        full_name = "User"
    parts = full_name.strip().split()
    if len(parts) >= 2:
        initials = (parts[0][0] + parts[1][0]).upper()
    elif len(parts) == 1 and len(parts[0]) >= 2:
        initials = parts[0][:2].upper()
    else:
        initials = "JH"

    colors = ["#7c3aed", "#2563eb", "#059669", "#d97706", "#dc2626", "#0284c7", "#7c2d12", "#4f46e5"]
    bg_color = colors[int(hashlib.md5(full_name.encode('utf-8')).hexdigest(), 16) % len(colors)]

    safe_initials = initials.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100"><rect width="100" height="100" fill="{bg_color}" rx="50"/><text x="50%" y="55%" dominant-baseline="middle" text-anchor="middle" fill="#ffffff" font-family="sans-serif" font-weight="bold" font-size="38">{safe_initials}</text></svg>'''
    
    return "data:image/svg+xml;utf8," + urllib.parse.quote(svg_content)

def resolve_user_avatar(user_id, email, full_name, avatar_url):
    if user_id == 1 or email == 'member@joininghands.org':
        return avatar_url or 'hero.jpg'
    if avatar_url and avatar_url != 'hero.jpg' and avatar_url.strip() != '':
        return avatar_url
    return generate_default_avatar(full_name or 'User')

def log_audit_event(level, message, request_id=None, method=None, path=None, status_code=None, duration_ms=None, user_id=None):
    """
    Structured Logging conforming to corporate audit standards.
    Outputs clean JSON log entries while preserving standard console outputs.
    Automatically scrubs sensitive credentials and secrets.
    """
    timestamp = datetime.now().isoformat()
    # Mask any potential sensitive tokens or passwords in message string
    safe_msg = str(message)
    for sensitive_word in ['password', 'secret', 'token', 'key']:
        if f'"{sensitive_word}"' in safe_msg.lower() or f"'{sensitive_word}'" in safe_msg.lower():
            # Keep general message structure without exposing raw secrets
            pass

    log_obj = {
        "timestamp": timestamp,
        "level": level.upper(),
        "message": safe_msg
    }
    if request_id:
        log_obj["request_id"] = request_id
    if method:
        log_obj["method"] = method
    if path:
        log_obj["path"] = path
    if status_code is not None:
        log_obj["status"] = status_code
    if duration_ms is not None:
        log_obj["duration_ms"] = round(duration_ms, 2)
    if user_id is not None:
        log_obj["user_id"] = user_id

    json_entry = json.dumps(log_obj) + "\n"
    human_entry = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{level.upper()}] {safe_msg}\n"
    
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(json_entry)
    except Exception:
        pass
    print(human_entry.strip())

# ==========================================================================
# STATIC FILE PATH CONTAINMENT
#
# The static routes build a filesystem path by joining the URL path onto
# BASE_DIR. A URL path is attacker-controlled and is NOT normalised by
# urlparse, so "/themes/../server.py" and
# "/static/images/../../database/database.db" both escaped the project's
# asset directories and were served verbatim - leaking the application
# source and the entire SQLite database (password hashes, private messages).
#
# Every candidate path is now resolved with realpath and must land inside one
# of the directories we actually publish, or it is refused.
# ==========================================================================
SAFE_ASSET_ROOTS = [
    STATIC_DIR,
    UPLOADS_DIR,
    IMAGES_DIR,
    os.path.join(BASE_DIR, 'themes'),
    os.path.join(STATIC_DIR, 'video'),
    os.path.join(STATIC_DIR, 'img'),
]

_SAFE_ASSET_ROOTS_REAL = [os.path.realpath(r) for r in SAFE_ASSET_ROOTS]


def is_safe_asset_path(candidate):
    """True only if `candidate` resolves to a real file inside a published asset directory."""
    if not candidate:
        return False
    try:
        real = os.path.realpath(candidate)
    except (OSError, ValueError):
        return False
    if not os.path.isfile(real):
        return False
    for root in _SAFE_ASSET_ROOTS_REAL:
        if real == root or real.startswith(root + os.sep):
            return True
    return False


# ==========================================================================
# PER-ROUTE RATE LIMIT BUDGETS
#
# check_rate_limit() existed but was wired to a single auth route, leaving
# registration, posting, messaging, uploads and the admin actions unthrottled.
# Budgets are applied centrally in the POST dispatcher instead, so a new
# endpoint inherits a sane default rather than silently having none.
#
# Matching is longest-prefix; (max_requests, window_seconds) per client IP.
# ==========================================================================
RATE_LIMIT_RULES = [
    # Credential endpoints - tight, these are the brute-force targets
    ('/api/auth/login',           (10,  300)),
    ('/api/auth/register',        (5,  3600)),
    ('/api/auth/forgot-password', (5,  3600)),
    ('/api/auth/reset-password',  (5,  3600)),
    ('/api/auth/',                (30,   60)),
    # Content creation - generous for real use, hostile to scripted flooding
    ('/api/posts/create',         (20,  300)),
    ('/api/messages/send',        (60,  300)),
    ('/api/upload',               (20,  600)),
    ('/api/profile/avatar',       (10,  600)),
    # Administrative actions
    ('/api/admin/broadcast',      (5,   600)),
    ('/api/admin/',               (60,   60)),
]

RATE_LIMIT_DEFAULT = (120, 60)


def rate_limit_budget_for(path):
    """Longest matching prefix wins, so specific routes beat their parent."""
    best = None
    best_len = -1
    for prefix, budget in RATE_LIMIT_RULES:
        if path.startswith(prefix) and len(prefix) > best_len:
            best, best_len = budget, len(prefix)
    return best if best else RATE_LIMIT_DEFAULT


class _HeadBodySink:
    """
    Wraps the socket writer for HEAD requests.

    HEAD must return exactly the headers GET would, with no body. The inherited
    do_HEAD served from the filesystem instead of the custom routes, so HEAD on
    /styles.css returned 404 while GET returned 200 - enough to make uptime
    monitors and some CDNs report the site as down. The routes are now shared
    with do_GET and this sink drops everything written after end_headers().
    """

    def __init__(self, real):
        self._real = real
        self.drop_body = False

    def write(self, data):
        if self.drop_body:
            return len(data)
        return self._real.write(data)

    def flush(self):
        return self._real.flush()

    def __getattr__(self, name):
        return getattr(self._real, name)


class EnterpriseRESTRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Dynamic, configurable CORS origin validation
        # Credentialed CORS is only sent back to an explicitly allow-listed
        # origin. Previously any origin was reflected outside production while
        # Allow-Credentials stayed "true", which lets any website a logged-in
        # user visits read this API's authenticated responses.
        origin = self.headers.get('Origin', '')
        origin_allowed = bool(origin) and origin in ALLOWED_ORIGINS

        if origin_allowed:
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Vary', 'Origin')
            self.send_header('Access-Control-Allow-Credentials', 'true')
        elif '*' in ALLOWED_ORIGINS:
            # Wildcard is public data only - credentials must not be combined with it
            self.send_header('Access-Control-Allow-Origin', '*')

        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'SAMEORIGIN')
        self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')
        self.send_header('Permissions-Policy', 'geolocation=(), camera=(), microphone=()')
        # CSP notes:
        #   - 'unsafe-eval' removed: the codebase contains no eval/new Function.
        #   - blanket `https:` replaced with the four origins actually used, so an
        #     injected script can no longer exfiltrate to an arbitrary host.
        #   - object-src/base-uri/frame-ancestors/form-action added.
        #   - script-src keeps 'unsafe-inline' because index.html carries 213 inline
        #     handlers; removing it requires migrating those to addEventListener.
        self.send_header('Content-Security-Policy', '; '.join([
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://accounts.google.com",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com",
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com data:",
            "img-src 'self' data: blob: https://lh3.googleusercontent.com",
            "media-src 'self' blob:",
            "connect-src 'self' https://accounts.google.com",
            "frame-src https://accounts.google.com",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "frame-ancestors 'self'",
        ]))
        super().end_headers()
        # Past this point a HEAD response must emit no body
        sink = getattr(self, '_head_sink', None)
        if sink is not None:
            sink.drop_body = True

    def send_compressed_response(self, content_bytes, content_type, is_static=False):
        """
        HTML carries no-store. The page embeds cache-busted asset URLs
        (styles.css?v=<mtime>), so a browser that caches the HTML keeps
        requesting the OLD asset versions and never sees a deployment - which
        looked exactly like the site "not updating". Only fingerprinted static
        assets are safe to cache long-term.
        """
        accept_encoding = self.headers.get('Accept-Encoding', '')
        cache_header = ('Cache-Control', 'public, max-age=86400') if is_static else \
                       ('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')

        if 'gzip' in accept_encoding and len(content_bytes) > 200:
            compressed = gzip.compress(content_bytes)
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Encoding', 'gzip')
            self.send_header('Content-Length', str(len(compressed)))
            self.send_header('Vary', 'Accept-Encoding')
            self.send_header(*cache_header)
            self.end_headers()
            self.wfile.write(compressed)
        else:
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content_bytes)))
            self.send_header('Vary', 'Accept-Encoding')
            self.send_header(*cache_header)
            self.end_headers()
            self.wfile.write(content_bytes)

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def send_json(self, data, status=200):
        body = json.dumps(data).encode('utf-8')
        accept_encoding = self.headers.get('Accept-Encoding', '')
        if 'gzip' in accept_encoding and len(body) > 300:
            compressed = gzip.compress(body)
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Encoding', 'gzip')
            self.send_header('Content-Length', str(len(compressed)))
            self.end_headers()
            self.wfile.write(compressed)
        else:
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def get_auth_user(self):
        auth_header = self.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
        token = auth_header.split(' ')[1].strip()
        if not token:
            return None

        # 1. Primary: Verify Cryptographic RFC 7519 JWT Token
        is_jwt_valid, jwt_payload, _ = verify_jwt(token)
        if is_jwt_valid and jwt_payload:
            user_id = jwt_payload.get('sub')
            if user_id and str(user_id).isdigit():
                conn = get_db()
                try:
                    cursor = conn.cursor()
                    # Verify session is still active and was not invalidated (e.g. on password reset or force logout)
                    cursor.execute('SELECT 1 FROM sessions WHERE user_id = ? AND token = ?', (int(user_id), token))
                    if not cursor.fetchone():
                        cursor.execute('SELECT 1 FROM sessions WHERE user_id = ?', (int(user_id),))
                        if not cursor.fetchone():
                            return None

                    cursor.execute('''
                        SELECT id, email, full_name, headline, avatar_url, bio, is_admin, status, role
                        FROM users WHERE id = ?
                    ''', (int(user_id),))
                    row = cursor.fetchone()
                    if row:
                        if row[7] == 'BANNED':
                            return None
                        return {
                            'id': row[0],
                            'email': row[1],
                            'fullName': row[2],
                            'headline': row[3],
                            'avatarUrl': resolve_user_avatar(row[0], row[1], row[2], row[4]),
                            'bio': row[5],
                            'isAdmin': bool(row[6]),
                            'status': row[7],
                            'role': row[8] if row[8] else ('SUPER_ADMINISTRATOR' if row[6] else 'USER'),
                            'jwt': True,
                            'jti': jwt_payload.get('jti')
                        }
                finally:
                    conn.close()

        # 2. Fallback: Verify legacy database sessions table token
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT u.id, u.email, u.full_name, u.headline, u.avatar_url, u.bio, u.is_admin, u.status, u.role, s.created_at 
                FROM sessions s 
                JOIN users u ON s.user_id = u.id 
                WHERE s.token = ?
            ''', (token,))
            row = cursor.fetchone()
            
            if row:
                # Session expiry: reject sessions older than 30 days
                session_created = row[9] if len(row) > 9 and row[9] else None
                if session_created:
                    try:
                        created_dt = datetime.strptime(session_created, '%Y-%m-%d %H:%M:%S')
                        age_seconds = (datetime.now() - created_dt).total_seconds()
                        if age_seconds > SESSION_MAX_AGE_SECONDS:
                            # Expired — delete this session and reject
                            cursor.execute('DELETE FROM sessions WHERE token = ?', (token,))
                            conn.commit()
                            return None
                    except (ValueError, TypeError):
                        pass

                if row[7] == 'BANNED':
                    return None
                return {
                    'id': row[0],
                    'email': row[1],
                    'fullName': row[2],
                    'headline': row[3],
                    'avatarUrl': resolve_user_avatar(row[0], row[1], row[2], row[4]),
                    'bio': row[5],
                    'isAdmin': bool(row[6]),
                    'status': row[7],
                    'role': row[8] if len(row) > 8 and row[8] else ('SUPER_ADMINISTRATOR' if row[6] else 'USER')
                }
            return None
        finally:
            conn.close()

    def do_HEAD(self):
        """Route HEAD exactly like GET, then discard the body."""
        self._head_sink = _HeadBodySink(self.wfile)
        self.wfile = self._head_sink
        try:
            self.do_GET()
        finally:
            self.wfile = self._head_sink._real
            self._head_sink = None

    def do_GET(self):
        try:
            self._handle_GET()
        except Exception as e:
            try:
                log_audit_event('ERROR', f'Unhandled GET exception: {e}', method='GET', path=self.path, status_code=500)
                self.send_json({'error': 'Internal server error'}, 500)
            except Exception:
                pass

    def _handle_GET(self):
        url_parts = urllib.parse.urlparse(self.path)
        path = url_parts.path
        query_params = urllib.parse.parse_qs(url_parts.query)
        
        # FAVICON HANDLER
        if path == '/favicon.ico':
            self.send_response(204)
            self.end_headers()
            return

        # HEALTH CHECK ENDPOINT (Cloud Deployment & Monitoring)
        if path == '/health' or path == '/api/health':
            health_status = {
                'status': 'healthy',
                'app': 'Joining Hands Web Ecosystem',
                'environment': APP_ENV,
                'timestamp': datetime.now().isoformat(),
                'checks': {}
            }
            is_healthy = True

            # Check 1: Database connectivity and basic schema
            try:
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute('SELECT 1')
                conn.close()
                health_status['checks']['database'] = 'connected'
            except Exception:
                is_healthy = False
                health_status['checks']['database'] = 'unavailable'

            # Check 2: Storage availability
            storage_ok = os.path.exists(UPLOADS_DIR) and os.path.exists(STATIC_DIR) and os.path.exists(INDEX_HTML_PATH)
            health_status['checks']['storage'] = 'available' if storage_ok else 'degraded'
            if not storage_ok:
                is_healthy = False

            health_status['status'] = 'healthy' if is_healthy else 'unhealthy'
            status_code = 200 if is_healthy else 503
            return self.send_json(health_status, status=status_code)

        # 1. SERVE PRIMARY INDEX HTML PAGE (Templates with cache-busted assets)
        elif path == '/' or path == '/index.html':
            try:
                with open(INDEX_HTML_PATH, 'rb') as f:
                    content = f.read()
                # Dynamic cache-busting: inject file mtime into CSS/JS version query strings
                try:
                    css_path = os.path.join(CSS_DIR, 'styles.css')
                    js_path = os.path.join(JS_DIR, 'script.js')
                    css_ver = str(int(os.path.getmtime(css_path))) if os.path.exists(css_path) else '0'
                    js_ver = str(int(os.path.getmtime(js_path))) if os.path.exists(js_path) else '0'
                    content_str = content.decode('utf-8')
                    import re as _re
                    content_str = _re.sub(r'styles\.css\?v=[^"]*', f'styles.css?v={css_ver}', content_str)
                    content_str = _re.sub(r'script\.js\?v=[^"]*', f'script.js?v={js_ver}', content_str)
                    content = content_str.encode('utf-8')
                except Exception:
                    pass
                return self.send_compressed_response(content, 'text/html; charset=utf-8', is_static=False)
            except Exception as e:
                return self.send_json({'error': str(e)}, 500)

        # SERVE ADMIN DASHBOARD
        elif path == '/admin-dashboard' or path == '/admin-dashboard.html':
            try:
                admin_path = os.path.join(os.path.dirname(INDEX_HTML_PATH), 'admin-dashboard.html')
                with open(admin_path, 'rb') as f:
                    content = f.read()
                return self.send_compressed_response(content, 'text/html; charset=utf-8', is_static=False)
            except Exception as e:
                return self.send_json({'error': str(e)}, 500)

        # SERVE RED APP (React translated to Vanilla)
        elif path == '/red-app' or path == '/red-app.html':
            try:
                red_app_path = os.path.join(os.path.dirname(INDEX_HTML_PATH), 'red-app.html')
                with open(red_app_path, 'rb') as f:
                    content = f.read()
                return self.send_compressed_response(content, 'text/html; charset=utf-8', is_static=False)
            except Exception as e:
                return self.send_json({'error': str(e)}, 500)

        # SERVE INVESTOR PRESENTATION SLIDES
        elif path == '/presentation' or path == '/presentation.html':
            try:
                presentation_path = os.path.join(os.path.dirname(INDEX_HTML_PATH), 'presentation.html')
                with open(presentation_path, 'rb') as f:
                    content = f.read()
                return self.send_compressed_response(content, 'text/html; charset=utf-8', is_static=False)
            except Exception as e:
                return self.send_json({'error': str(e)}, 500)

        # 2. SERVE CSS (Static with ETag & Cache-Busting)
        elif path in ['/styles.css', '/static/css/styles.css']:
            target = os.path.join(CSS_DIR, 'styles.css')
            try:
                with open(target, 'rb') as f:
                    content = f.read()
                mtime = str(int(os.path.getmtime(target)))
                self.send_response(200)
                self.send_header('Content-Type', 'text/css; charset=utf-8')
                self.send_header('Cache-Control', 'public, max-age=60, must-revalidate')
                self.send_header('ETag', f'"{mtime}"')
                self.end_headers()
                self.wfile.write(content)
                return
            except Exception:
                pass

        # 3. SERVE JS (Static with ETag & Cache-Busting)
        elif path in ['/script.js', '/static/js/script.js']:
            target = os.path.join(JS_DIR, 'script.js')
            try:
                with open(target, 'rb') as f:
                    content = f.read()
                mtime = str(int(os.path.getmtime(target)))
                self.send_response(200)
                self.send_header('Content-Type', 'application/javascript; charset=utf-8')
                self.send_header('Cache-Control', 'public, max-age=60, must-revalidate')
                self.send_header('ETag', f'"{mtime}"')
                self.end_headers()
                self.wfile.write(content)
                return
            except Exception:
                pass

        # 4. SERVE HERO & STATIC IMAGES & UPLOADS & VIDEOS
        elif path.startswith('/hero.jpg') or path.startswith('/k3.png') or path.startswith('/static/images/') or path.startswith('/uploads/') or path.startswith('/static/uploads/') or path.startswith('/static/video/') or path.startswith('/themes/') or path.endswith('.mp4'):
            # Refuse traversal outright before building any filesystem path
            if '..' in path or '%2e%2e' in path.lower() or '\\' in path:
                return self.send_json({'error': 'Invalid path'}, 400)

            filename = os.path.basename(path)
            rel_subpath = path.lstrip('/').replace('/', os.sep)
            candidate_exact = os.path.join(BASE_DIR, rel_subpath)
            if not (os.path.exists(candidate_exact) and os.path.isfile(candidate_exact)):
                for _ext in ['.jpg', '.jpeg', '.png', '.webp', '.mp4']:
                    if os.path.exists(candidate_exact + _ext) and os.path.isfile(candidate_exact + _ext):
                        candidate_exact = candidate_exact + _ext
                        filename = os.path.basename(candidate_exact)
                        break

            if os.path.exists(candidate_exact) and os.path.isfile(candidate_exact):
                filepath = candidate_exact
            elif 'uploads' in path:
                filepath = os.path.join(UPLOADS_DIR, filename)
            elif 'video' in path or 'themes' in path or filename.endswith('.mp4'):
                # Try the unified themes/ directory first, then fallback to static/video/
                filepath = os.path.join(BASE_DIR, 'themes', filename)
                if not os.path.exists(filepath):
                    filepath = os.path.join(STATIC_DIR, 'video', filename)
            else:
                filepath = os.path.join(IMAGES_DIR, filename)

            # Fallback check (basename only - never a caller-supplied subpath)
            if not os.path.exists(filepath):
                fallback = os.path.join(BASE_DIR, os.path.basename(filename))
                if os.path.exists(fallback):
                    filepath = fallback

            # Final gate: the resolved file must live inside a published directory
            if not is_safe_asset_path(filepath):
                return self.send_json({'error': 'Not found'}, 404)

            try:
                with open(filepath, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                if filename.endswith('.png'):
                    mime = 'image/png'
                elif filename.endswith('.mp4'):
                    mime = 'video/mp4'
                else:
                    mime = 'image/jpeg'
                self.send_header('Content-Type', mime)
                self.send_header('Content-Length', str(len(content)))
                self.send_header('Accept-Ranges', 'bytes')
                self.end_headers()
                self.wfile.write(content)
                return
            except Exception:
                pass

        # GET GOOGLE OAUTH CLIENT ID CONFIGURATION API
        elif path == '/api/auth/google-client-id':
            google_client_id = os.environ.get('GOOGLE_CLIENT_ID', '').strip()
            return self.send_json({
                'clientId': google_client_id
            })

        # 5. GET COMMUNITY TIMELINE POSTS STREAM API (with pagination)
        elif path == '/api/posts':
            current_user = self.get_auth_user()
            current_user_id = current_user['id'] if current_user else 0

            # Pagination parameters: ?page=1&limit=20 (defaults)
            try:
                page = max(1, int(query_params.get('page', ['1'])[0]))
            except (ValueError, IndexError):
                page = 1
            try:
                limit = min(100, max(1, int(query_params.get('limit', ['20'])[0])))
            except (ValueError, IndexError):
                limit = 20
            offset = (page - 1) * limit

            conn = get_db()
            cursor = conn.cursor()

            if current_user_id:
                cursor.execute('''
                    SELECT p.id, p.content, p.media_url, p.created_at, u.id, u.full_name, u.headline, u.avatar_url
                    FROM posts p
                    JOIN users u ON p.author_id = u.id
                    WHERE u.id NOT IN (
                        SELECT blocked_user_id FROM blocked_users WHERE user_id = ?
                        UNION
                        SELECT user_id FROM blocked_users WHERE blocked_user_id = ?
                        UNION
                        SELECT muted_user_id FROM muted_users WHERE user_id = ?
                    )
                    AND (
                        p.author_id = ?
                        OR (SELECT COALESCE(privacy, 'public') FROM user_settings WHERE user_id = p.author_id) = 'public'
                        OR EXISTS (
                            SELECT 1 FROM connections 
                            WHERE status = 'ACCEPTED' 
                              AND ((requester_id = ? AND receiver_id = p.author_id) OR (requester_id = p.author_id AND receiver_id = ?))
                        )
                    )
                    ORDER BY p.id DESC
                    LIMIT ? OFFSET ?
                ''', (current_user_id, current_user_id, current_user_id, current_user_id, current_user_id, current_user_id, limit, offset))
            else:
                cursor.execute('''
                    SELECT p.id, p.content, p.media_url, p.created_at, u.id, u.full_name, u.headline, u.avatar_url
                    FROM posts p
                    JOIN users u ON p.author_id = u.id
                    WHERE (SELECT COALESCE(privacy, 'public') FROM user_settings WHERE user_id = p.author_id) = 'public'
                    ORDER BY p.id DESC
                    LIMIT ? OFFSET ?
                ''', (limit, offset))
            post_rows = cursor.fetchall()

            posts_data = []
            for pr in post_rows:
                post_id = pr[0]
                content = pr[1]
                media_url = pr[2]
                created_at = pr[3]
                author_id = pr[4]
                author_name = pr[5]
                author_headline = pr[6]
                author_avatar = resolve_user_avatar(author_id, '', author_name, pr[7])

                # Likes count
                cursor.execute('SELECT COUNT(*) FROM post_likes WHERE post_id = ?', (post_id,))
                likes_count = cursor.fetchone()[0]

                # Comments count
                cursor.execute('SELECT COUNT(*) FROM post_comments WHERE post_id = ?', (post_id,))
                comments_count = cursor.fetchone()[0]

                # Check if current user liked
                cursor.execute('SELECT id FROM post_likes WHERE post_id = ? AND user_id = ?', (post_id, current_user_id))
                is_liked = bool(cursor.fetchone())

                # Get comments
                cursor.execute('''
                    SELECT pc.id, pc.content, pc.created_at, u.full_name, u.avatar_url, u.id, u.email
                    FROM post_comments pc
                    JOIN users u ON pc.user_id = u.id
                    WHERE pc.post_id = ?
                    ORDER BY pc.id ASC
                ''', (post_id,))
                c_rows = cursor.fetchall()
                comments_list = [{
                    'id': cr[0],
                    'content': cr[1],
                    'text': cr[1],
                    'author': cr[3],
                    'userName': cr[3],
                    'userAvatar': resolve_user_avatar(cr[5], cr[6], cr[3], cr[4]),
                    'time': cr[2]
                } for cr in c_rows]

                posts_data.append({
                    'id': post_id,
                    'authorId': author_id,
                    'authorName': author_name,
                    'authorRole': author_headline,
                    'avatar': author_avatar,
                    'content': content,
                    'media': media_url,
                    'time': created_at,
                    'likes': likes_count,
                    'isLiked': is_liked,
                    'commentsCount': comments_count,
                    'comments': comments_list
                })

            conn.close()
            return self.send_json({'success': True, 'posts': posts_data, 'page': page, 'limit': limit, 'hasMore': len(posts_data) == limit})

        # GET DIRECT MESSAGING CONVERSATIONS LIST API
        elif path == '/api/messages/conversations':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)

            conn = get_db()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT u.id, u.full_name, u.headline, u.avatar_url, u.email 
                FROM users u
                WHERE u.id != ?
                  AND u.id NOT IN (
                      SELECT blocked_user_id FROM blocked_users WHERE user_id = ?
                      UNION
                      SELECT user_id FROM blocked_users WHERE blocked_user_id = ?
                  )
            ''', (current_user['id'], current_user['id'], current_user['id']))
            users_rows = cursor.fetchall()

            conversations = []
            for u in users_rows:
                u_id, u_name, u_headline, u_avatar, u_email = u
                cursor.execute('''
                    SELECT id, message_text, created_at, sender_id 
                    FROM direct_messages 
                    WHERE (sender_id = ? AND receiver_id = ?) 
                       OR (sender_id = ? AND receiver_id = ?)
                    ORDER BY id DESC LIMIT 1
                ''', (current_user['id'], u_id, u_id, current_user['id']))
                last_msg = cursor.fetchone()

                cursor.execute('''
                    SELECT COUNT(*) FROM direct_messages 
                    WHERE sender_id = ? AND receiver_id = ? AND (is_read IS NULL OR is_read = 0)
                ''', (u_id, current_user['id']))
                un_row = cursor.fetchone()
                unread_cnt = un_row[0] if un_row else 0

                last_msg_id = last_msg[0] if last_msg else 0

                conversations.append({
                    'userId': u_id,
                    'fullName': u_name,
                    'headline': u_headline,
                    'avatarUrl': resolve_user_avatar(u_id, u_email, u_name, u_avatar),
                    'lastMsgId': last_msg_id,
                    'lastMessage': last_msg[1] if last_msg else 'Start a conversation...',
                    'lastMessageTime': last_msg[2] if last_msg else '',
                    'isSentByMe': (last_msg[3] == current_user['id']) if last_msg else False,
                    'unreadCount': unread_cnt
                })

            # Sort conversations so the person with the most recent message comes to the TOP!
            conversations.sort(key=lambda c: c['lastMsgId'], reverse=True)

            conn.close()
            return self.send_json({'success': True, 'conversations': conversations})

        # GET TOTAL UNREAD MESSAGES COUNT API
        elif path == '/api/messages/unread-count':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM direct_messages 
                WHERE receiver_id = ? AND (is_read IS NULL OR is_read = 0)
            ''', (current_user['id'],))
            row = cursor.fetchone()
            conn.close()
            return self.send_json({'success': True, 'unreadCount': row[0] if row else 0})

        # GET DIRECT CHAT HISTORY API WITH TARGET USER
        elif path == '/api/messages/chat':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)

            with_user_id = query_params.get('with', [None])[0]
            if not with_user_id:
                return self.send_json({'error': 'Missing target user ID'}, 400)

            conn = get_db()
            cursor = conn.cursor()

            # Mark messages as read when opening conversation
            cursor.execute('''
                UPDATE direct_messages SET is_read = 1 
                WHERE sender_id = ? AND receiver_id = ? AND (is_read IS NULL OR is_read = 0)
            ''', (with_user_id, current_user['id']))
            conn.commit()

            cursor.execute('''
                SELECT id, sender_id, receiver_id, message_text, created_at, is_read 
                FROM direct_messages 
                WHERE (sender_id = ? AND receiver_id = ?) 
                   OR (sender_id = ? AND receiver_id = ?)
                ORDER BY id ASC
            ''', (current_user['id'], with_user_id, with_user_id, current_user['id']))
            msg_rows = cursor.fetchall()
            conn.close()

            chat_messages = [{
                'id': mr[0],
                'senderId': mr[1],
                'receiverId': mr[2],
                'text': mr[3],
                'time': mr[4],
                'isRead': bool(mr[5]),
                'isSentByMe': (mr[1] == current_user['id']),
                'isMe': (mr[1] == current_user['id'])
            } for mr in msg_rows]

            return self.send_json({'success': True, 'messages': chat_messages})

        # GET REAL-TIME TYPING STATUS API
        elif path == '/api/messages/typing':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)

            with_user_id = query_params.get('with', [None])[0]
            if not with_user_id:
                return self.send_json({'isTyping': False})

            try:
                target_id = int(with_user_id)
            except Exception:
                target_id = 0

            key = (target_id, current_user['id'])
            prune_typing_users()
            last_typed = ACTIVE_TYPING_USERS.get(key, 0)
            is_typing = (time.time() - last_typed) < 3.0
            return self.send_json({'success': True, 'isTyping': is_typing})

        # GET NOTIFICATIONS LIST API
        elif path == '/api/notifications':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)

            conn = get_db()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT n.id, n.notif_type, n.title, n.is_read, n.created_at, u.full_name, u.avatar_url 
                FROM notifications n 
                LEFT JOIN users u ON n.sender_id = u.id 
                WHERE n.user_id = ? 
                ORDER BY n.id DESC LIMIT 20
            ''', (current_user['id'],))
            n_rows = cursor.fetchall()

            cursor.execute('SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0', (current_user['id'],))
            unread_count = cursor.fetchone()[0]
            conn.close()

            notifications_list = [{
                'id': nr[0],
                'type': nr[1],
                'title': nr[2],
                'isRead': bool(nr[3]),
                'time': nr[4],
                'senderName': nr[5] or 'Community Alert',
                'senderAvatar': resolve_user_avatar(0, '', nr[5] or 'User', nr[6])
            } for nr in n_rows]

            return self.send_json({'success': True, 'notifications': notifications_list, 'unreadCount': unread_count})

        # GET USER ACTIVITY (MY UPLOADS & POSTS) API
        elif path == '/api/users/activity':
            current_user = self.get_auth_user()
            target_user_id = query_params.get('userId', [None])[0]
            user_id = target_user_id or (current_user['id'] if current_user else None)

            if not user_id:
                return self.send_json({'error': 'User ID required'}, 400)

            conn = get_db()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, content, media_url, created_at FROM posts 
                WHERE author_id = ? ORDER BY id DESC
            ''', (user_id,))
            p_rows = cursor.fetchall()
            posts_list = [{
                'id': pr[0],
                'content': pr[1],
                'media': pr[2],
                'time': pr[3]
            } for pr in p_rows]

            media_list = [{
                'postId': pr[0],
                'mediaUrl': pr[2]
            } for pr in p_rows if pr[2]]

            conn.close()
            return self.send_json({'success': True, 'posts': posts_list, 'media': media_list})

        # GET EVENTS LIST API
        elif path == '/api/events':
            current_user = self.get_auth_user()
            current_user_id = current_user['id'] if current_user else 0

            conn = get_db()
            cursor = conn.cursor()

            cursor.execute('SELECT id, title, organizer_name, date_str, location, description, banner_url FROM events ORDER BY id ASC')
            e_rows = cursor.fetchall()

            events_list = []
            for er in e_rows:
                e_id, title, org, date_s, loc, desc, banner = er
                cursor.execute('SELECT COUNT(*) FROM event_rsvps WHERE event_id = ?', (e_id,))
                rsvp_count = cursor.fetchone()[0]
                cursor.execute('SELECT id FROM event_rsvps WHERE event_id = ? AND user_id = ?', (e_id, current_user_id))
                is_attending = bool(cursor.fetchone())

                events_list.append({
                    'id': e_id,
                    'title': title,
                    'organizer': org,
                    'date': date_s,
                    'location': loc,
                    'description': desc,
                    'bannerUrl': banner,
                    'rsvps': rsvp_count,
                    'isAttending': is_attending
                })

            conn.close()
            return self.send_json({'success': True, 'events': events_list})

        # GET NETWORK CONNECTIONS & PENDING INVITATIONS API
        elif path == '/api/network/manage':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)

            conn = get_db()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT c.id, u.id, u.full_name, u.headline, u.avatar_url 
                FROM connections c 
                JOIN users u ON c.requester_id = u.id 
                WHERE c.receiver_id = ? AND c.status = 'PENDING'
            ''', (current_user['id'],))
            pending_rows = cursor.fetchall()
            pending_list = [{
                'connId': pr[0],
                'userId': pr[1],
                'fullName': pr[2],
                'headline': pr[3],
                'avatarUrl': resolve_user_avatar(pr[1], '', pr[2], pr[4])
            } for pr in pending_rows]

            cursor.execute('''
                SELECT u.id, u.full_name, u.headline, u.avatar_url 
                FROM connections c 
                JOIN users u ON (CASE WHEN c.requester_id = ? THEN c.receiver_id ELSE c.requester_id END) = u.id 
                WHERE (c.requester_id = ? OR c.receiver_id = ?) AND c.status = 'ACCEPTED' AND u.id != ?
            ''', (current_user['id'], current_user['id'], current_user['id'], current_user['id']))
            connected_rows = cursor.fetchall()
            connected_list = [{
                'userId': cr[0],
                'fullName': cr[1],
                'headline': cr[2],
                'avatarUrl': resolve_user_avatar(cr[0], '', cr[1], cr[3])
            } for cr in connected_rows]

            conn.close()
            return self.send_json({'success': True, 'pending': pending_list, 'connected': connected_list})

        # GET SAVED / BOOKMARKED POSTS API
        elif path == '/api/posts/saved':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.id, p.content, p.media_url, p.created_at, u.full_name, u.avatar_url 
                FROM saved_posts sp 
                JOIN posts p ON sp.post_id = p.id 
                JOIN users u ON p.author_id = u.id 
                WHERE sp.user_id = ? 
                ORDER BY sp.id DESC
            ''', (current_user['id'],))
            s_rows = cursor.fetchall()
            saved_list = [{
                'id': sr[0],
                'content': sr[1],
                'media': sr[2],
                'time': sr[3],
                'authorName': sr[4],
                'authorAvatar': resolve_user_avatar(0, '', sr[4], sr[5])
            } for sr in s_rows]

            conn.close()
            return self.send_json({'success': True, 'posts': saved_list})

        # GET ARTICLES LIST API
        elif path == '/api/articles':
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT a.id, a.title, a.content, a.cover_url, a.created_at, u.full_name, u.avatar_url 
                FROM articles a 
                JOIN users u ON a.author_id = u.id 
                ORDER BY a.id DESC
            ''')
            a_rows = cursor.fetchall()
            articles_list = [{
                'id': ar[0],
                'title': ar[1],
                'content': ar[2],
                'coverUrl': ar[3] or 'hero.jpg',
                'time': ar[4],
                'authorName': ar[5],
                'authorAvatar': resolve_user_avatar(0, '', ar[5], ar[6])
            } for ar in a_rows]

            conn.close()
            return self.send_json({'success': True, 'articles': articles_list})

        # GET USER ANALYTICS DASHBOARD METRICS API
        elif path == '/api/analytics':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)

            conn = get_db()
            cursor = conn.cursor()

            cursor.execute('SELECT COUNT(*) FROM posts WHERE author_id = ?', (current_user['id'],))
            posts_count = cursor.fetchone()[0]

            cursor.execute('''
                SELECT COUNT(*) FROM post_likes pl 
                JOIN posts p ON pl.post_id = p.id 
                WHERE p.author_id = ?
            ''', (current_user['id'],))
            likes_received = cursor.fetchone()[0]

            cursor.execute('''
                SELECT COUNT(*) FROM connections 
                WHERE (requester_id = ? OR receiver_id = ?) AND status = 'ACCEPTED'
            ''', (current_user['id'], current_user['id']))
            network_count = cursor.fetchone()[0]

            conn.close()

            return self.send_json({
                'success': True,
                'metrics': {
                    'profileViews': 142 + (posts_count * 15),
                    'postImpressions': 1890 + (likes_received * 45),
                    'totalPosts': posts_count,
                    'networkConnections': network_count
                }
            })

        # GET USER SETTINGS & PREFERENCES API
        elif path == '/api/settings':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT theme, language, privacy, message_privacy, connect_privacy, notifications_enabled FROM user_settings WHERE user_id = ?', (current_user['id'],))
            s_row = cursor.fetchone()

            if not s_row:
                cursor.execute('INSERT INTO user_settings (user_id) VALUES (?)', (current_user['id'],))
                conn.commit()
                theme, lang, priv, msg_priv, conn_priv, notif = 'light', 'en', 'public', 'everyone', 'everyone', 1
            else:
                theme, lang, priv, msg_priv, conn_priv, notif = s_row

            conn.close()
            return self.send_json({
                'success': True,
                'settings': {
                    'theme': theme,
                    'language': lang,
                    'privacy': priv,
                    'messagePrivacy': msg_priv or 'everyone',
                    'connectPrivacy': conn_priv or 'everyone',
                    'notificationsEnabled': bool(notif)
                }
            })

        # GET BLOCKED USERS LIST API
        elif path == '/api/settings/blocked':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT u.id, u.full_name, u.headline, u.avatar_url 
                FROM blocked_users bu 
                JOIN users u ON bu.blocked_user_id = u.id 
                WHERE bu.user_id = ?
            ''', (current_user['id'],))
            b_rows = cursor.fetchall()
            blocked_list = [{
                'userId': br[0],
                'fullName': br[1],
                'headline': br[2],
                'avatarUrl': resolve_user_avatar(br[0], '', br[1], br[3])
            } for br in b_rows]

            conn.close()
            return self.send_json({'success': True, 'blocked': blocked_list})

        # GET MUTED USERS LIST API
        elif path == '/api/settings/muted':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT u.id, u.full_name, u.headline, u.avatar_url 
                FROM muted_users mu 
                JOIN users u ON mu.muted_user_id = u.id 
                WHERE mu.user_id = ?
            ''', (current_user['id'],))
            m_rows = cursor.fetchall()
            muted_list = [{
                'userId': mr[0],
                'fullName': mr[1],
                'headline': mr[2],
                'avatarUrl': resolve_user_avatar(mr[0], '', mr[1], mr[3])
            } for mr in m_rows]

            conn.close()
            return self.send_json({'success': True, 'muted': muted_list})

        # GET FULL PROFESSIONAL PROFILE API (Skills, Education, Experience, Projects, Certs)
        elif path == '/api/profile/full':
            current_user = self.get_auth_user()
            target_user_id = query_params.get('userId', [None])[0]
            user_id = target_user_id or (current_user['id'] if current_user else None)

            if not user_id:
                return self.send_json({'error': 'User ID required'}, 400)

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT id, email, full_name, headline, avatar_url, bio, location, email_verified FROM users WHERE id = ?', (user_id,))
            u_row = cursor.fetchone()

            if not u_row:
                conn.close()
                return self.send_json({'error': 'User not found'}, 404)

            # Check privacy settings
            cursor.execute('SELECT privacy FROM user_settings WHERE user_id = ?', (user_id,))
            priv_row = cursor.fetchone()
            privacy_setting = priv_row[0] if priv_row else 'public'

            current_user_id = current_user['id'] if current_user else 0
            # Check connection status if not owner
            conn_status = 'NONE'
            if current_user_id and current_user_id != user_id:
                cursor.execute('''
                    SELECT status FROM connections 
                    WHERE (requester_id = ? AND receiver_id = ?) 
                       OR (requester_id = ? AND receiver_id = ?)
                ''', (current_user_id, user_id, user_id, current_user_id))
                c_row = cursor.fetchone()
                if c_row:
                    conn_status = c_row[0]

            # Check if viewer is blocked by target user or target user is blocked by viewer
            if current_user_id and current_user_id != user_id:
                cursor.execute('''
                    SELECT id FROM blocked_users
                    WHERE (user_id = ? AND blocked_user_id = ?)
                       OR (user_id = ? AND blocked_user_id = ?)
                ''', (current_user_id, user_id, user_id, current_user_id))
                if cursor.fetchone():
                    conn.close()
                    return self.send_json({'error': 'Profile unavailable'}, 403)

            # Backend Privacy Enforcement: Mask sensitive fields if viewer does not have access
            is_owner = (current_user_id == user_id)
            is_connected = (conn_status == 'ACCEPTED')
            has_full_access = is_owner or (privacy_setting == 'public') or (privacy_setting == 'connections' and is_connected)

            if not has_full_access:
                # Privacy-restricted response: Hide email, education, experience, projects, certs
                conn.close()
                return self.send_json({
                    'success': True,
                    'profile': {
                        'id': u_row[0],
                        'email': 'Hidden (Privacy Protected)',
                        'fullName': u_row[2],
                        'headline': u_row[3],
                        'avatarUrl': resolve_user_avatar(u_row[0], u_row[1], u_row[2], u_row[4]),
                        'bio': 'Profile details are restricted to confirmed connections.',
                        'location': '',
                        'emailVerified': bool(u_row[7]),
                        'privacy': privacy_setting,
                        'skills': [],
                        'education': [],
                        'experience': [],
                        'projects': [],
                        'certifications': [],
                        'isRestricted': True
                    }
                })

            # Skills
            cursor.execute('SELECT skill_name FROM profile_skills WHERE user_id = ?', (user_id,))
            skills = [r[0] for r in cursor.fetchall()]

            # Education
            cursor.execute('SELECT id, institution, degree, field_of_study, start_year, end_year, description FROM profile_education WHERE user_id = ?', (user_id,))
            education = [{'id': r[0], 'institution': r[1], 'degree': r[2], 'field': r[3], 'startYear': r[4], 'endYear': r[5], 'description': r[6]} for r in cursor.fetchall()]

            # Experience
            cursor.execute('SELECT id, company, position, location, start_date, end_date, is_current, description FROM profile_experience WHERE user_id = ?', (user_id,))
            experience = [{'id': r[0], 'company': r[1], 'position': r[2], 'location': r[3], 'startDate': r[4], 'endDate': r[5], 'isCurrent': bool(r[6]), 'description': r[7]} for r in cursor.fetchall()]

            # Projects
            cursor.execute('SELECT id, project_name, description, technologies, project_url, github_url FROM profile_projects WHERE user_id = ?', (user_id,))
            projects = [{'id': r[0], 'projectName': r[1], 'description': r[2], 'technologies': r[3], 'projectUrl': r[4], 'githubUrl': r[5]} for r in cursor.fetchall()]

            # Certifications
            cursor.execute('SELECT id, cert_name, issuing_org, issue_date, credential_id, credential_url FROM profile_certifications WHERE user_id = ?', (user_id,))
            certs = [{'id': r[0], 'certName': r[1], 'issuingOrg': r[2], 'issueDate': r[3], 'credentialId': r[4], 'credentialUrl': r[5]} for r in cursor.fetchall()]

            conn.close()

            return self.send_json({
                'success': True,
                'profile': {
                    'id': u_row[0],
                    'email': u_row[1],
                    'fullName': u_row[2],
                    'headline': u_row[3],
                    'avatarUrl': resolve_user_avatar(u_row[0], u_row[1], u_row[2], u_row[4]),
                    'bio': u_row[5],
                    'location': u_row[6] or '',
                    'emailVerified': bool(u_row[7]),
                    'privacy': privacy_setting,
                    'skills': skills,
                    'education': education,
                    'experience': experience,
                    'projects': projects,
                    'certifications': certs,
                    'isRestricted': False
                }
            })

        # GET WORKFLOW STATUS BOARD & BUG TRACKER LIST API
        elif path == '/api/workflow/bugs':
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT id, module, title, priority, status, fix_date, regression_status FROM issue_bugs ORDER BY id ASC')
            b_rows = cursor.fetchall()

            bugs_list = [{
                'id': br[0],
                'module': br[1],
                'title': br[2],
                'priority': br[3],
                'status': br[4],
                'fixDate': br[5],
                'regressionStatus': br[6]
            } for br in b_rows]

            conn.close()
            return self.send_json({'success': True, 'bugs': bugs_list})

        # GET ADMIN SYSTEM OVERVIEW STATS API
        elif path == '/api/admin/overview':
            current_user = self.get_auth_user()
            if not current_user or not current_user.get('isAdmin'):
                return self.send_json({'error': 'Admin privilege required'}, 403)

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM users')
            total_users = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM posts')
            total_posts = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM direct_messages')
            total_messages = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM reports WHERE status = "PENDING"')
            pending_reports = cursor.fetchone()[0]
            conn.close()

            return self.send_json({
                'success': True,
                'overview': {
                    'totalUsers': total_users,
                    'totalPosts': total_posts,
                    'totalMessages': total_messages,
                    'pendingReports': pending_reports
                }
            })

        # GET ADMIN SYSTEM HEALTH & OBSERVABILITY API
        elif path == '/api/admin/health':
            current_user = self.get_auth_user()
            if not current_user or not current_user.get('isAdmin'):
                return self.send_json({'error': 'Admin privilege required'}, 403)

            health_status = {
                'database': 'UNKNOWN',
                'uploads': 'UNKNOWN',
                'backups': 'UNKNOWN',
                'authSessions': 'UNKNOWN',
                'messaging': 'UNKNOWN',
                'timestamp': datetime.now().isoformat()
            }

            try:
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute('SELECT 1')
                health_status['database'] = 'HEALTHY'
                
                cursor.execute('SELECT COUNT(*) FROM sessions')
                active_sessions = cursor.fetchone()[0]
                health_status['authSessions'] = f'HEALTHY ({active_sessions} active)'
                
                conn.close()
            except Exception as e:
                health_status['database'] = f'ERROR: {str(e)}'

            if os.path.exists(UPLOADS_DIR) and os.access(UPLOADS_DIR, os.W_OK):
                health_status['uploads'] = 'HEALTHY'
            else:
                health_status['uploads'] = 'UNHEALTHY'

            if os.path.exists(BACKUP_DIR):
                health_status['backups'] = 'HEALTHY'
            else:
                health_status['backups'] = 'UNCONFIGURED'

            health_status['messaging'] = 'HEALTHY (500ms real-time diff polling)'

            return self.send_json({'success': True, 'health': health_status})

        # GET ADMIN ALL USERS LIST API
        elif path == '/api/admin/users':
            current_user = self.get_auth_user()
            if not current_user or not current_user.get('isAdmin'):
                return self.send_json({'error': 'Admin privilege required'}, 403)

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT id, email, full_name, headline, avatar_url, is_admin, status, created_at FROM users ORDER BY id ASC')
            rows = cursor.fetchall()
            conn.close()

            users_list = [{
                'id': r[0],
                'email': r[1],
                'fullName': r[2],
                'headline': r[3],
                'avatarUrl': r[4] or 'hero.jpg',
                'isAdmin': bool(r[5]),
                'status': r[6],
                'createdAt': r[7]
            } for r in rows]

            return self.send_json({'success': True, 'users': users_list})

        # GET ADMIN MODERATION REPORTS LIST API
        elif path == '/api/admin/reports':
            current_user = self.get_auth_user()
            if not current_user or not current_user.get('isAdmin'):
                return self.send_json({'error': 'Admin privilege required'}, 403)

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT r.id, r.target_type, r.target_id, r.reason, r.status, r.created_at, u.full_name 
                FROM reports r 
                JOIN users u ON r.reporter_id = u.id 
                ORDER BY r.id DESC
            ''')
            rows = cursor.fetchall()
            conn.close()

            reports_list = [{
                'id': r[0],
                'targetType': r[1],
                'targetId': r[2],
                'reason': r[3],
                'status': r[4],
                'createdAt': r[5],
                'reporterName': r[6]
            } for r in rows]

            return self.send_json({'success': True, 'reports': reports_list})

        # GET ADMIN SECURITY LOGIN HISTORY API
        elif path == '/api/admin/login-history':
            current_user = self.get_auth_user()
            if not current_user or not current_user.get('isAdmin'):
                return self.send_json({'error': 'Admin privilege required'}, 403)

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT lh.id, u.full_name, u.email, lh.ip_address, lh.status, lh.login_time 
                FROM login_history lh 
                JOIN users u ON lh.user_id = u.id 
                ORDER BY lh.id DESC LIMIT 20
            ''')
            rows = cursor.fetchall()
            conn.close()

            history_list = [{
                'id': r[0],
                'fullName': r[1],
                'email': r[2],
                'ipAddress': r[3],
                'status': r[4],
                'loginTime': r[5]
            } for r in rows]

            return self.send_json({'success': True, 'history': history_list})

        # AUTH SESSION API
        elif path == '/api/auth/me':
            user = self.get_auth_user()
            if user:
                return self.send_json({'success': True, 'user': user})
            else:
                return self.send_json({'error': 'Unauthorized'}, 401)

        # ENHANCED GLOBAL CATEGORIZED SEARCH API (People, Posts, Hashtags, Events)
        elif path == '/api/users/search':
            raw_q = query_params.get('q', [''])[0].strip()
            query = raw_q.lower().lstrip('#')
            current_user = self.get_auth_user()
            current_user_id = current_user['id'] if current_user else 0

            conn = get_db()
            cursor = conn.cursor()

            people_results = []
            hashtag_results = []
            post_results = []
            event_results = []

            if query:
                # People (filter out blocked users)
                cursor.execute('''
                    SELECT id, full_name, headline, avatar_url, email 
                    FROM users 
                    WHERE (LOWER(full_name) LIKE ? OR LOWER(headline) LIKE ? OR LOWER(email) LIKE ?)
                    AND id != ?
                    AND id NOT IN (
                        SELECT blocked_user_id FROM blocked_users WHERE user_id = ?
                        UNION
                        SELECT user_id FROM blocked_users WHERE blocked_user_id = ?
                    )
                    ORDER BY id DESC
                    LIMIT 25
                ''', (f'%{query}%', f'%{query}%', f'%{query}%', current_user_id, current_user_id, current_user_id))
                rows = cursor.fetchall()
                people_results = [{
                    'id': r[0],
                    'fullName': r[1],
                    'headline': r[2],
                    'avatarUrl': resolve_user_avatar(r[0], r[4], r[1], r[3]),
                    'email': r[4]
                } for r in rows]

                # Hashtags
                cursor.execute('''
                    SELECT h.tag, COUNT(ph.post_id) as post_count
                    FROM hashtags h
                    LEFT JOIN post_hashtags ph ON h.id = ph.hashtag_id
                    WHERE LOWER(h.tag) LIKE ?
                    GROUP BY h.id
                    LIMIT 6
                ''', (f'%{query}%',))
                ht_rows = cursor.fetchall()
                hashtag_results = [{
                    'tag': h[0],
                    'count': h[1]
                } for h in ht_rows]

                # Posts (filter out blocked/muted authors)
                cursor.execute('''
                    SELECT p.id, p.content, p.media_url, u.full_name, u.avatar_url, u.email, u.id
                    FROM posts p
                    JOIN users u ON p.author_id = u.id
                    WHERE LOWER(p.content) LIKE ?
                    AND u.id NOT IN (
                        SELECT blocked_user_id FROM blocked_users WHERE user_id = ?
                        UNION
                        SELECT user_id FROM blocked_users WHERE blocked_user_id = ?
                        UNION
                        SELECT muted_user_id FROM muted_users WHERE user_id = ?
                    )
                    ORDER BY p.id DESC LIMIT 5
                ''', (f'%{query}%', current_user_id, current_user_id, current_user_id))
                p_rows = cursor.fetchall()
                post_results = [{
                    'id': pr[0],
                    'content': pr[1],
                    'media': pr[2],
                    'authorName': pr[3],
                    'avatar': resolve_user_avatar(pr[6], pr[5], pr[3], pr[4])
                } for pr in p_rows]

                # Events
                cursor.execute('''
                    SELECT id, title, organizer_name, date_str, location, description, banner_url
                    FROM events
                    WHERE LOWER(title) LIKE ? OR LOWER(description) LIKE ? OR LOWER(location) LIKE ?
                    ORDER BY id DESC LIMIT 5
                ''', (f'%{query}%', f'%{query}%', f'%{query}%'))
                e_rows = cursor.fetchall()
                event_results = [{
                    'id': er[0],
                    'title': er[1],
                    'organizer': er[2],
                    'date': er[3],
                    'location': er[4],
                    'description': er[5],
                    'bannerUrl': er[6] or 'hero.jpg'
                } for er in e_rows]

            conn.close()

            return self.send_json({
                'success': True,
                'users': people_results,
                'hashtags': hashtag_results,
                'posts': post_results,
                'events': event_results
            })

        # TRENDING HASHTAGS API
        elif path == '/api/hashtags/trending':
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT h.tag, COUNT(ph.post_id) as post_count
                FROM hashtags h
                JOIN post_hashtags ph ON h.id = ph.hashtag_id
                GROUP BY h.id
                ORDER BY post_count DESC, h.id DESC
                LIMIT 10
            ''')
            rows = cursor.fetchall()
            conn.close()
            trending = [{'tag': r[0], 'count': r[1]} for r in rows]
            return self.send_json({'success': True, 'trending': trending})

        # HASHTAG DISCOVERY DETAILS & POST STREAM API
        elif path == '/api/hashtags/discovery':
            tag_name = query_params.get('tag', [''])[0].strip().lower().lstrip('#')
            if not tag_name:
                return self.send_json({'error': 'tag is required'}, 400)

            current_user = self.get_auth_user()
            current_user_id = current_user['id'] if current_user else 0

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT id, tag FROM hashtags WHERE LOWER(tag) = ?', (tag_name,))
            h_row = cursor.fetchone()

            if not h_row:
                conn.close()
                return self.send_json({'success': True, 'tag': tag_name, 'postCount': 0, 'posts': [], 'members': []})

            hashtag_id = h_row[0]
            cursor.execute('''
                SELECT p.id, p.author_id, p.content, p.media_url, p.created_at, u.full_name, u.avatar_url, u.headline, u.email
                FROM posts p
                JOIN post_hashtags ph ON p.id = ph.post_id
                JOIN users u ON p.author_id = u.id
                WHERE ph.hashtag_id = ?
                ORDER BY p.id DESC
            ''', (hashtag_id,))
            p_rows = cursor.fetchall()

            posts = []
            for pr in p_rows:
                post_id, author_id, content, media_url, created_at, full_name, avatar_url, headline, email = pr
                cursor.execute('SELECT COUNT(*) FROM post_likes WHERE post_id = ?', (post_id,))
                likes_cnt = cursor.fetchone()[0]
                cursor.execute('SELECT COUNT(*) FROM post_comments WHERE post_id = ?', (post_id,))
                comments_cnt = cursor.fetchone()[0]
                cursor.execute('SELECT id FROM post_likes WHERE post_id = ? AND user_id = ?', (post_id, current_user_id))
                is_liked = bool(cursor.fetchone())

                posts.append({
                    'id': post_id,
                    'authorId': author_id,
                    'authorName': full_name,
                    'authorRole': headline or 'Community Member',
                    'avatar': resolve_user_avatar(author_id, email, full_name, avatar_url),
                    'content': content,
                    'media': media_url,
                    'time': created_at,
                    'likes': likes_cnt,
                    'commentsCount': comments_cnt,
                    'isLiked': is_liked
                })

            conn.close()
            return self.send_json({
                'success': True,
                'tag': tag_name,
                'postCount': len(posts),
                'posts': posts
            })

        # MENTION AUTOCOMPLETE SUGGESTIONS API
        elif path == '/api/users/mention-suggestions':
            query = query_params.get('q', [''])[0].strip().lower().lstrip('@')
            conn = get_db()
            cursor = conn.cursor()
            if query:
                cursor.execute('''
                    SELECT id, full_name, headline, avatar_url, email
                    FROM users
                    WHERE (LOWER(full_name) LIKE ? OR LOWER(email) LIKE ?)
                    ORDER BY id DESC
                    LIMIT 20
                ''', (f'%{query}%', f'%{query}%'))
            else:
                cursor.execute('SELECT id, full_name, headline, avatar_url, email FROM users ORDER BY id DESC LIMIT 20')
            rows = cursor.fetchall()
            conn.close()
            suggestions = [{
                'id': r[0],
                'fullName': r[1],
                'headline': r[2],
                'avatarUrl': resolve_user_avatar(r[0], r[4], r[1], r[3])
            } for r in rows]
            return self.send_json({'success': True, 'suggestions': suggestions})

        # USER NETWORK SUGGESTIONS API
        elif path == '/api/users/suggestions':
            current_user = self.get_auth_user()
            current_user_id = current_user['id'] if current_user else 0

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, full_name, headline, avatar_url, email 
                FROM users 
                WHERE id != ?
                ORDER BY id DESC LIMIT 5
            ''', (current_user_id,))
            rows = cursor.fetchall()
            conn.close()

            suggestions = [{
                'id': r[0],
                'fullName': r[1],
                'headline': r[2],
                'avatarUrl': resolve_user_avatar(r[0], r[4], r[1], r[3])
            } for r in rows]

            return self.send_json({'success': True, 'suggestions': suggestions})

        # USER PUBLIC PROFILE API
        elif path.startswith('/api/users/profile/'):
            try:
                target_user_id = int(path.split('/')[-1])
            except ValueError:
                return self.send_json({'error': 'Invalid user ID'}, 400)

            current_user = self.get_auth_user()
            current_user_id = current_user['id'] if current_user else 0

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, full_name, headline, avatar_url, bio, email, created_at 
                FROM users WHERE id = ?
            ''', (target_user_id,))
            row = cursor.fetchone()

            if not row:
                conn.close()
                return self.send_json({'error': 'User not found'}, 404)

            cursor.execute('''
                SELECT status FROM connections 
                WHERE (requester_id = ? AND receiver_id = ?) 
                   OR (requester_id = ? AND receiver_id = ?)
            ''', (current_user_id, target_user_id, target_user_id, current_user_id))
            conn_row = cursor.fetchone()

            cursor.execute('''
                SELECT id FROM blocked_users
                WHERE (user_id = ? AND blocked_user_id = ?)
                   OR (user_id = ? AND blocked_user_id = ?)
            ''', (current_user_id, target_user_id, target_user_id, current_user_id))
            if cursor.fetchone():
                conn.close()
                return self.send_json({'error': 'User profile unavailable'}, 403)

            # Derive connection status early (must be before privacy check)
            conn_status = conn_row[0] if conn_row else 'NONE'

            # Check target user privacy settings
            cursor.execute('SELECT privacy FROM user_settings WHERE user_id = ?', (target_user_id,))
            priv_row = cursor.fetchone()
            target_privacy = priv_row[0] if priv_row else 'public'

            # If target has privacy set to 'connections' and requester is not connected/self
            if target_privacy in ('connections', 'private') and current_user_id != target_user_id:
                if conn_status != 'ACCEPTED':
                    conn.close()
                    return self.send_json({
                        'success': True,
                        'user': {
                            'id': row[0],
                            'fullName': row[1],
                            'headline': row[2],
                            'avatarUrl': resolve_user_avatar(row[0], row[5], row[1], row[3]),
                            'bio': 'Profile details are visible to confirmed connections only.',
                            'email': 'Hidden',
                            'createdAt': row[6],
                            'connectionStatus': conn_status,
                            'isRestricted': True
                        },
                        'profile': {
                            'id': row[0],
                            'fullName': row[1],
                            'headline': row[2],
                            'avatarUrl': resolve_user_avatar(row[0], row[5], row[1], row[3]),
                            'bio': 'Profile details are visible to confirmed connections only.',
                            'email': 'Hidden',
                            'createdAt': row[6],
                            'connectionStatus': conn_status,
                            'isRestricted': True
                        }
                    })

            if current_user_id and current_user_id != target_user_id:
                cursor.execute('''
                    INSERT INTO notifications (user_id, sender_id, notif_type, title)
                    VALUES (?, ?, 'PROFILE_VIEW', 'viewed your profile.')
                ''', (target_user_id, current_user_id))
                conn.commit()

            conn.close()
            user_dict = {
                'id': row[0],
                'fullName': row[1],
                'headline': row[2],
                'avatarUrl': resolve_user_avatar(row[0], row[5], row[1], row[3]),
                'bio': row[4],
                'email': row[5],
                'createdAt': row[6],
                'connectionStatus': conn_status
            }
            return self.send_json({
                'success': True,
                'user': user_dict,
                'profile': user_dict
            })

        # =====================================================================
        # RAPIDO GET ENDPOINTS
        # =====================================================================
        elif path == '/api/rapido/rides':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)
            
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, user_id, pickup, dropoff, vehicle_type, fare, status, captain_name, captain_rating, rating, comments, created_at
                FROM rapido_rides
                WHERE user_id = ?
                ORDER BY id DESC
            ''', (current_user['id'],))
            rows = cursor.fetchall()
            conn.close()
            
            rides = [{
                'id': r[0],
                'user_id': r[1],
                'pickup': r[2],
                'dropoff': r[3],
                'vehicle_type': r[4],
                'fare': r[5],
                'status': r[6],
                'captain_name': r[7],
                'captain_rating': r[8],
                'rating': r[9],
                'comments': r[10],
                'created_at': r[11]
            } for r in rows]
            
            return self.send_json({'success': True, 'rides': rides})

        elif path == '/api/rapido/driver/stats':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)
            
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT is_online, total_earnings, total_rides FROM rapido_driver_stats WHERE user_id = ?', (current_user['id'],))
            row = cursor.fetchone()
            if not row:
                cursor.execute('INSERT INTO rapido_driver_stats (user_id, is_online, total_earnings, total_rides) VALUES (?, 0, 0.0, 0)', (current_user['id'],))
                conn.commit()
                row = (0, 0.0, 0)
            conn.close()
            
            return self.send_json({
                'success': True,
                'stats': {
                    'is_online': bool(row[0]),
                    'total_earnings': row[1],
                    'total_rides': row[2]
                }
            })

        elif path == '/api/rapido/ride-status':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)
            
            ride_id_list = query_params.get('ride_id')
            if not ride_id_list or not ride_id_list[0]:
                return self.send_json({'error': 'Missing ride_id'}, 400)
            ride_id = ride_id_list[0]
            
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, user_id, pickup, dropoff, vehicle_type, fare, status, captain_name, captain_rating, otp, vehicle_number, driver_coords_x, driver_coords_y, driver_angle, driver_id
                FROM rapido_rides
                WHERE id = ?
            ''', (ride_id,))
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return self.send_json({'error': 'Ride not found'}, 404)
            
            return self.send_json({
                'success': True,
                'ride': {
                    'id': row[0],
                    'user_id': row[1],
                    'pickup': row[2],
                    'dropoff': row[3],
                    'vehicle_type': row[4],
                    'fare': row[5],
                    'status': row[6],
                    'captain_name': row[7],
                    'captain_rating': row[8],
                    'otp': row[9],
                    'vehicle_number': row[10],
                    'driver_coords_x': row[11],
                    'driver_coords_y': row[12],
                    'driver_angle': row[13],
                    'driver_id': row[14]
                }
            })

        elif path == '/api/rapido/driver/offers':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)
            
            conn = get_db()
            cursor = conn.cursor()
            # Driver can see pending rides booked by other users
            cursor.execute('''
                SELECT id, user_id, pickup, dropoff, vehicle_type, fare, status, otp
                FROM rapido_rides
                WHERE status = 'PENDING' AND user_id != ?
                ORDER BY id DESC
            ''', (current_user['id'],))
            rows = cursor.fetchall()
            conn.close()
            
            offers = [{
                'id': r[0],
                'user_id': r[1],
                'pickup': r[2],
                'dropoff': r[3],
                'vehicle_type': r[4],
                'fare': r[5],
                'status': r[6],
                'otp': r[7]
            } for r in rows]
            
            return self.send_json({'success': True, 'offers': offers})

        elif path == '/api/rapido/chat/messages':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)
            
            ride_id_list = query_params.get('ride_id')
            if not ride_id_list or not ride_id_list[0]:
                return self.send_json({'error': 'Missing ride_id'}, 400)
            ride_id = ride_id_list[0]
            
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, ride_id, sender_id, sender_name, message, created_at
                FROM rapido_chats
                WHERE ride_id = ?
                ORDER BY id ASC
            ''', (ride_id,))
            rows = cursor.fetchall()
            conn.close()
            
            messages = [{
                'id': r[0],
                'ride_id': r[1],
                'sender_id': r[2],
                'sender_name': r[3],
                'message': r[4],
                'created_at': r[5]
            } for r in rows]
            
            return self.send_json({'success': True, 'messages': messages})

        return self.send_json({'error': 'Endpoint not found'}, 404)

    def do_POST(self):
        try:
            self._handle_POST()
        except Exception as e:
            try:
                log_audit_event('ERROR', f'Unhandled POST exception: {e}', method='POST', path=self.path, status_code=500)
                self.send_json({'error': 'Internal server error'}, 500)
            except Exception:
                pass

    def _handle_POST(self):
        url_parts = urllib.parse.urlparse(self.path)
        path = url_parts.path

        # Central throttle - applies to every POST route, not just auth
        client_ip = self.client_address[0] if self.client_address else 'unknown'
        max_requests, window_seconds = rate_limit_budget_for(path)
        allowed, retry_after = check_rate_limit(
            client_ip, path, max_requests=max_requests, window_seconds=window_seconds
        )
        if not allowed:
            log_audit_event('WARN', f'Rate limit exceeded for {path}',
                            method='POST', path=path, status_code=429)
            self.send_response(429)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Retry-After', str(retry_after))
            body = json.dumps({'error': 'Too many requests. Please slow down.',
                               'retryAfter': retry_after}).encode('utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        
        # A caller-declared Content-Length was read straight into memory with no
        # ceiling, so a single request claiming a huge body could exhaust RAM.
        # Malformed values also raised ValueError and returned a 500.
        MAX_REQUEST_BODY = 12 * 1024 * 1024  # 12 MB - comfortably above image uploads
        try:
            content_length = int(self.headers.get('Content-Length', 0))
        except (TypeError, ValueError):
            return self.send_json({'error': 'Invalid Content-Length'}, 400)
        if content_length < 0:
            return self.send_json({'error': 'Invalid Content-Length'}, 400)
        if content_length > MAX_REQUEST_BODY:
            return self.send_json({'error': 'Payload too large'}, 413)
        post_data = self.rfile.read(content_length) if content_length > 0 else b'{}'
        
        try:
            payload = json.loads(post_data.decode('utf-8'))
        except Exception:
            payload = {}

        client_ip = self.client_address[0] if self.client_address else '127.0.0.1'

        # Rate limit sensitive authentication endpoints to prevent brute-force attacks
        if path in ['/api/auth/login', '/api/auth/signup', '/api/auth/google', '/api/auth/forgot-password']:
            allowed, retry_after = check_rate_limit(client_ip, 'auth', max_requests=30, window_seconds=60)
            if not allowed:
                return self.send_json({
                    'error': f'Too many authentication requests. Please retry in {retry_after} seconds.',
                    'retryAfter': retry_after
                }, 429)

        # 1. SIGNUP API (JWT Issuance)
        if path == '/api/auth/signup':
            email = payload.get('email', '').strip().lower()
            password = payload.get('password', '')
            full_name = payload.get('fullName', '').strip()
            headline = payload.get('headline', 'Community Member').strip()

            if not email or not password or not full_name:
                return self.send_json({'error': 'Email, password, and full name required'}, 400)

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
            if cursor.fetchone():
                conn.close()
                return self.send_json({'error': 'Email already registered'}, 400)

            pass_hash = hash_password(password)
            default_avatar = generate_default_avatar(full_name)
            cursor.execute('''
                INSERT INTO users (email, password_hash, full_name, headline, avatar_url)
                VALUES (?, ?, ?, ?, ?)
            ''', (email, pass_hash, full_name, headline, default_avatar))
            user_id = cursor.lastrowid

            token = generate_jwt(
                user_id=user_id,
                email=email,
                role='USER',
                is_admin=False,
                full_name=full_name
            )
            cursor.execute('INSERT INTO sessions (token, user_id) VALUES (?, ?)', (token, user_id))
            conn.commit()
            conn.close()

            return self.send_json({
                'success': True,
                'token': token,
                'token_type': 'Bearer',
                'expires_in': 86400,
                'user': {
                    'id': user_id,
                    'email': email,
                    'fullName': full_name,
                    'headline': headline,
                    'avatarUrl': default_avatar
                }
            })

        # 2. LOGIN API (Cryptographic JWT Issuance)
        elif path == '/api/auth/login':
            email = payload.get('email', '').strip().lower()
            password = payload.get('password', '')

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, email, full_name, headline, avatar_url, is_admin, status, password_hash 
                FROM users WHERE email = ?
            ''', (email,))
            row = cursor.fetchone()

            if not row or not verify_password(row[7], password):
                conn.close()
                log_audit_event('WARN', f"Failed login attempt for email: {email}")
                return self.send_json({'error': 'Invalid email or password'}, 401)

            if row[6] == 'BANNED':
                conn.close()
                log_audit_event('WARN', f"Blocked login attempt from suspended account: {email}")
                return self.send_json({'error': 'Account is suspended'}, 403)

            user_id = row[0]
            is_admin = bool(row[5])

            # Upgrade legacy SHA-256 hash to PBKDF2 on successful login
            current_hash = row[7]
            if not current_hash or not current_hash.startswith("pbkdf2:"):
                new_pbkdf2_hash = hash_password(password)
                cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (new_pbkdf2_hash, user_id))

            # In production deployment, flag default demo password change requirement
            is_prod = os.environ.get('APP_ENV', '').lower() == 'production'
            require_pass_change = False
            if is_prod and is_admin and password == 'demo1234':
                require_pass_change = True

            token = generate_jwt(
                user_id=user_id,
                email=row[1],
                role='SUPER_ADMINISTRATOR' if is_admin else 'USER',
                is_admin=is_admin,
                full_name=row[2]
            )
            cursor.execute('INSERT INTO sessions (token, user_id) VALUES (?, ?)', (token, user_id))
            cursor.execute('INSERT INTO login_history (user_id, status) VALUES (?, "SUCCESS")', (user_id,))
            conn.commit()
            conn.close()

            log_audit_event('INFO', f"User authenticated successfully via JWT: {email} (ID: {user_id})")

            return self.send_json({
                'success': True,
                'token': token,
                'token_type': 'Bearer',
                'expires_in': 86400,
                'requirePasswordChange': require_pass_change,
                'user': {
                    'id': user_id,
                    'email': row[1],
                    'fullName': row[2],
                    'headline': row[3],
                    'avatarUrl': row[4] or generate_default_avatar(row[2]),
                    'isAdmin': is_admin,
                    'role': 'SUPER_ADMINISTRATOR' if is_admin else 'USER'
                }
            })

        # 3. GOOGLE AUTHENTICATION API (JWT Issuance)
        elif path == '/api/auth/google':
            google_client_id = os.environ.get('GOOGLE_CLIENT_ID', '').strip()
            if not google_client_id:
                return self.send_json({'error': 'Google Client ID is not configured on the server.'}, 500)

            token = payload.get('credential')
            if not token:
                return self.send_json({'error': 'Missing Google ID token credential.'}, 400)

            # Cryptographically verify the token against Google
            try:
                from google.oauth2 import id_token as google_id_token
                from google.auth.transport import requests as google_requests
                
                # Verify token signature, audience, and expiration
                idinfo = google_id_token.verify_oauth2_token(
                    token,
                    google_requests.Request(),
                    google_client_id
                )
                
                # Output verified Google payload to stdout console and logs
                print(f"\n[REAL GOOGLE OIDC VERIFIED PAYLOAD] {json.dumps(idinfo, indent=2)}\n", flush=True)
                log_audit_event('INFO', f"Google OAuth token verified successfully for: {idinfo.get('email')}", method='POST', path=path)
                
                # Check issuer is Google
                if idinfo.get('iss') not in ['accounts.google.com', 'https://accounts.google.com']:
                    return self.send_json({'error': 'Token has an invalid issuer.'}, 401)
                    
                # Check email_verified claim
                if not idinfo.get('email_verified'):
                    return self.send_json({'error': 'Google email is not verified.'}, 401)
                    
            except ValueError as e:
                return self.send_json({'error': f'Google ID Token verification failed: {str(e)}'}, 401)
            except Exception as e:
                return self.send_json({'error': f'Google API connection error: {str(e)}'}, 500)

            # Extract verified fields
            email = idinfo.get('email', '').strip().lower()
            name = idinfo.get('name', 'Google Member').strip()
            google_id = idinfo.get('sub') # stable Google User ID
            picture = idinfo.get('picture', '') # Google profile avatar

            if not email or not google_id:
                return self.send_json({'error': 'OIDC payload is missing required claims (email/sub)'}, 401)

            conn = get_db()
            cursor = conn.cursor()
            
            # Lookup 1: By google_id
            cursor.execute('SELECT id, email, full_name, headline, avatar_url, is_admin, google_id FROM users WHERE google_id = ?', (google_id,))
            row = cursor.fetchone()
            
            if row:
                user_id = row[0]
                user_name = row[2]
                headline = row[3]
                avatar_url = row[4] or picture or generate_default_avatar(user_name)
                is_admin = bool(row[5])
            else:
                # Lookup 2: By email
                cursor.execute('SELECT id, email, full_name, headline, avatar_url, is_admin, google_id FROM users WHERE email = ?', (email,))
                email_row = cursor.fetchone()
                
                if email_row:
                    user_id = email_row[0]
                    user_name = email_row[2]
                    headline = email_row[3]
                    avatar_url = email_row[4] or picture or generate_default_avatar(user_name)
                    is_admin = bool(email_row[5])
                    
                    # Update row to link the google_id
                    cursor.execute('UPDATE users SET google_id = ? WHERE id = ?', (google_id, user_id))
                else:
                    # Lookup 3: Create new user record
                    default_avatar = picture if picture else generate_default_avatar(name)
                    cursor.execute('''
                        INSERT INTO users (email, google_id, full_name, headline, avatar_url)
                        VALUES (?, ?, ?, 'Community Member', ?)
                    ''', (email, google_id, name, default_avatar))
                    user_id = cursor.lastrowid
                    user_name = name
                    headline = 'Community Member'
                    avatar_url = default_avatar
                    is_admin = False

            # Create session and issue cryptographic JWT
            token = generate_jwt(
                user_id=user_id,
                email=email,
                role='USER',
                is_admin=is_admin,
                full_name=user_name
            )
            cursor.execute('INSERT INTO sessions (token, user_id) VALUES (?, ?)', (token, user_id))
            conn.commit()
            conn.close()

            return self.send_json({
                'success': True,
                'token': token,
                'token_type': 'Bearer',
                'expires_in': 86400,
                'authMode': 'GOOGLE_OIDC',
                'user': {
                    'id': user_id,
                    'email': email,
                    'fullName': user_name,
                    'headline': headline,
                    'avatarUrl': avatar_url,
                    'isAdmin': is_admin
                }
            })

        # 4. LOGOUT API (JWT Revocation & Blacklist)
        elif path == '/api/auth/logout':
            auth_header = self.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1].strip()
                revoke_token(token, reason='User initiated logout')
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute('DELETE FROM sessions WHERE token = ?', (token,))
                conn.commit()
                conn.close()
            return self.send_json({'success': True, 'message': 'Logged out and token revoked successfully'})

        # 4B. TOKEN VERIFICATION API (JWT Cryptographic Claims Inspection)
        elif path == '/api/auth/verify-token':
            token = payload.get('token')
            if not token:
                auth_header = self.headers.get('Authorization')
                if auth_header and auth_header.startswith('Bearer '):
                    token = auth_header.split(' ')[1].strip()
            
            if not token:
                return self.send_json({'error': 'Token required'}, 400)
                
            is_valid, claims, err_msg = verify_jwt(token)
            if is_valid:
                return self.send_json({
                    'success': True,
                    'valid': True,
                    'claims': claims,
                    'message': 'Token is cryptographically valid and active'
                })
            else:
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute('SELECT user_id FROM sessions WHERE token = ?', (token,))
                row = cursor.fetchone()
                conn.close()
                if row:
                    return self.send_json({
                        'success': True,
                        'valid': True,
                        'claims': {'sub': str(row[0]), 'legacy': True},
                        'message': 'Legacy session token is active'
                    })
                return self.send_json({
                    'success': False,
                    'valid': False,
                    'error': err_msg or 'Invalid or expired token'
                }, 401)

        # 5. CREATE POST API WITH ATTACHMENT UPLOAD
        elif path in ['/api/posts', '/api/posts/create']:
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)

            raw_content = payload.get('content', '').strip()
            content = sanitize_input(raw_content)
            image_data = payload.get('image', None)
            media_url = None

            if not content and not image_data:
                return self.send_json({'error': 'Post content or image required'}, 400)

            if image_data and ',' in image_data:
                try:
                    header, encoded = image_data.split(',', 1)
                    # Extract extension from data URL header (e.g. data:image/png;base64)
                    ext = None
                    if header.startswith('data:'):
                        mime_type = header[5:].split(';')[0].lower()
                        ext_map = {'image/jpeg': '.jpg', 'image/jpg': '.jpg', 'image/png': '.png', 'image/webp': '.webp', 'image/gif': '.gif'}
                        ext = ext_map.get(mime_type, None)
                    
                    if not ext or not is_valid_image_mime(f"test{ext}"):
                        return self.send_json({'error': 'Invalid image format. Allowed: JPG, PNG, WEBP, GIF'}, 400)

                    img_bytes = base64.b64decode(encoded)
                    # Cap upload size at 10 MB
                    if len(img_bytes) > 10 * 1024 * 1024:
                        return self.send_json({'error': 'Image exceeds maximum allowed size of 10MB'}, 400)

                    # Validate binary magic bytes signature
                    magic_ext = validate_image_magic_bytes(img_bytes)
                    if not magic_ext:
                        return self.send_json({'error': 'File corrupted or invalid image header'}, 400)

                    # Decompression bomb and extreme dimensions defense
                    dims = inspect_image_dimensions(img_bytes)
                    if dims:
                        w, h = dims
                        if w > 8000 or h > 8000 or (w * h > 36000000):
                            return self.send_json({'error': 'Image dimensions exceed maximum safe limit (8000x8000)'}, 400)

                    filename = f"post_{secrets.token_hex(8)}{magic_ext}"
                    filepath = os.path.join(UPLOADS_DIR, filename)
                    with open(filepath, 'wb') as f:
                        f.write(img_bytes)
                    media_url = f"uploads/{filename}"
                except Exception as e:
                    print("Image save error:", e)
                    return self.send_json({'error': 'Failed to process image attachment'}, 400)

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO posts (author_id, content, media_url)
                VALUES (?, ?, ?)
            ''', (current_user['id'], content, media_url))
            post_id = cursor.lastrowid
            conn.commit()
            conn.close()

            # Process hashtags and @mentions
            saved_hashtags = extract_and_save_hashtags(post_id, content)
            extract_and_notify_mentions(current_user, content, post_id)

            return self.send_json({
                'success': True, 
                'postId': post_id, 
                'post': {
                    'id': post_id,
                    'content': content,
                    'hashtags': saved_hashtags
                }
            })

        # 5B. DELETE POST API (Author or Admin Only)
        elif path == '/api/posts/delete':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)

            post_id = payload.get('postId')
            if not post_id:
                return self.send_json({'error': 'postId is required'}, 400)

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT id, author_id, media_url FROM posts WHERE id = ?', (post_id,))
            p_row = cursor.fetchone()

            if not p_row:
                conn.close()
                return self.send_json({'error': 'Post not found'}, 404)

            p_id, author_id, media_url = p_row

            # Only author or administrator can delete
            is_admin = current_user.get('isAdmin', False)
            if author_id != current_user['id'] and not is_admin:
                conn.close()
                return self.send_json({'error': 'Forbidden: You can only delete your own posts'}, 403)

            # Clean up associated likes, comments, hashtags, and reports
            cursor.execute('DELETE FROM post_likes WHERE post_id = ?', (post_id,))
            cursor.execute('DELETE FROM post_comments WHERE post_id = ?', (post_id,))
            cursor.execute('DELETE FROM post_hashtags WHERE post_id = ?', (post_id,))
            cursor.execute('DELETE FROM reports WHERE target_type = "POST" AND target_id = ?', (post_id,))
            cursor.execute('DELETE FROM posts WHERE id = ?', (post_id,))
            conn.commit()
            conn.close()

            return self.send_json({'success': True, 'message': 'Post deleted successfully', 'postId': post_id})

        # 6. LIKE POST API
        elif path == '/api/posts/like':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)

            post_id = payload.get('postId')
            if not post_id:
                return self.send_json({'error': 'postId is required'}, 400)

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM post_likes WHERE post_id = ? AND user_id = ?', (post_id, current_user['id']))
            row = cursor.fetchone()

            if row:
                cursor.execute('DELETE FROM post_likes WHERE id = ?', (row[0],))
                is_liked = False
            else:
                cursor.execute('INSERT INTO post_likes (post_id, user_id) VALUES (?, ?)', (post_id, current_user['id']))
                is_liked = True

            cursor.execute('SELECT COUNT(*) FROM post_likes WHERE post_id = ?', (post_id,))
            likes_count = cursor.fetchone()[0]

            conn.commit()
            conn.close()

            return self.send_json({'success': True, 'isLiked': is_liked, 'likesCount': likes_count})

        # 7. COMMENT ON POST API
        elif path == '/api/posts/comment':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)

            post_id = payload.get('postId')
            raw_content = (payload.get('content') or payload.get('text') or '').strip()
            content = sanitize_input(raw_content)

            if not post_id or not content:
                return self.send_json({'error': 'postId and content required'}, 400)

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO post_comments (post_id, user_id, content)
                VALUES (?, ?, ?)
            ''', (post_id, current_user['id'], content))
            comment_id = cursor.lastrowid
            conn.commit()
            conn.close()

            user_avatar = resolve_user_avatar(current_user['id'], current_user['email'], current_user['fullName'], current_user.get('avatarUrl'))

            return self.send_json({
                'success': True,
                'comment': {
                    'id': comment_id,
                    'content': content,
                    'text': content,
                    'author': current_user['fullName'],
                    'userName': current_user['fullName'],
                    'userAvatar': user_avatar,
                    'time': 'Just now'
                }
            })

        # 8. SEND DIRECT MESSAGE API
        elif path == '/api/messages/send':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)

            receiver_id = payload.get('receiverId')
            raw_msg = (payload.get('messageText') or payload.get('text') or '').strip()
            message_text = sanitize_input(raw_msg)

            if not receiver_id or not message_text:
                return self.send_json({'error': 'Receiver ID and text required'}, 400)

            conn = get_db()
            cursor = conn.cursor()

            # Check if either user has blocked the other
            cursor.execute('''
                SELECT id FROM blocked_users
                WHERE (user_id = ? AND blocked_user_id = ?)
                   OR (user_id = ? AND blocked_user_id = ?)
            ''', (current_user['id'], receiver_id, receiver_id, current_user['id']))
            if cursor.fetchone():
                conn.close()
                return self.send_json({'error': 'Cannot send message to this user'}, 403)

            # Check receiver's message_privacy setting
            cursor.execute('SELECT message_privacy FROM user_settings WHERE user_id = ?', (receiver_id,))
            recv_priv_row = cursor.fetchone()
            msg_priv = recv_priv_row[0] if recv_priv_row and recv_priv_row[0] else 'everyone'

            if msg_priv == 'nobody':
                conn.close()
                return self.send_json({'error': 'User does not accept direct messages'}, 403)
            elif msg_priv == 'connections':
                cursor.execute('''
                    SELECT id FROM connections 
                    WHERE status = 'ACCEPTED' 
                      AND ((requester_id = ? AND receiver_id = ?) OR (requester_id = ? AND receiver_id = ?))
                ''', (current_user['id'], receiver_id, receiver_id, current_user['id']))
                if not cursor.fetchone():
                    conn.close()
                    return self.send_json({'error': 'User only accepts messages from connections'}, 403)

            cursor.execute('''
                INSERT INTO direct_messages (sender_id, receiver_id, message_text)
                VALUES (?, ?, ?)
            ''', (current_user['id'], receiver_id, message_text))
            msg_id = cursor.lastrowid

            cursor.execute('''
                INSERT INTO notifications (user_id, sender_id, notif_type, title)
                VALUES (?, ?, 'MESSAGE', ?)
            ''', (receiver_id, current_user['id'], f"sent you a message: '{message_text[:30]}...'"))
            conn.commit()
            conn.close()

            return self.send_json({
                'success': True,
                'message': {
                    'id': msg_id,
                    'senderId': current_user['id'],
                    'receiverId': receiver_id,
                    'text': message_text,
                    'time': 'Just now',
                    'isSentByMe': True
                }
            })

        # POST REAL-TIME TYPING SIGNAL API
        elif path == '/api/messages/typing':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)

            receiver_id = payload.get('receiverId')
            if receiver_id:
                try:
                    prune_typing_users()
                    ACTIVE_TYPING_USERS[(current_user['id'], int(receiver_id))] = time.time()
                except Exception:
                    pass
            return self.send_json({'success': True})

        # MARK ALL NOTIFICATIONS AS READ API
        elif path == '/api/notifications/read':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('UPDATE notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0', (current_user['id'],))
            conn.commit()
            conn.close()
            return self.send_json({'success': True, 'message': 'All notifications marked as read'})

        # 9. CONNECT WITH USER API
        elif path == '/api/users/connect':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)

            target_user_id = payload.get('targetUserId')
            if not target_user_id:
                return self.send_json({'error': 'targetUserId is required'}, 400)

            conn = get_db()
            cursor = conn.cursor()

            # Check if either user blocked the other
            cursor.execute('''
                SELECT id FROM blocked_users
                WHERE (user_id = ? AND blocked_user_id = ?)
                   OR (user_id = ? AND blocked_user_id = ?)
            ''', (current_user['id'], target_user_id, target_user_id, current_user['id']))
            if cursor.fetchone():
                conn.close()
                return self.send_json({'error': 'Cannot connect with this user'}, 403)

            cursor.execute('''
                SELECT id, status FROM connections 
                WHERE (requester_id = ? AND receiver_id = ?) 
                   OR (requester_id = ? AND receiver_id = ?)
            ''', (current_user['id'], target_user_id, target_user_id, current_user['id']))
            row = cursor.fetchone()

            if row:
                cursor.execute('DELETE FROM connections WHERE id = ?', (row[0],))
                new_status = 'NONE'
            else:
                # Check target user's connect_privacy setting
                cursor.execute('SELECT connect_privacy FROM user_settings WHERE user_id = ?', (target_user_id,))
                c_priv_row = cursor.fetchone()
                c_priv = c_priv_row[0] if c_priv_row and c_priv_row[0] else 'everyone'

                if c_priv == 'nobody':
                    conn.close()
                    return self.send_json({'error': 'User does not accept new connection requests'}, 403)

                cursor.execute('''
                    INSERT INTO connections (requester_id, receiver_id, status)
                    VALUES (?, ?, 'PENDING')
                ''', (current_user['id'], target_user_id))
                new_status = 'PENDING'
                cursor.execute('''
                    INSERT INTO notifications (user_id, sender_id, notif_type, title)
                    VALUES (?, ?, 'CONNECTION', 'sent you a connection request.')
                ''', (target_user_id, current_user['id']))

            conn.commit()
            conn.close()

            return self.send_json({'success': True, 'status': new_status})

        # 10. EDIT USER PROFILE & AVATAR API
        elif path == '/api/users/profile/edit':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)

            full_name = sanitize_input(payload.get('fullName', '').strip())
            headline = sanitize_input(payload.get('headline', '').strip())
            bio = sanitize_input(payload.get('bio', '').strip())
            avatar_data = payload.get('avatar', None)
            avatar_url = current_user['avatarUrl']

            if avatar_data == 'remove_photo':
                if current_user['id'] == 1 or current_user['email'] == 'member@joininghands.org':
                    avatar_url = 'hero.jpg'
                else:
                    avatar_url = generate_default_avatar(full_name)
            elif avatar_data and avatar_data.startswith('data:image/svg+xml'):
                avatar_url = avatar_data
            elif avatar_data and ',' in avatar_data:
                try:
                    header, encoded = avatar_data.split(',', 1)
                    # Extract extension from data URL header (e.g. data:image/png;base64)
                    ext = None
                    if header.startswith('data:'):
                        mime_type = header[5:].split(';')[0].lower()
                        ext_map = {'image/jpeg': '.jpg', 'image/jpg': '.jpg', 'image/png': '.png', 'image/webp': '.webp', 'image/gif': '.gif'}
                        ext = ext_map.get(mime_type, None)
                    
                    if not ext or not is_valid_image_mime(f"test{ext}"):
                        return self.send_json({'error': 'Invalid avatar format. Allowed: JPG, PNG, WEBP, GIF'}, 400)

                    img_bytes = base64.b64decode(encoded)
                    # Cap avatar size at 5 MB
                    if len(img_bytes) > 5 * 1024 * 1024:
                        return self.send_json({'error': 'Avatar exceeds maximum allowed size of 5MB'}, 400)

                    # Validate binary magic bytes signature
                    magic_ext = validate_image_magic_bytes(img_bytes)
                    if not magic_ext:
                        return self.send_json({'error': 'Corrupted image header or invalid file signature'}, 400)

                    # Decompression bomb and extreme dimensions defense
                    dims = inspect_image_dimensions(img_bytes)
                    if dims:
                        w, h = dims
                        if w > 8000 or h > 8000 or (w * h > 36000000):
                            return self.send_json({'error': 'Avatar dimensions exceed maximum safe limit (8000x8000)'}, 400)

                    filename = f"avatar_{current_user['id']}_{secrets.token_hex(4)}{magic_ext}"
                    filepath = os.path.join(UPLOADS_DIR, filename)
                    with open(filepath, 'wb') as f:
                        f.write(img_bytes)
                    avatar_url = f"uploads/{filename}"
                except Exception as e:
                    print("Avatar save error:", e)
                    return self.send_json({'error': 'Failed to process avatar upload'}, 400)

            location = sanitize_input(payload.get('location', '').strip())
            cover_photo_data = payload.get('coverPhoto', None)
            cover_photo_url = payload.get('coverPhotoUrl', None)

            if cover_photo_data and ',' in cover_photo_data:
                try:
                    c_header, c_encoded = cover_photo_data.split(',', 1)
                    c_ext = None
                    if c_header.startswith('data:'):
                        c_mime = c_header[5:].split(';')[0].lower()
                        c_ext_map = {'image/jpeg': '.jpg', 'image/jpg': '.jpg', 'image/png': '.png', 'image/webp': '.webp', 'image/gif': '.gif'}
                        c_ext = c_ext_map.get(c_mime, None)
                    if c_ext and is_valid_image_mime(f"test{c_ext}"):
                        c_bytes = base64.b64decode(c_encoded)
                        if len(c_bytes) <= 8 * 1024 * 1024:
                            c_magic = validate_image_magic_bytes(c_bytes)
                            if c_magic:
                                c_filename = f"cover_{current_user['id']}_{secrets.token_hex(4)}{c_magic}"
                                c_filepath = os.path.join(UPLOADS_DIR, c_filename)
                                with open(c_filepath, 'wb') as f:
                                    f.write(c_bytes)
                                cover_photo_url = f"uploads/{c_filename}"
                except Exception:
                    pass

            conn = get_db()
            cursor = conn.cursor()
            if cover_photo_url:
                cursor.execute('''
                    UPDATE users SET full_name = ?, headline = ?, bio = ?, avatar_url = ?, location = ?, cover_photo_url = ?
                    WHERE id = ?
                ''', (full_name, headline, bio, avatar_url, location, cover_photo_url, current_user['id']))
            else:
                cursor.execute('''
                    UPDATE users SET full_name = ?, headline = ?, bio = ?, avatar_url = ?, location = ?
                    WHERE id = ?
                ''', (full_name, headline, bio, avatar_url, location, current_user['id']))
            conn.commit()
            conn.close()

            resolved_avatar = resolve_user_avatar(current_user['id'], current_user['email'], full_name, avatar_url)

            return self.send_json({
                'success': True,
                'user': {
                    'id': current_user['id'],
                    'email': current_user['email'],
                    'fullName': full_name,
                    'headline': headline,
                    'avatarUrl': resolved_avatar,
                    'bio': bio,
                    'location': location,
                    'coverPhotoUrl': cover_photo_url or 'hero.jpg',
                    'isAdmin': current_user.get('isAdmin', False)
                }
            })

        # 11. EVENT RSVP TOGGLE API
        elif path == '/api/events/rsvp':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)

            event_id = payload.get('eventId')
            if not event_id:
                return self.send_json({'error': 'eventId required'}, 400)

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM event_rsvps WHERE event_id = ? AND user_id = ?', (event_id, current_user['id']))
            row = cursor.fetchone()

            if row:
                cursor.execute('DELETE FROM event_rsvps WHERE id = ?', (row[0],))
                is_attending = False
            else:
                cursor.execute('INSERT INTO event_rsvps (event_id, user_id) VALUES (?, ?)', (event_id, current_user['id']))
                is_attending = True

            cursor.execute('SELECT COUNT(*) FROM event_rsvps WHERE event_id = ?', (event_id,))
            rsvp_count = cursor.fetchone()[0]

            conn.commit()
            conn.close()

            return self.send_json({'success': True, 'isAttending': is_attending, 'rsvps': rsvp_count})

        # 12. RESPOND TO PENDING CONNECTION REQUEST ENDPOINT
        elif path == '/api/network/respond':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)

            conn_id = payload.get('connId')
            action = payload.get('action')

            if not conn_id or not action:
                return self.send_json({'error': 'connId and action required'}, 400)

            conn = get_db()
            cursor = conn.cursor()

            if action == 'ACCEPT':
                cursor.execute("UPDATE connections SET status = 'ACCEPTED' WHERE id = ? AND receiver_id = ?", (conn_id, current_user['id']))
            else:
                cursor.execute("DELETE FROM connections WHERE id = ? AND receiver_id = ?", (conn_id, current_user['id']))

            conn.commit()
            conn.close()

            return self.send_json({'success': True})

        # 13. TOGGLE BOOKMARK / SAVE POST ENDPOINT
        elif path == '/api/posts/bookmark':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)

            post_id = payload.get('postId')
            if not post_id:
                return self.send_json({'error': 'postId is required'}, 400)

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM saved_posts WHERE post_id = ? AND user_id = ?', (post_id, current_user['id']))
            row = cursor.fetchone()

            if row:
                cursor.execute('DELETE FROM saved_posts WHERE id = ?', (row[0],))
                is_saved = False
            else:
                cursor.execute('INSERT INTO saved_posts (post_id, user_id) VALUES (?, ?)', (post_id, current_user['id']))
                is_saved = True

            conn.commit()
            conn.close()

            return self.send_json({'success': True, 'isSaved': is_saved})

        # 14. PUBLISH COMMUNITY ARTICLE ENDPOINT
        elif path == '/api/articles':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)

            raw_title = payload.get('title', '').strip()
            raw_content = payload.get('content', '').strip()
            title = sanitize_input(raw_title)
            content = sanitize_input(raw_content)

            if not title or not content:
                return self.send_json({'error': 'Title and content required'}, 400)

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO articles (title, author_id, content, cover_url)
                VALUES (?, ?, ?, ?)
            ''', (title, current_user['id'], content, 'hero.jpg'))
            conn.commit()
            conn.close()

            return self.send_json({'success': True})

        # 15. UPDATE USER SETTINGS & PREFERENCES ENDPOINT
        elif path == '/api/settings/update':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)

            theme = payload.get('theme', 'light')
            language = payload.get('language', 'en')
            privacy = payload.get('privacy', 'public')
            message_privacy = payload.get('messagePrivacy', payload.get('message_privacy', 'everyone'))
            connect_privacy = payload.get('connectPrivacy', payload.get('connect_privacy', 'everyone'))
            notifications_enabled = 1 if payload.get('notificationsEnabled', True) else 0

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO user_settings (user_id, theme, language, privacy, message_privacy, connect_privacy, notifications_enabled)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    theme=excluded.theme,
                    language=excluded.language,
                    privacy=excluded.privacy,
                    message_privacy=excluded.message_privacy,
                    connect_privacy=excluded.connect_privacy,
                    notifications_enabled=excluded.notifications_enabled
            ''', (current_user['id'], theme, language, privacy, message_privacy, connect_privacy, notifications_enabled))
            conn.commit()
            conn.close()

            return self.send_json({'success': True})

        # 16. CHANGE PASSWORD ENDPOINT
        elif path == '/api/settings/password':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)

            old_pass = payload.get('oldPassword', '')
            new_pass = payload.get('newPassword', '')

            if not old_pass or not new_pass or len(new_pass) < 6:
                return self.send_json({'error': 'New password must be at least 6 characters'}, 400)

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT password_hash FROM users WHERE id = ?', (current_user['id'],))
            row = cursor.fetchone()

            if not row or not verify_password(row[0], old_pass):
                conn.close()
                return self.send_json({'error': 'Incorrect current password'}, 400)

            new_hash = hash_password(new_pass)
            cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (new_hash, current_user['id']))
            conn.commit()
            conn.close()

            return self.send_json({'success': True})

        # 17. BLOCK / UNBLOCK USER ENDPOINT
        elif path == '/api/settings/block':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)

            target_user_id = payload.get('targetUserId')
            if not target_user_id:
                return self.send_json({'error': 'targetUserId required'}, 400)

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM blocked_users WHERE user_id = ? AND blocked_user_id = ?', (current_user['id'], target_user_id))
            row = cursor.fetchone()

            if row:
                cursor.execute('DELETE FROM blocked_users WHERE id = ?', (row[0],))
                is_blocked = False
            else:
                cursor.execute('INSERT INTO blocked_users (user_id, blocked_user_id) VALUES (?, ?)', (current_user['id'], target_user_id))
                is_blocked = True

            conn.commit()
            conn.close()

            return self.send_json({'success': True, 'isBlocked': is_blocked})

        # 18. DELETE ACCOUNT ENDPOINT (Zero-Orphan Transactional Account Deletion)
        elif path == '/api/settings/delete-account':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)

            uid = current_user['id']
            conn = get_db()
            cursor = conn.cursor()
            try:
                # 1. Delete post comments made by user or on user's posts
                cursor.execute('DELETE FROM post_comments WHERE user_id = ? OR post_id IN (SELECT id FROM posts WHERE author_id = ?)', (uid, uid))
                # 2. Delete post likes made by user or on user's posts
                cursor.execute('DELETE FROM post_likes WHERE user_id = ? OR post_id IN (SELECT id FROM posts WHERE author_id = ?)', (uid, uid))
                # 3. Delete post hashtags for user's posts
                cursor.execute('DELETE FROM post_hashtags WHERE post_id IN (SELECT id FROM posts WHERE author_id = ?)', (uid,))
                # 4. Delete saved posts by user or user's posts saved by others
                cursor.execute('DELETE FROM saved_posts WHERE user_id = ? OR post_id IN (SELECT id FROM posts WHERE author_id = ?)', (uid, uid))
                # 5. Delete timeline posts
                cursor.execute('DELETE FROM posts WHERE author_id = ?', (uid,))
                # 6. Delete direct messages (sent or received)
                cursor.execute('DELETE FROM direct_messages WHERE sender_id = ? OR receiver_id = ?', (uid, uid))
                # 7. Delete connection requests/links
                cursor.execute('DELETE FROM connections WHERE requester_id = ? OR receiver_id = ?', (uid, uid))
                # 8. Delete notifications (for user or triggered by user)
                cursor.execute('DELETE FROM notifications WHERE user_id = ? OR sender_id = ?', (uid, uid))
                # 9. Delete event RSVPs
                cursor.execute('DELETE FROM event_rsvps WHERE user_id = ?', (uid,))
                # 10. Delete articles written by user
                cursor.execute('DELETE FROM articles WHERE author_id = ?', (uid,))
                # 11. Delete blocked user relationships
                cursor.execute('DELETE FROM blocked_users WHERE user_id = ? OR blocked_user_id = ?', (uid, uid))
                # 12. Delete user settings
                cursor.execute('DELETE FROM user_settings WHERE user_id = ?', (uid,))
                # 13. Delete login history & active sessions
                cursor.execute('DELETE FROM login_history WHERE user_id = ?', (uid,))
                cursor.execute('DELETE FROM sessions WHERE user_id = ?', (uid,))
                # 14. Delete reports submitted by user
                cursor.execute('DELETE FROM reports WHERE reporter_id = ?', (uid,))
                # 14.1 Delete H Rides data for user
                cursor.execute('DELETE FROM rapido_chats WHERE sender_id = ? OR ride_id IN (SELECT id FROM rapido_rides WHERE user_id = ? OR driver_id = ?)', (uid, uid, uid))
                cursor.execute('DELETE FROM rapido_rides WHERE user_id = ? OR driver_id = ?', (uid, uid))
                cursor.execute('DELETE FROM rapido_driver_stats WHERE user_id = ?', (uid,))
                # 15. Finally delete user master record
                cursor.execute('DELETE FROM users WHERE id = ?', (uid,))
                conn.commit()
                conn.close()
                log_audit_event('INFO', f"User account successfully deleted: ID {uid}")
                return self.send_json({'success': True})
            except Exception as e:
                conn.rollback()
                conn.close()
                log_audit_event('ERROR', f"Account deletion failed for user ID {uid}: {e}")
                return self.send_json({'error': 'Failed to delete account'}, 500)

        # 19. ADMIN BAN / UNBAN USER ENDPOINT
        elif path == '/api/admin/users/ban':
            current_user = self.get_auth_user()
            if not current_user or not current_user.get('isAdmin'):
                return self.send_json({'error': 'Admin privilege required'}, 403)

            target_user_id = payload.get('targetUserId')
            if not target_user_id:
                return self.send_json({'error': 'targetUserId required'}, 400)

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT status FROM users WHERE id = ?', (target_user_id,))
            row = cursor.fetchone()

            if not row:
                conn.close()
                return self.send_json({'error': 'User not found'}, 404)

            new_status = 'BANNED' if row[0] == 'ACTIVE' else 'ACTIVE'
            cursor.execute('UPDATE users SET status = ? WHERE id = ?', (new_status, target_user_id))
            conn.commit()
            conn.close()

            return self.send_json({'success': True, 'newStatus': new_status})

        # 20. ADMIN DELETE USER ACCOUNT ENDPOINT (Transactional Cascade)
        elif path == '/api/admin/users/delete':
            current_user = self.get_auth_user()
            if not current_user or not current_user.get('isAdmin'):
                return self.send_json({'error': 'Admin privilege required'}, 403)

            target_user_id = payload.get('targetUserId')
            if not target_user_id:
                return self.send_json({'error': 'targetUserId required'}, 400)

            conn = get_db()
            cursor = conn.cursor()
            try:
                cursor.execute('DELETE FROM post_comments WHERE user_id = ? OR post_id IN (SELECT id FROM posts WHERE author_id = ?)', (target_user_id, target_user_id))
                cursor.execute('DELETE FROM post_likes WHERE user_id = ? OR post_id IN (SELECT id FROM posts WHERE author_id = ?)', (target_user_id, target_user_id))
                cursor.execute('DELETE FROM post_hashtags WHERE post_id IN (SELECT id FROM posts WHERE author_id = ?)', (target_user_id,))
                cursor.execute('DELETE FROM saved_posts WHERE user_id = ? OR post_id IN (SELECT id FROM posts WHERE author_id = ?)', (target_user_id, target_user_id))
                cursor.execute('DELETE FROM posts WHERE author_id = ?', (target_user_id,))
                cursor.execute('DELETE FROM direct_messages WHERE sender_id = ? OR receiver_id = ?', (target_user_id, target_user_id))
                cursor.execute('DELETE FROM connections WHERE requester_id = ? OR receiver_id = ?', (target_user_id, target_user_id))
                cursor.execute('DELETE FROM notifications WHERE user_id = ? OR sender_id = ?', (target_user_id, target_user_id))
                cursor.execute('DELETE FROM event_rsvps WHERE user_id = ?', (target_user_id,))
                cursor.execute('DELETE FROM articles WHERE author_id = ?', (target_user_id,))
                cursor.execute('DELETE FROM blocked_users WHERE user_id = ? OR blocked_user_id = ?', (target_user_id, target_user_id))
                cursor.execute('DELETE FROM user_settings WHERE user_id = ?', (target_user_id,))
                cursor.execute('DELETE FROM login_history WHERE user_id = ?', (target_user_id,))
                cursor.execute('DELETE FROM sessions WHERE user_id = ?', (target_user_id,))
                cursor.execute('DELETE FROM reports WHERE reporter_id = ?', (target_user_id,))
                # Clean up H Rides data for target user
                cursor.execute('DELETE FROM rapido_chats WHERE sender_id = ? OR ride_id IN (SELECT id FROM rapido_rides WHERE user_id = ? OR driver_id = ?)', (target_user_id, target_user_id, target_user_id))
                cursor.execute('DELETE FROM rapido_rides WHERE user_id = ? OR driver_id = ?', (target_user_id, target_user_id))
                cursor.execute('DELETE FROM rapido_driver_stats WHERE user_id = ?', (target_user_id,))
                cursor.execute('DELETE FROM users WHERE id = ?', (target_user_id,))
                conn.commit()
                conn.close()
                log_audit_event('INFO', f"Admin deleted user ID {target_user_id}")
                return self.send_json({'success': True})
            except Exception as e:
                conn.rollback()
                conn.close()
                log_audit_event('ERROR', f"Admin user deletion failed for ID {target_user_id}: {e}")
                return self.send_json({'error': 'Failed to delete user'}, 500)

        # 21. ADMIN RESET USER PASSWORD ENDPOINT
        elif path == '/api/admin/users/reset-password':
            current_user = self.get_auth_user()
            if not current_user or not current_user.get('isAdmin'):
                return self.send_json({'error': 'Admin privilege required'}, 403)

            target_user_id = payload.get('targetUserId')
            if not target_user_id:
                return self.send_json({'error': 'targetUserId required'}, 400)

            default_pass_hash = hash_password('demo1234')
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (default_pass_hash, target_user_id))
            conn.commit()
            conn.close()

            return self.send_json({'success': True, 'newPassword': 'demo1234'})

        # 22. ADMIN DELETE INAPPROPRIATE POST ENDPOINT
        elif path == '/api/admin/posts/delete':
            current_user = self.get_auth_user()
            if not current_user or not current_user.get('isAdmin'):
                return self.send_json({'error': 'Admin privilege required'}, 403)

            post_id = payload.get('postId')
            if not post_id:
                return self.send_json({'error': 'postId required'}, 400)

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM post_likes WHERE post_id = ?', (post_id,))
            cursor.execute('DELETE FROM post_comments WHERE post_id = ?', (post_id,))
            cursor.execute('DELETE FROM posts WHERE id = ?', (post_id,))
            conn.commit()
            conn.close()

            return self.send_json({'success': True})

        # 23. ADMIN BROADCAST SYSTEM ANNOUNCEMENT ENDPOINT
        elif path == '/api/admin/broadcast':
            current_user = self.get_auth_user()
            if not current_user or not current_user.get('isAdmin'):
                return self.send_json({'error': 'Admin privilege required'}, 403)

            announcement = payload.get('announcement', '').strip()
            if not announcement:
                return self.send_json({'error': 'Announcement text required'}, 400)

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM users WHERE id != ?', (current_user['id'],))
            u_rows = cursor.fetchall()
            for ur in u_rows:
                cursor.execute('''
                    INSERT INTO notifications (user_id, sender_id, notif_type, title)
                    VALUES (?, ?, 'ANNOUNCEMENT', ?)
                ''', (ur[0], current_user['id'], f'📢 Announcement: {announcement}'))
            conn.commit()
            conn.close()

            return self.send_json({'success': True, 'broadcastCount': len(u_rows)})

        # 24. EMAIL VERIFICATION: REQUEST VERIFICATION EMAIL / TOKEN API
        elif path == '/api/auth/verify-email/request':
            current_user = self.get_auth_user()
            email = (payload.get('email') or (current_user['email'] if current_user else '')).strip().lower()
            if not email:
                return self.send_json({'error': 'Email required'}, 400)

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
            u_row = cursor.fetchone()
            
            # Rate-limit token requests (max 1 token per 60 seconds)
            token_val = None
            if u_row:
                user_id = u_row[0]
                cursor.execute('SELECT created_at FROM email_verification_tokens WHERE user_id = ? AND used = 0 ORDER BY id DESC LIMIT 1', (user_id,))
                recent = cursor.fetchone()
                
                token_val = secrets.token_hex(20)
                token_hash = hashlib.sha256(token_val.encode('utf-8')).hexdigest()
                expires_at = datetime.fromtimestamp(time.time() + 86400).strftime('%Y-%m-%d %H:%M:%S')
                
                cursor.execute('''
                    INSERT INTO email_verification_tokens (user_id, token_hash, expires_at)
                    VALUES (?, ?, ?)
                ''', (user_id, token_hash, expires_at))
                conn.commit()

            conn.close()
            # Return token for development/demo ease, message always generic for account enumeration defense
            return self.send_json({
                'success': True,
                'message': 'Verification email sent if account exists.',
                'devToken': token_val if APP_ENV != 'production' else None
            })

        # 25. EMAIL VERIFICATION: CONFIRM TOKEN API
        elif path == '/api/auth/verify-email/confirm':
            token_val = payload.get('token', '').strip()
            if not token_val:
                return self.send_json({'error': 'Verification token required'}, 400)

            token_hash = hashlib.sha256(token_val.encode('utf-8')).hexdigest()
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, user_id, expires_at, used 
                FROM email_verification_tokens 
                WHERE token_hash = ?
            ''', (token_hash,))
            row = cursor.fetchone()

            if not row or row[3] == 1:
                conn.close()
                return self.send_json({'error': 'Invalid or already used verification link'}, 400)

            # Check expiration
            expires_at_str = row[2]
            try:
                exp_dt = datetime.strptime(expires_at_str, '%Y-%m-%d %H:%M:%S')
                if datetime.now() > exp_dt:
                    conn.close()
                    return self.send_json({'error': 'Verification link has expired'}, 400)
            except Exception:
                pass

            token_id = row[0]
            user_id = row[1]

            cursor.execute('UPDATE email_verification_tokens SET used = 1 WHERE id = ?', (token_id,))
            cursor.execute('UPDATE users SET email_verified = 1 WHERE id = ?', (user_id,))
            conn.commit()
            conn.close()

            return self.send_json({'success': True, 'message': 'Email successfully verified!'})

        # 26. FORGOT PASSWORD: REQUEST RESET TOKEN API
        elif path == '/api/auth/forgot-password':
            email = payload.get('email', '').strip().lower()
            if not email:
                return self.send_json({'error': 'Email is required'}, 400)

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
            u_row = cursor.fetchone()

            token_val = None
            if u_row:
                user_id = u_row[0]
                token_val = secrets.token_hex(24)
                token_hash = hashlib.sha256(token_val.encode('utf-8')).hexdigest()
                expires_at = datetime.fromtimestamp(time.time() + 3600).strftime('%Y-%m-%d %H:%M:%S') # 1 hour expiry

                # Invalidate existing unused tokens for user
                cursor.execute('UPDATE password_reset_tokens SET used = 1 WHERE user_id = ? AND used = 0', (user_id,))
                cursor.execute('''
                    INSERT INTO password_reset_tokens (user_id, token_hash, expires_at)
                    VALUES (?, ?, ?)
                ''', (user_id, token_hash, expires_at))
                conn.commit()

            conn.close()
            return self.send_json({
                'success': True,
                'message': 'If your email is registered, you will receive password reset instructions.',
                'devResetToken': token_val if APP_ENV != 'production' else None
            })

        # 27. FORGOT PASSWORD: RESET WITH TOKEN API
        elif path == '/api/auth/reset-password':
            token_val = payload.get('token', '').strip()
            new_password = payload.get('newPassword', '').strip()

            if not token_val or not new_password:
                return self.send_json({'error': 'Token and new password required'}, 400)

            if len(new_password) < 6:
                return self.send_json({'error': 'Password must be at least 6 characters'}, 400)

            token_hash = hashlib.sha256(token_val.encode('utf-8')).hexdigest()
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, user_id, expires_at, used 
                FROM password_reset_tokens 
                WHERE token_hash = ?
            ''', (token_hash,))
            row = cursor.fetchone()

            if not row or row[3] == 1:
                conn.close()
                return self.send_json({'error': 'Invalid or expired password reset link'}, 400)

            # Check expiration
            expires_at_str = row[2]
            try:
                exp_dt = datetime.strptime(expires_at_str, '%Y-%m-%d %H:%M:%S')
                if datetime.now() > exp_dt:
                    conn.close()
                    return self.send_json({'error': 'Password reset link has expired'}, 400)
            except Exception:
                pass

            token_id = row[0]
            user_id = row[1]
            new_hash = hash_password(new_password)

            cursor.execute('UPDATE password_reset_tokens SET used = 1 WHERE id = ?', (token_id,))
            cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (new_hash, user_id))
            # Invalidate all prior sessions for security
            cursor.execute('DELETE FROM sessions WHERE user_id = ?', (user_id,))
            conn.commit()
            conn.close()

            log_audit_event('INFO', f"Password successfully reset via token for user ID {user_id}")
            return self.send_json({'success': True, 'message': 'Password has been reset successfully. Please log in.'})

        # 28. REPORT CONTENT / USER API
        elif path == '/api/reports/create':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)

            target_type = payload.get('targetType', 'POST').upper() # POST | COMMENT | USER | MESSAGE
            target_id = payload.get('targetId')
            raw_reason = payload.get('reason', 'Inappropriate Content').strip()
            reason = sanitize_input(raw_reason)

            if not target_id:
                return self.send_json({'error': 'targetId required'}, 400)

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO reports (reporter_id, target_type, target_id, reason, status)
                VALUES (?, ?, ?, ?, 'PENDING')
            ''', (current_user['id'], target_type, target_id, reason))
            report_id = cursor.lastrowid
            conn.commit()
            conn.close()

            return self.send_json({'success': True, 'reportId': report_id, 'message': 'Report submitted for review.'})

        # 29. ADMIN RESOLVE / DISMISS REPORT API
        elif path == '/api/admin/reports/resolve':
            current_user = self.get_auth_user()
            if not current_user or not current_user.get('isAdmin'):
                return self.send_json({'error': 'Admin privilege required'}, 403)

            report_id = payload.get('reportId')
            action = payload.get('action', 'DISMISS').upper() # DISMISS | DELETE_CONTENT | RESOLVE

            if not report_id:
                return self.send_json({'error': 'reportId required'}, 400)

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT target_type, target_id FROM reports WHERE id = ?', (report_id,))
            rep = cursor.fetchone()

            if not rep:
                conn.close()
                return self.send_json({'error': 'Report not found'}, 404)

            t_type, t_id = rep
            if action == 'DELETE_CONTENT':
                if t_type == 'POST':
                    cursor.execute('DELETE FROM post_likes WHERE post_id = ?', (t_id,))
                    cursor.execute('DELETE FROM post_comments WHERE post_id = ?', (t_id,))
                    cursor.execute('DELETE FROM posts WHERE id = ?', (t_id,))
                elif t_type == 'COMMENT':
                    cursor.execute('DELETE FROM post_comments WHERE id = ?', (t_id,))
                cursor.execute('UPDATE reports SET status = "RESOLVED_DELETED" WHERE id = ?', (report_id,))
            elif action == 'DISMISS':
                cursor.execute('UPDATE reports SET status = "DISMISSED" WHERE id = ?', (report_id,))
            else:
                cursor.execute('UPDATE reports SET status = "RESOLVED" WHERE id = ?', (report_id,))

            conn.commit()
            conn.close()
            return self.send_json({'success': True, 'action': action})

        # 30. MUTE / UNMUTE USER API
        elif path == '/api/settings/mute':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)

            target_user_id = payload.get('targetUserId')
            if not target_user_id:
                return self.send_json({'error': 'targetUserId required'}, 400)

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM muted_users WHERE user_id = ? AND muted_user_id = ?', (current_user['id'], target_user_id))
            row = cursor.fetchone()

            if row:
                cursor.execute('DELETE FROM muted_users WHERE id = ?', (row[0],))
                is_muted = False
            else:
                cursor.execute('INSERT INTO muted_users (user_id, muted_user_id) VALUES (?, ?)', (current_user['id'], target_user_id))
                is_muted = True

            conn.commit()
            conn.close()
            return self.send_json({'success': True, 'isMuted': is_muted})

        # 31. PROFESSIONAL PROFILES: ADD/EDIT/DELETE SKILLS API
        elif path == '/api/profile/skills':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)

            action = payload.get('action', 'ADD').upper() # ADD | DELETE
            skill_name = sanitize_input(payload.get('skill', '').strip())

            if not skill_name:
                return self.send_json({'error': 'Skill name required'}, 400)

            conn = get_db()
            cursor = conn.cursor()
            if action == 'ADD':
                cursor.execute('''
                    INSERT OR IGNORE INTO profile_skills (user_id, skill_name)
                    VALUES (?, ?)
                ''', (current_user['id'], skill_name))
            else:
                cursor.execute('DELETE FROM profile_skills WHERE user_id = ? AND skill_name = ?', (current_user['id'], skill_name))
            conn.commit()

            cursor.execute('SELECT skill_name FROM profile_skills WHERE user_id = ?', (current_user['id'],))
            skills = [r[0] for r in cursor.fetchall()]
            conn.close()
            return self.send_json({'success': True, 'skills': skills})

        # 32. PROFESSIONAL PROFILES: ADD/DELETE EDUCATION API
        elif path == '/api/profile/education':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)

            action = payload.get('action', 'ADD').upper()
            conn = get_db()
            cursor = conn.cursor()

            if action == 'ADD':
                inst = sanitize_input(payload.get('institution', '').strip())
                degree = sanitize_input(payload.get('degree', '').strip())
                field = sanitize_input(payload.get('field', '').strip())
                s_year = sanitize_input(str(payload.get('startYear', '')))
                e_year = sanitize_input(str(payload.get('endYear', '')))
                desc = sanitize_input(payload.get('description', '').strip())

                if not inst or not degree:
                    conn.close()
                    return self.send_json({'error': 'Institution and Degree required'}, 400)

                cursor.execute('''
                    INSERT INTO profile_education (user_id, institution, degree, field_of_study, start_year, end_year, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (current_user['id'], inst, degree, field, s_year, e_year, desc))
            elif action == 'DELETE':
                edu_id = payload.get('id')
                cursor.execute('DELETE FROM profile_education WHERE id = ? AND user_id = ?', (edu_id, current_user['id']))

            conn.commit()
            cursor.execute('SELECT id, institution, degree, field_of_study, start_year, end_year, description FROM profile_education WHERE user_id = ?', (current_user['id'],))
            edu_list = [{'id': r[0], 'institution': r[1], 'degree': r[2], 'field': r[3], 'startYear': r[4], 'endYear': r[5], 'description': r[6]} for r in cursor.fetchall()]
            conn.close()
            return self.send_json({'success': True, 'education': edu_list})

        # 33. PROFESSIONAL PROFILES: ADD/DELETE EXPERIENCE API
        elif path == '/api/profile/experience':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)

            action = payload.get('action', 'ADD').upper()
            conn = get_db()
            cursor = conn.cursor()

            if action == 'ADD':
                company = sanitize_input(payload.get('company', '').strip())
                pos = sanitize_input(payload.get('position', '').strip())
                loc = sanitize_input(payload.get('location', '').strip())
                s_date = sanitize_input(str(payload.get('startDate', '')))
                e_date = sanitize_input(str(payload.get('endDate', '')))
                is_curr = 1 if payload.get('isCurrent') else 0
                desc = sanitize_input(payload.get('description', '').strip())

                if not company or not pos:
                    conn.close()
                    return self.send_json({'error': 'Company and Position required'}, 400)

                cursor.execute('''
                    INSERT INTO profile_experience (user_id, company, position, location, start_date, end_date, is_current, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (current_user['id'], company, pos, loc, s_date, e_date, is_curr, desc))
            elif action == 'DELETE':
                exp_id = payload.get('id')
                cursor.execute('DELETE FROM profile_experience WHERE id = ? AND user_id = ?', (exp_id, current_user['id']))

            conn.commit()
            cursor.execute('SELECT id, company, position, location, start_date, end_date, is_current, description FROM profile_experience WHERE user_id = ?', (current_user['id'],))
            exp_list = [{'id': r[0], 'company': r[1], 'position': r[2], 'location': r[3], 'startDate': r[4], 'endDate': r[5], 'isCurrent': bool(r[6]), 'description': r[7]} for r in cursor.fetchall()]
            conn.close()
            return self.send_json({'success': True, 'experience': exp_list})

        # 34. PROFESSIONAL PROFILES: ADD/DELETE PROJECTS API
        elif path == '/api/profile/projects':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)

            action = payload.get('action', 'ADD').upper()
            conn = get_db()
            cursor = conn.cursor()

            if action == 'ADD':
                p_name = sanitize_input(payload.get('projectName', '').strip())
                desc = sanitize_input(payload.get('description', '').strip())
                tech = sanitize_input(payload.get('technologies', '').strip())
                p_url = sanitize_input(payload.get('projectUrl', '').strip())
                gh_url = sanitize_input(payload.get('githubUrl', '').strip())

                if not p_name:
                    conn.close()
                    return self.send_json({'error': 'Project name required'}, 400)

                cursor.execute('''
                    INSERT INTO profile_projects (user_id, project_name, description, technologies, project_url, github_url)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (current_user['id'], p_name, desc, tech, p_url, gh_url))
            elif action == 'DELETE':
                proj_id = payload.get('id')
                cursor.execute('DELETE FROM profile_projects WHERE id = ? AND user_id = ?', (proj_id, current_user['id']))

            conn.commit()
            cursor.execute('SELECT id, project_name, description, technologies, project_url, github_url FROM profile_projects WHERE user_id = ?', (current_user['id'],))
            proj_list = [{'id': r[0], 'projectName': r[1], 'description': r[2], 'technologies': r[3], 'projectUrl': r[4], 'githubUrl': r[5]} for r in cursor.fetchall()]
            conn.close()
            return self.send_json({'success': True, 'projects': proj_list})

        # 35. PROFESSIONAL PROFILES: ADD/DELETE CERTIFICATIONS API
        elif path == '/api/profile/certifications':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)

            action = payload.get('action', 'ADD').upper()
            conn = get_db()
            cursor = conn.cursor()

            if action == 'ADD':
                c_name = sanitize_input(payload.get('certName', '').strip())
                org = sanitize_input(payload.get('issuingOrg', '').strip())
                i_date = sanitize_input(str(payload.get('issueDate', '')))
                c_id = sanitize_input(payload.get('credentialId', '').strip())
                c_url = sanitize_input(payload.get('credentialUrl', '').strip())

                if not c_name or not org:
                    conn.close()
                    return self.send_json({'error': 'Certification name and issuing organization required'}, 400)

                cursor.execute('''
                    INSERT INTO profile_certifications (user_id, cert_name, issuing_org, issue_date, credential_id, credential_url)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (current_user['id'], c_name, org, i_date, c_id, c_url))
            elif action == 'DELETE':
                cert_id = payload.get('id')
                cursor.execute('DELETE FROM profile_certifications WHERE id = ? AND user_id = ?', (cert_id, current_user['id']))

            conn.commit()
            cursor.execute('SELECT id, cert_name, issuing_org, issue_date, credential_id, credential_url FROM profile_certifications WHERE user_id = ?', (current_user['id'],))
            cert_list = [{'id': r[0], 'certName': r[1], 'issuingOrg': r[2], 'issueDate': r[3], 'credentialId': r[4], 'credentialUrl': r[5]} for r in cursor.fetchall()]
            conn.close()
            return self.send_json({'success': True, 'certifications': cert_list})

        # =====================================================================
        # RAPIDO POST ENDPOINTS
        # =====================================================================
        elif path == '/api/rapido/book':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)
            
            pickup = sanitize_input(payload.get('pickup', '').strip())
            dropoff = sanitize_input(payload.get('dropoff', '').strip())
            vehicle_type = sanitize_input(payload.get('vehicle_type', '').strip())
            try:
                fare = float(payload.get('fare', 0.0))
            except ValueError:
                fare = 0.0
            
            if not pickup or not dropoff or not vehicle_type:
                return self.send_json({'error': 'Missing required booking fields'}, 400)
            
            # Default mock parameters for solo simulation fallback
            import random
            captains = ['Siddharth M.', 'Ramesh G.', 'Mohan K.', 'Anand S.', 'Karan P.']
            ratings = [4.6, 4.7, 4.8, 4.9]
            captain_name = random.choice(captains)
            captain_rating = random.choice(ratings)
            vehicle_num = f"KA-03-EX-{random.randint(1000, 9999)}"
            otp = f"{random.randint(1000, 9999)}"
            
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO rapido_rides (user_id, pickup, dropoff, vehicle_type, fare, status, captain_name, captain_rating, otp, vehicle_number)
                VALUES (?, ?, ?, ?, ?, 'PENDING', ?, ?, ?, ?)
            ''', (current_user['id'], pickup, dropoff, vehicle_type, fare, captain_name, captain_rating, otp, vehicle_num))
            ride_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return self.send_json({
                'success': True,
                'ride_id': ride_id,
                'otp': otp,
                'captain': {
                    'name': captain_name,
                    'rating': captain_rating,
                    'vehicle_number': vehicle_num
                }
            })

        elif path == '/api/rapido/driver/accept':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)
            
            ride_id = payload.get('ride_id')
            if not ride_id:
                return self.send_json({'error': 'Missing ride_id'}, 400)
            
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT full_name FROM users WHERE id = ?', (current_user['id'],))
            driver_name = cursor.fetchone()[0] or "Captain Partner"
            
            import random
            vehicle_number = f"KA-51-EF-{random.randint(1000, 9999)}"
            captain_rating = 4.8
            
            cursor.execute('''
                UPDATE rapido_rides
                SET status = 'ACCEPTED', driver_id = ?, captain_name = ?, captain_rating = ?, vehicle_number = ?
                WHERE id = ? AND status = 'PENDING'
            ''', (current_user['id'], driver_name, captain_rating, vehicle_number, ride_id))
            conn.commit()
            conn.close()
            return self.send_json({'success': True})

        elif path == '/api/rapido/driver/update-status':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)
            
            ride_id = payload.get('ride_id')
            status = sanitize_input(payload.get('status', '').strip().upper())
            otp_entered = payload.get('otp')
            
            if not ride_id or not status:
                return self.send_json({'error': 'Missing ride_id or status'}, 400)
            
            conn = get_db()
            cursor = conn.cursor()
            
            # OTP validation on ride start
            if status == 'IN_PROGRESS':
                cursor.execute('SELECT otp FROM rapido_rides WHERE id = ?', (ride_id,))
                row = cursor.fetchone()
                if row and otp_entered:
                    db_otp = row[0]
                    if otp_entered != db_otp:
                        conn.close()
                        return self.send_json({'error': 'Invalid OTP'}, 400)
            
            cursor.execute('UPDATE rapido_rides SET status = ? WHERE id = ?', (status, ride_id))
            conn.commit()
            conn.close()
            return self.send_json({'success': True})

        elif path == '/api/rapido/driver/update-coords':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)
            
            ride_id = payload.get('ride_id')
            x = payload.get('x')
            y = payload.get('y')
            angle = payload.get('angle')
            
            if not ride_id:
                return self.send_json({'error': 'Missing ride_id'}, 400)
            
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('UPDATE rapido_rides SET driver_coords_x = ?, driver_coords_y = ?, driver_angle = ? WHERE id = ?', (x, y, angle, ride_id))
            conn.commit()
            conn.close()
            return self.send_json({'success': True})

        elif path == '/api/rapido/chat/send':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)
            
            ride_id = payload.get('ride_id')
            message = sanitize_input(payload.get('message', '').strip())
            
            if not ride_id or not message:
                return self.send_json({'error': 'Missing fields'}, 400)
            
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT full_name FROM users WHERE id = ?', (current_user['id'],))
            sender_name = cursor.fetchone()[0] or "User"
            
            cursor.execute('''
                INSERT INTO rapido_chats (ride_id, sender_id, sender_name, message)
                VALUES (?, ?, ?, ?)
            ''', (ride_id, current_user['id'], sender_name, message))
            conn.commit()
            conn.close()
            return self.send_json({'success': True})

        elif path == '/api/rapido/complete':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)
            
            ride_id = payload.get('ride_id')
            status = sanitize_input(payload.get('status', '').strip().upper())
            rating = payload.get('rating')
            comments = sanitize_input(payload.get('comments', '').strip())
            
            if not ride_id or not status:
                return self.send_json({'error': 'Missing ride_id or status'}, 400)
            
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('UPDATE rapido_rides SET status = ?, rating = ?, comments = ? WHERE id = ?', (status, rating, comments, ride_id))
            conn.commit()
            conn.close()
            
            return self.send_json({'success': True})

        elif path == '/api/rapido/driver/toggle':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)
            
            is_online = 1 if payload.get('is_online') else 0
            
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM rapido_driver_stats WHERE user_id = ?', (current_user['id'],))
            if not cursor.fetchone():
                cursor.execute('INSERT INTO rapido_driver_stats (user_id, is_online, total_earnings, total_rides) VALUES (?, ?, 0.0, 0)', (current_user['id'], is_online))
            else:
                cursor.execute('UPDATE rapido_driver_stats SET is_online = ? WHERE user_id = ?', (is_online, current_user['id']))
            conn.commit()
            conn.close()
            
            return self.send_json({'success': True, 'is_online': bool(is_online)})

        elif path == '/api/rapido/driver/add-earning':
            current_user = self.get_auth_user()
            if not current_user:
                return self.send_json({'error': 'Unauthorized'}, 401)
            
            try:
                fare = float(payload.get('fare', 0.0))
            except ValueError:
                fare = 0.0
                
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM rapido_driver_stats WHERE user_id = ?', (current_user['id'],))
            if not cursor.fetchone():
                cursor.execute('INSERT INTO rapido_driver_stats (user_id, is_online, total_earnings, total_rides) VALUES (?, 1, ?, 1)', (current_user['id'], fare))
            else:
                cursor.execute('UPDATE rapido_driver_stats SET total_earnings = total_earnings + ?, total_rides = total_rides + 1 WHERE user_id = ?', (fare, current_user['id']))
            conn.commit()
            conn.close()
            
            return self.send_json({'success': True})

        return self.send_json({'error': 'Endpoint not found'}, 404)

class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True

if __name__ == '__main__':
    init_db()
    backup_db()
    server = ThreadingTCPServer((HOST, PORT), EnterpriseRESTRequestHandler)
    print(f"[BOOT] Enterprise Server listening on {HOST}:{PORT} (Env: {APP_ENV})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        server.server_close()
