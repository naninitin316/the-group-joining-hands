"""
The Group of Joining Hands - Clean & Simple Project Overview PDF Generator
========================================================================
Generates an easy-to-read, clean 3-page summary document:
- Page 1: What the project is, what it does (modules), and the tech stack used
- Page 2: Core frontend SPA routing and backend request handling (with clean code snippets)
- Page 3: User authentication (JWT), database storage/backups, deployment, and key takeaways
"""

import os
import html
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.pdfgen import canvas
import pymupdf
import pygments
from pygments.lexers import PythonLexer, JavascriptLexer
from pygments.token import Token

PDF_PATH = "Joining_Hands_Project_Overview.pdf"

# Clean, elegant color palette
C_PRIMARY = colors.HexColor("#1e293b")      # Deep Slate (Title & Headers)
C_ACCENT_BLUE = colors.HexColor("#2563eb")  # Vibrant Blue
C_ACCENT_PURPLE = colors.HexColor("#7c3aed")# Elegant Purple
C_ACCENT_AMBER = colors.HexColor("#d97706") # Amber / Warm Gold
C_ACCENT_GREEN = colors.HexColor("#059669") # Emerald Green
C_TEXT = colors.HexColor("#1e293b")         # Main Text
C_TEXT_MUTED = colors.HexColor("#475569")   # Subtext / Muted Text
C_CARD_BG = colors.HexColor("#f8fafc")      # Soft Light Grey Card
C_BORDER = colors.HexColor("#e2e8f0")       # Border Line
C_CODE_BG = colors.HexColor("#0f172a")      # Dark Slate for Code
C_CODE_BAR = colors.HexColor("#1e293b")     # Code Titlebar

TOKEN_COLOR_MAP = {
    Token.Keyword: "#38bdf8",            # Sky Blue
    Token.Keyword.Constant: "#fbbf24",   # Amber
    Token.Name.Function: "#a78bfa",      # Lavender Purple
    Token.Name.Builtin: "#f472b6",       # Pink
    Token.String: "#34d399",             # Emerald
    Token.Number: "#fbbf24",             # Gold
    Token.Comment: "#94a3b8",            # Slate Grey
    Token.Operator: "#e2e8f0",           # Crisp White/Grey
    Token.Punctuation: "#94a3b8",
}


def highlight_code(code_str: str, lexer) -> str:
    """Highlight code using Pygments into ReportLab font tags."""
    tokens = pygments.lex(code_str.strip(), lexer)
    out = []
    for ttype, val in tokens:
        curr = ttype
        color = None
        while curr:
            if curr in TOKEN_COLOR_MAP:
                color = TOKEN_COLOR_MAP[curr]
                break
            curr = curr.parent
        escaped = html.escape(val).replace(' ', '&nbsp;').replace('\n', '<br/>')
        if color and escaped.strip() and escaped not in ('<br/>', '&nbsp;'):
            out.append(f'<font color="{color}">{escaped}</font>')
        else:
            out.append(escaped)
    return ''.join(out)


def create_code_card(code_str: str, lexer, file_label: str, tag: str, usable_w: float, code_style, bar_style):
    """Creates a clean IDE-style code box with header and syntax highlighting."""
    highlighted = highlight_code(code_str, lexer)
    
    dots = '<font color="#ef4444">&bull;</font> <font color="#f59e0b">&bull;</font> <font color="#10b981">&bull;</font>&nbsp;&nbsp;<b>' + file_label + '</b>'
    badge = f'<font color="#38bdf8"><b>[{tag}]</b></font>'
    
    header_table = Table([[Paragraph(dots, bar_style), Paragraph(badge, bar_style)]], colWidths=[usable_w * 0.75, usable_w * 0.25])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), C_CODE_BAR),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    
    body_table = Table([[Paragraph(highlighted, code_style)]], colWidths=[usable_w])
    body_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), C_CODE_BG),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    full_table = Table([[header_table], [body_table]], colWidths=[usable_w])
    full_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.7, colors.HexColor("#334155")),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    return full_table


