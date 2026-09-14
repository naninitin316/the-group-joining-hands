"""
The Group of Joining Hands - Database Module
============================================
SQLite Connection Manager, Schema Initializer, and Backup Engine
"""

import sqlite3
import os
import shutil
from datetime import datetime
from app.config.config import DB_FILE, BACKUP_DIR, DB_DIR
from app.helpers.security import hash_password

import urllib.parse
import hashlib

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

def get_db():
    """Retrieve SQLite database connection with a 30-second timeout."""
    db_dir = os.path.dirname(os.path.abspath(DB_FILE))
    if not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_FILE, timeout=30.0)
    conn.execute('PRAGMA journal_mode = WAL')
    conn.execute('PRAGMA foreign_keys = ON')
    return conn

def backup_db(custom_target_path: str = None) -> str:
    """Create timestamped backup copy of SQLite database."""
    try:
        if os.path.exists(DB_FILE):
            if not os.path.exists(BACKUP_DIR):
                os.makedirs(BACKUP_DIR, exist_ok=True)
            if custom_target_path:
                backup_path = custom_target_path
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = os.path.join(BACKUP_DIR, f"database_{timestamp}.db")
            
            # Using SQLite native backup API when possible for zero-lock live consistency
            src_conn = sqlite3.connect(DB_FILE)
            dst_conn = sqlite3.connect(backup_path)
            with dst_conn:
                src_conn.backup(dst_conn)
            dst_conn.close()
            src_conn.close()
            
            print(f"[SECURITY] Database backup created successfully: {backup_path}")
            return backup_path
    except Exception as e:
        print("[SECURITY] Database backup error:", e)
    return None

def restore_db(backup_file_path: str, target_db_file: str = None) -> bool:
    """
    Restore database from a verified backup file into target database path.
    Preserves all users, posts, comments, hashtags, mentions, messages, connections, events, and admin data.
    """
    if not os.path.exists(backup_file_path):
        print(f"[RESTORE ERROR] Backup file not found: {backup_file_path}")
        return False
        
    target_path = target_db_file if target_db_file else DB_FILE
    try:
        # Verify backup integrity first before applying
        if not verify_backup_integrity(backup_file_path):
            print(f"[RESTORE ERROR] Backup file failed integrity check: {backup_file_path}")
            return False
            
        target_dir = os.path.dirname(target_path)
        if target_dir and not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)
            
        src_conn = sqlite3.connect(backup_file_path)
        dst_conn = sqlite3.connect(target_path)
        with dst_conn:
            src_conn.backup(dst_conn)
        dst_conn.close()
        src_conn.close()
        
        print(f"[RESTORE SUCCESS] Database restored from {backup_file_path} to {target_path}")
        return True
    except Exception as e:
        print(f"[RESTORE ERROR] Failed to restore database: {e}")
        return False

def verify_backup_integrity(backup_file_path: str) -> bool:
    """
    Non-destructive integrity verification of a backup file.
    Validates SQLite file header, runs PRAGMA integrity_check, and verifies essential schema tables.
    """
    if not os.path.exists(backup_file_path):
        return False
        
    try:
        conn = sqlite3.connect(backup_file_path)
        cursor = conn.cursor()
        
        # 1. Run low-level SQLite integrity check
        cursor.execute("PRAGMA integrity_check")
        row = cursor.fetchone()
        if not row or row[0].lower() != "ok":
            conn.close()
            return False
            
        # 2. Verify all critical schema tables exist
        required_tables = {
            'users', 'sessions', 'connections', 'posts', 'post_likes', 
            'post_comments', 'hashtags', 'post_hashtags',
            'direct_messages', 'notifications', 'events', 'event_rsvps',
            'articles', 'saved_posts', 'login_history', 'issue_bugs',
            'reports', 'blocked_users', 'user_settings'
        }
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = {r[0] for r in cursor.fetchall()}
        
        missing_tables = required_tables - existing_tables
        conn.close()
        
        if missing_tables:
            print(f"[BACKUP VERIFICATION WARNING] Missing tables in backup: {missing_tables}")
            return False
            
        return True
    except Exception as e:
        print(f"[BACKUP VERIFICATION ERROR]: {e}")
        return False

