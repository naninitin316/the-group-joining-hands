# The Group of Joining Hands - Ecosystem Documentation

## 1. Project Overview
"The Group of Joining Hands" is a modular web ecosystem designed to provide multiple interconnected applications (social, professional, and cultural) from a single unified landing interface. The project follows a strict "Pure Vanilla" development philosophy, utilizing raw HTML, CSS, JavaScript, and Python without heavy modern frontend frameworks (like React or Angular) to ensure lightning-fast performance and a hand-crafted cinematic user experience.

- **Slogan:** "Together Forever"
- **Design Philosophy:** Pure white minimalist landing page, vibrant 3D floating tiles, and cinematic micro-interactions.

---

## 2. Technology Stack
- **Frontend:** Vanilla HTML5, CSS3, JavaScript (ES6+).
- **Backend:** Python 3 (`server.py`) utilizing `http.server` and `socketserver` for a custom Enterprise REST API.
- **Database:** SQLite3 (`database.db`) with automated backups.
- **Authentication:** JWT (JSON Web Tokens) with custom middleware.
- **Hosting:** GoDaddy cPanel (Shared/VPS) via Phusion Passenger.
- **CI/CD Pipeline:** GitHub Actions automated FTP Deployment.

---

## 3. The Ecosystem Applications (Modules)
The main landing page features interactive 3D tiles that launch individual single-page applications (SPAs) dynamically via JavaScript (`showView()`):

1. **Purple Mobility Tile:** A dynamic transit and mobility interface featuring live geospatial mapping and location tracking.
2. **White Foundation Tile:** A clean, reserved architectural space designed for future ecosystem expansion.
3. **Saffron Cultural Tile:** A cinematic cultural showcase featuring infinitely flowing historical portraits perfectly aligned within a structured color band layout. It includes a voice-synthesized AI assistant and a secure administrative shell.
4. **Blue Professional Tile:** A comprehensive professional networking portal featuring a community feed, personalized profile management, and a modular layout that adapts cleanly to mobile.
5. **Gradient Story Tile:** A visual media and story-sharing portal focused on community moments, currently protected by an administrative login module.
6. **Orange Initiative Tile:** A dedicated portal for the Orange Initiative community programs (in development).
7. **Floating Control Tiles:** Dedicated corner interactive triggers for backdrop themes, system navigation, and the upcoming Natural Intelligent Machine.

---

## 4. UI/UX & Responsive Guidelines
The ecosystem strictly adheres to the following UI rules:
- **Universal Header:** Every application (except the landing page) strictly features a top navigation bar with the Handshake Icon (`fa-handshake-angle`) on the far left, and the Home button on the far right.
- **Mobile Responsiveness:** All views utilize flexbox wrapping and dynamic `@media` queries. Large typography is allowed to wrap natively (`white-space: normal`) to prevent horizontal scrolling on mobile devices.
- **Cinematic Transitions:** Switching between applications utilizes a smooth CSS `@keyframes viewFadeIn` animation to simulate native mobile app routing.
- **Asset Sizing:** Flowing portraits in the Red App are strictly standardized (220px by 280px) to prevent layout shifting.

---

## 5. Deployment & CI/CD Pipeline
The project utilizes a seamless, fully automated deployment pipeline:
1. **GitHub Actions:** Pushing code to the `Godaddy` branch triggers `.github/workflows/deploy.yml`.
2. **FTP Sync:** The pipeline uses `SamKirkland/FTP-Deploy-Action` to sync files directly to the GoDaddy `public_html` (or designated directory) using repository secrets (`FTP_SERVER`, `FTP_USERNAME`, `FTP_PASSWORD`).
3. **Phusion Passenger Restart:** Because Python applications on GoDaddy are cached in memory, a script automatically updates the timestamp inside `tmp/restart.txt` during every commit. This tells the GoDaddy server to flush the cache and serve the latest Python code instantly.

---

## 6. DNS & Hosting Configuration
- **Registrar:** GoDaddy
- **Nameservers:** Default GoDaddy Nameservers (`nsXX.domaincontrol.com`)
- **Proxy Status:** Cloudflare DNS has been fully detached to ensure the domain resolves directly to the singular GoDaddy Origin Server IP. This prevents "Multi-IP" proxy conflicts during ICANN/WHOIS lookups.

---

## 7. Secret Developer Triggers (AGENTS.md)
The platform contains hidden easter eggs and developer overrides:
- **"Iron Man" Trigger:** Restores hidden letters (H, I, P, E, O and Swastika) inside the 3D ecosystem cards.
- **"Iron Man Two" Trigger:** Restores the settings popover themes panel to its legacy design (solid frosted glass, clickable buttons grid for themes).