class SimpleNumberedCanvas(canvas.Canvas):
    """Adds running headers and footers with Page X of Y."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            super().showPage()
        super().save()

    def draw_header_footer(self, total_pages):
        self.saveState()
        page_w, page_h = A4

        # Header for pages 2 and 3
        if self._pageNumber > 1:
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(C_TEXT_MUTED)
            self.drawString(38, page_h - 26, "The Group of Joining Hands — Project Overview & Code Highlights")
            self.drawRightString(page_w - 38, page_h - 26, "Together Forever")
            self.setStrokeColor(C_BORDER)
            self.setLineWidth(0.6)
            self.line(38, page_h - 30, page_w - 38, page_h - 30)

        # Footer for all pages
        self.setStrokeColor(C_BORDER)
        self.setLineWidth(0.6)
        self.line(38, 32, page_w - 38, 32)

        self.setFont("Helvetica", 8)
        self.setFillColor(C_TEXT_MUTED)
        self.drawString(38, 20, "The Group of Joining Hands \u2022 Web Ecosystem Overview")
        page_str = f"Page {self._pageNumber} of {total_pages}"
        self.drawRightString(page_w - 38, 20, page_str)

        self.restoreState()


def generate_simple_pdf():
    margin = 38
    doc = SimpleDocTemplate(
        PDF_PATH,
        pagesize=A4,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=36,
        bottomMargin=38
    )

    styles = getSampleStyleSheet()

    # Typography styles
    s_title = ParagraphStyle(
        'MainTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.white,
        spaceAfter=3
    )
    s_subtitle = ParagraphStyle(
        'SubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#cbd5e1")
    )
    s_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=C_PRIMARY,
        spaceBefore=7,
        spaceAfter=4
    )
    s_subheading = ParagraphStyle(
        'SectionSubheading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=12,
        textColor=C_ACCENT_BLUE,
        spaceBefore=4,
        spaceAfter=2
    )
    s_body = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.3,
        leading=11.2,
        textColor=C_TEXT,
        spaceAfter=3
    )
    s_callout = ParagraphStyle(
        'CalloutText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.8,
        leading=10.2,
        textColor=C_TEXT
    )
    s_th = ParagraphStyle(
        'TH',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.8,
        leading=9.5,
        textColor=colors.white
    )
    s_td = ParagraphStyle(
        'TD',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.4,
        leading=9.4,
        textColor=C_TEXT
    )
    s_td_bold = ParagraphStyle(
        'TDBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.4,
        leading=9.4,
        textColor=C_TEXT
    )
    s_code = ParagraphStyle(
        'CodeText',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=6.8,
        leading=8.6,
        textColor=colors.HexColor("#e2e8f0")
    )
    s_code_bar = ParagraphStyle(
        'CodeBarText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.2,
        leading=9.0,
        textColor=colors.HexColor("#94a3b8")
    )

    usable_w = A4[0] - (margin * 2)  # ~519 pt

    story = []

    # =========================================================================
    # PAGE 1: WHAT IT IS, WHAT IT DOES, AND TECH STACK
    # =========================================================================

    # Title Card
    header_html = """
    <b>The Group of Joining Hands</b> &nbsp;|&nbsp; <font color="#f59e0b">"Together Forever"</font><br/>
    <font size="13"><b>Project Overview, Architecture & Core Code Highlights</b></font>
    """
    sub_html = "A modular multi-application web ecosystem built using pure vanilla technologies and Python standard library."
    
    title_table = Table(
        [[Paragraph(header_html, s_title)], [Paragraph(sub_html, s_subtitle)]],
        colWidths=[usable_w]
    )
    title_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), C_PRIMARY),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('LINEBELOW', (0, 0), (0, 0), 1, C_ACCENT_BLUE),
    ]))
    story.append(title_table)
    story.append(Spacer(1, 5))

    # Section 1: What is this project?
    story.append(Paragraph("1. What is this Project?", s_heading))
    desc = """
    <b>The Group of Joining Hands</b> is a modular web ecosystem that brings several different applications 
    together into one single, cohesive website. Instead of building separate disconnected apps or relying on heavy 
    modern frontend frameworks (like React, Next.js, or Angular), this project follows a strict <b>"Pure Vanilla" philosophy</b>. 
    It delivers an ultra-fast, cinematic user experience with zero monthly hosting fees, instant page loading, and interactive 3D elements.
    """
    story.append(Paragraph(desc, s_body))
    story.append(Spacer(1, 3))

    # Section 2: What Does it Do? (Core Applications)
    story.append(Paragraph("2. What Does It Do? (Core Applications)", s_heading))
    apps_desc = """
    The landing page features interactive 3D floating tiles that tilt when you hover over them. Clicking any tile launches 
    a specialized single-page application (SPA) dynamically without reloading the webpage:
    """
    story.append(Paragraph(apps_desc, s_body))

    app_modules = [
        [
            Paragraph("Application", s_th),
            Paragraph("Tile Color", s_th),
            Paragraph("What it Does & Key Features", s_th)
        ],
        [
            Paragraph("<b>Purple Mobility</b>", s_td_bold),
            Paragraph("Purple Glass", s_td),
            Paragraph("A city transit & ride-hailing portal. Provides interactive live maps for riders and drivers, fare estimation, and route tracking.", s_td)
        ],
        [
            Paragraph("<b>Blue Professional</b>", s_td_bold),
            Paragraph("Corporate Blue", s_td),
            Paragraph("A full professional networking network (similar to LinkedIn). Features a real-time post feed, hashtag indexing (#tag), user mentions (@user), rich comments, likes, and member profiles.", s_td)
        ],
        [
            Paragraph("<b>Saffron Cultural (Red App)</b>", s_td_bold),
            Paragraph("Saffron Red", s_td),
            Paragraph("A cultural showcase featuring continuously flowing historical portraits, interactive biographical cards, and a built-in voice-synthesized AI assistant.", s_td)
        ],
        [
            Paragraph("<b>Visual Stories Portal</b>", s_td_bold),
            Paragraph("Sunset Gradient", s_td),
            Paragraph("A photo and story-sharing community feed designed to highlight community moments and shared memories with admin-moderated submissions.", s_td)
        ],
        [
            Paragraph("<b>Admin Governance Dashboard</b>", s_td_bold),
            Paragraph("Dark Glass", s_td),
            Paragraph("A protected control panel for administrators to monitor live server health, download automated SQLite database backups, and manage user accounts.", s_td)
        ]
    ]

    apps_table = Table(app_modules, colWidths=[usable_w * 0.25, usable_w * 0.17, usable_w * 0.58])
    apps_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), C_PRIMARY),
        ('GRID', (0, 0), (-1, -1), 0.5, C_BORDER),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, C_CARD_BG]),
        ('TOPPADDING', (0, 0), (-1, -1), 3.2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.2),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(apps_table)
    story.append(Spacer(1, 5))

    # Section 3: Technology Stack
    story.append(Paragraph("3. Tools & Technologies Used (Tech Stack)", s_heading))

    tech_stack = [
        [
            Paragraph("Layer", s_th),
            Paragraph("Technology", s_th),
            Paragraph("Role & Why It Was Chosen", s_th)
        ],
        [
            Paragraph("<b>Frontend</b>", s_td_bold),
            Paragraph("HTML5, CSS3, Vanilla JavaScript", s_td),
            Paragraph("No frameworks or bundlers. Modern CSS variables, glassmorphism, 3D perspective tilts, and native ES6+ for instant rendering and zero load time.", s_td)
        ],
        [
            Paragraph("<b>Backend</b>", s_td_bold),
            Paragraph("Python 3 (Standard Library)", s_td),
            Paragraph("Uses Python's built-in <code>http.server</code> and <code>socketserver</code>. Multi-threaded, lightweight (~40MB RAM), and handles all REST API requests without Flask or Django overhead.", s_td)
        ],
        [
            Paragraph("<b>Database</b>", s_td_bold),
            Paragraph("SQLite3 (WAL Mode)", s_td),
            Paragraph("Self-contained relational database with Write-Ahead Logging (WAL) for concurrent reads/writes and automated zero-downtime backups.", s_td)
        ],
        [
            Paragraph("<b>Authentication</b>", s_td_bold),
            Paragraph("Custom JWT + PBKDF2 Hashing", s_td),
            Paragraph("Pure Python JSON Web Token generator (HMAC-SHA256) and PBKDF2 password hashing (600,000 rounds) for enterprise-grade login security.", s_td)
        ],
        [
            Paragraph("<b>Hosting & CI/CD</b>", s_td_bold),
            Paragraph("GoDaddy cPanel + GitHub Actions", s_td),
            Paragraph("Automated FTP deployment on git push to the <code>Godaddy</code> branch, with automatic Phusion Passenger cache reloading.", s_td)
        ]
    ]

    tech_table = Table(tech_stack, colWidths=[usable_w * 0.18, usable_w * 0.28, usable_w * 0.54])
    tech_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), C_ACCENT_BLUE),
        ('GRID', (0, 0), (-1, -1), 0.5, C_BORDER),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, C_CARD_BG]),
        ('TOPPADDING', (0, 0), (-1, -1), 3.2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.2),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(tech_table)

    story.append(PageBreak())

    # =========================================================================
    # PAGE 2: HOW IT WORKS & CORE FUNCTIONALITY (FRONTEND & BACKEND CODE)
    # =========================================================================

    story.append(Paragraph("4. Core Functionality & Important Code Snippets", s_heading))
    story.append(Paragraph(
        "The project's functionality is powered by focused, clean modules. Below are the key implementations "
        "that drive the frontend Single-Page Application and the backend API server.", s_body
    ))
    story.append(Spacer(1, 3))

    # Functionality 1: Frontend SPA Router
    story.append(Paragraph("A. Single-Page Application (SPA) View Router (static/js/script.js)", s_subheading))
    story.append(Paragraph(
        "<b>What it does:</b> When a user clicks a tile on the home screen, instead of refreshing the webpage or navigating "
        "to another URL, this JavaScript function smoothly hides previous screens and displays the requested app with a fade-in animation.", s_body
    ))

    code_spa = """// Switches active views dynamically without page reloads