def init_db():
    """Initialize database schemas, run migrations, and seed initial data."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            google_id TEXT,
            full_name TEXT NOT NULL,
            headline TEXT DEFAULT 'Community Member',
            avatar_url TEXT DEFAULT 'hero.jpg',
            bio TEXT DEFAULT '',
            is_admin INTEGER DEFAULT 0,
            status TEXT DEFAULT 'ACTIVE',
            role TEXT DEFAULT 'USER',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Safe Schema Migrations for Existing Database
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'ACTIVE'")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'USER'")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN email_verified INTEGER DEFAULT 1")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN location TEXT DEFAULT ''")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN cover_photo_url TEXT DEFAULT 'hero.jpg'")
    except Exception:
        pass

    # Safe Schema Migrations for user_settings
    try:
        cursor.execute("ALTER TABLE user_settings ADD COLUMN message_privacy TEXT DEFAULT 'everyone'")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE user_settings ADD COLUMN connect_privacy TEXT DEFAULT 'everyone'")
    except Exception:
        pass

    # Email Verification Tokens Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS email_verification_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token_hash TEXT UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_email_verif_token ON email_verification_tokens(token_hash)')

    # Password Reset Tokens Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token_hash TEXT UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_pass_reset_token ON password_reset_tokens(token_hash)')

    # Reports Table for Content & User Moderation
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_id INTEGER NOT NULL,
            target_type TEXT NOT NULL,
            target_id INTEGER NOT NULL,
            reason TEXT NOT NULL,
            status TEXT DEFAULT 'PENDING',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (reporter_id) REFERENCES users (id)
        )
    ''')

    # Login History Security Log Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS login_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            ip_address TEXT DEFAULT '127.0.0.1',
            status TEXT DEFAULT 'SUCCESS',
            login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Sessions Table (Legacy Token Compatibility)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Token Blacklist & Revocation Table (JWT Enterprise Security)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS token_blacklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jti TEXT UNIQUE NOT NULL,
            token_hash TEXT UNIQUE NOT NULL,
            user_id INTEGER,
            revoked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            reason TEXT DEFAULT 'Logout',
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_token_blacklist_jti ON token_blacklist(jti)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_token_blacklist_hash ON token_blacklist(token_hash)')

    # Connections / Network Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            requester_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            status TEXT DEFAULT 'PENDING',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (requester_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (receiver_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE(requester_id, receiver_id)
        )
    ''')
    cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_connections_pair ON connections(requester_id, receiver_id)')
    
    # Timeline Posts Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            media_url TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (author_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_posts_author_id ON posts(author_id)')

    # Post Likes Table (Enforces unique like per user per post)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS post_likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE(post_id, user_id)
        )
    ''')
    cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_post_likes_user ON post_likes(post_id, user_id)')

    # Post Comments Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS post_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            parent_id INTEGER DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_post_comments_post_id ON post_comments(post_id)')

    # Hashtags Master Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hashtags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Post Hashtags Junction Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS post_hashtags (
            post_id INTEGER NOT NULL,
            hashtag_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (post_id, hashtag_id),
            FOREIGN KEY (post_id) REFERENCES posts (id) ON DELETE CASCADE,
            FOREIGN KEY (hashtag_id) REFERENCES hashtags (id) ON DELETE CASCADE
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_post_hashtags_hashtag_id ON post_hashtags(hashtag_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_hashtags_tag ON hashtags(tag)')
    
    # Direct Messages Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS direct_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            message_text TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sender_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (receiver_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_dm_pair ON direct_messages(sender_id, receiver_id)')
    try:
        cursor.execute("ALTER TABLE direct_messages ADD COLUMN is_read INTEGER DEFAULT 0")
    except Exception:
        pass

    # Notifications Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            sender_id INTEGER DEFAULT NULL,
            notif_type TEXT NOT NULL,
            title TEXT NOT NULL,
            reference_id INTEGER DEFAULT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read)')
    try:
        cursor.execute("ALTER TABLE notifications ADD COLUMN reference_id INTEGER DEFAULT NULL")
    except Exception:
        pass

    # Saved Posts Table (Enforces unique bookmark per user per post)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS saved_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            post_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (post_id) REFERENCES posts (id) ON DELETE CASCADE,
            UNIQUE(user_id, post_id)
        )
    ''')
    cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_saved_posts_user ON saved_posts(user_id, post_id)')

    # Events Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            organizer_name TEXT NOT NULL,
            date_str TEXT NOT NULL,
            location TEXT NOT NULL,
            description TEXT NOT NULL,
            banner_url TEXT DEFAULT 'hero.jpg',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Event RSVPs Table (Enforces unique RSVP per user per event)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS event_rsvps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE(event_id, user_id)
        )
    ''')
    cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_event_rsvps_pair ON event_rsvps(event_id, user_id)')

    # Articles Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            cover_url TEXT DEFAULT 'hero.jpg',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (author_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')

    # Blocked Users Table (Enforces unique block pair)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS blocked_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            blocked_user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (blocked_user_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE(user_id, blocked_user_id)
        )
    ''')
    cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_blocked_pair ON blocked_users(user_id, blocked_user_id)')

    # Muted Users Table (Enforces unique mute pair)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS muted_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            muted_user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (muted_user_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE(user_id, muted_user_id)
        )
    ''')
    cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_muted_pair ON muted_users(user_id, muted_user_id)')

    # -------------------------------------------------------------
    # Professional Profiles Tables (Skills, Edu, Exp, Projects, Certs)
    # -------------------------------------------------------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS profile_skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            skill_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE(user_id, skill_name)
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_profile_skills_user ON profile_skills(user_id)')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS profile_education (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            institution TEXT NOT NULL,
            degree TEXT NOT NULL,
            field_of_study TEXT DEFAULT '',
            start_year TEXT DEFAULT '',
            end_year TEXT DEFAULT '',
            description TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_profile_edu_user ON profile_education(user_id)')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS profile_experience (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            company TEXT NOT NULL,
            position TEXT NOT NULL,
            location TEXT DEFAULT '',
            start_date TEXT DEFAULT '',
            end_date TEXT DEFAULT '',
            is_current INTEGER DEFAULT 0,
            description TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_profile_exp_user ON profile_experience(user_id)')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS profile_projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            project_name TEXT NOT NULL,
            description TEXT DEFAULT '',
            technologies TEXT DEFAULT '',
            project_url TEXT DEFAULT '',
            github_url TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_profile_proj_user ON profile_projects(user_id)')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS profile_certifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            cert_name TEXT NOT NULL,
            issuing_org TEXT NOT NULL,
            issue_date TEXT DEFAULT '',
            credential_id TEXT DEFAULT '',
            credential_url TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_profile_cert_user ON profile_certifications(user_id)')

    # User Settings & Preferences Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            theme TEXT DEFAULT 'light',
            language TEXT DEFAULT 'en',
            privacy TEXT DEFAULT 'public',
            message_privacy TEXT DEFAULT 'everyone',
            connect_privacy TEXT DEFAULT 'everyone',
            notifications_enabled INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Workflow Issue & Bug Tracker Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS issue_bugs (
            id TEXT PRIMARY KEY,
            module TEXT NOT NULL,
            title TEXT NOT NULL,
            priority TEXT DEFAULT 'HIGH',
            status TEXT DEFAULT 'STABLE',
            fix_date TEXT,
            regression_status TEXT DEFAULT 'PASSED'
        )
    ''')

    # Rapido Rides table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rapido_rides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            pickup TEXT NOT NULL,
            dropoff TEXT NOT NULL,
            vehicle_type TEXT NOT NULL,
            fare REAL NOT NULL,
            status TEXT NOT NULL,
            captain_name TEXT,
            captain_rating REAL,
            rating INTEGER,
            comments TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            driver_id INTEGER,
            otp TEXT,
            vehicle_number TEXT,
            driver_coords_x REAL,
            driver_coords_y REAL,
            driver_angle REAL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Alter table to support existing tables
    import sqlite3
    for col, col_type in [("driver_id", "INTEGER"), ("otp", "TEXT"), ("vehicle_number", "TEXT"), ("driver_coords_x", "REAL"), ("driver_coords_y", "REAL"), ("driver_angle", "REAL")]:
        try:
            cursor.execute(f"ALTER TABLE rapido_rides ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError:
            pass

    # Rapido Chats table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rapido_chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ride_id INTEGER NOT NULL,
            sender_id INTEGER NOT NULL,
            sender_name TEXT,
            message TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Rapido Driver (Captain) Stats table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rapido_driver_stats (
            user_id INTEGER PRIMARY KEY,
            is_online INTEGER DEFAULT 0,
            total_earnings REAL DEFAULT 0.0,
            total_rides INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Create default demo user if not exists
    cursor.execute('SELECT * FROM users WHERE email = ?', ('member@joininghands.org',))
    if not cursor.fetchone():
        demo_pass_hash = hash_password('demo1234')
        cursor.execute('''
            INSERT INTO users (email, password_hash, full_name, headline, avatar_url, bio, is_admin, role)
            VALUES (?, ?, ?, ?, ?, ?, 1, 'SUPER_ADMINISTRATOR')
        ''', ('member@joininghands.org', demo_pass_hash, 'Joining Hands Leader', 'Leader & Developer at The Group of Joining Hands', 'hero.jpg', 'Active participant in The Group of Joining Hands community.'))
    else:
        cursor.execute("UPDATE users SET is_admin = 1, role = 'SUPER_ADMINISTRATOR', avatar_url = 'hero.jpg' WHERE email = 'member@joininghands.org'")

    # Seed Sample Community Members
    sample_users = [
        ('ramesh@joininghands.org', 'Dr. Ramesh Kumar', 'Community Lead & Cultural Director', 'Dedicated to cultural preservation and community welfare.'),
        ('priya@joininghands.org', 'Priya Sharma', 'Event Lead & Strategist', 'Organizing community gatherings and youth leadership initiatives.'),
        ('anil@joininghands.org', 'Anil Mehta', 'Senior Systems Architect', 'Passionate about open technology and community empowerment.'),
        ('sunita@joininghands.org', 'Sunita Rao', 'Creative Director & Designer', 'Crafting visual stories for community unity.'),
        ('vikram@joininghands.org', 'Vikram Singh', 'Social Initiatives Director', 'Driving social outreach and youth empowerment projects.')
    ]

    for email, name, headline, bio in sample_users:
        cursor.execute('SELECT id, avatar_url FROM users WHERE email = ?', (email,))
        row = cursor.fetchone()
        distinct_avatar = generate_default_avatar(name)
        if not row:
            pass_hash = hash_password('demo1234')
            cursor.execute('''
                INSERT INTO users (email, password_hash, full_name, headline, avatar_url, bio)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (email, pass_hash, name, headline, distinct_avatar, bio))
        elif row[1] == 'hero.jpg':
            cursor.execute('UPDATE users SET avatar_url = ? WHERE email = ?', (distinct_avatar, email))
    
    # Seed Initial Notifications if empty
    cursor.execute('SELECT COUNT(*) FROM notifications')
    if cursor.fetchone()[0] == 0:
        cursor.execute('SELECT id FROM users WHERE email = ?', ('member@joininghands.org',))
        leader = cursor.fetchone()
        cursor.execute('SELECT id FROM users WHERE email = ?', ('ramesh@joininghands.org',))
        ramesh = cursor.fetchone()
        cursor.execute('SELECT id FROM users WHERE email = ?', ('priya@joininghands.org',))
        priya = cursor.fetchone()

        if leader and ramesh and priya:
            cursor.execute('''
                INSERT INTO notifications (user_id, sender_id, notif_type, title)
                VALUES (?, ?, 'CONNECTION', 'sent you a connection request.')
            ''', (leader[0], priya[0]))
            cursor.execute('''
                INSERT INTO notifications (user_id, sender_id, notif_type, title)
                VALUES (?, ?, 'LIKE', 'liked your community post.')
            ''', (leader[0], ramesh[0]))
            cursor.execute('''
                INSERT INTO notifications (user_id, sender_id, notif_type, title)
                VALUES (?, ?, 'PROFILE_VIEW', 'viewed your profile.')
            ''', (leader[0], ramesh[0]))
            cursor.execute('''
                INSERT INTO notifications (user_id, sender_id, notif_type, title)
                VALUES (?, ?, 'EVENT_REMINDER', 'Reminder: Annual Cultural & Spiritual Gathering starts soon!')
            ''', (leader[0], ramesh[0]))

    # Seed Initial Issue & Bug Tracker records if empty
    cursor.execute('SELECT COUNT(*) FROM issue_bugs')
    if cursor.fetchone()[0] == 0:
        seed_bugs = [
            ('BUG-101', 'Core System / Auth', 'Authentication Engine & Google OAuth', 'HIGH', 'COMPLETED', '2026-08-06', 'PASSED'),
            ('BUG-102', 'Social Engine / Posts', 'Timeline Feed & Local Photo Uploads', 'CRITICAL', 'STABLE', '2026-08-06', 'PASSED'),
            ('BUG-103', 'Communication / Chat', 'Real-Time Direct Messaging Drawer', 'MEDIUM', 'STABLE', '2026-08-06', 'PASSED'),
            ('BUG-104', 'Communication / Notifs', 'Expanded 8-Type Notification Engine', 'HIGH', 'STABLE', '2026-08-06', 'PASSED'),
            ('BUG-105', 'Administration / Settings', 'Settings, Privacy & Security Engine', 'HIGH', 'STABLE', '2026-08-06', 'PASSED'),
            ('BUG-106', 'Content / Events & Gallery', 'GramConnect Lightbox & Events RSVP', 'MEDIUM', 'STABLE', '2026-08-06', 'PASSED')
        ]
        for b_id, mod, title, prio, stat, f_date, reg_stat in seed_bugs:
            cursor.execute('''
                INSERT INTO issue_bugs (id, module, title, priority, status, fix_date, regression_status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (b_id, mod, title, prio, stat, f_date, reg_stat))

    # Seed Initial Events if empty
    cursor.execute('SELECT COUNT(*) FROM events')
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO events (title, organizer_name, date_str, location, description, banner_url)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ("Annual Cultural & Spiritual Gathering 2026", "Dr. Ramesh Kumar", "Aug 25, 2026 • 5:00 PM", "Community Cultural Auditorium", "Join us for our flagship annual gathering celebrating unity, traditional music, and sacred art.", "hero.jpg"))
        cursor.execute('''
            INSERT INTO events (title, organizer_name, date_str, location, description, banner_url)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ("Youth Leadership & Tech Workshop", "Priya Sharma", "Sep 10, 2026 • 10:00 AM", "Joining Hands Innovation Center", "Empowering the next generation of community leaders through tech and collaboration.", "hero.jpg"))

    # Seed Initial Articles if empty
    cursor.execute('SELECT COUNT(*) FROM articles')
    if cursor.fetchone()[0] == 0:
        cursor.execute('SELECT id FROM users WHERE email = ?', ('member@joininghands.org',))
        leader = cursor.fetchone()
        if leader:
            cursor.execute('''
                INSERT INTO articles (title, author_id, content, cover_url)
                VALUES (?, ?, ?, ?)
            ''', ("The Group of Joining Hands Blueprint 2026", leader[0], "Our vision for 2026 centers on fostering digital harmony, economic empowerment, and sacred cultural preservation across all community chapters.", "hero.jpg"))
    
    # Seed Initial Timeline Posts if empty
    cursor.execute('SELECT COUNT(*) FROM posts')
    if cursor.fetchone()[0] == 0:
        cursor.execute('SELECT id FROM users WHERE email = ?', ('member@joininghands.org',))
        leader = cursor.fetchone()
        cursor.execute('SELECT id FROM users WHERE email = ?', ('ramesh@joininghands.org',))
        ramesh = cursor.fetchone()
        cursor.execute('SELECT id FROM users WHERE email = ?', ('priya@joininghands.org',))
        priya = cursor.fetchone()

        if leader and ramesh and priya:
            cursor.execute('''
                INSERT INTO posts (author_id, content, media_url)
                VALUES (?, ?, ?)
            ''', (leader[0], 'Welcome to The Group of Joining Hands community platform! Together Forever.', 'hero.jpg'))
            cursor.execute('''
                INSERT INTO posts (author_id, content, media_url)
                VALUES (?, ?, NULL)
            ''', (ramesh[0], 'Honored to lead our cultural preservation initiatives. Looking forward to our upcoming 2026 gatherings!'))
            cursor.execute('''
                INSERT INTO posts (author_id, content, media_url)
                VALUES (?, ?, NULL)
            ''', (priya[0], 'Excited to launch our Youth Leadership & Tech workshops next month! Join us.'))

            cursor.execute('SELECT id FROM posts LIMIT 1')
            first_post = cursor.fetchone()
            if first_post:
                cursor.execute('INSERT INTO post_likes (post_id, user_id) VALUES (?, ?)', (first_post[0], ramesh[0]))
                cursor.execute('INSERT INTO post_likes (post_id, user_id) VALUES (?, ?)', (first_post[0], priya[0]))
                cursor.execute('''
                    INSERT INTO post_comments (post_id, user_id, content)
                    VALUES (?, ?, ?)
                ''', (first_post[0], ramesh[0], 'Incredible initiative! Proud to be part of Joining Hands.'))

    # Seed Initial Direct Messages if empty
    cursor.execute('SELECT COUNT(*) FROM direct_messages')
    if cursor.fetchone()[0] == 0:
        cursor.execute('SELECT id FROM users WHERE email = ?', ('member@joininghands.org',))
        leader = cursor.fetchone()
        cursor.execute('SELECT id FROM users WHERE email = ?', ('ramesh@joininghands.org',))
        ramesh = cursor.fetchone()

        if leader and ramesh:
            cursor.execute('''
                INSERT INTO direct_messages (sender_id, receiver_id, message_text)
                VALUES (?, ?, ?)
            ''', (ramesh[0], leader[0], "Namaste! Welcome to Joining Hands messaging."))
            cursor.execute('''
                INSERT INTO direct_messages (sender_id, receiver_id, message_text)
                VALUES (?, ?, ?)
            ''', (leader[0], ramesh[0], "Thank you Dr. Ramesh! Together Forever."))

    # Clean non-admin avatars: ensure any user except ID 1 / member@joininghands.org has a distinct SVG avatar if their avatar_url is 'hero.jpg' or empty
    cursor.execute("SELECT id, full_name, email, avatar_url FROM users WHERE email != 'member@joininghands.org' AND id != 1")
    non_admin_users = cursor.fetchall()
    for uid, u_name, u_email, u_avatar in non_admin_users:
        if not u_avatar or u_avatar == 'hero.jpg':
            distinct_svg = generate_default_avatar(u_name)
            cursor.execute("UPDATE users SET avatar_url = ? WHERE id = ?", (distinct_svg, uid))

    conn.commit()
    conn.close()
    print("[DATABASE] Database, tables & seed initial data initialized successfully.")