function showView(viewId) {
    // Hide all existing open views
    document.querySelectorAll(".view-active, .app-view").forEach(el => {
        el.classList.remove("active");
        el.style.display = "none";
    });

    // Reveal the requested application view and reset scroll
    const targetView = document.getElementById(viewId);
    if (targetView) {
        targetView.style.display = (viewId === "insta-view") ? "flex" : "block";
        targetView.classList.add("active");
        window.scrollTo(0, 0);
    }
}

// Example: Opening the Professional Network with login checks
function openLinkedinClone() {
    if (checkAppLock()) return;
    showView("pro-network-view");
    if (isProLoggedIn) {
        showProStage("pro-main-stage");
    } else {
        showProStage("pro-login-stage");
    }
}"""

    story.append(create_code_card(code_spa, JavascriptLexer(), "static/js/script.js", "VANILLA JAVASCRIPT", usable_w, s_code, s_code_bar))
    story.append(Spacer(1, 6))

    # Functionality 2: Backend API & JSON Request Handler
    story.append(Paragraph("B. Backend REST Request Handler & JSON Response (server.py)", s_subheading))
    story.append(Paragraph(
        "<b>What it does:</b> Built directly on Python's <code>http.server</code>, this custom handler routes incoming HTTP requests, "
        "checks client authentication headers for a valid JWT token, and returns compressed JSON responses.", s_body
    ))

    code_server = """class EnterpriseRESTRequestHandler(http.server.SimpleHTTPRequestHandler):
    
    # Helper to send JSON responses with optional Gzip compression
    def send_json(self, data, status=200):
        body = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # Validates Authorization: Bearer <token> from incoming requests
    def get_auth_user(self):
        auth_header = self.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
        token = auth_header.split(' ')[1].strip()
        is_valid, payload, err = verify_jwt(token)
        return payload if is_valid else None"""

    story.append(create_code_card(code_server, PythonLexer(), "server.py", "PYTHON 3 (HTTP SERVER)", usable_w, s_code, s_code_bar))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 3: AUTHENTICATION, DATABASE BACKUPS, DEPLOYMENT & SUMMARY
    # =========================================================================

    story.append(Paragraph("5. Security, Database Storage & Automated Deployment", s_heading))
    story.append(Paragraph(
        "Here are the core implementations for user security, database persistence, and automated cloud deployment.", s_body
    ))
    story.append(Spacer(1, 3))

    # Functionality 3: JWT Token Generation
    story.append(Paragraph("A. Pure-Python JWT Token Generator (app/helpers/jwt_auth.py)", s_subheading))
    story.append(Paragraph(
        "<b>What it does:</b> Creates RFC 7519 JSON Web Tokens (HS256) entirely with Python's standard <code>hashlib</code> and "
        "<code>hmac</code> modules. No heavy external auth libraries required.", s_body
    ))

    code_jwt = """# Generates an RFC-compliant JWT token signed with HMAC-SHA256
def generate_jwt(user_id: int, email: str, role: str = "member", 
                 is_admin: bool = False, full_name: str = "", expires_in: int = 86400) -> str:
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": str(user_id), "email": email, "role": role,
        "is_admin": bool(is_admin), "name": full_name,
        "iat": now, "exp": now + expires_in, "iss": "joining-hands-auth-v1"
    }
    # Encode URL-safe Base64 and compute cryptographic signature
    enc_header = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
    enc_payload = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
    signing_input = f"{enc_header}.{enc_payload}".encode('utf-8')
    signature = hmac.new(EFFECTIVE_JWT_SECRET.encode('utf-8'), signing_input, hashlib.sha256).digest()
    enc_sig = base64.urlsafe_b64encode(signature).decode().rstrip('=')
    
    return f"{enc_header}.{enc_payload}.{enc_sig}" """

    story.append(create_code_card(code_jwt, PythonLexer(), "app/helpers/jwt_auth.py", "PYTHON 3 (CRYPTOGRAPHY)", usable_w, s_code, s_code_bar))
    story.append(Spacer(1, 5))

    # Functionality 4: SQLite Connection & Live Backup
    story.append(Paragraph("B. Database Connection & Live Zero-Lock Backup (app/database/db.py)", s_subheading))
    story.append(Paragraph(
        "<b>What it does:</b> Configures SQLite with Write-Ahead Logging (WAL) for fast concurrent access, "
        "and uses SQLite's native C-backup API to create automated live backups without locking the database.", s_body
    ))

    code_db = """# Connect to database with WAL mode for speed and durability
def get_db():
    conn = sqlite3.connect(DB_FILE, timeout=30.0)
    conn.execute('PRAGMA journal_mode = WAL')
    conn.execute('PRAGMA foreign_keys = ON')
    return conn

# Creates a timestamped live backup without locking active users out
def backup_db():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"database_{timestamp}.db")
    src_conn = sqlite3.connect(DB_FILE)
    dst_conn = sqlite3.connect(backup_path)
    with dst_conn:
        src_conn.backup(dst_conn)  # Online streaming backup
    dst_conn.close(); src_conn.close()
    return backup_path"""

    story.append(create_code_card(code_db, PythonLexer(), "app/database/db.py", "PYTHON 3 (SQLITE)", usable_w, s_code, s_code_bar))
    story.append(Spacer(1, 5))

    # Section 6: Deployment & Key Takeaways
    story.append(Paragraph("6. Automated Deployment & Summary", s_heading))

    summary_text = """
    <b>Automated GitHub Actions CI/CD:</b> Whenever code is pushed to the <code>Godaddy</code> branch, a GitHub Actions workflow 
    (<code>.github/workflows/deploy.yml</code>) triggers an FTP sync to the GoDaddy server and updates <code>tmp/restart.txt</code>. 
    This automatically signals Phusion Passenger to reload the Python server without downtime.<br/><br/>
    <b>Key Takeaways:</b>
    <br/>&bull; <b>Fast & Lightweight:</b> Zero framework dependencies means pages load in under 50ms with a tiny memory footprint.
    <br/>&bull; <b>Zero Cloud Fees:</b> Standard library architecture runs completely on standard cPanel hosting with no monthly SaaS bills.
    <br/>&bull; <b>Enterprise Security:</b> Industry-standard password hashing, JWT sessions, and automated database backups built right in.
    """
    summary_table = Table([[Paragraph(summary_text, s_callout)]], colWidths=[usable_w])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), C_CARD_BG),
        ('BOX', (0, 0), (-1, -1), 0.8, C_ACCENT_GREEN),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(summary_table)

    # Build Document
    doc.build(story, canvasmaker=SimpleNumberedCanvas)
    print(f"Simple PDF generated successfully at: {os.path.abspath(PDF_PATH)}")


def verify_simple_pdf():
    doc = pymupdf.open(PDF_PATH)
    page_count = doc.page_count
    print(f"Total Page Count: {page_count}")
    for i in range(page_count):
        page = doc.load_page(i)
        pix = page.get_pixmap(dpi=150)
        img_path = f"simple_page_{i+1}_preview.png"
        pix.save(img_path)
        print(f"Saved {img_path} ({pix.width}x{pix.height})")
    return page_count


if __name__ == "__main__":
    generate_simple_pdf()
    verify_simple_pdf()
