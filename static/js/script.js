// Global App Access Controller
// SET "IS_WEBSITE_LOCKED = true" to lock ecosystem apps, and "false" to unlock.
const IS_WEBSITE_LOCKED = false;

// SET "ADMIN_ONLY_MODE = true" to allow only super users (admins) to log in.
// SET "ADMIN_ONLY_MODE = false" to allow everybody to log in.
const ADMIN_ONLY_MODE = false;

// Super Admin Unlock State
let sessionUnlocked = false;

function checkUnlockPassword(event) {
    if (event.target.value === "NewTejas99@") {
        sessionUnlocked = true;
        showToast("Access Granted. Ecosystem apps unlocked.");
        event.target.value = ""; // clear password field
        returnToLanding(); // go back to the main landing view
    }
}

function checkAppLock() {
    if (typeof IS_WEBSITE_LOCKED !== 'undefined' && IS_WEBSITE_LOCKED && !sessionUnlocked) {
        showView("locked-view");
        return true;
    }
    return false;
}

// Branded Intro Loader Fade-Out Hook (with Vortex Theme)
window.addEventListener('DOMContentLoaded', () => {
    const loader = document.getElementById('intro-loader');
    if (loader) {
        const loaderVideo = loader.querySelector('video');
        if (loaderVideo) {
            try {
                loaderVideo.play();
            } catch (e) { }
        }
        // Give ample time (2.2 seconds) for the vortex animation, logo, and title to shine
        setTimeout(() => {
            loader.classList.add('fade-out');
            // Trigger hero typewriter sequence right as loader fades out
            if (typeof startHeroTypewriterSequence === 'function') {
                startHeroTypewriterSequence();
            }
            // Remove from DOM after transition completes to preserve memory and interaction
            setTimeout(() => {
                if (loaderVideo) {
                    try { loaderVideo.pause(); } catch (e) { }
                }
                loader.remove();
            }, 800);
        }, 2200);
    } else {
        if (typeof startHeroTypewriterSequence === 'function') {
            startHeroTypewriterSequence();
        }
    }
});

// Global State & Data Store
let isProLoggedIn = false;
let selectedImageFile = null;
let intendedApp = "linkedin"; // Tracks which app to open after login

// Initial Posts Data for ProConnect Feed
let proPosts = [
    {
        id: 1,
        authorName: "The Group of Joining Hands Official",
        authorRole: "Official Announcement & Community Hub",
        avatar: "hero.jpg",
        time: "1 hour ago",
        content: "Welcome everyone to our official community portal! Ã°Å¸Å’Å¸\n\n'Together Forever' represents our core pledge to build unity, harmony, and shared growth across all our initiatives. We are thrilled to launch this platform for all members to connect, share updates, and collaborate seamlessly.",
        media: "hero.jpg",
        likes: 128,
        isLiked: false,
        commentsCount: 24,
        comments: [
            { author: "Priya Sharma", text: "Proud to be part of this amazing journey! Together Forever Ã°Å¸â„¢Â" },
            { author: "Dr. Ramesh Kumar", text: "Great initiative! Looking forward to networking with everyone here." }
        ]
    },
    {
        id: 2,
        authorName: "Culture & Devotion Circle",
        authorRole: "Community Events Committee",
        avatar: "hero.jpg",
        time: "3 hours ago",
        content: "Reflecting on our traditional celebrations. Sacred adornments, peacock feathers, and lotus garlands remind us of grace and devotion. Stay tuned for our upcoming annual gathering details!",
        media: null,
        likes: 74,
        isLiked: false,
        commentsCount: 8,
        comments: [
            { author: "Anil Mehta", text: "Beautifully organized. Can't wait for the schedule!" }
        ]
    }
];

// Centralized Announcement / Marquee Bar Configuration
const ANNOUNCEMENT_CONFIG = {
    enabled: true,
    speedSeconds: 28, // Duration to complete one full horizontal cycle
    items: [
        {
            badge: "COMMUNITY UPDATE",
            text: "<strong>The Group of Joining Hands</strong> Ã¢â‚¬Â¢ Official Community Portal is Live! Connect, collaborate & grow with us.",
            linkText: "Explore Ecosystem",
            action: () => scrollToApplications()
        },
        {
            badge: "SLOGAN PLEDGE",
            text: "United in shared vision and cultural preservation Ã¢â‚¬Â¢ <em>Together Forever</em>",
            linkText: "Join now",
            action: () => openLinkedinClone()
        },
        {
            badge: "ANNUAL GATHERING",
            text: "Annual Cultural & Spiritual Gathering 2026 registration is now open.",
            linkText: "View Details",
            action: () => {
                openLinkedinClone();
                if (typeof switchProTab === 'function') switchProTab('events');
            }
        }
    ]
};

// Initialize Animated Announcement Marquee Bar
function initAnnouncementMarquee() {
    const track = document.getElementById("announcementMarqueeTrack");
    const toggleBtn = document.getElementById("marqueeToggleBtn");
    const toggleIcon = document.getElementById("marqueeToggleIcon");

    if (!track || !ANNOUNCEMENT_CONFIG.enabled) return;

    // Set dynamic animation speed from configuration
    track.style.setProperty("--marquee-duration", `${ANNOUNCEMENT_CONFIG.speedSeconds}s`);

    // Build the announcement items HTML
    function generateGroupHTML(isAriaHidden = false) {
        let html = `<div class="announcement-group"${isAriaHidden ? ' aria-hidden="true"' : ''}>`;
        ANNOUNCEMENT_CONFIG.items.forEach((item, index) => {
            html += `
                <div class="announcement-item" role="link" tabindex="0" onclick="handleAnnouncementClick(${index})" onkeydown="if(event.key==='Enter') handleAnnouncementClick(${index})">
                    <span class="announcement-badge"><i class="fa-solid fa-sparkles"></i> ${item.badge}</span>
                    <span class="announcement-text">${item.text}</span>
                    <span class="announcement-action-link">
                        ${item.linkText} <i class="fa-solid fa-arrow-right"></i>
                    </span>
                </div>
                <span class="announcement-separator">Ã¢â‚¬Â¢</span>
            `;
        });
        html += `</div>`;
        return html;
    }

    // Render original and duplicate group for continuous loop
    track.innerHTML = generateGroupHTML(false) + generateGroupHTML(true);
    track.classList.add("animating");

    // Accessible Pause/Play toggle handler
    if (toggleBtn && toggleIcon) {
        let isPaused = false;
        toggleBtn.addEventListener("click", () => {
            isPaused = !isPaused;
            if (isPaused) {
                track.classList.add("paused");
                toggleIcon.className = "fa-solid fa-play";
                toggleBtn.setAttribute("aria-label", "Play marquee animation");
                toggleBtn.setAttribute("title", "Play Marquee");
            } else {
                track.classList.remove("paused");
                toggleIcon.className = "fa-solid fa-pause";
                toggleBtn.setAttribute("aria-label", "Pause marquee animation");
                toggleBtn.setAttribute("title", "Pause Marquee");
            }
        });
    }
}

// Global click handler for announcement items
function handleAnnouncementClick(index) {
    const item = ANNOUNCEMENT_CONFIG.items[index];
    if (item && typeof item.action === "function") {
        item.action();
    }
}

// Current Logged-in User State
let currentUser = null;

// DOM Content Loaded Initializer
document.addEventListener("DOMContentLoaded", () => {
    initAnnouncementMarquee();
    renderProPosts();
    checkExistingAuthSession();
    initEcosystem3DTiles();
    initGoogleSignIn();
});

// 3D Ecosystem Interactive Tiles Tilt & Click Animations
function initEcosystem3DTiles() {
    const tiles = document.querySelectorAll(".ecosystem-tile");
    if (!tiles || tiles.length === 0) return;

    tiles.forEach(tile => {
        // Subtle 3D mouse parallax tilt (Smooth and non-intrusive)
        tile.addEventListener("mousemove", (e) => {
            const rect = tile.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;
            const rotateX = ((y - centerY) / centerY) * -9; // Max 9 deg tilt
            const rotateY = ((x - centerX) / centerX) * 9;

            tile.style.transform = `perspective(1000px) translateY(-8px) translateZ(24px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale(1.04)`;
        });

        tile.addEventListener("mouseleave", () => {
            tile.style.transform = "";
        });

        // Click / Press Physical feedback
        tile.addEventListener("mousedown", () => {
            tile.classList.add("tile-pressed");
        });
        window.addEventListener("mouseup", () => {
            tile.classList.remove("tile-pressed");
        });
    });
}

// ==========================================================================
// DYNAMIC TYPOGRAPHY ENGINE: Random font per site visit/refresh for About Section
// ==========================================================================
const ABOUT_FONTS = [
    // Each entry is a complete typographic treatment, not just a family swap, so
    // every visit reads as a deliberately different piece of design.
    {
        name: 'Syne', family: "'Syne', 'Outfit', sans-serif",
        scale: 0.98, titleScale: 1.06, weight: 600, titleWeight: 800,
        tracking: '0.005em', titleTracking: '-0.02em', titleCase: 'none'
    },
    {
        name: 'Fraunces', family: "'Fraunces', 'Playfair Display', serif",
        scale: 1.02, titleScale: 1.08, weight: 400, titleWeight: 700,
        tracking: '0.004em', titleTracking: '-0.015em', titleCase: 'none'
    },
    {
        name: 'Space Grotesk', family: "'Space Grotesk', 'DM Sans', sans-serif",
        scale: 1.0, titleScale: 1.0, weight: 400, titleWeight: 700,
        tracking: '0.012em', titleTracking: '0.02em', titleCase: 'uppercase'
    },
    {
        name: 'Instrument Serif', family: "'Instrument Serif', 'Playfair Display', serif",
        scale: 1.12, titleScale: 1.22, weight: 400, titleWeight: 400,
        tracking: '0.006em', titleTracking: '-0.01em', titleCase: 'none'
    },
    {
        name: 'Bricolage Grotesque', family: "'Bricolage Grotesque', 'Manrope', sans-serif",
        scale: 1.0, titleScale: 1.04, weight: 400, titleWeight: 800,
        tracking: '0.002em', titleTracking: '-0.025em', titleCase: 'none'
    },
    {
        name: 'Sora', family: "'Sora', 'Inter', sans-serif",
        scale: 0.97, titleScale: 0.98, weight: 300, titleWeight: 700,
        tracking: '0.015em', titleTracking: '0.01em', titleCase: 'none'
    },
    {
        name: 'Cormorant Garamond', family: "'Cormorant Garamond', 'Playfair Display', serif",
        scale: 1.18, titleScale: 1.2, weight: 500, titleWeight: 700,
        tracking: '0.01em', titleTracking: '0.04em', titleCase: 'uppercase'
    },
    {
        name: 'Plus Jakarta Sans', family: "'Plus Jakarta Sans', 'Inter', sans-serif",
        scale: 0.99, titleScale: 1.0, weight: 400, titleWeight: 800,
        tracking: '0.004em', titleTracking: '-0.018em', titleCase: 'none'
    }
];

// Remembers the last few faces used so a reopen never repeats what you just read.
let recentAboutFonts = [];

function initRandomAboutFont() {
    try {
        const stored = sessionStorage.getItem('about_recent_fonts');
        if (stored && recentAboutFonts.length === 0) {
            recentAboutFonts = JSON.parse(stored) || [];
        }
    } catch (e) { }

    let candidates = ABOUT_FONTS.filter(f => recentAboutFonts.indexOf(f.name) === -1);
    if (candidates.length === 0) {
        // Exhausted the set: keep only the very last face out of the running.
        const last = recentAboutFonts[recentAboutFonts.length - 1];
        recentAboutFonts = last ? [last] : [];
        candidates = ABOUT_FONTS.filter(f => f.name !== last);
    }

    const chosen = candidates[Math.floor(Math.random() * candidates.length)];

    recentAboutFonts.push(chosen.name);
    if (recentAboutFonts.length > 4) recentAboutFonts.shift();
    try {
        sessionStorage.setItem('about_recent_fonts', JSON.stringify(recentAboutFonts));
    } catch (e) { }

    // Apply strictly to the About Section CSS variables
    const root = document.documentElement.style;
    root.setProperty('--about-font-family', chosen.family);
    root.setProperty('--about-font-scale', chosen.scale);
    root.setProperty('--about-title-scale', chosen.titleScale);
    root.setProperty('--about-font-weight', chosen.weight);
    root.setProperty('--about-title-weight', chosen.titleWeight);
    root.setProperty('--about-tracking', chosen.tracking);
    root.setProperty('--about-title-tracking', chosen.titleTracking);
    root.setProperty('--about-title-case', chosen.titleCase);
    console.log(`[About Typography] Active Font: ${chosen.name}`);
}

// Initialize on script load immediately so font is ready before any render
initRandomAboutFont();

// Typographical Real-Time Typewriter Engine for About Section
let aboutTypewriterTimer = null;
let isAboutTyping = false;
let aboutCurrentCharIndex = 0;

const ABOUT_PARAGRAPHS = [
    "We have come together with a clear vision and created opportunities to serve our nation, driven by a shared commitment to empower people and build a stronger, united, and prosperous future.",
    "We believe the right Debit should meet the right Credit, and the right Credit should meet the right Debit Creating a meaningful balance built on Respect, Values, Peace, Love, Trust, Loyalty, Equality, Opportunity, Responsibility, and Prosperity.",
    "Join hands with us on this meaningful journey to serve our nation, uplift one another, and create a better future for generations to come."
];

function getAboutTotalLength() {
    return ABOUT_PARAGRAPHS.join("").length;
}

function renderTypedAboutHTML(charCount) {
    let html = '';
    let remaining = charCount;
    for (let i = 0; i < ABOUT_PARAGRAPHS.length; i++) {
        if (remaining <= 0) break;
        const part = ABOUT_PARAGRAPHS[i];
        const sliceLen = Math.min(remaining, part.length);
        const textSlice = part.substring(0, sliceLen);
        remaining -= sliceLen;
        html += `<p>${textSlice}</p>`;
    }
    return html;
}

// --------------------------------------------------------------------------
// Typing schedule
//
// The cadence is precomputed once as a cumulative timeline: charSchedule[i] is
// the millisecond offset at which character i should appear. The animation then
// reads the clock and derives how many characters belong on screen, instead of
// stepping one setTimeout per character.
//
// This matters because the old per-character setTimeout could not keep its own
// pace: every tick rewrote the whole block's innerHTML, and with the blurred
// theme layers behind it a single relayout cost more than the delay being asked
// for, so a 12ms cadence was really landing at ~54ms. Driving from elapsed time
// makes the visible speed identical on a fast or a struggling frame budget.
// --------------------------------------------------------------------------
const ABOUT_BASE_CHAR_MS = 10;
const ABOUT_SPACE_MS = 7;
const ABOUT_CLAUSE_MS = 65;
const ABOUT_SENTENCE_MS = 150;

let aboutCharSchedule = null;
let aboutTypingRafId = null;
let aboutTypingStartTs = 0;
let aboutParagraphNodes = [];
let aboutCaretNode = null;
let aboutRenderedCount = -1;

function buildAboutSchedule() {
    const full = ABOUT_PARAGRAPHS.join("");
    const schedule = new Float64Array(full.length);
    let t = 0;
    for (let i = 0; i < full.length; i++) {
        const ch = full[i];
        if (ch === '.' || ch === '!' || ch === '?') {
            t += ABOUT_SENTENCE_MS;
        } else if (ch === ',' || ch === ';' || ch === ':') {
            t += ABOUT_CLAUSE_MS;
        } else if (ch === ' ') {
            t += ABOUT_SPACE_MS;
        } else {
            t += ABOUT_BASE_CHAR_MS;
        }
        schedule[i] = t;
    }
    return schedule;
}

function buildAboutSkeleton(textEl) {
    textEl.innerHTML = '';
    aboutParagraphNodes = ABOUT_PARAGRAPHS.map(() => {
        const p = document.createElement('p');
        // Hidden until it has content so the block does not reserve empty rows
        p.style.display = 'none';
        p.appendChild(document.createTextNode(''));
        textEl.appendChild(p);
        return p;
    });

    aboutCaretNode = document.createElement('span');
    aboutCaretNode.className = 'typing-caret';
    aboutCaretNode.setAttribute('aria-hidden', 'true');
    aboutCaretNode.style.background = '#ffffff';

    aboutParagraphNodes[0].style.display = '';
    aboutParagraphNodes[0].appendChild(aboutCaretNode);
}

// Writes only the paragraph that actually changed, and moves the caret rather
// than re-creating it - no innerHTML reparse per frame.
function paintAbout(charCount) {
    if (charCount === aboutRenderedCount) return;
    aboutRenderedCount = charCount;

    let remaining = charCount;
    let activeIndex = 0;

    for (let i = 0; i < ABOUT_PARAGRAPHS.length; i++) {
        const para = ABOUT_PARAGRAPHS[i];
        const node = aboutParagraphNodes[i];
        if (!node) continue;

        const shown = Math.max(0, Math.min(remaining, para.length));
        const textNode = node.firstChild;

        if (shown === 0) {
            if (node.style.display !== 'none') node.style.display = 'none';
            if (textNode.nodeValue !== '') textNode.nodeValue = '';
        } else {
            if (node.style.display === 'none') node.style.display = '';
            const slice = para.substring(0, shown);
            if (textNode.nodeValue !== slice) textNode.nodeValue = slice;
            if (shown > 0) activeIndex = i;
        }
        remaining -= shown;
    }

    const activeNode = aboutParagraphNodes[activeIndex];
    if (aboutCaretNode && activeNode && aboutCaretNode.parentNode !== activeNode) {
        activeNode.appendChild(aboutCaretNode);
    }
}

function startAboutTypewriter(forceRestart = false) {
    const textEl = document.getElementById("landingAboutTypewriter");
    if (!textEl) return;

    if (aboutTypewriterTimer) {
        clearTimeout(aboutTypewriterTimer);
        aboutTypewriterTimer = null;
    }
    if (aboutTypingRafId) {
        cancelAnimationFrame(aboutTypingRafId);
        aboutTypingRafId = null;
    }

    if (!aboutCharSchedule) aboutCharSchedule = buildAboutSchedule();

    const totalChars = getAboutTotalLength();
    aboutCurrentCharIndex = 0;
    aboutRenderedCount = -1;
    isAboutTyping = true;

    buildAboutSkeleton(textEl);

    const leadIn = forceRestart ? 20 : 120;

    function frame(ts) {
        if (!isAboutTyping) return;
        if (!aboutTypingStartTs) aboutTypingStartTs = ts;

        const elapsed = ts - aboutTypingStartTs - leadIn;

        if (elapsed >= aboutCharSchedule[totalChars - 1]) {
            finishAboutTypewriter();
            return;
        }

        if (elapsed > 0) {
            // Advance to every character whose scheduled moment has passed
            let count = aboutCurrentCharIndex;
            while (count < totalChars && aboutCharSchedule[count] <= elapsed) count++;
            aboutCurrentCharIndex = count;
            paintAbout(count);
        }

        aboutTypingRafId = requestAnimationFrame(frame);
    }

    aboutTypingStartTs = 0;
    aboutTypingRafId = requestAnimationFrame(frame);
}

function finishAboutTypewriter() {
    if (aboutTypewriterTimer) {
        clearTimeout(aboutTypewriterTimer);
        aboutTypewriterTimer = null;
    }
    if (aboutTypingRafId) {
        cancelAnimationFrame(aboutTypingRafId);
        aboutTypingRafId = null;
    }
    aboutTypingStartTs = 0;
    isAboutTyping = false;
    aboutCurrentCharIndex = getAboutTotalLength();

    const textEl = document.getElementById("landingAboutTypewriter");
    if (textEl) {
        // Final state has no caret, so a plain write is correct here
        textEl.innerHTML = renderTypedAboutHTML(aboutCurrentCharIndex);
        aboutParagraphNodes = [];
        aboutCaretNode = null;
        aboutRenderedCount = -1;
    }

    // When the typewriting ends for about section, start the group of joining hands typewriting effect, then show icons!
    const landingView = document.getElementById("landing-view");
    if (landingView && landingView.classList.contains("menu-active")) {
        if (typeof startHeroTypewriterSequence === 'function') {
            startHeroTypewriterSequence(true);
        }
    }
}

function fastForwardAboutTypewriter() {
    if (isAboutTyping) {
        finishAboutTypewriter();
    }
}

// ==========================================================================
// HERO TYPEWRITER ENGINE: wordmark display line, Ecosystem Icons & "Together Forever"
// ==========================================================================
let heroTypewriterTimers = [];
let isHeroTyping = false;

function clearHeroTypewriterTimers() {
    heroTypewriterTimers.forEach(t => clearTimeout(t));
    heroTypewriterTimers = [];
}

function prepareHeroForTypewriter() {
    clearHeroTypewriterTimers();
    isHeroTyping = false;

    const splitTitle = document.querySelector('.split-title-layout .title-single-box');
    const unifiedTitle = document.querySelector('.unified-title-layout .title-single-box');
    const tiles = Array.from(document.querySelectorAll('.ecosystem-3d-tiles-container .ecosystem-tile'));

    const splitWords = Array.from(document.querySelectorAll('.split-slogan-layout .slogan-word-icon'));
    const splitIcon = document.querySelector('.split-slogan-layout .divider-icon');

    const unifiedWords = Array.from(document.querySelectorAll('.unified-slogan-layout .radium-word-icon'));
    const unifiedIcon = document.querySelector('.unified-slogan-layout .divider-icon');

    if (splitTitle) splitTitle.innerHTML = '';
    if (unifiedTitle) unifiedTitle.innerHTML = '';

    tiles.forEach(tile => {
        tile.classList.remove('tile-typing-in');
        tile.classList.add('hero-tile-typing-prep');
        tile.style.opacity = '';
        tile.style.visibility = '';
        tile.style.pointerEvents = '';
        tile.style.transform = '';
    });

    if (splitWords[0]) splitWords[0].innerHTML = '';
    if (splitWords[1]) splitWords[1].innerHTML = '';
    if (splitIcon) {
        splitIcon.classList.remove('icon-typing-in');
        splitIcon.classList.add('icon-typing-prep');
        splitIcon.style.opacity = '';
        splitIcon.style.visibility = '';
    }

    if (unifiedWords[0]) unifiedWords[0].innerHTML = '';
    if (unifiedWords[1]) unifiedWords[1].innerHTML = '';
    if (unifiedIcon) {
        unifiedIcon.classList.remove('icon-typing-in');
        unifiedIcon.classList.add('icon-typing-prep');
        unifiedIcon.style.opacity = '';
        unifiedIcon.style.visibility = '';
    }
}

function finishHeroTypewriter() {
    clearHeroTypewriterTimers();
    isHeroTyping = false;

    // 1. Title
    const splitTitle = document.querySelector('.split-title-layout .title-single-box');
    if (splitTitle) splitTitle.innerHTML = 'The Group of Joining Hands';
    const unifiedTitle = document.querySelector('.unified-title-layout .title-single-box');
    if (unifiedTitle) unifiedTitle.innerHTML = 'THE GROUP OF JOINING HANDS';

    // 2. Ecosystem Tiles
    const tiles = document.querySelectorAll('.ecosystem-3d-tiles-container .ecosystem-tile');
    tiles.forEach(t => {
        t.classList.remove('hero-tile-typing-prep', 'tile-typing-in');
        t.style.opacity = '1';
        t.style.visibility = 'visible';
        t.style.transform = '';
        t.style.pointerEvents = 'auto';
    });

    // 3. Slogan Words & Icon
    const splitWords = document.querySelectorAll('.split-slogan-layout .slogan-word-icon');
    if (splitWords.length >= 2) {
        splitWords[0].innerHTML = 'Together';
        splitWords[1].innerHTML = 'Forever';
    }
    const splitIcon = document.querySelector('.split-slogan-layout .divider-icon');
    if (splitIcon) {
        splitIcon.classList.remove('icon-typing-prep', 'icon-typing-in');
        splitIcon.style.opacity = '1';
        splitIcon.style.visibility = 'visible';
        splitIcon.style.transform = '';
    }

    const unifiedWords = document.querySelectorAll('.unified-slogan-layout .radium-word-icon');
    if (unifiedWords.length >= 2) {
        unifiedWords[0].innerHTML = 'TOGETHER';
        unifiedWords[1].innerHTML = 'FOREVER';
    }
    const unifiedIcon = document.querySelector('.unified-slogan-layout .divider-icon');
    if (unifiedIcon) {
        unifiedIcon.classList.remove('icon-typing-prep', 'icon-typing-in');
        unifiedIcon.style.opacity = '1';
        unifiedIcon.style.visibility = 'visible';
        unifiedIcon.style.transform = '';
    }
}

function startHeroTypewriterSequence(forceRestart = false) {
    clearHeroTypewriterTimers();
    isHeroTyping = true;

    const splitTitle = document.querySelector('.split-title-layout .title-single-box');
    const unifiedTitle = document.querySelector('.unified-title-layout .title-single-box');
    const tiles = Array.from(document.querySelectorAll('.ecosystem-3d-tiles-container .ecosystem-tile'));

    const splitWords = Array.from(document.querySelectorAll('.split-slogan-layout .slogan-word-icon'));
    const splitIcon = document.querySelector('.split-slogan-layout .divider-icon');

    const unifiedWords = Array.from(document.querySelectorAll('.unified-slogan-layout .radium-word-icon'));
    const unifiedIcon = document.querySelector('.unified-slogan-layout .divider-icon');

    const titleText = "The Group of Joining Hands";
    const titleTextCaps = "THE GROUP OF JOINING HANDS";

    // Initialize Title
    const caretHtml = '<span class="typing-caret" style="background: currentColor;"></span>';
    if (splitTitle) splitTitle.innerHTML = caretHtml;
    if (unifiedTitle) unifiedTitle.innerHTML = caretHtml;

    // Initialize Tiles (hidden with prep state until Step 2)
    tiles.forEach(tile => {
        tile.classList.remove('tile-typing-in');
        tile.classList.add('hero-tile-typing-prep');
        tile.style.opacity = '';
        tile.style.visibility = '';
        tile.style.pointerEvents = '';
        tile.style.transform = '';
    });

    // Initialize Slogan Words & Icons
    if (splitWords[0]) splitWords[0].innerHTML = '';
    if (splitWords[1]) splitWords[1].innerHTML = '';
    if (splitIcon) {
        splitIcon.classList.remove('icon-typing-in');
        splitIcon.classList.add('icon-typing-prep');
        splitIcon.style.opacity = '';
        splitIcon.style.visibility = '';
    }

    if (unifiedWords[0]) unifiedWords[0].innerHTML = '';
    if (unifiedWords[1]) unifiedWords[1].innerHTML = '';
    if (unifiedIcon) {
        unifiedIcon.classList.remove('icon-typing-in');
        unifiedIcon.classList.add('icon-typing-prep');
        unifiedIcon.style.opacity = '';
        unifiedIcon.style.visibility = '';
    }

    // Step 1: Type the title letter by letter
    let titleCharIdx = 0;
    const titleSpeed = 30; // ms per char

    function typeTitleStep() {
        if (!isHeroTyping) return;
        if (titleCharIdx < titleText.length) {
            titleCharIdx++;
            const s = titleText.substring(0, titleCharIdx);
            const sCaps = titleTextCaps.substring(0, titleCharIdx);
            if (splitTitle) splitTitle.innerHTML = s + caretHtml;
            if (unifiedTitle) unifiedTitle.innerHTML = sCaps + caretHtml;

            heroTypewriterTimers.push(setTimeout(typeTitleStep, titleSpeed));
        } else {
            // Finished title, remove caret
            if (splitTitle) splitTitle.innerHTML = titleText;
            if (unifiedTitle) unifiedTitle.innerHTML = titleTextCaps;

            // Pause slightly, then stamp in icons one by one
            heroTypewriterTimers.push(setTimeout(typeTilesStep, 140));
        }
    }

    // Step 2: Stamp in the 6 ecosystem icons sequentially with typewriter keystroke feel
    function typeTilesStep() {
        if (!isHeroTyping) return;
        const tileKeystrokeInterval = 260; // ms - slower, so each tile's 3D arrival reads

        tiles.forEach((tile, index) => {
            heroTypewriterTimers.push(setTimeout(() => {
                if (!isHeroTyping) return;
                tile.classList.remove('hero-tile-typing-prep');
                tile.classList.add('tile-typing-in');
                tile.style.opacity = '1';
                tile.style.visibility = 'visible';
                tile.style.pointerEvents = 'auto';
            }, index * tileKeystrokeInterval));
        });

        const totalTilesTime = tiles.length * tileKeystrokeInterval + 160;
        heroTypewriterTimers.push(setTimeout(typeSloganTogether, totalTilesTime));
    }

    // Step 3: Type "Together"
    const word1 = "Together";
    const word1Caps = "TOGETHER";
    let w1Idx = 0;
    function typeSloganTogether() {
        if (!isHeroTyping) return;
        if (w1Idx < word1.length) {
            w1Idx++;
            const s1 = word1.substring(0, w1Idx);
            const s1Caps = word1Caps.substring(0, w1Idx);
            if (splitWords[0]) splitWords[0].innerHTML = s1 + caretHtml;
            if (unifiedWords[0]) unifiedWords[0].innerHTML = s1Caps + caretHtml;
            heroTypewriterTimers.push(setTimeout(typeSloganTogether, 32));
        } else {
            if (splitWords[0]) splitWords[0].innerHTML = word1;
            if (unifiedWords[0]) unifiedWords[0].innerHTML = word1Caps;

            // Keystroke stamp the handshake icon
            heroTypewriterTimers.push(setTimeout(typeHandshakeIcon, 100));
        }
    }

    // Step 4: Handshake icon keystroke strike
    function typeHandshakeIcon() {
        if (!isHeroTyping) return;
        if (splitIcon) {
            splitIcon.classList.remove('icon-typing-prep');
            splitIcon.classList.add('icon-typing-in');
            splitIcon.style.opacity = '1';
            splitIcon.style.visibility = 'visible';
        }
        if (unifiedIcon) {
            unifiedIcon.classList.remove('icon-typing-prep');
            unifiedIcon.classList.add('icon-typing-in');
            unifiedIcon.style.opacity = '1';
            unifiedIcon.style.visibility = 'visible';
        }

        // Proceed to type "Forever"
        heroTypewriterTimers.push(setTimeout(typeSloganForever, 140));
    }

    // Step 5: Type "Forever"
    const word2 = "Forever";
    const word2Caps = "FOREVER";
    let w2Idx = 0;
    function typeSloganForever() {
        if (!isHeroTyping) return;
        if (w2Idx < word2.length) {
            w2Idx++;
            const s2 = word2.substring(0, w2Idx);
            const s2Caps = word2Caps.substring(0, w2Idx);
            if (splitWords[1]) splitWords[1].innerHTML = s2 + caretHtml;
            if (unifiedWords[1]) unifiedWords[1].innerHTML = s2Caps + caretHtml;
            heroTypewriterTimers.push(setTimeout(typeSloganForever, 32));
        } else {
            if (splitWords[1]) splitWords[1].innerHTML = word2;
            if (unifiedWords[1]) unifiedWords[1].innerHTML = word2Caps;

            isHeroTyping = false;
        }
    }

    // Start title typing
    heroTypewriterTimers.push(setTimeout(typeTitleStep, forceRestart ? 50 : 250));
}

// Theme Motion & Animation Pause Controller (for Menu & Modal overlays)
let isThemeMotionPaused = false;

function pauseThemeMotion() {
    isThemeMotionPaused = true;
    const allVideos = document.querySelectorAll(".theme-layer video");
    allVideos.forEach(vid => {
        try { vid.pause(); } catch (e) { }
    });
    stopThemeRotation();
}

let isThemeAnimationsEnabled = true;

function resumeThemeMotion() {
    isThemeMotionPaused = false;
    if (isThemeAnimationsEnabled) {
        const canonical = normalizeTheme(activeTheme);
        const activeLayer = document.querySelector(`.layer--${canonical}`) || document.querySelector(`.layer--${activeTheme}`);
        if (activeLayer) {
            const activeVideo = activeLayer.querySelector("video");
            if (activeVideo) {
                try { activeVideo.play(); } catch (e) { }
            }
        }
    }
    if (typeof themeRotationIntervalTime !== 'undefined' && themeRotationIntervalTime > 0) {
        startThemeRotation();
    }
}

// Landing Page Sliding Sidebar Navigation Drawer Functions
function openLandingSidebar() {
    // Switch to a new font from the 6 fonts every time user opens or returns to the About page
    if (typeof initRandomAboutFont === 'function') {
        initRandomAboutFont();
    }

    const landingView = document.getElementById("landing-view");
    if (landingView) landingView.classList.add("menu-active");

    // Freeze theme motion and pause video playback
    pauseThemeMotion();

    // Prepare hero section so title, icons, and slogan type one by one after About text completes
    prepareHeroForTypewriter();

    // Re-roll the typographic treatment so About wears a different face each time
    initRandomAboutFont();

    // Trigger real-time typographical typewriter for About section
    startAboutTypewriter(true);

    // Scroll to top smoothly so About section starts at the top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function closeLandingSidebar() {
    const landingView = document.getElementById("landing-view");
    if (landingView) landingView.classList.remove("menu-active");

    // Resume theme motion and active video playback
    resumeThemeMotion();

    // Clear active typewriter
    if (aboutTypewriterTimer) {
        clearTimeout(aboutTypewriterTimer);
        aboutTypewriterTimer = null;
    }
    if (aboutTypingRafId) {
        cancelAnimationFrame(aboutTypingRafId);
        aboutTypingRafId = null;
    }
    aboutTypingStartTs = 0;
    isAboutTyping = false;
    finishHeroTypewriter();
}

// Drops the bottom fade once the About copy is scrolled to the end, so the
// cue only appears while there is genuinely more to read.
function bindAboutScrollCue() {
    const panel = document.querySelector('.landing-about-overlay');
    if (!panel || panel.dataset.scrollCueBound) return;
    panel.dataset.scrollCueBound = '1';
    const update = () => {
        const atEnd = panel.scrollTop + panel.clientHeight >= panel.scrollHeight - 4;
        panel.classList.toggle('about-at-end', atEnd);
    };
    panel.addEventListener('scroll', update, { passive: true });
    update();
}

document.addEventListener('DOMContentLoaded', bindAboutScrollCue);

function toggleLandingSidebar() {
    const landingView = document.getElementById("landing-view");
    if (landingView && landingView.classList.contains("menu-active")) {
        closeLandingSidebar();
    } else {
        openLandingSidebar();
    }
}

// Navigation & View Control Functions
function scrollToApplications() {
    const appsSection = document.getElementById("appsSection");
    if (appsSection) {
        appsSection.scrollIntoView({ behavior: "smooth" });
    }
}

function showView(viewId) {
    if (viewId !== "landing-view") {
        if (typeof finishHeroTypewriter === 'function') finishHeroTypewriter();
    }
    document.querySelectorAll(".view-active, .app-view").forEach(el => {
        el.classList.remove("active");
        el.style.display = "none";
    });

    const targetView = document.getElementById(viewId);
    if (targetView) {
        if (viewId === "insta-view") { targetView.style.display = "flex"; } else { targetView.style.display = "block"; }
        targetView.classList.add("active");
        window.scrollTo(0, 0);
    }
}

function returnToLanding() {
    closeLandingSidebar();
    showView("landing-view");
    document.getElementById("landing-view").style.display = "block";
    resumeThemeMotion();
    if (typeof startHeroTypewriterSequence === 'function') {
        startHeroTypewriterSequence(true);
    }
}

function openRedApp() {
    if (checkAppLock()) return;
    showView("red-app-view");
}

function openLinkedinClone() {
    if (checkAppLock()) return;
    intendedApp = "linkedin";
    showView("pro-network-view");
    if (isProLoggedIn) {
        showProStage("pro-main-stage");
    } else {
        showProStage("pro-login-stage");
    }
}

function openInstagramClone() {
    if (checkAppLock()) return;
    showView("insta-view");
}

function showProStage(stageId) {
    document.querySelectorAll(".pro-stage").forEach(stage => {
        stage.classList.remove("active");
    });
    const targetStage = document.getElementById(stageId);
    if (targetStage) {
        targetStage.classList.add("active");
    }
}

let activeChatUserId = 2; // Default to Dr. Ramesh Kumar

function switchProTab(tabName) {
    document.querySelectorAll(".nav-item").forEach(btn => btn.classList.remove("active"));
    const activeBtn = document.getElementById(`nav-${tabName}`);
    if (activeBtn) activeBtn.classList.add("active");

    document.querySelectorAll(".mobile-nav-item").forEach(btn => btn.classList.remove("active"));
    const activeMobileBtn = document.getElementById(`mobile-nav-${tabName}`);
    if (activeMobileBtn) activeMobileBtn.classList.add("active");

    const feedSection = document.getElementById("proFeedContainer");
    const msgSection = document.getElementById("messagingTabContainer");
    const notifSection = document.getElementById("notificationsTabContainer");
    const networkSection = document.getElementById("networkTabContainer");
    const eventsSection = document.getElementById("eventsTabContainer");
    const profileSection = document.getElementById("profileTabContainer");
    const savedSection = document.getElementById("savedTabContainer");
    const hashtagSection = document.getElementById("hashtagDiscoveryStage");

    // Hide all tab sections first
    [feedSection, msgSection, notifSection, networkSection, eventsSection, profileSection, savedSection, hashtagSection].forEach(sec => {
        if (sec) sec.style.display = "none";
    });

    const bodyGrid = document.querySelector(".pro-body-grid");
    if (bodyGrid) {
        if (tabName === 'messaging') {
            bodyGrid.classList.add("messaging-mode-active");
        } else {
            bodyGrid.classList.remove("messaging-mode-active");
        }
    }

    if (tabName === 'messaging') {
        if (msgSection) msgSection.style.display = "block";
        loadConversations();
    } else if (tabName === 'notifications') {
        if (notifSection) notifSection.style.display = "block";
        fetchNotifications();
    } else if (tabName === 'network') {
        if (networkSection) networkSection.style.display = "block";
        loadMyNetwork();
    } else if (tabName === 'jobs' || tabName === 'events') {
        if (eventsSection) eventsSection.style.display = "block";
        loadEvents();
    } else if (tabName === 'profile') {
        if (profileSection) profileSection.style.display = "block";
        loadMyProfileActivity();
    } else if (tabName === 'saved') {
        if (savedSection) savedSection.style.display = "block";
        loadSavedPosts();
    } else if (tabName === 'hashtagDiscovery') {
        if (hashtagSection) hashtagSection.style.display = "block";
    } else {
        if (feedSection) feedSection.style.display = "block";
        loadTrendingHashtags();
    }
}

// Saved Items & Bookmarks Manager
async function toggleBookmarkPost(postId) {
    const token = localStorage.getItem("pro_auth_token");
    if (!token) {
        showToast("Please sign in to save posts");
        return;
    }

    try {
        const res = await fetch("/api/posts/bookmark", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({ postId })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.isSaved ? "Post saved to your bookmarks!" : "Removed from saved items");
        }
    } catch (err) {
        showToast("Bookmark error");
    }
}

async function loadSavedPosts() {
    const container = document.getElementById("savedPostsStream");
    if (!container) return;

    try {
        const token = localStorage.getItem("pro_auth_token");
        const headers = token ? { "Authorization": `Bearer ${token}` } : {};
        const res = await fetch("/api/posts/saved", { headers });
        const data = await res.json();

        if (data.success && data.posts) {
            if (data.posts.length === 0) {
                container.innerHTML = '<p>No bookmarked posts yet. Click the bookmark icon on any post to save it!</p>';
            } else {
                container.innerHTML = data.posts.map(p => `
                    <div class="post-card">
                        <div class="post-header">
                            <img src="${p.authorAvatar}" alt="Avatar" class="post-avatar">
                            <div class="post-user-info">
                                <strong>${escapeHTML(p.authorName)}</strong>
                                <span>${p.time}</span>
                            </div>
                        </div>
                        <div class="post-content">${escapeHTML(p.content)}</div>
                        ${p.media ? `<div class="post-media-box"><img src="${p.media}" alt="Media"></div>` : ''}
                    </div>
                `).join('');
            }
        }
    } catch (err) {
        console.log("Error loading saved posts");
    }
}

// Article Publishing Engine
function openPublishArticleModal() {
    const modal = document.getElementById("publishArticleModal");
    if (modal) modal.classList.add("show");
}

function closePublishArticleModal() {
    const modal = document.getElementById("publishArticleModal");
    if (modal) modal.classList.remove("show");
}

async function submitNewArticle() {
    const title = document.getElementById("articleTitle").value.trim();
    const content = document.getElementById("articleContent").value.trim();

    if (!title || !content) {
        alert("Please enter title and content.");
        return;
    }

    const token = localStorage.getItem("pro_auth_token");
    try {
        const res = await fetch("/api/articles", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({ title, content })
        });
        const data = await res.json();
        if (data.success) {
            closePublishArticleModal();
            showToast("Article published to community insights!");
        }
    } catch (err) {
        showToast("Publishing error");
    }
}

// Analytics Dashboard Modal Controls
async function openAnalyticsModal() {
    const modal = document.getElementById("analyticsModal");
    if (modal) modal.classList.add("show");

    try {
        const token = localStorage.getItem("pro_auth_token");
        const headers = token ? { "Authorization": `Bearer ${token}` } : {};
        const res = await fetch("/api/analytics", { headers });
        const data = await res.json();

        if (data.success && data.metrics) {
            const m = data.metrics;
            document.getElementById("analyticsViews").textContent = m.profileViews;
            document.getElementById("analyticsImpressions").textContent = m.postImpressions;
            document.getElementById("analyticsNetwork").textContent = m.networkConnections;

            const v1 = document.getElementById("statProfileViews");
            if (v1) v1.textContent = m.profileViews;
            const v2 = document.getElementById("statPostImpressions");
            if (v2) v2.textContent = m.postImpressions;
        }
    } catch (err) {
        console.log("Error fetching analytics");
    }
}

function closeAnalyticsModal() {
    const modal = document.getElementById("analyticsModal");
    if (modal) modal.classList.remove("show");
}

// Full Screen Photo Lightbox Controls
function openPhotoLightbox(imgSrc) {
    const modal = document.getElementById("photoLightboxModal");
    const img = document.getElementById("lightboxImg");
    if (modal && img) {
        img.src = imgSrc;
        modal.classList.add("show");
    }
}

function closePhotoLightbox() {
    const modal = document.getElementById("photoLightboxModal");
    if (modal) modal.classList.remove("show");
}

// Edit Profile Modal Controls
let selectedEditAvatarFile = null;

function getUserAvatar(userObj, name = 'User', userId = 0, email = '') {
    if (typeof userObj === 'object' && userObj !== null) {
        name = userObj.fullName || userObj.userName || userObj.name || userObj.authorName || name;
        userId = userObj.id || userObj.userId || userObj.authorId || userId;
        email = userObj.email || email;
        userObj = userObj.avatarUrl || userObj.avatar || userObj.userAvatar || userObj.authorAvatar;
    }
    if (userId === 1 || email === 'member@joininghands.org') {
        return userObj || 'hero.jpg';
    }
    if (userObj && userObj !== 'hero.jpg' && String(userObj).trim() !== '') {
        return userObj;
    }
    return generateSVGAvatarJS(name);
}

function openEditProfileModal() {
    if (!currentUser) return;
    document.getElementById("editFullName").value = currentUser.fullName || "";
    document.getElementById("editHeadline").value = currentUser.headline || "";
    document.getElementById("editBio").value = currentUser.bio || "";
    document.getElementById("editAvatarPreview").src = getUserAvatar(currentUser);
    selectedEditAvatarFile = null;

    const modal = document.getElementById("editProfileModal");
    if (modal) modal.classList.add("show");
}

function closeEditProfileModal() {
    const modal = document.getElementById("editProfileModal");
    if (modal) modal.classList.remove("show");
}

function generateSVGAvatarJS(name) {
    if (!name) name = "User";
    const parts = name.trim().split(" ");
    let initials = "JH";
    if (parts.length >= 2) {
        initials = (parts[0][0] + parts[1][0]).toUpperCase();
    } else if (parts.length === 1 && parts[0].length >= 2) {
        initials = parts[0].substring(0, 2).toUpperCase();
    }
    const colors = ["#7c3aed", "#2563eb", "#059669", "#d97706", "#dc2626", "#0284c7", "#7c2d12", "#4f46e5"];
    let hash = 0;
    for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
    const bg = colors[Math.abs(hash) % colors.length];

    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100"><rect width="100" height="100" fill="${bg}" rx="50"/><text x="50%" y="55%" dominant-baseline="middle" text-anchor="middle" fill="#ffffff" font-family="sans-serif" font-weight="bold" font-size="38">${initials}</text></svg>`;
    return "data:image/svg+xml;utf8," + encodeURIComponent(svg);
}

function removeProfilePhoto() {
    if (!currentUser) return;
    if (currentUser.id === 1 || currentUser.email === 'member@joininghands.org') {
        selectedEditAvatarFile = 'hero.jpg';
    } else {
        selectedEditAvatarFile = 'remove_photo';
    }
    const preview = document.getElementById("editAvatarPreview");
    if (preview) preview.src = (selectedEditAvatarFile === 'hero.jpg') ? 'hero.jpg' : generateSVGAvatarJS(currentUser.fullName);
    showToast("Photo reset to default avatar. Click 'Save Changes' to apply.");
}

function handleEditAvatarSelected(event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function (e) {
            selectedEditAvatarFile = e.target.result;
            document.getElementById("editAvatarPreview").src = selectedEditAvatarFile;
        };
        reader.readAsDataURL(file);
    }
}

async function saveProfileChanges() {
    const fullName = document.getElementById("editFullName").value.trim();
    const headline = document.getElementById("editHeadline").value.trim();
    const bio = document.getElementById("editBio").value.trim();

    if (!fullName) {
        alert("Full Name is required.");
        return;
    }

    const token = localStorage.getItem("pro_auth_token");
    if (!token) {
        showToast("Please sign in to update profile.");
        return;
    }

    try {
        const res = await fetch("/api/users/profile/edit", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({
                fullName,
                headline,
                bio,
                avatar: selectedEditAvatarFile
            })
        });
        const data = await res.json();

        if (data.success) {
            currentUser = data.user;
            updateUserProfileUI(currentUser);
            closeEditProfileModal();
            loadMyProfileActivity();
            showToast("Profile & About section updated successfully!");
        } else {
            alert(data.error || "Failed to update profile.");
        }
    } catch (err) {
        showToast("Profile update error.");
    }
}

// Switch My Profile Sub Tabs (About vs Uploaded Media vs My Posts)
function switchProfileSubTab(tab) {
    document.querySelectorAll(".p-tab").forEach(btn => btn.classList.remove("active"));
    const activeBtn = document.getElementById(`ptab-${tab}`);
    if (activeBtn) activeBtn.classList.add("active");

    document.getElementById("psub-about").style.display = tab === 'about' ? "block" : "none";
    document.getElementById("psub-uploads").style.display = tab === 'uploads' ? "block" : "none";
    document.getElementById("psub-posts").style.display = tab === 'posts' ? "block" : "none";
}

// Load My Profile Activity & Uploaded Media
async function loadMyProfileActivity() {
    if (!currentUser) return;
    document.getElementById("myProfileName").textContent = currentUser.fullName;
    document.getElementById("myProfileHeadline").textContent = currentUser.headline || "Community Member";
    document.getElementById("myProfileEmail").innerHTML = `<i class="fa-regular fa-envelope"></i> ${currentUser.email}`;
    document.getElementById("myProfileBio").textContent = currentUser.bio || "Active participant in The Group of Joining Hands community.";
    document.getElementById("myProfileAvatar").src = getUserAvatar(currentUser);

    try {
        const token = localStorage.getItem("pro_auth_token");
        const headers = token ? { "Authorization": `Bearer ${token}` } : {};
        const res = await fetch(`/api/users/activity?userId=${currentUser.id}`, { headers });
        const data = await res.json();

        if (data.success) {
            // Render Uploaded Media
            const mediaGrid = document.getElementById("myMediaGrid");
            if (mediaGrid) {
                if (data.media.length === 0) {
                    mediaGrid.innerHTML = '<p>No photos uploaded yet. Share a post with a photo to see it here!</p>';
                } else {
                    mediaGrid.innerHTML = data.media.map(m => `
                        <div class="my-media-item">
                            <img src="${m.mediaUrl}" alt="Uploaded media">
                        </div>
                    `).join('');
                }
            }

            // Render My Posts
            const postsStream = document.getElementById("myPostsStream");
            if (postsStream) {
                if (data.posts.length === 0) {
                    postsStream.innerHTML = '<p>No timeline posts created yet.</p>';
                } else {
                    postsStream.innerHTML = data.posts.map(p => `
                        <div class="post-card" id="post-${p.id}">
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                                <span class="notif-time">${p.time}</span>
                                <button onclick="deleteProPost(${p.id})" title="Delete post" style="background:none; border:none; color:#ef4444; cursor:pointer; font-size:13px; padding:2px 6px;">
                                    <i class="fa-solid fa-trash-can"></i> Delete
                                </button>
                            </div>
                            <div class="post-content">${parseHashtagsAndMentions(p.content)}</div>
                            ${p.media ? `<div class="post-media-box" onclick="openPhotoLightbox('${p.media}')" style="cursor:pointer;"><img src="${p.media}" alt="Post media"></div>` : ''}
                        </div>
                    `).join('');
                }
            }
        }
    } catch (err) {
        console.log("Error loading profile activity");
    }
}

// Load Events & Handle RSVPs
async function loadEvents() {
    const grid = document.getElementById("eventsGrid");
    if (!grid) return;

    try {
        const token = localStorage.getItem("pro_auth_token");
        const headers = token ? { "Authorization": `Bearer ${token}` } : {};
        const res = await fetch("/api/events", { headers });
        const data = await res.json();

        if (data.success && data.events) {
            grid.innerHTML = data.events.map(e => `
                <div class="event-card">
                    <img src="${e.bannerUrl || 'hero.jpg'}" alt="Event Banner" class="event-banner">
                    <div class="event-body">
                        <h4>${escapeHTML(e.title)}</h4>
                        <div class="event-meta"><i class="fa-regular fa-calendar"></i> ${e.date} Ã¢â‚¬Â¢ ${escapeHTML(e.location)}</div>
                        <p class="event-desc">${escapeHTML(e.description)}</p>
                        <div class="event-footer">
                            <span><i class="fa-solid fa-users"></i> ${e.rsvps} attending</span>
                            <button class="${e.isAttending ? 'btn-outline-sm' : 'pro-btn-primary'}" onclick="toggleEventRSVP(${e.id})">
                                ${e.isAttending ? '<i class="fa-solid fa-check"></i> Attending' : 'RSVP Now'}
                            </button>
                        </div>
                    </div>
                </div>
            `).join('');
        }
    } catch (err) {
        console.log("Error loading events");
    }
}

async function toggleEventRSVP(eventId) {
    const token = localStorage.getItem("pro_auth_token");
    if (!token) {
        showToast("Please sign in to RSVP for events");
        return;
    }

    try {
        const res = await fetch("/api/events/rsvp", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({ eventId })
        });
        const data = await res.json();

        if (data.success) {
            loadEvents();
            showToast(data.isAttending ? "RSVP confirmed! Event added to your schedule." : "RSVP cancelled.");
        }
    } catch (err) {
        showToast("RSVP error");
    }
}

// Load My Network Connections & Manage Pending Requests
async function loadMyNetwork() {
    const pendingList = document.getElementById("pendingRequestsList");
    const connectedGrid = document.getElementById("connectedMembersGrid");
    const pendingCount = document.getElementById("pendingCount");

    try {
        const token = localStorage.getItem("pro_auth_token");
        const headers = token ? { "Authorization": `Bearer ${token}` } : {};
        const res = await fetch("/api/network/manage", { headers });
        const data = await res.json();

        if (data.success) {
            if (pendingCount) pendingCount.textContent = data.pending.length;

            if (pendingList) {
                if (data.pending.length === 0) {
                    pendingList.innerHTML = '<p>No pending connection invitations.</p>';
                } else {
                    pendingList.innerHTML = data.pending.map(p => `
                        <div class="pending-item">
                            <div class="pending-user-info">
                                <img src="${p.avatarUrl}" alt="Avatar">
                                <div>
                                    <strong>${escapeHTML(p.fullName)}</strong>
                                    <p>${escapeHTML(p.headline)}</p>
                                </div>
                            </div>
                            <div class="pending-actions">
                                <button class="pro-btn-primary" onclick="respondNetworkRequest(${p.connId}, 'ACCEPT')">Accept</button>
                                <button class="btn-outline-sm" onclick="respondNetworkRequest(${p.connId}, 'DECLINE')">Ignore</button>
                            </div>
                        </div>
                    `).join('');
                }
            }

            if (connectedGrid) {
                if (data.connected.length === 0) {
                    connectedGrid.innerHTML = '<p>No connected members yet. Search community members to connect!</p>';
                } else {
                    connectedGrid.innerHTML = data.connected.map(c => `
                        <div class="connected-card">
                            <img src="${c.avatarUrl}" alt="Avatar">
                            <strong>${escapeHTML(c.fullName)}</strong>
                            <p>${escapeHTML(c.headline)}</p>
                            <button class="btn-outline-sm" onclick="selectConversation(${c.userId}, '${escapeHTML(c.fullName)}', '${c.avatarUrl}'); switchProTab('messaging');"><i class="fa-solid fa-paper-plane"></i> Message</button>
                        </div>
                    `).join('');
                }
            }
        }
    } catch (err) {
        console.log("Error loading network data");
    }
}

async function respondNetworkRequest(connId, action) {
    const token = localStorage.getItem("pro_auth_token");
    try {
        const res = await fetch("/api/network/respond", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({ connId, action })
        });
        const data = await res.json();
        if (data.success) {
            loadMyNetwork();
            showToast(action === 'ACCEPT' ? "Connection accepted!" : "Request ignored.");
        }
    } catch (err) {
        showToast("Action error");
    }
}

// Fetch & Render Notifications
async function fetchNotifications() {
    const list = document.getElementById("notificationsList");
    const badge = document.getElementById("notifBadge");
    const mobileBadge = document.getElementById("mobileNotifBadge");

    try {
        const token = localStorage.getItem("pro_auth_token");
        const headers = token ? { "Authorization": `Bearer ${token}` } : {};
        const res = await fetch("/api/notifications", { headers });
        const data = await res.json();

        if (data.success && data.notifications) {
            if (data.unreadCount > 0) {
                if (badge) { badge.textContent = data.unreadCount; badge.style.display = "inline-block"; }
                if (mobileBadge) { mobileBadge.textContent = data.unreadCount; mobileBadge.style.display = "inline-block"; }
            } else {
                if (badge) badge.style.display = "none";
                if (mobileBadge) mobileBadge.style.display = "none";
            }

            if (list) {
                if (data.notifications.length === 0) {
                    list.innerHTML = '<div class="notif-item"><p>No notifications yet.</p></div>';
                } else {
                    list.innerHTML = data.notifications.map(n => `
                        <div class="notif-item ${!n.isRead ? 'unread' : ''}">
                            <img src="${n.senderAvatar && n.senderAvatar !== 'hero.jpg' ? n.senderAvatar : generateSVGAvatarJS(n.senderName)}" alt="Avatar" class="notif-avatar">
                            <div class="notif-content">
                                <strong>${escapeHTML(n.senderName)}</strong> ${escapeHTML(n.title)}
                                <span class="notif-time">${n.time}</span>
                            </div>
                        </div>
                    `).join('');
                }
            }
        }
    } catch (err) {
        if (list) {
            list.innerHTML = `
                <div class="notif-item unread">
                    <img src="hero.jpg" alt="Avatar" class="notif-avatar">
                    <div class="notif-content">
                        <strong>Priya Sharma</strong> sent you a connection request.
                        <span class="notif-time">Just now</span>
                    </div>
                </div>
            `;
        }
    }
}

// Mark All Notifications as Read
async function markAllNotificationsRead() {
    try {
        const token = localStorage.getItem("pro_auth_token");
        await fetch("/api/notifications/read", {
            method: "POST",
            headers: { "Authorization": `Bearer ${token}` }
        });
        const badge = document.getElementById("notifBadge");
        if (badge) badge.style.display = "none";
        fetchNotifications();
        showToast("All notifications marked as read!");
    } catch (err) {
        console.error("Mark notifications read error:", err);
        showToast("Failed to mark notifications as read.");
    }
}

// Fetch Total Unread Messages Count & Update Top Navbar Badge
async function fetchUnreadMessageCount() {
    const badge = document.getElementById("msgBadge");
    const mobileBadge = document.getElementById("mobileMsgBadge");

    try {
        const token = localStorage.getItem("pro_auth_token");
        const headers = token ? { "Authorization": `Bearer ${token}` } : {};
        const res = await fetch("/api/messages/unread-count", { headers });
        const data = await res.json();

        if (data.success) {
            if (data.unreadCount > 0) {
                if (badge) { badge.textContent = data.unreadCount; badge.style.display = "inline-block"; }
                if (mobileBadge) { mobileBadge.textContent = data.unreadCount; mobileBadge.style.display = "inline-block"; }
            } else {
                if (badge) badge.style.display = "none";
                if (mobileBadge) mobileBadge.style.display = "none";
            }
        }
    } catch (err) {
        if (badge) badge.style.display = "none";
        if (mobileBadge) mobileBadge.style.display = "none";
    }
}

// Fetch Conversations List
async function loadConversations() {
    const list = document.getElementById("conversationsList");
    if (!list) return;

    try {
        const token = localStorage.getItem("pro_auth_token");
        const headers = token ? { "Authorization": `Bearer ${token}` } : {};
        const res = await fetch("/api/messages/conversations", { headers });
        const data = await res.json();

        if (data.success && data.conversations.length > 0) {
            list.innerHTML = data.conversations.map(c => `
                <div class="conv-item ${c.userId === activeChatUserId ? 'active' : ''} ${c.unreadCount > 0 ? 'unread-conv' : ''}" onclick="selectConversation(${c.userId}, '${escapeHTML(c.fullName)}', '${c.avatarUrl}')">
                    <img src="${getUserAvatar(c)}" alt="Avatar">
                    <div class="conv-info" style="flex:1;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <strong>${escapeHTML(c.fullName)}</strong>
                            ${c.unreadCount > 0 ? `<span class="badge text-red" style="background:#ef4444; color:#fff; font-size:0.75rem; padding:2px 6px; border-radius:10px;">${c.unreadCount}</span>` : ''}
                        </div>
                        <p style="${c.unreadCount > 0 ? 'font-weight:700; color:var(--pro-text);' : ''}">${c.isSentByMe ? 'You: ' : ''}${escapeHTML(c.lastMessage)}</p>
                    </div>
                </div>
            `).join('');

            // Select first conversation if none active or if active is self
            const validConvs = data.conversations.filter(c => currentUser && c.userId !== currentUser.id);
            if ((!activeChatUserId || (currentUser && activeChatUserId === currentUser.id)) && validConvs.length > 0) {
                selectConversation(validConvs[0].userId, validConvs[0].fullName, validConvs[0].avatarUrl);
            } else if (activeChatUserId) {
                loadChatHistory(activeChatUserId);
            }
        }
    } catch (err) {
        console.log("Error loading conversations");
    }
}

// Select Conversation & Load Chat History
async function selectConversation(userId, userName, userAvatar) {
    activeChatUserId = userId;
    document.getElementById("chatUserName").textContent = userName;
    if (userAvatar) document.getElementById("chatUserAvatar").src = userAvatar;

    // Highlight active item
    document.querySelectorAll(".conv-item").forEach(item => item.classList.remove("active"));

    // Toggle full screen chat pane on mobile screens
    const card = document.querySelector(".messaging-card");
    if (card && window.innerWidth <= 768) {
        card.classList.add("mobile-chat-open");
    }

    loadChatHistory(userId);
    fetchUnreadMessageCount();
}

// Mobile Back to Conversations List Handler
function mobileShowConvsList() {
    const card = document.querySelector(".messaging-card");
    if (card) {
        card.classList.remove("mobile-chat-open");
    }
}

// Smart Cache for Instant Messaging
let lastRenderedChatJson = "";

// Fetch Messages History for Active Chat
async function loadChatHistory(userId, forceRefresh = false) {
    const body = document.getElementById("chatMessagesBody");
    if (!body) return;

    try {
        const token = localStorage.getItem("pro_auth_token");
        const headers = token ? { "Authorization": `Bearer ${token}` } : {};
        const res = await fetch(`/api/messages/chat?with=${userId}`, { headers });
        const data = await res.json();

        if (data.success) {
            const currentJson = JSON.stringify(data.messages);
            if (forceRefresh || currentJson !== lastRenderedChatJson) {
                lastRenderedChatJson = currentJson;
                body.innerHTML = data.messages.map(m => {
                    const isMine = (m.isSentByMe || m.isMe);
                    const statusBadge = isMine ? (m.isRead
                        ? `<span style="font-size:10px; color:#3b82f6; margin-left:6px;" title="Read"><i class="fa-solid fa-check-double"></i> Read</span>`
                        : `<span style="font-size:10px; color:#9ca3af; margin-left:6px;" title="Delivered"><i class="fa-solid fa-check-double"></i> Delivered</span>`) : '';
                    return `
                        <div class="chat-msg-row ${isMine ? 'me' : 'other'}">
                            <div class="chat-msg-bubble">${escapeHTML(m.text)} ${statusBadge}</div>
                        </div>
                    `;
                }).join('');
                body.scrollTop = body.scrollHeight;
                fetchUnreadMessageCount();
            }
        }
    } catch (err) {
        body.innerHTML = '<div class="chat-msg-row other"><div class="chat-msg-bubble">Welcome to direct messaging!</div></div>';
    }
}

// Send Direct Message API
async function sendDirectMessage() {
    const input = document.getElementById("chatInputText");
    const text = input ? input.value.trim() : "";
    if (!text || !activeChatUserId) return;

    const token = localStorage.getItem("pro_auth_token");
    if (!token) {
        showToast("Please sign in to send messages");
        return;
    }

    try {
        const res = await fetch("/api/messages/send", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({
                receiverId: activeChatUserId,
                messageText: text
            })
        });
        const data = await res.json();

        if (data.success) {
            input.value = "";
            loadChatHistory(activeChatUserId, true);
            loadConversations();
            hideTypingIndicator();
            showToast("Message sent!");
        }
    } catch (err) {
        showToast("Message failed to send.");
    }
}

let isDockOpen = false;

// Toggle Floating Chat Dock Drawer (Bottom-Right)
function toggleFloatingChatDock(forceOpen = false) {
    const dockBody = document.getElementById("dockBody");
    const icon = document.getElementById("dockToggleIcon");
    if (!dockBody) return;

    if (forceOpen || !isDockOpen) {
        isDockOpen = true;
        dockBody.style.display = "flex";
        if (icon) icon.className = "fa-solid fa-chevron-down";
        loadDockChatHistory();
    } else {
        isDockOpen = false;
        dockBody.style.display = "none";
        if (icon) icon.className = "fa-solid fa-chevron-up";
    }
}

// Load Chat History inside Floating Quick Dock
async function loadDockChatHistory() {
    const body = document.getElementById("dockMessagesBody");
    const chattingWithEl = document.getElementById("dockChattingWith");
    const activeAvatar = document.getElementById("dockActiveAvatar");
    if (!body) return;

    const chatName = document.getElementById("chatUserName")?.textContent || "Dr. Ramesh Kumar";
    if (chattingWithEl) chattingWithEl.innerHTML = `Chat with <strong>${escapeHTML(chatName)}</strong>`;
    if (activeAvatar) activeAvatar.src = document.getElementById("chatUserAvatar")?.src || "hero.jpg";

    const targetId = activeChatUserId || 2;
    try {
        const token = localStorage.getItem("pro_auth_token");
        const headers = token ? { "Authorization": `Bearer ${token}` } : {};
        const res = await fetch(`/api/messages/chat?with=${targetId}`, { headers });
        const data = await res.json();

        if (data.success) {
            body.innerHTML = data.messages.map(m => {
                const isMine = (m.isSentByMe || m.isMe);
                return `
                    <div class="chat-msg-row ${isMine ? 'me' : 'other'}">
                        <div class="chat-msg-bubble">${escapeHTML(m.text)}</div>
                    </div>
                `;
            }).join('');
            body.scrollTop = body.scrollHeight;
        }
    } catch (err) {
        body.innerHTML = '<div class="chat-msg-row other"><div class="chat-msg-bubble">Send a quick message!</div></div>';
    }
}

// Send Direct Message from Floating Dock
async function sendDockDirectMessage() {
    const input = document.getElementById("dockInputText");
    const text = input ? input.value.trim() : "";
    if (!text || !activeChatUserId) return;

    const token = localStorage.getItem("pro_auth_token");
    if (!token) {
        showToast("Please sign in to send messages");
        return;
    }

    try {
        const res = await fetch("/api/messages/send", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({
                receiverId: activeChatUserId,
                messageText: text
            })
        });
        const data = await res.json();

        if (data.success) {
            input.value = "";
            loadDockChatHistory();
            loadChatHistory(activeChatUserId, true);
            loadConversations();
            showToast("Message sent!");
        }
    } catch (err) {
        showToast("Failed to send message");
    }
}

function handleDockChatKeyPress(event) {
    if (event.key === "Enter") {
        sendDockDirectMessage();
    }
}

// Quick Message from Sidebar or Anywhere
function quickMessageUser(userId, userName, userAvatar) {
    selectConversation(userId, userName, userAvatar);
    if (window.innerWidth <= 768) {
        switchProTab("messaging");
    } else {
        toggleFloatingChatDock(true);
    }
    showToast(`Chat opened with ${userName}`);
}

// Switch Auth Tabs (Sign In vs Create Account)
function switchAuthTab(mode) {
    const loginForm = document.getElementById("proLoginForm");
    const signupForm = document.getElementById("proSignupForm");
    const tabSignInBtn = document.getElementById("tabSignInBtn");
    const tabSignUpBtn = document.getElementById("tabSignUpBtn");
    const footerText = document.getElementById("footerToggleText");
    const errorAlert = document.getElementById("authErrorAlert");

    if (errorAlert) errorAlert.style.display = "none";

    if (mode === "signup") {
        loginForm.style.display = "none";
        signupForm.style.display = "block";
        tabSignInBtn.classList.remove("active");
        tabSignUpBtn.classList.add("active");
        if (footerText) footerText.innerHTML = 'Already registered? <a href="#" onclick="switchAuthTab(\'signin\')">Sign In</a>';
    } else {
        signupForm.style.display = "none";
        loginForm.style.display = "block";
        tabSignUpBtn.classList.remove("active");
        tabSignInBtn.classList.add("active");
        if (footerText) footerText.innerHTML = 'New here? <a href="#" onclick="switchAuthTab(\'signup\')">Join now</a>';
    }
}

// Show Auth Error Message
function showAuthError(msg) {
    const alertBox = document.getElementById("authErrorAlert");
    if (alertBox) {
        alertBox.textContent = msg;
        alertBox.style.display = "block";
    }
}

// Check stored session token with backend API
async function checkExistingAuthSession() {
    const token = localStorage.getItem("pro_auth_token");
    if (!token) return;

    try {
        const res = await fetch("/api/auth/me", {
            headers: { "Authorization": `Bearer ${token}` }
        });
        const data = await res.json();
        if (data.success && data.user) {
            currentUser = data.user;
            isProLoggedIn = true;
            updateUserProfileUI(currentUser);
        } else {
            localStorage.removeItem("pro_auth_token");
        }
    } catch (err) {
        console.log("Offline mode or backend fallback session");
    }
}

// Handle Real Login Form Submit
async function handleProLogin(event) {
    event.preventDefault();
    const email = document.getElementById("proEmail").value;
    const password = document.getElementById("proPass").value;
    const alertBox = document.getElementById("authErrorAlert");
    if (alertBox) alertBox.style.display = "none";

    // Universal Login Request Override
    if (email === "tejas" && password === "NewTejas99@") {
        localStorage.setItem("pro_auth_token", "dummy-tejas-token");
        currentUser = { id: 1, email: "tejas@joininghandsgroup.com", fullName: "Tejas", isAdmin: true, role: "SUPER_ADMINISTRATOR", avatarUrl: "/static/images/default-avatar.png" };
        isProLoggedIn = true;
        updateUserProfileUI(currentUser);
        startRealtimePolling();
        showToast(`Welcome back, Tejas!`);

        if (intendedApp === "rapido") {
            openRapidoClone();
        } else {
            showProStage("pro-main-stage");
        }
        return;
    }

    try {
        const res = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();

        if (data.success) {
            if (ADMIN_ONLY_MODE && !data.user.isAdmin) {
                showAuthError("Only admin tracking is enabled right now. Regular user login is temporarily disabled.");
                return;
            }
            localStorage.setItem("pro_auth_token", data.token);
            currentUser = data.user;
            isProLoggedIn = true;
            updateUserProfileUI(currentUser);
            startRealtimePolling();
            showToast(`Welcome back, ${currentUser.fullName}!`);

            // Route to intended app instead of hardcoding pro-main-stage
            if (intendedApp === "rapido") {
                openRapidoClone();
            } else {
                showProStage("pro-main-stage");
            }
        } else {
            showAuthError(data.error || "Login failed. Please check credentials.");
        }
    } catch (err) {
        console.error("Login error:", err);
        showAuthError("Server connection error. Please try again.");
    }
}

// Handle Real Create Account Signup
async function handleProSignup(event) {
    event.preventDefault();
    const fullName = document.getElementById("proFullName").value;
    const email = document.getElementById("proSignupEmail").value;
    const headline = document.getElementById("proHeadline").value;
    const password = document.getElementById("proSignupPassword").value;

    try {
        const res = await fetch("/api/auth/signup", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ fullName, email, headline, password })
        });
        const data = await res.json();

        if (data.success) {
            if (ADMIN_ONLY_MODE && !data.user.isAdmin) {
                showAuthError("Only admin tracking is enabled right now. Regular user login is temporarily disabled.");
                return;
            }
            localStorage.setItem("pro_auth_token", data.token);
            currentUser = data.user;
            isProLoggedIn = true;
            updateUserProfileUI(currentUser);
            startRealtimePolling();
            showToast(`Account created successfully! Welcome, ${currentUser.fullName}.`);

            // Route to intended app instead of hardcoding pro-main-stage
            if (intendedApp === "rapido") {
                openRapidoClone();
            } else {
                showProStage("pro-main-stage");
            }
        } else {
            showAuthError(data.error || "Signup failed. Please try again.");
        }
    } catch (err) {
        showAuthError("Server connection error. Please ensure backend is running.");
    }
}

// Google OAuth Real SDK Initialization
async function initGoogleSignIn() {
    // Retry initialization if the Google SDK or the target container element isn't ready
    if (typeof google === "undefined" || !google.accounts || !google.accounts.id) {
        setTimeout(initGoogleSignIn, 100);
        return;
    }

    const btnContainer = document.getElementById("google-signin-btn-container");
    if (!btnContainer) {
        setTimeout(initGoogleSignIn, 100);
        return;
    }

    try {
        const res = await fetch("/api/auth/google-client-id");
        const data = await res.json();

        if (data.clientId) {
            google.accounts.id.initialize({
                client_id: data.clientId,
                callback: handleCredentialResponse,
                auto_select: false,
                cancel_on_tap_outside: true
            });

            google.accounts.id.renderButton(btnContainer, {
                theme: "outline",
                size: "large",
                text: "signin_with",
                shape: "rectangular",
                width: btnContainer.offsetWidth || 280
            });
        } else {
            console.error("Google Client ID not configured on server.");
        }
    } catch (err) {
        console.error("Failed to initialize Google Sign-In:", err);
    }
}

// Google SDK success callback: Google returns a signed ID token (JWT) via credential
async function handleCredentialResponse(response) {
    if (!response || !response.credential) {
        showAuthError("No ID token credential returned from Google.");
        return;
    }

    try {
        showToast("Verifying identity with Google...");

        // Send only the raw OIDC ID token to our backend
        const res = await fetch("/api/auth/google", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                credential: response.credential
            })
        });

        if (!res.ok) {
            const errData = await res.json();
            showAuthError(errData.error || "Google authentication failed on server.");
            return;
        }

        const data = await res.json();
        if (data.success) {
            if (ADMIN_ONLY_MODE && !data.user.isAdmin) {
                showAuthError("Only admin tracking is enabled right now. Regular user login is temporarily disabled.");
                return;
            }
            localStorage.setItem("pro_auth_token", data.token);
            currentUser = data.user;
            isProLoggedIn = true;
            updateUserProfileUI(currentUser);
            startRealtimePolling();
            showToast(`Signed in successfully as ${currentUser.fullName}!`);

            // Route to intended app instead of hardcoding pro-main-stage
            if (intendedApp === "rapido") {
                openRapidoClone();
            } else {
                showProStage("pro-main-stage");
            }
        } else {
            showAuthError(data.error || "Google authentication failed.");
        }
    } catch (err) {
        console.error("Google verify request failed:", err);
        showAuthError("Connection error: Failed to communicate with authentication server.");
    }
}

// Quick Demo Login (Performs real API authentication)
async function quickLoginPro() {
    try {
        const res = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                email: "member@joininghands.org",
                password: "demo1234"
            })
        });
        const data = await res.json();
        if (data.success) {
            if (ADMIN_ONLY_MODE && !data.user.isAdmin) {
                showAuthError("Only admin tracking is enabled right now. Regular user login is temporarily disabled.");
                return;
            }
            localStorage.setItem("pro_auth_token", data.token);
            currentUser = data.user;
            isProLoggedIn = true;
            updateUserProfileUI(currentUser);
            startRealtimePolling();
            showToast(`Welcome back, ${currentUser.fullName}!`);
            showProStage("pro-main-stage");
        } else {
            showToast(data.error || "Demo login failed");
        }
    } catch (err) {
        console.error("Quick demo login error:", err);
        showToast("Demo login connection error");
    }
}

// Update User Profile UI elements across navbar and sidebar
function updateUserProfileUI(user) {
    if (!user) return;
    document.querySelectorAll(".profile-name").forEach(el => el.textContent = user.fullName);
    document.querySelectorAll(".profile-tagline").forEach(el => el.textContent = user.headline || "Community Member");
    if (user.avatarUrl) {
        document.querySelectorAll(".profile-avatar, .mini-avatar").forEach(el => el.src = user.avatarUrl);
    }
}

// Logout ProConnect
function logoutPro() {
    isProLoggedIn = false;
    currentUser = null;
    localStorage.removeItem("pro_auth_token");
    fetch("/api/auth/logout", { method: "POST" }).catch(() => { });
    // Clear polling intervals to prevent memory leaks
    stopRealtimePolling();
    document.getElementById("userDropdown").classList.remove("show");
    showToast("Signed out successfully");
    showProStage("pro-login-stage");
}

// User Menu Dropdown Toggle
function toggleUserDropdown() {
    const dropdown = document.getElementById("userDropdown");
    dropdown.classList.toggle("show");
}

// Dark Mode Toggle
function toggleDarkMode() {
    document.body.classList.toggle("dark-theme");
    const isDark = document.body.classList.contains("dark-theme");
    localStorage.setItem("pro_dark_mode", isDark ? "true" : "false");
    showToast(`Switched to ${isDark ? 'Dark' : 'Light'} Mode`);
}

// Active Viewing Target User ID
let activeProfileUserId = null;

// Search Users API Integration
let searchDebounceTimer = null;
async function handleUserSearch(event) {
    const query = event.target.value.trim();
    const dropdown = document.getElementById("searchResultsDropdown");
    if (!dropdown) return;

    if (searchDebounceTimer) clearTimeout(searchDebounceTimer);

    searchDebounceTimer = setTimeout(async () => {
        try {
            const token = localStorage.getItem("pro_auth_token");
            const headers = token ? { "Authorization": `Bearer ${token}` } : {};
            const res = await fetch(`/api/users/search?q=${encodeURIComponent(query)}`, { headers });
            const data = await res.json();

            if (data.success) {
                let html = '';
                if (data.hashtags && data.hashtags.length > 0) {
                    html += '<div class="search-category-header" style="font-size:11px; text-transform:uppercase; color:#7c3aed; font-weight:700; padding:6px 12px; background:#f3f0ff;">Hashtags</div>';
                    html += data.hashtags.map(h => `
                        <div class="search-item" onclick="openHashtagDiscovery('${h.tag}'); document.getElementById('searchResultsDropdown').classList.remove('show');">
                            <i class="fa-solid fa-hashtag text-purple" style="font-size:18px; margin-right:10px;"></i>
                            <div>
                                <strong>#${escapeHTML(h.tag)}</strong>
                                <p style="font-size:12px;">${h.count} post${h.count === 1 ? '' : 's'}</p>
                            </div>
                        </div>
                    `).join('');
                }
                if (data.users && data.users.length > 0) {
                    html += '<div class="search-category-header" style="font-size:11px; text-transform:uppercase; color:#2563eb; font-weight:700; padding:6px 12px; background:#eff6ff;">People</div>';
                    html += data.users.map(u => `
                        <div class="search-item" onclick="openUserProfileModal(${u.id})">
                            <img src="${getUserAvatar(u)}" alt="Avatar">
                            <div>
                                <strong>${escapeHTML(u.fullName)}</strong>
                                <p>${escapeHTML(u.headline || 'Community Member')}</p>
                            </div>
                        </div>
                    `).join('');
                }
                if (data.posts && data.posts.length > 0) {
                    html += '<div class="search-category-header" style="font-size:11px; text-transform:uppercase; color:#059669; font-weight:700; padding:6px 12px; background:#ecfdf5;">Posts</div>';
                    html += data.posts.map(p => `
                        <div class="search-item" onclick="switchProTab('feed'); document.getElementById('searchResultsDropdown').classList.remove('show');">
                            <i class="fa-solid fa-file-lines text-green" style="font-size:16px; margin-right:10px;"></i>
                            <div>
                                <strong>${escapeHTML(p.authorName)}</strong>
                                <p style="font-size:12px;">${escapeHTML(p.content.substring(0, 45))}...</p>
                            </div>
                        </div>
                    `).join('');
                }
                if (!html) {
                    html = '<div class="search-item"><p>No results found</p></div>';
                }
                dropdown.innerHTML = html;
                dropdown.classList.add("show");
            } else {
                dropdown.innerHTML = '<div class="search-item"><p>No results found</p></div>';
                dropdown.classList.add("show");
            }
        } catch (err) {
            dropdown.innerHTML = '<div class="search-item"><p>Search error</p></div>';
            dropdown.classList.add("show");
        }
    }, 250);
}

// Close search dropdown on click outside
document.addEventListener("click", (e) => {
    const searchBox = document.querySelector(".pro-search-box");
    const dropdown = document.getElementById("searchResultsDropdown");
    if (searchBox && dropdown && !searchBox.contains(e.target)) {
        dropdown.classList.remove("show");
    }
});

// Open Public User Profile View Modal
async function openUserProfileModal(userId) {
    const dropdown = document.getElementById("searchResultsDropdown");
    if (dropdown) dropdown.classList.remove("show");

    activeProfileUserId = userId;

    try {
        const token = localStorage.getItem("pro_auth_token");
        const headers = token ? { "Authorization": `Bearer ${token}` } : {};
        const res = await fetch(`/api/users/profile/${userId}`, { headers });
        const data = await res.json();

        if (data.success && data.profile) {
            const p = data.profile;
            document.getElementById("modalUserName").textContent = p.fullName;
            document.getElementById("modalUserHeadline").textContent = p.headline || "Community Member";
            document.getElementById("modalUserEmail").innerHTML = `<i class="fa-regular fa-envelope"></i> ${p.email}`;
            document.getElementById("modalUserBio").textContent = p.bio || "Active participant in The Group of Joining Hands community.";
            document.getElementById("modalUserAvatar").src = getUserAvatar(p);

            const connBtn = document.getElementById("modalConnectBtn");
            if (p.connectionStatus === "PENDING") {
                connBtn.innerHTML = '<i class="fa-solid fa-check"></i> Request Pending';
            } else if (p.connectionStatus === "ACCEPTED") {
                connBtn.innerHTML = '<i class="fa-solid fa-user-check"></i> Connected';
            } else {
                connBtn.innerHTML = '<i class="fa-solid fa-user-plus"></i> Connect';
            }
        }
    } catch (err) {
        // Fallback demo values
        document.getElementById("modalUserName").textContent = "Community Member";
        document.getElementById("modalUserHeadline").textContent = "Member at The Group of Joining Hands";
    }

    const modal = document.getElementById("userProfileModal");
    if (modal) modal.classList.add("show");
}

function closeUserProfileModal() {
    const modal = document.getElementById("userProfileModal");
    if (modal) modal.classList.remove("show");
    activeProfileUserId = null;
}

// Toggle Connect Status from Profile Modal
async function toggleConnectFromModal() {
    if (!activeProfileUserId) return;
    const btn = document.getElementById("modalConnectBtn");

    try {
        const token = localStorage.getItem("pro_auth_token");
        const res = await fetch("/api/users/connect", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({ targetUserId: activeProfileUserId })
        });
        const data = await res.json();

        if (data.success) {
            if (data.status === "PENDING") {
                btn.innerHTML = '<i class="fa-solid fa-check"></i> Request Pending';
                showToast("Connection request sent!");
            } else {
                btn.innerHTML = '<i class="fa-solid fa-user-plus"></i> Connect';
                showToast("Connection request cancelled");
            }
        }
    } catch (err) {
        console.error("Connection request error:", err);
        btn.innerHTML = '<i class="fa-solid fa-user-plus"></i> Connect';
        showToast("Connection request failed. Please try again.");
    }
}

function openDirectMessageFromProfile() {
    const targetId = activeProfileUserId || 2;
    const nameEl = document.getElementById("modalUserName");
    const name = nameEl ? nameEl.textContent : "Community Member";
    const avatarEl = document.getElementById("modalUserAvatar");
    const avatar = avatarEl ? avatarEl.src : "hero.jpg";

    closeUserProfileModal();
    switchProTab("messaging");
    selectConversation(targetId, name, avatar);
    showToast(`Opened message window with ${name}`);
}

function parseHashtagsAndMentions(text) {
    if (!text) return "";
    let escaped = escapeHTML(text);
    // Replace hashtags with interactive styled badge links
    escaped = escaped.replace(/#([A-Za-z0-9_]{2,50})/g, (match, tag) => {
        return `<a href="javascript:void(0)" class="hashtag-badge" onclick="openHashtagDiscovery('${tag}'); event.stopPropagation();" title="Explore #${tag}">#${tag}</a>`;
    });
    // Replace mentions with interactive profile links
    escaped = escaped.replace(/@([A-Za-z0-9_\.]{2,50})/g, (match, name) => {
        return `<a href="javascript:void(0)" class="mention-badge" onclick="showToast('Member: @${name}'); event.stopPropagation();" title="Mention @${name}">@${name}</a>`;
    });
    return escaped;
}

async function openHashtagDiscovery(tag) {
    tag = tag.replace('#', '').trim();
    switchProTab('hashtagDiscovery');

    const titleEl = document.getElementById("discoveryHashtagTitle");
    const metaEl = document.getElementById("discoveryHashtagMeta");
    const container = document.getElementById("discoveryPostsStream");

    if (titleEl) titleEl.textContent = `#${tag}`;
    if (metaEl) metaEl.textContent = `Loading posts discussing #${tag}...`;
    if (container) container.innerHTML = '<div class="post-card"><p><i class="fa-solid fa-spinner fa-spin text-purple"></i> Finding all conversations with <strong>#' + escapeHTML(tag) + '</strong>...</p></div>';

    try {
        const token = localStorage.getItem("pro_auth_token");
        const headers = token ? { "Authorization": `Bearer ${token}` } : {};
        const res = await fetch(`/api/hashtags/discovery?tag=${encodeURIComponent(tag)}`, { headers });
        const data = await res.json();

        if (data.success) {
            if (metaEl) metaEl.textContent = `${data.postCount} community post${data.postCount === 1 ? '' : 's'} tagged with #${tag}`;
            if (container) {
                if (!data.posts || data.posts.length === 0) {
                    container.innerHTML = `
                        <div class="post-card" style="text-align:center; padding: 40px 20px;">
                            <div style="font-size: 48px; color: #7c3aed; margin-bottom: 12px;"><i class="fa-solid fa-hashtag"></i></div>
                            <h3 style="margin-bottom: 8px;">No posts for #${escapeHTML(tag)} yet</h3>
                            <p style="color: var(--pro-text-secondary); margin-bottom: 16px;">Be the first to start the conversation by including <strong>#${escapeHTML(tag)}</strong> in your next post!</p>
                            <button class="pro-btn-primary" onclick="openCreatePostWithTag('${escapeHTML(tag)}')"><i class="fa-solid fa-pen-to-square"></i> Create Post with #${escapeHTML(tag)}</button>
                        </div>
                    `;
                } else {
                    container.innerHTML = data.posts.map(post => `
                        <div class="post-card" id="post-${post.id}">
                            <div class="post-header">
                                <img src="${getUserAvatar(post, post.authorName, post.authorId)}" alt="Avatar" class="post-avatar">
                                <div class="post-user-info">
                                    <strong>${escapeHTML(post.authorName)}</strong>
                                    <span>${escapeHTML(post.authorRole || 'Community Member')} Ã¢â‚¬Â¢ ${post.time}</span>
                                </div>
                            </div>
                            <div class="post-content">${parseHashtagsAndMentions(post.content)}</div>
                            ${post.media ? `
                                <div class="post-media-box" onclick="openPhotoLightbox('${post.media}')" style="cursor:pointer;" title="Click to view full photo">
                                    <img src="${post.media}" alt="Post attachment">
                                </div>
                            ` : ''}
                            <div class="post-stats-row">
                                <span><i class="fa-solid fa-thumbs-up text-blue"></i> ${post.likes || 0} likes</span>
                                <span>${post.commentsCount || 0} comments</span>
                            </div>
                            <div class="post-action-buttons">
                                <button class="post-btn ${post.isLiked ? 'liked' : ''}" onclick="toggleLikePost(${post.id})">
                                    <i class="${post.isLiked ? 'fa-solid' : 'fa-regular'} fa-thumbs-up"></i> Like
                                </button>
                                <button class="post-btn" onclick="toggleCommentsSection(${post.id})">
                                    <i class="fa-regular fa-comment"></i> Comment
                                </button>
                                <button class="post-btn" onclick="toggleBookmarkPost(${post.id})">
                                    <i class="fa-regular fa-bookmark"></i> Save
                                </button>
                                <button class="post-btn" onclick="showToast('Post shared to your network!')">
                                    <i class="fa-regular fa-share-from-square"></i> Share
                                </button>
                            </div>
                            <div class="comments-section" id="comments-${post.id}">
                                <div class="comment-input-row">
                                    <input type="text" id="input-comment-${post.id}" placeholder="Add a comment..." onkeypress="handleCommentKeyPress(event, ${post.id})">
                                    <button class="btn-outline-sm" onclick="addComment(${post.id})">Post</button>
                                </div>
                                <div class="comments-list" id="comments-list-${post.id}">
                                    ${(post.comments || []).map(c => `
                                        <div class="comment-item">
                                            <img src="${c.userAvatar || generateSVGAvatarJS(c.userName || c.author || 'User')}" alt="Avatar" class="mini-avatar" style="width:28px;height:28px;border-radius:50%;object-fit:cover;">
                                            <div class="comment-bubble">
                                                <strong>${escapeHTML(c.userName || c.author || 'Member')}</strong>
                                                <p>${escapeHTML(c.content || c.text || '')}</p>
                                            </div>
                                        </div>
                                    `).join('')}
                                </div>
                            </div>
                        </div>
                    `).join('');
                }
            }
        }
    } catch (err) {
        if (container) container.innerHTML = `<div class="post-card"><p>Failed to load #${escapeHTML(tag)} posts.</p></div>`;
        showToast("Error loading hashtag posts.");
    }
}

function openCreatePostWithTag(tag) {
    openCreatePostModal();
    const textarea = document.getElementById("newPostText");
    if (textarea) {
        textarea.value = `#${tag} `;
        textarea.focus();
    }
}

async function loadTrendingHashtags() {
    try {
        const res = await fetch('/api/hashtags/trending');
        const data = await res.json();
        if (data.success && data.trending && data.trending.length > 0) {
            const listEl = document.getElementById("trendingHashtagsList");
            if (listEl) {
                listEl.innerHTML = data.trending.map(t => `
                    <li onclick="openHashtagDiscovery('${t.tag}')" style="cursor:pointer; display:flex; justify-content:space-between; align-items:center; padding: 6px 0;">
                        <span class="news-head text-purple" style="font-weight:600;">#${escapeHTML(t.tag)}</span>
                        <span class="news-meta" style="font-size:12px; opacity:0.8;">${t.count} post${t.count === 1 ? '' : 's'}</span>
                    </li>
                `).join('');
            }
        }
    } catch (err) {
        console.log("Trending hashtags fetch error:", err);
    }
}

// Render Feed Posts with REST API Fetching
async function renderProPosts() {
    const container = document.getElementById("postsStream");
    if (!container) return;

    try {
        const token = localStorage.getItem("pro_auth_token");
        const headers = token ? { "Authorization": `Bearer ${token}` } : {};
        const res = await fetch("/api/posts", { headers });
        const data = await res.json();

        if (data.success && data.posts) {
            proPosts = data.posts;
        }
    } catch (err) {
        console.log("Using local proPosts cache");
    }

    const currentUserId = currentUser ? currentUser.id : null;
    const isUserAdmin = currentUser ? currentUser.isAdmin : false;

    container.innerHTML = proPosts.map(post => {
        const isAuthor = (currentUserId && post.authorId === currentUserId) || isUserAdmin;
        return `
        <div class="post-card" id="post-${post.id}">
            <div class="post-header">
                <img src="${getUserAvatar(post, post.authorName, post.authorId)}" alt="Avatar" class="post-avatar">
                <div class="post-user-info">
                    <strong>${escapeHTML(post.authorName)}</strong>
                    <span>${escapeHTML(post.authorRole || 'Community Member')} Ã¢â‚¬Â¢ ${post.time}</span>
                </div>
                <div class="post-header-actions" style="margin-left:auto; display:flex; align-items:center; gap:8px;">
                    ${isAuthor ? `
                        <button class="post-action-icon-btn delete-btn" onclick="deleteProPost(${post.id})" title="Delete your post" style="background:none; border:none; color:#ef4444; cursor:pointer; font-size:14px; padding:4px 8px; border-radius:6px; transition:background 0.2s;" onmouseover="this.style.background='#fee2e2'" onmouseout="this.style.background='none'">
                            <i class="fa-solid fa-trash-can"></i>
                        </button>
                    ` : `
                        <button class="post-action-icon-btn report-btn" onclick="openReportModal('POST', ${post.id})" title="Report post" style="background:none; border:none; color:#9ca3af; cursor:pointer; font-size:14px; padding:4px 8px; border-radius:6px; transition:color 0.2s;" onmouseover="this.style.color='#dc2626'" onmouseout="this.style.color='#9ca3af'">
                            <i class="fa-regular fa-flag"></i>
                        </button>
                    `}
                </div>
            </div>

            <div class="post-content">${parseHashtagsAndMentions(post.content)}</div>

            ${post.media ? `
                <div class="post-media-box" onclick="openPhotoLightbox('${post.media}')" style="cursor:pointer;" title="Click to view full photo">
                    <img src="${post.media}" alt="Post attachment">
                </div>
            ` : ''}

            <div class="post-stats-row">
                <span><i class="fa-solid fa-thumbs-up text-blue"></i> ${post.likes} likes</span>
                <span>${post.commentsCount} comments</span>
            </div>

            <div class="post-action-buttons">
                <button class="post-btn ${post.isLiked ? 'liked' : ''}" onclick="toggleLikePost(${post.id})">
                    <i class="${post.isLiked ? 'fa-solid' : 'fa-regular'} fa-thumbs-up"></i> Like
                </button>
                <button class="post-btn" onclick="toggleCommentsSection(${post.id})">
                    <i class="fa-regular fa-comment"></i> Comment
                </button>
                <button class="post-btn" onclick="toggleBookmarkPost(${post.id})">
                    <i class="fa-regular fa-bookmark"></i> Save
                </button>
                <button class="post-btn" onclick="showToast('Post shared to your network!')">
                    <i class="fa-regular fa-share-from-square"></i> Share
                </button>
            </div>

            <div class="comments-section" id="comments-${post.id}">
                <div class="comment-input-row">
                    <input type="text" id="input-comment-${post.id}" placeholder="Add a comment..." onkeypress="handleCommentKeyPress(event, ${post.id})">
                    <button class="btn-outline-sm" onclick="addComment(${post.id})">Post</button>
                </div>
                <div class="comments-list" id="comments-list-${post.id}">
                    ${(post.comments || []).map(c => `
                        <div class="comment-item">
                            <img src="${c.userAvatar || generateSVGAvatarJS(c.userName || c.author || 'User')}" alt="Avatar" class="mini-avatar" style="width:28px;height:28px;border-radius:50%;object-fit:cover;">
                            <div class="comment-bubble">
                                <strong>${escapeHTML(c.userName || c.author || 'Member')}</strong>
                                <p>${escapeHTML(c.content || c.text || '')}</p>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        </div>
        `;
    }).join('');
}

// Delete Post API Function
async function deleteProPost(postId) {
    if (!confirm("Are you sure you want to delete this post? This action cannot be undone.")) {
        return;
    }

    const token = localStorage.getItem("pro_auth_token");
    if (!token) {
        showToast("Please sign in to manage posts");
        return;
    }

    try {
        const res = await fetch("/api/posts/delete", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({ postId })
        });
        const data = await res.json();

        if (data.success) {
            showToast("Post deleted successfully");
            // Animate card removal
            const postCard = document.getElementById(`post-${postId}`);
            if (postCard) {
                postCard.style.transition = "all 0.3s ease";
                postCard.style.opacity = "0";
                postCard.style.transform = "scale(0.95)";
                setTimeout(() => {
                    renderProPosts();
                    loadMyProfileActivity();
                }, 300);
            } else {
                renderProPosts();
            }
        } else {
            alert(data.error || "Failed to delete post.");
        }
    } catch (err) {
        showToast("Error deleting post");
    }
}

// Like / Unlike Post API Integration
async function toggleLikePost(postId) {
    const token = localStorage.getItem("pro_auth_token");
    if (!token) {
        showToast("Please sign in to like posts");
        return;
    }

    try {
        const res = await fetch("/api/posts/like", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({ postId })
        });
        const data = await res.json();
        if (data.success) {
            renderProPosts();
        }
    } catch (err) {
        const post = proPosts.find(p => p.id === postId);
        if (post) {
            post.isLiked = !post.isLiked;
            post.likes += post.isLiked ? 1 : -1;
            renderProPosts();
        }
    }
}

// Toggle Comments View
function toggleCommentsSection(postId) {
    const section = document.getElementById(`comments-${postId}`);
    if (section) {
        section.classList.toggle("show");
    }
}

// Add Comment Logic with REST API
async function addComment(postId) {
    const input = document.getElementById(`input-comment-${postId}`);
    const text = input ? input.value.trim() : "";
    if (!text) return;

    const token = localStorage.getItem("pro_auth_token");
    if (!token) {
        showToast("Please sign in to post comments");
        return;
    }

    try {
        const res = await fetch("/api/posts/comment", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({ postId, content: text, text: text })
        });
        const data = await res.json();

        if (data.success) {
            if (input) input.value = "";
            await renderProPosts();
            showToast("Comment posted!");
            setTimeout(() => {
                const section = document.getElementById(`comments-${postId}`);
                if (section) section.classList.add("show");
            }, 50);
        } else {
            showToast(data.error || "Could not post comment");
        }
    } catch (err) {
        console.error("Comment submission error:", err);
        showToast("Comment submission failed. Please try again.");
    }
}

function handleCommentKeyPress(event, postId) {
    if (event.key === "Enter") {
        addComment(postId);
    }
}

// Create Post Modal Controls
function openCreatePostModal(type) {
    const modal = document.getElementById("createPostModal");
    if (modal) {
        modal.classList.add("show");
        if (type === 'photo') {
            document.getElementById("postImageUpload").click();
        }
    }
}

function closeCreatePostModal() {
    const modal = document.getElementById("createPostModal");
    if (modal) modal.classList.remove("show");
    document.getElementById("newPostText").value = "";
    removeImagePreview();
}

function handleImageSelected(event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function (e) {
            selectedImageFile = e.target.result;
            const imgPreview = document.getElementById("imagePreview");
            imgPreview.src = selectedImageFile;
            document.getElementById("imagePreviewContainer").style.display = "block";
        };
        reader.readAsDataURL(file);
    }
}

function removeImagePreview() {
    selectedImageFile = null;
    document.getElementById("imagePreviewContainer").style.display = "none";
    document.getElementById("postImageUpload").value = "";
}

// Submit New Post to REST API
async function submitNewPost() {
    const text = document.getElementById("newPostText").value.trim();
    if (!text && !selectedImageFile) {
        alert("Please enter some text or select an image for your post.");
        return;
    }

    const token = localStorage.getItem("pro_auth_token");
    if (!token) {
        showToast("Please sign in to publish posts.");
        return;
    }

    try {
        const res = await fetch("/api/posts", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({
                content: text,
                image: selectedImageFile
            })
        });
        const data = await res.json();

        if (data.success) {
            closeCreatePostModal();
            renderProPosts();
            showToast("Post published to community timeline!");
        } else {
            alert(data.error || "Failed to publish post.");
        }
    } catch (err) {
        alert("Server connection error.");
    }
}

// Connect Button Toggle
function connectUser(btn) {
    if (btn.classList.contains("connected")) {
        btn.classList.remove("connected");
        btn.innerHTML = '<i class="fa-solid fa-user-plus"></i> Connect';
        btn.style.color = "";
        showToast("Connection request cancelled");
    } else {
        btn.classList.add("connected");
        btn.innerHTML = '<i class="fa-solid fa-check"></i> Pending';
        btn.style.color = "#059669";
        showToast("Connection invitation sent!");
    }
}

// Instagram Like Toggle
function toggleInstaLike(btn) {
    const icon = btn.querySelector("i");
    if (icon.classList.contains("fa-regular")) {
        icon.classList.remove("fa-regular");
        icon.classList.add("fa-solid");
        icon.style.color = "#ef4444";
        showToast("Liked photo!");
    } else {
        icon.classList.remove("fa-solid");
        icon.classList.add("fa-regular");
        icon.style.color = "";
    }
}

// Toast Notification Helper
function showToast(message) {
    const container = document.getElementById("toastContainer");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = "toast";
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        setTimeout(() => toast.remove(), 300);
    }, 2800);
}

// Helper to escape HTML strings
function escapeHTML(str) {
    if (!str) return '';
    return String(str).replace(/[&<>'"]/g,
        tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
    );
}

// Restore Dark Theme from localStorage on initial load
if (localStorage.getItem("pro_dark_mode") === "true") {
    document.body.classList.add("dark-theme");
}

// Typing Status Checker
async function checkRemoteTypingStatus(userId) {
    if (!userId) return;
    try {
        const token = localStorage.getItem("pro_auth_token");
        if (!token) return;
        const res = await fetch(`/api/messages/typing?with=${userId}`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        const data = await res.json();
        const indicator = document.getElementById("typingIndicator");
        if (indicator) {
            indicator.style.display = data.isTyping ? "block" : "none";
        }
    } catch (err) {
        // Silently ignore typing status errors
    }
}

// Real-Time Polling Engine (Safely managed without duplicates)
function startRealtimePolling() {
    // Clear any existing intervals first to prevent duplicate runners
    stopRealtimePolling();

    window._messagingInterval = setInterval(() => {
        const token = localStorage.getItem("pro_auth_token");
        if (!token) return;

        fetchUnreadMessageCount();

        const messagingTab = document.getElementById("messagingTabContainer");
        if (messagingTab && messagingTab.style.display !== "none" && activeChatUserId) {
            loadChatHistory(activeChatUserId);
            checkRemoteTypingStatus(activeChatUserId);
        }
    }, 2000);

    window._notifInterval = setInterval(() => {
        const token = localStorage.getItem("pro_auth_token");
        if (!token) return;
        fetchNotifications();
    }, 5000);
}

function stopRealtimePolling() {
    if (window._messagingInterval) {
        clearInterval(window._messagingInterval);
        window._messagingInterval = null;
    }
    if (window._notifInterval) {
        clearInterval(window._notifInterval);
        window._notifInterval = null;
    }
}

// Start polling on initial page load if user already has an active session
if (localStorage.getItem("pro_auth_token")) {
    startRealtimePolling();
}

// Settings Center Controls
function openSettingsModal() {
    const modal = document.getElementById("settingsModal");
    if (modal) modal.classList.add("show");
    loadSettingsPreferences();
}

function closeSettingsModal() {
    const modal = document.getElementById("settingsModal");
    if (modal) modal.classList.remove("show");
}

function switchSettingsSection(sec) {
    document.querySelectorAll(".set-nav-btn").forEach(btn => btn.classList.remove("active"));
    const btn = document.getElementById(`setnav-${sec}`);
    if (btn) btn.classList.add("active");

    document.querySelectorAll(".set-section").forEach(s => s.style.display = "none");
    const target = document.getElementById(`setsec-${sec}`);
    if (target) target.style.display = "block";

    if (sec === 'blocked') loadBlockedUsers();
}

async function loadSettingsPreferences() {
    try {
        const token = localStorage.getItem("pro_auth_token");
        const headers = token ? { "Authorization": `Bearer ${token}` } : {};
        const res = await fetch("/api/settings", { headers });
        const data = await res.json();

        if (data.success && data.settings) {
            const s = data.settings;
            document.getElementById("settingTheme").value = s.theme || 'light';
            document.getElementById("settingLang").value = s.language || 'en';
            document.getElementById("settingPrivacy").value = s.privacy || 'public';
            document.getElementById("settingNotifChecked").checked = s.notificationsEnabled;
        }
    } catch (err) {
        console.log("Error loading settings");
    }
}

function applySettingTheme() {
    const theme = document.getElementById("settingTheme").value;
    if (theme === 'dark') {
        document.body.classList.add("dark-theme");
        localStorage.setItem("pro_dark_mode", "true");
    } else {
        document.body.classList.remove("dark-theme");
        localStorage.setItem("pro_dark_mode", "false");
    }
}

async function saveSettingsPreferences() {
    const themeEl = document.getElementById("settingTheme");
    const langEl = document.getElementById("settingLang");
    const privacyEl = document.getElementById("settingPrivacy");
    const notifEl = document.getElementById("settingNotifChecked");
    if (!themeEl || !langEl || !privacyEl || !notifEl) return;
    const theme = themeEl.value;
    const language = langEl.value;
    const privacy = privacyEl.value;
    const notificationsEnabled = notifEl.checked;

    const token = localStorage.getItem("pro_auth_token");
    if (!token) return;

    try {
        const res = await fetch("/api/settings/update", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({ theme, language, privacy, notificationsEnabled })
        });
        const data = await res.json();
        if (data.success) {
            closeSettingsModal();
            showToast("Settings & preferences saved successfully!");
        }
    } catch (err) {
        showToast("Error saving settings");
    }
}

async function submitChangePassword() {
    const oldPassEl = document.getElementById("oldPassInput");
    const newPassEl = document.getElementById("newPassInput");
    if (!oldPassEl || !newPassEl) return;
    const oldPassword = oldPassEl.value;
    const newPassword = newPassEl.value;

    if (!oldPassword || !newPassword) {
        alert("Please enter current and new passwords");
        return;
    }

    const token = localStorage.getItem("pro_auth_token");
    try {
        const res = await fetch("/api/settings/password", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({ oldPassword, newPassword })
        });
        const data = await res.json();
        if (data.success) {
            document.getElementById("oldPassInput").value = "";
            document.getElementById("newPassInput").value = "";
            showToast("Password updated successfully!");
        } else {
            alert(data.error || "Password change failed");
        }
    } catch (err) {
        showToast("Password update error");
    }
}

async function loadBlockedUsers() {
    const list = document.getElementById("blockedUsersList");
    if (!list) return;

    try {
        const token = localStorage.getItem("pro_auth_token");
        const headers = token ? { "Authorization": `Bearer ${token}` } : {};
        const res = await fetch("/api/settings/blocked", { headers });
        const data = await res.json();

        if (data.success) {
            if (data.blocked.length === 0) {
                list.innerHTML = '<p>No blocked members.</p>';
            } else {
                list.innerHTML = data.blocked.map(b => `
                    <div class="pending-item">
                        <div class="pending-user-info">
                            <img src="${b.avatarUrl}" alt="Avatar">
                            <div>
                                <strong>${escapeHTML(b.fullName)}</strong>
                                <p>${escapeHTML(b.headline)}</p>
                            </div>
                        </div>
                        <button class="btn-outline-sm" onclick="toggleBlockUser(${b.userId})">Unblock</button>
                    </div>
                `).join('');
            }
        }
    } catch (err) {
        console.log("Error loading blocked users");
    }
}

async function toggleBlockUser(targetUserId) {
    const token = localStorage.getItem("pro_auth_token");
    try {
        const res = await fetch("/api/settings/block", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({ targetUserId })
        });
        const data = await res.json();
        if (data.success) {
            loadBlockedUsers();
            showToast(data.isBlocked ? "Member blocked" : "Member unblocked");
        }
    } catch (err) {
        showToast("Action error");
    }
}

async function confirmDeleteAccount() {
    if (!confirm("Are you sure you want to permanently delete your account? This action cannot be undone.")) return;

    const token = localStorage.getItem("pro_auth_token");
    try {
        const res = await fetch("/api/settings/delete-account", {
            method: "POST",
            headers: { "Authorization": `Bearer ${token}` }
        });
        const data = await res.json();
        if (data.success) {
            closeSettingsModal();
            logoutPro();
            showToast("Account permanently deleted.");
        }
    } catch (err) {
        showToast("Account deletion error");
    }
}

// In-App Workflow & Bug Tracker Controls
function openWorkflowTrackerModal() {
    const modal = document.getElementById("workflowTrackerModal");
    if (modal) modal.classList.add("show");
    loadWorkflowBugTracker();
}

function closeWorkflowTrackerModal() {
    const modal = document.getElementById("workflowTrackerModal");
    if (modal) modal.classList.remove("show");
}

async function loadWorkflowBugTracker() {
    const tbody = document.getElementById("bugTrackerTableBody");
    if (!tbody) return;

    try {
        const res = await fetch("/api/workflow/bugs");
        const data = await res.json();

        if (data.success && data.bugs) {
            tbody.innerHTML = data.bugs.map(b => `
                <tr>
                    <td><strong>${b.id}</strong></td>
                    <td>${escapeHTML(b.module)}</td>
                    <td>${escapeHTML(b.title)}</td>
                    <td><span class="status-badge ${b.priority === 'CRITICAL' ? 'badge-red' : 'badge-orange'}">${b.priority}</span></td>
                    <td><strong class="status-green">Ã°Å¸Å¸Â¢ ${b.status}</strong></td>
                    <td>${b.fixDate}</td>
                    <td><span class="status-green">Ã¢Å“â€¦ ${b.regressionStatus}</span></td>
                </tr>
            `).join('');
        }
    } catch (err) {
        console.log("Error loading bug tracker");
    }
}

// Admin Panel Control Center Functions
function openAdminPanelModal() {
    if (!currentUser || (!currentUser.isAdmin && currentUser.role !== 'SUPER_ADMINISTRATOR')) {
        showToast("Access Denied: Administrator role required.");
        return;
    }
    const modal = document.getElementById("adminPanelModal");
    if (modal) modal.classList.add("show");
    loadAdminOverview();
}

function closeAdminPanelModal() {
    const modal = document.getElementById("adminPanelModal");
    if (modal) modal.classList.remove("show");
}

function switchAdminSection(sec) {
    document.querySelectorAll("#adminPanelModal .set-nav-btn").forEach(btn => btn.classList.remove("active"));
    const btn = document.getElementById(`adminnav-${sec}`);
    if (btn) btn.classList.add("active");

    document.querySelectorAll("#adminPanelModal .set-section").forEach(s => s.style.display = "none");
    const target = document.getElementById(`adminsec-${sec}`);
    if (target) target.style.display = "block";

    if (sec === 'users') loadAdminUsers();
    else if (sec === 'reports') loadAdminReports();
    else if (sec === 'history') loadAdminLoginHistory();
}

async function loadAdminOverview() {
    try {
        const token = localStorage.getItem("pro_auth_token");
        const headers = token ? { "Authorization": `Bearer ${token}` } : {};
        const res = await fetch("/api/admin/overview", { headers });
        const data = await res.json();

        if (data.success && data.overview) {
            const o = data.overview;
            document.getElementById("adminTotalUsers").textContent = o.totalUsers;
            document.getElementById("adminTotalPosts").textContent = o.totalPosts;
            document.getElementById("adminTotalMessages").textContent = o.totalMessages;
            document.getElementById("adminPendingReports").textContent = o.pendingReports;
        }
    } catch (err) {
        console.log("Error loading admin overview");
    }
}

async function loadAdminUsers() {
    const tbody = document.getElementById("adminUsersTableBody");
    if (!tbody) return;

    try {
        const token = localStorage.getItem("pro_auth_token");
        const headers = token ? { "Authorization": `Bearer ${token}` } : {};
        const res = await fetch("/api/admin/users", { headers });
        const data = await res.json();

        if (data.success && data.users) {
            tbody.innerHTML = data.users.map(u => `
                <tr>
                    <td><strong>#${u.id}</strong></td>
                    <td>
                        <div class="pending-user-info">
                            <img src="${u.avatarUrl}" alt="Avatar" class="mini-avatar">
                            <div>
                                <strong>${escapeHTML(u.fullName)}</strong>
                                <p>${escapeHTML(u.email)}</p>
                            </div>
                        </div>
                    </td>
                    <td>${u.isAdmin ? '<span class="status-badge badge-orange">Admin</span>' : 'Member'}</td>
                    <td><strong class="${u.status === 'BANNED' ? 'text-red' : 'status-green'}">${u.status}</strong></td>
                    <td>
                        <div style="display:flex; gap:6px;">
                            <button class="${u.status === 'BANNED' ? 'pro-btn-primary' : 'btn-outline-sm'}" onclick="adminBanUser(${u.id})">
                                ${u.status === 'BANNED' ? 'Unban' : 'Ban User'}
                            </button>
                            <button class="btn-outline-sm" onclick="adminResetPassword(${u.id})">Reset Pass</button>
                            <button class="btn-danger" onclick="adminDeleteUser(${u.id})">Delete</button>
                        </div>
                    </td>
                </tr>
            `).join('');
        }
    } catch (err) {
        console.log("Error loading admin users");
    }
}

async function adminBanUser(targetUserId) {
    const token = localStorage.getItem("pro_auth_token");
    try {
        const res = await fetch("/api/admin/users/ban", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({ targetUserId })
        });
        const data = await res.json();
        if (data.success) {
            loadAdminUsers();
            showToast(`User status updated to ${data.newStatus}`);
        }
    } catch (err) {
        showToast("Ban action error");
    }
}

async function adminDeleteUser(targetUserId) {
    if (!confirm("Are you sure you want to delete this account?")) return;
    const token = localStorage.getItem("pro_auth_token");
    try {
        const res = await fetch("/api/admin/users/delete", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({ targetUserId })
        });
        const data = await res.json();
        if (data.success) {
            loadAdminUsers();
            loadAdminOverview();
            showToast("User account deleted");
        }
    } catch (err) {
        showToast("Delete error");
    }
}

async function adminResetPassword(targetUserId) {
    const token = localStorage.getItem("pro_auth_token");
    try {
        const res = await fetch("/api/admin/users/reset-password", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({ targetUserId })
        });
        const data = await res.json();
        if (data.success) {
            alert(`Password reset successfully! New temporary password: ${data.newPassword}`);
        }
    } catch (err) {
        showToast("Reset password error");
    }
}

async function submitAdminBroadcast() {
    const broadcastEl = document.getElementById("adminBroadcastText");
    if (!broadcastEl) return;
    const announcement = broadcastEl.value.trim();
    if (!announcement) {
        alert("Please enter announcement text");
        return;
    }

    const token = localStorage.getItem("pro_auth_token");
    try {
        const res = await fetch("/api/admin/broadcast", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({ announcement })
        });
        const data = await res.json();
        if (data.success) {
            document.getElementById("adminBroadcastText").value = "";
            showToast(`Announcement broadcasted to ${data.broadcastCount} members!`);
        }
    } catch (err) {
        showToast("Broadcast error");
    }
}

async function loadAdminReports() {
    const list = document.getElementById("adminReportsList");
    if (!list) return;

    try {
        const token = localStorage.getItem("pro_auth_token");
        const headers = token ? { "Authorization": `Bearer ${token}` } : {};
        const res = await fetch("/api/admin/reports", { headers });
        const data = await res.json();

        if (data.success) {
            if (data.reports.length === 0) {
                list.innerHTML = '<p>No content reports submitted.</p>';
            } else {
                list.innerHTML = data.reports.map(r => `
                    <div class="pending-item">
                        <div>
                            <strong>Flagged ${r.targetType} #${r.targetId}</strong>
                            <p>Reason: ${escapeHTML(r.reason)} Ã¢â‚¬Â¢ Reported by ${escapeHTML(r.reporterName)}</p>
                        </div>
                        <button class="btn-danger" onclick="adminDeletePost(${r.targetId})">Remove Content</button>
                    </div>
                `).join('');
            }
        }
    } catch (err) {
        console.log("Error loading admin reports");
    }
}

async function adminDeletePost(postId) {
    const token = localStorage.getItem("pro_auth_token");
    try {
        const res = await fetch("/api/admin/posts/delete", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({ postId })
        });
        const data = await res.json();
        if (data.success) {
            loadAdminReports();
            loadAdminOverview();
            renderProPosts();
            showToast("Inappropriate post removed");
        }
    } catch (err) {
        showToast("Delete post error");
    }
}

async function loadAdminLoginHistory() {
    const tbody = document.getElementById("adminLoginLogsBody");
    if (!tbody) return;

    try {
        const token = localStorage.getItem("pro_auth_token");
        const headers = token ? { "Authorization": `Bearer ${token}` } : {};
        const res = await fetch("/api/admin/login-history", { headers });
        const data = await res.json();

        if (data.success && data.history) {
            tbody.innerHTML = data.history.map(h => `
                <tr>
                    <td><strong>#${h.id}</strong></td>
                    <td>${escapeHTML(h.fullName)}</td>
                    <td>${escapeHTML(h.email)}</td>
                    <td>${h.ipAddress}</td>
                    <td><strong class="status-green">${h.status}</strong></td>
                    <td>${h.loginTime}</td>
                </tr>
            `).join('');
        }
    } catch (err) {
        console.log("Error loading login history");
    }
}

/* ==========================================================================
   SAFE EXPANSION: USER SAFETY, PASSWORD RECOVERY & PROFILE ENHANCEMENTS
   ========================================================================== */
async function requestPasswordResetPrompt() {
    const email = prompt("Enter your registered email address for password reset:");
    if (!email || !email.trim()) return;

    try {
        const res = await fetch("/api/auth/forgot-password", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: email.trim() })
        });
        const data = await res.json();
        showToast(data.message || "Password reset instructions sent.");
    } catch (err) {
        showToast("Error requesting password reset.");
    }
}

async function submitContentReport(targetType, targetId) {
    const reason = prompt("Please select or enter the reason for reporting (e.g. Spam, Harassment, Inappropriate):", "Inappropriate Content");
    if (!reason || !reason.trim()) return;

    try {
        const token = localStorage.getItem("pro_auth_token");
        const headers = { "Content-Type": "application/json" };
        if (token) headers["Authorization"] = `Bearer ${token}`;

        const res = await fetch("/api/reports/create", {
            method: "POST",
            headers,
            body: JSON.stringify({ targetType, targetId, reason: reason.trim() })
        });
        const data = await res.json();
        if (data.success) {
            showToast("Thank you. Report submitted for moderator review.");
        } else {
            showToast(data.error || "Failed to submit report.");
        }
    } catch (err) {
        showToast("Error submitting report.");
    }
}

async function toggleMuteUser(targetUserId, userName) {
    try {
        const token = localStorage.getItem("pro_auth_token");
        const headers = { "Content-Type": "application/json" };
        if (token) headers["Authorization"] = `Bearer ${token}`;

        const res = await fetch("/api/settings/mute", {
            method: "POST",
            headers,
            body: JSON.stringify({ targetUserId })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.isMuted ? `Muted ${userName || 'user'}. Their posts are now hidden.` : `Unmuted ${userName || 'user'}.`);
            if (typeof loadFeedPosts === "function") loadFeedPosts();
        }
    } catch (err) {
        showToast("Error updating mute status.");
    }
}

async function addProfileSkill(skillName) {
    if (!skillName || !skillName.trim()) return;
    try {
        const token = localStorage.getItem("pro_auth_token");
        const headers = { "Content-Type": "application/json" };
        if (token) headers["Authorization"] = `Bearer ${token}`;

        const res = await fetch("/api/profile/skills", {
            method: "POST",
            headers,
            body: JSON.stringify({ action: "ADD", skill: skillName.trim() })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`Skill added: ${skillName}`);
        }
    } catch (err) {
        showToast("Error adding skill.");
    }
}

// ==========================================================================
// RAPIDO CLONE APPLICATION CONTROLLER (PREMIUM & HIGH AUTHENTICITY)
// ==========================================================================

// Coordinate dictionary for Bengaluru routing map
const RAPIDO_LOCATIONS = {
    "MG Road": { x: 150, y: 150, name: "MG Road Metro Station" },
    "Indiranagar": { x: 450, y: 100, name: "Indiranagar 100ft Road" },
    "Koramangala": { x: 400, y: 350, name: "Koramangala 5th Block" },
    "HSR Layout": { x: 300, y: 500, name: "HSR Layout Sector 1" },
    "Whitefield": { x: 700, y: 220, name: "Whitefield ITPL Main Gate" },
    "Airport": { x: 550, y: 40, name: "Kempegowda Airport (BLR)" }
};

// Predefined street route paths connecting the nodes along the highways
const RAPIDO_PATHS = {
    "Airport-MG Road": [{ x: 550, y: 40 }, { x: 350, y: 70 }, { x: 150, y: 150 }],
    "MG Road-Airport": [{ x: 150, y: 150 }, { x: 350, y: 70 }, { x: 550, y: 40 }],

    "MG Road-Indiranagar": [{ x: 150, y: 150 }, { x: 300, y: 120 }, { x: 450, y: 100 }],
    "Indiranagar-MG Road": [{ x: 450, y: 100 }, { x: 300, y: 120 }, { x: 150, y: 150 }],

    "Indiranagar-Whitefield": [{ x: 450, y: 100 }, { x: 580, y: 160 }, { x: 700, y: 220 }],
    "Whitefield-Indiranagar": [{ x: 700, y: 220 }, { x: 580, y: 160 }, { x: 450, y: 100 }],

    "MG Road-Koramangala": [{ x: 150, y: 150 }, { x: 220, y: 250 }, { x: 400, y: 350 }],
    "Koramangala-MG Road": [{ x: 400, y: 350 }, { x: 220, y: 250 }, { x: 150, y: 150 }],

    "Indiranagar-Koramangala": [{ x: 450, y: 100 }, { x: 420, y: 220 }, { x: 400, y: 350 }],
    "Koramangala-Indiranagar": [{ x: 400, y: 350 }, { x: 420, y: 220 }, { x: 450, y: 100 }],

    "Koramangala-HSR Layout": [{ x: 400, y: 350 }, { x: 350, y: 420 }, { x: 300, y: 500 }],
    "HSR Layout-Koramangala": [{ x: 300, y: 500 }, { x: 350, y: 420 }, { x: 400, y: 350 }]
};

// Global variables for Rapido state
let rapidoRole = "RIDER"; // RIDER or CAPTAIN
let selectedService = "BIKE"; // BIKE, AUTO, CAB
let activeBooking = null; // Stores currently booking details
let rapidoMapAnimationId = null;
let rapidoCaptainMapAnimationId = null;
let nearbyCaptains = [];
let rapidoChatHistory = [];
let rapidoFeedbackRating = 0;

// Captain Mode state variables
let driverStats = { is_online: false, total_earnings: 0.0, total_rides: 0 };
let currentIncomingRequest = null;
let incomingRequestTimer = null;
let driverActiveTrip = null;

// Peer-to-peer real-time poller references
let riderStatusPoller = null;
let captainOffersPoller = null;
let chatPoller = null;
let lastChatMsgCount = 0;

// Multi-segment pathfinder assembler
function getRoutePath(locA, locB) {
    if (locA === locB) return [{ ...RAPIDO_LOCATIONS[locA], name: locA }];

    const directKey = `${locA}-${locB}`;
    if (RAPIDO_PATHS[directKey]) {
        return RAPIDO_PATHS[directKey].map((pt, i) => ({
            ...pt,
            name: i === 0 ? locA : (i === RAPIDO_PATHS[directKey].length - 1 ? locB : "Main Street")
        }));
    }

    const lookupKey = `${locA}-${locB}`;
    const lookup = {
        "Airport-Indiranagar": ["Airport", "MG Road", "Indiranagar"],
        "Indiranagar-Airport": ["Indiranagar", "MG Road", "Airport"],
        "Airport-Whitefield": ["Airport", "MG Road", "Indiranagar", "Whitefield"],
        "Whitefield-Airport": ["Whitefield", "Indiranagar", "MG Road", "Airport"],
        "Airport-Koramangala": ["Airport", "MG Road", "Koramangala"],
        "Koramangala-Airport": ["Koramangala", "MG Road", "Airport"],
        "Airport-HSR Layout": ["Airport", "MG Road", "Koramangala", "HSR Layout"],
        "HSR Layout-Airport": ["HSR Layout", "Koramangala", "MG Road", "Airport"],
        "MG Road-Whitefield": ["MG Road", "Indiranagar", "Whitefield"],
        "Whitefield-MG Road": ["Whitefield", "Indiranagar", "MG Road"],
        "MG Road-HSR Layout": ["MG Road", "Koramangala", "HSR Layout"],
        "HSR Layout-MG Road": ["HSR Layout", "Koramangala", "MG Road"],
        "Indiranagar-HSR Layout": ["Indiranagar", "Koramangala", "HSR Layout"],
        "HSR Layout-Indiranagar": ["HSR Layout", "Koramangala", "Indiranagar"],
        "Whitefield-Koramangala": ["Whitefield", "Indiranagar", "Koramangala"],
        "Koramangala-Whitefield": ["Koramangala", "Indiranagar", "Whitefield"],
        "Whitefield-HSR Layout": ["Whitefield", "Indiranagar", "Koramangala", "HSR Layout"],
        "HSR Layout-Whitefield": ["HSR Layout", "Koramangala", "Indiranagar", "Whitefield"]
    };

    const nodeNames = lookup[lookupKey];
    if (nodeNames) {
        let coordinates = [];
        for (let idx = 0; idx < nodeNames.length - 1; idx++) {
            const segA = nodeNames[idx];
            const segB = nodeNames[idx + 1];
            const segKey = `${segA}-${segB}`;
            const segCoords = RAPIDO_PATHS[segKey] || [RAPIDO_LOCATIONS[segA], RAPIDO_LOCATIONS[segB]];

            const resolvedCoords = segCoords.map((pt, i) => ({
                ...pt,
                name: i === 0 ? segA : (i === segCoords.length - 1 ? segB : "Highway Junction")
            }));

            if (coordinates.length > 0) {
                coordinates = coordinates.concat(resolvedCoords.slice(1));
            } else {
                coordinates = coordinates.concat(resolvedCoords);
            }
        }
        return coordinates;
    }

    return [
        { ...RAPIDO_LOCATIONS[locA], name: locA },
        { ...RAPIDO_LOCATIONS[locB], name: locB }
    ];
}

// Vector vehicle rendering engine
function drawVehicle(ctx, x, y, angle, type, isCaptain) {
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(angle);

    // Choose primary theme color (Green for online active captains, yellow for rider)
    const primaryColor = isCaptain ? "#10b981" : "var(--rapido-yellow)";

    if (type === "BIKE") {
        // Draw tires
        ctx.fillStyle = "#3f3f46";
        ctx.fillRect(-8, -2, 4, 4); // rear
        ctx.fillRect(4, -2, 4, 4);  // front

        // Chassis frame
        ctx.fillStyle = "#27272a";
        ctx.fillRect(-5, -1, 10, 2);

        // Fuel tank
        ctx.fillStyle = primaryColor;
        ctx.beginPath();
        ctx.ellipse(0, 0, 5, 2.5, 0, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = "#121212";
        ctx.lineWidth = 1;
        ctx.stroke();

        // Rider head helmet (Black)
        ctx.fillStyle = "#121212";
        ctx.beginPath();
        ctx.arc(-1, 0, 2, 0, Math.PI * 2);
        ctx.fill();

        // Passenger helmet (Yellow)
        if (!isCaptain) {
            ctx.fillStyle = "var(--rapido-yellow)";
            ctx.beginPath();
            ctx.arc(-4, 0, 2, 0, Math.PI * 2);
            ctx.fill();
            ctx.strokeStyle = "#121212";
            ctx.lineWidth = 0.5;
            ctx.stroke();
        }

        // Light glow
        ctx.fillStyle = "rgba(255, 221, 0, 0.4)";
        ctx.beginPath();
        ctx.moveTo(8, 0);
        ctx.lineTo(18, -6);
        ctx.lineTo(18, 6);
        ctx.closePath();
        ctx.fill();

    } else if (type === "AUTO") {
        // Rear wheels
        ctx.fillStyle = "#3f3f46";
        ctx.fillRect(-6, -6.5, 3, 1.5);
        ctx.fillRect(-6, 5, 3, 1.5);

        // Cabin
        ctx.fillStyle = primaryColor;
        ctx.beginPath();
        ctx.roundRect(-7, -5, 14, 10, [2, 4, 4, 2]);
        ctx.fill();
        ctx.strokeStyle = "#121212";
        ctx.lineWidth = 1.2;
        ctx.stroke();

        // Canopy
        ctx.fillStyle = "#121212";
        ctx.beginPath();
        ctx.roundRect(-4, -4, 9, 8, 2);
        ctx.fill();

        // Front single wheel nose
        ctx.fillStyle = "#27272a";
        ctx.fillRect(7, -1.5, 2.5, 3);

        // Dual front lights
        ctx.fillStyle = "#ffdd00";
        ctx.beginPath();
        ctx.arc(8, -2, 1, 0, Math.PI * 2);
        ctx.arc(8, 2, 1, 0, Math.PI * 2);
        ctx.fill();

    } else {
        // CAB (Sedan)
        // Wheels
        ctx.fillStyle = "#121212";
        ctx.fillRect(-6, -7, 4, 1.5);
        ctx.fillRect(-6, 5.5, 4, 1.5);
        ctx.fillRect(4, -7, 4, 1.5);
        ctx.fillRect(4, 5.5, 4, 1.5);

        // Body
        ctx.fillStyle = primaryColor;
        ctx.beginPath();
        ctx.roundRect(-9, -5.5, 18, 11, 3);
        ctx.fill();
        ctx.strokeStyle = "#121212";
        ctx.lineWidth = 1.2;
        ctx.stroke();

        // Windshield
        ctx.fillStyle = "#a5d8ff";
        ctx.beginPath();
        ctx.roundRect(-3, -4, 7, 8, 1.5);
        ctx.fill();

        // Roof
        ctx.fillStyle = "#121212";
        ctx.beginPath();
        ctx.roundRect(-4, -3, 6, 6, 1);
        ctx.fill();

        // Cab sign
        ctx.fillStyle = "#ffdd00";
        ctx.fillRect(-1.5, -1, 3, 2);
        ctx.strokeStyle = "#121212";
        ctx.lineWidth = 0.5;
        ctx.stroke();
    }

    ctx.restore();
}

// Cityscape Vector Map Renderer (Ulsoor Lake, Cubbon Park, tech zones, traffic roads)
function drawCityBackground(ctx, width, height, isDark) {
    // Base surface fill
    ctx.fillStyle = isDark ? "#121212" : "#f1f3f6";
    ctx.fillRect(0, 0, width, height);

    // Draw Parks (Greenery zones)
    ctx.fillStyle = isDark ? "#142d1b" : "#d3f9d8";
    ctx.strokeStyle = isDark ? "#1d3d27" : "#b2f2bb";
    ctx.lineWidth = 1.5;

    // Cubbon Park (near MG Road)
    ctx.beginPath();
    ctx.roundRect(40, 80, 110, 55, 8);
    ctx.fill();
    ctx.stroke();

    // Lalbagh Botanical Garden (south)
    ctx.beginPath();
    ctx.roundRect(220, 390, 95, 75, 12);
    ctx.fill();
    ctx.stroke();

    // Indiranagar local park
    ctx.beginPath();
    ctx.roundRect(480, 130, 40, 35, 6);
    ctx.fill();
    ctx.stroke();

    // Draw Lakes (Water zones)
    ctx.fillStyle = isDark ? "#122a4a" : "#a5d8ff";
    ctx.strokeStyle = isDark ? "#1c3d69" : "#74c0fc";

    // Ulsoor Lake (center)
    ctx.beginPath();
    ctx.arc(330, 160, 28, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    // Bellandur Lake (southeast)
    ctx.beginPath();
    ctx.ellipse(590, 370, 48, 26, Math.PI / 6, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    // ITPL Corporate Tech Blocks
    ctx.fillStyle = isDark ? "#242427" : "#e9ecef";
    ctx.strokeStyle = isDark ? "#3f3f46" : "#dee2e6";

    ctx.beginPath();
    ctx.roundRect(700, 240, 45, 30, 4);
    ctx.fill();
    ctx.stroke();
    ctx.beginPath();
    ctx.roundRect(715, 280, 35, 40, 4);
    ctx.fill();
    ctx.stroke();

    // Local street grid lines (Secondary lanes)
    ctx.strokeStyle = isDark ? "#1a1a1a" : "#ffffff";
    ctx.lineWidth = 2.5;
    ctx.lineCap = "round";

    const gridCols = [80, 180, 280, 380, 480, 580, 680];
    const gridRows = [60, 130, 200, 270, 340, 410, 480];

    gridCols.forEach(col => {
        ctx.beginPath();
        ctx.moveTo(col, 10);
        ctx.lineTo(col, height - 10);
        ctx.stroke();
    });
    gridRows.forEach(row => {
        ctx.beginPath();
        ctx.moveTo(10, row);
        ctx.lineTo(width - 10, row);
        ctx.stroke();
    });

    // Draw Main Asphalt Highways
    ctx.strokeStyle = isDark ? "#27272a" : "#e2e8f0";
    ctx.lineWidth = 14;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    const drawHighways = () => {
        // MG road -> Indiranagar -> Whitefield
        ctx.beginPath();
        ctx.moveTo(150, 150);
        ctx.lineTo(300, 120);
        ctx.lineTo(450, 100);
        ctx.lineTo(580, 160);
        ctx.lineTo(700, 220);
        ctx.stroke();

        // Koramangala -> HSR layout
        ctx.beginPath();
        ctx.moveTo(400, 350);
        ctx.lineTo(350, 420);
        ctx.lineTo(300, 500);
        ctx.stroke();

        // Connectors
        ctx.beginPath();
        ctx.moveTo(150, 150);
        ctx.lineTo(220, 250);
        ctx.lineTo(400, 350);
        ctx.stroke();

        ctx.beginPath();
        ctx.moveTo(450, 100);
        ctx.lineTo(420, 220);
        ctx.lineTo(400, 350);
        ctx.stroke();

        ctx.beginPath();
        ctx.moveTo(550, 40);
        ctx.lineTo(350, 70);
        ctx.lineTo(150, 150);
        ctx.stroke();
    };

    drawHighways();

    // Layered inner center lines
    ctx.strokeStyle = isDark ? "#3f3f46" : "#cbd5e1";
    ctx.lineWidth = 11;
    drawHighways();

    // Draw traffic speed flow colors
    ctx.lineWidth = 2.5;

    // Segment 1: Airport -> MG Road (Green/Free traffic)
    ctx.strokeStyle = "#51cf66";
    ctx.beginPath(); ctx.moveTo(550, 40); ctx.lineTo(350, 70); ctx.stroke();

    // Segment 2: MG Road -> Indiranagar (Yellow/Moderate traffic)
    ctx.strokeStyle = "#fcc419";
    ctx.beginPath(); ctx.moveTo(150, 150); ctx.lineTo(300, 120); ctx.stroke();

    // Segment 3: Koramangala -> HSR Layout (Red/Heavy congestion)
    ctx.strokeStyle = "#ff8787";
    ctx.beginPath(); ctx.moveTo(400, 350); ctx.lineTo(350, 420); ctx.stroke();
}

// Sound Synthesizer using Web Audio API (Premium Envelope Filters)
function playRapidoSound(type) {
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        if (!audioCtx) return;

        const osc = audioCtx.createOscillator();
        const gainNode = audioCtx.createGain();
        osc.connect(gainNode);
        gainNode.connect(audioCtx.destination);

        const now = audioCtx.currentTime;

        if (type === "request") {
            // Warm sonar ring sweep
            osc.type = "sine";
            osc.frequency.setValueAtTime(380, now);
            osc.frequency.exponentialRampToValueAtTime(760, now + 0.35);
            gainNode.gain.setValueAtTime(0.12, now);
            gainNode.gain.linearRampToValueAtTime(0.001, now + 0.35);
            osc.start(now);
            osc.stop(now + 0.35);
        } else if (type === "assigned") {
            // Premium double-arpeggio chime (C5 -> E5 -> G5 -> C6)
            osc.type = "triangle";
            const notes = [523.25, 659.25, 783.99, 1046.50];
            notes.forEach((freq, idx) => {
                const noteTime = now + idx * 0.08;
                osc.frequency.setValueAtTime(freq, noteTime);
            });
            gainNode.gain.setValueAtTime(0.15, now);
            gainNode.gain.linearRampToValueAtTime(0.001, now + 0.5);
            osc.start(now);
            osc.stop(now + 0.5);
        } else if (type === "arrived") {
            // Soft motorcycle double beep
            osc.type = "triangle";
            osc.frequency.setValueAtTime(420, now);
            gainNode.gain.setValueAtTime(0.1, now);
            gainNode.gain.linearRampToValueAtTime(0.001, now + 0.12);
            osc.start(now);
            osc.stop(now + 0.12);

            // Second beep
            setTimeout(() => {
                playSingleBeep(420, 0.1, 0.12);
            }, 180);
        } else if (type === "completed") {
            // Uplifting major scale arpeggio
            osc.type = "sine";
            const scale = [523.25, 587.33, 659.25, 698.46, 783.99];
            scale.forEach((freq, idx) => {
                osc.frequency.setValueAtTime(freq, now + idx * 0.07);
            });
            gainNode.gain.setValueAtTime(0.18, now);
            gainNode.gain.linearRampToValueAtTime(0.001, now + 0.6);
            osc.start(now);
            osc.stop(now + 0.6);
        }
    } catch (e) {
        console.warn("Web Audio system warning:", e);
    }
}

function playSingleBeep(freq, gainVal, duration) {
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.type = "triangle";
        osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
        gain.gain.setValueAtTime(gainVal, audioCtx.currentTime);
        gain.gain.linearRampToValueAtTime(0.001, audioCtx.currentTime + duration);
        osc.start();
        osc.stop(audioCtx.currentTime + duration);
    } catch (err) { }
}

// Show view controller trigger
async function openRapidoClone() {
    if (checkAppLock()) return;

    const token = localStorage.getItem("pro_auth_token");
    if (!token) {
        intendedApp = "rapido";
        showView("pro-network-view");
        showProStage("pro-login-stage");
        return;
    }

    intendedApp = "rapido";
    showView("rapido-view");

    // Cache the user full name from API profile on boot
    try {
        const res = await fetch("/api/profile/full", {
            headers: { "Authorization": `Bearer ${token}` }
        });
        const data = await res.json();
        if (data.success && data.profile) {
            localStorage.setItem("pro_auth_user_name", data.profile.fullName || data.profile.email);
        }
    } catch (e) { }

    document.getElementById("rapido-rider-body").style.display = "flex";
    document.getElementById("rapido-captain-body").style.display = "none";
    document.getElementById("rapido-mode-toggle").innerHTML = `<i class="fa-solid fa-motorcycle"></i> <span>Switch to Captain Mode</span>`;
    rapidoRole = "RIDER";

    resetRiderBookingView();
    calculateRapidoFare();
    initRapidoRiderMap();
    fetchDriverStats();
}

function resetRiderBookingView() {
    activeBooking = null;
    if (riderStatusPoller) clearInterval(riderStatusPoller);
    if (chatPoller) clearInterval(chatPoller);

    document.querySelectorAll(".rapido-panel-state").forEach(p => p.classList.remove("active"));
    document.getElementById("rapido-state-search").classList.add("active");
    document.getElementById("rapidoChatBoxContent").style.display = "none";
    document.getElementById("chat-arrow-icon").className = "fa-solid fa-chevron-up";

    document.getElementById("telemetry-speed").innerText = "0 km/h";
    document.getElementById("telemetry-guidance").innerText = "Select route to book ride.";
}

// Distance calculator
function getRouteDistance(locA, locB) {
    const coordsA = RAPIDO_LOCATIONS[locA];
    const coordsB = RAPIDO_LOCATIONS[locB];
    if (!coordsA || !coordsB) return 0;

    const dx = coordsA.x - coordsB.x;
    const dy = coordsA.y - coordsB.y;
    const pxDist = Math.sqrt(dx * dx + dy * dy);
    return Math.max(1.5, Math.round((pxDist / 80) * 10) / 10);
}

// Calculate fares based on dropdowns
function calculateRapidoFare() {
    const pickup = document.getElementById("rapido-pickup").value;
    const dropoff = document.getElementById("rapido-dropoff").value;

    if (pickup === dropoff) {
        document.getElementById("rapido-route-info").style.opacity = "0.5";
        document.getElementById("price-bike").innerText = "Ã¢â€šÂ¹15";
        document.getElementById("price-auto").innerText = "Ã¢â€šÂ¹30";
        document.getElementById("price-cab").innerText = "Ã¢â€šÂ¹60";
        return;
    }
    document.getElementById("rapido-route-info").style.opacity = "1";

    const dist = getRouteDistance(pickup, dropoff);
    const etaMin = Math.round(dist * 2.5);

    const bikePrice = Math.round(15 + dist * 8);
    const autoPrice = Math.round(30 + dist * 12);
    const cabPrice = Math.round(60 + dist * 18);

    document.getElementById("rapido-route-info").innerHTML = `<i class="fa-solid fa-route"></i> Distance: <span>${dist} km</span> &nbsp;&bull;&nbsp; Est. Time: <span>${etaMin} mins</span>`;
    document.getElementById("price-bike").innerText = `Ã¢â€šÂ¹${bikePrice}`;
    document.getElementById("price-auto").innerText = `Ã¢â€šÂ¹${autoPrice}`;
    document.getElementById("price-cab").innerText = `Ã¢â€šÂ¹${cabPrice}`;
}

function selectRapidoService(service) {
    selectedService = service;
    document.querySelectorAll(".service-option").forEach(opt => opt.classList.remove("selected"));
    if (service === "BIKE") document.getElementById("opt-bike").classList.add("selected");
    else if (service === "AUTO") document.getElementById("opt-auto").classList.add("selected");
    else if (service === "CAB") document.getElementById("opt-cab").classList.add("selected");
}

// Map Animation loop
function initRapidoRiderMap() {
    if (rapidoMapAnimationId) cancelAnimationFrame(rapidoMapAnimationId);

    const canvas = document.getElementById("rapidoMapCanvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    const dpr = window.devicePixelRatio || 1;
    canvas.width = canvas.parentElement.clientWidth * dpr;
    canvas.height = 450 * dpr;
    canvas.style.width = canvas.parentElement.clientWidth + "px";
    canvas.style.height = "450px";
    ctx.scale(dpr, dpr);

    // Spawn idle captains
    nearbyCaptains = [];
    const keys = Object.keys(RAPIDO_LOCATIONS);
    for (let i = 0; i < 4; i++) {
        const randLoc = RAPIDO_LOCATIONS[keys[Math.floor(Math.random() * keys.length)]];
        nearbyCaptains.push({
            x: randLoc.x + (Math.random() - 0.5) * 50,
            y: randLoc.y + (Math.random() - 0.5) * 50,
            angle: Math.random() * Math.PI * 2,
            speed: 0.22 + Math.random() * 0.3
        });
    }

    function drawMap() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Draw Cityscape Background
        drawCityBackground(ctx, canvas.width / dpr, 450, false);

        // Draw Locations pins
        for (let name in RAPIDO_LOCATIONS) {
            const loc = RAPIDO_LOCATIONS[name];
            ctx.fillStyle = "#ffffff";
            ctx.beginPath();
            ctx.arc(loc.x, loc.y, 6, 0, Math.PI * 2);
            ctx.fill();
            ctx.strokeStyle = "#1e293b";
            ctx.lineWidth = 2.5;
            ctx.stroke();

            ctx.fillStyle = "#0f172a";
            ctx.beginPath();
            ctx.arc(loc.x, loc.y, 2, 0, Math.PI * 2);
            ctx.fill();

            // Labels
            ctx.fillStyle = "#334155";
            ctx.font = "bold 9px Outfit, sans-serif";
            ctx.textAlign = "center";
            ctx.fillText(name, loc.x, loc.y - 12);
        }

        // Draw idle captains
        nearbyCaptains.forEach(cap => {
            cap.x += Math.cos(cap.angle) * cap.speed;
            cap.y += Math.sin(cap.angle) * cap.speed;

            if (cap.x < 50 || cap.x > (canvas.width / dpr) - 50) cap.angle = Math.PI - cap.angle;
            if (cap.y < 50 || cap.y > 400) cap.angle = -cap.angle;

            if (Math.random() < 0.02) cap.angle += (Math.random() - 0.5) * 1.5;

            // Draw vehicle vector (Idle motorcycles)
            drawVehicle(ctx, cap.x, cap.y, cap.angle, "BIKE", true);
        });

        // Draw active trip routes and captain
        if (activeBooking && activeBooking.pickup && activeBooking.dropoff) {
            const pick = RAPIDO_LOCATIONS[activeBooking.pickup];
            const drop = RAPIDO_LOCATIONS[activeBooking.dropoff];

            // Draw Pickup Flag
            ctx.fillStyle = "#10b981";
            ctx.beginPath();
            ctx.arc(pick.x, pick.y, 8, 0, Math.PI * 2);
            ctx.fill();
            ctx.strokeStyle = "#ffffff";
            ctx.lineWidth = 2.5;
            ctx.stroke();

            // Pulsing pickup ring
            ctx.strokeStyle = "rgba(16,185,129,0.4)";
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            ctx.arc(pick.x, pick.y, 10 + Math.sin(Date.now() / 150) * 4, 0, Math.PI * 2);
            ctx.stroke();

            // Draw Drop Flag
            ctx.fillStyle = "#ef4444";
            ctx.beginPath();
            ctx.arc(drop.x, drop.y, 8, 0, Math.PI * 2);
            ctx.fill();
            ctx.strokeStyle = "#ffffff";
            ctx.lineWidth = 2.5;
            ctx.stroke();

            // Pulsing drop ring
            ctx.strokeStyle = "rgba(239,68,68,0.4)";
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            ctx.arc(drop.x, drop.y, 10 + Math.sin(Date.now() / 150) * 4, 0, Math.PI * 2);
            ctx.stroke();

            // Draw route lines connecting the assembled path nodes
            const routePath = activeBooking.state === "IN_PROGRESS"
                ? activeBooking.dropoffRoutePath
                : activeBooking.routePath;

            if (routePath && routePath.length > 0) {
                ctx.strokeStyle = "rgba(255, 221, 0, 0.75)";
                ctx.lineWidth = 4.5;
                ctx.lineCap = "round";
                ctx.lineJoin = "round";
                ctx.beginPath();
                ctx.moveTo(routePath[0].x, routePath[0].y);
                for (let j = 1; j < routePath.length; j++) {
                    ctx.lineTo(routePath[j].x, routePath[j].y);
                }
                ctx.stroke();
            }

            // Draw animating Captain vehicle
            if (activeBooking.captainCoords) {
                const capCoords = activeBooking.captainCoords;

                // Pulsing glow circle
                ctx.fillStyle = "rgba(255,221,0,0.25)";
                ctx.beginPath();
                ctx.arc(capCoords.x, capCoords.y, 16 + Math.sin(Date.now() / 150) * 4, 0, Math.PI * 2);
                ctx.fill();

                // Draw rotating custom vehicle shapes
                drawVehicle(ctx, capCoords.x, capCoords.y, capCoords.angle || 0, selectedService, false);
            }
        }

        rapidoMapAnimationId = requestAnimationFrame(drawMap);
    }

    drawMap();
}

// Start booking API integration
async function startRapidoBooking() {
    const pickup = document.getElementById("rapido-pickup").value;
    const dropoff = document.getElementById("rapido-dropoff").value;

    if (pickup === dropoff) {
        showToast("Pickup and drop-off locations must be different.");
        return;
    }

    const priceText = document.getElementById(`price-${selectedService.toLowerCase()}`).innerText;
    const fare = parseFloat(priceText.replace("Ã¢â€šÂ¹", ""));

    document.getElementById("rapido-state-search").classList.remove("active");
    document.getElementById("rapido-state-matching").classList.add("active");

    document.getElementById("match-service").innerText = selectedService === "BIKE" ? "Bike Taxi" : selectedService === "AUTO" ? "H Auto" : "H Cab";
    document.getElementById("match-fare").innerText = priceText;

    playRapidoSound("request");

    try {
        const token = localStorage.getItem("pro_auth_token");
        const headers = { "Content-Type": "application/json" };
        if (token) headers["Authorization"] = `Bearer ${token}`;

        const res = await fetch("/api/rapido/book", {
            method: "POST",
            headers,
            body: JSON.stringify({ pickup, dropoff, vehicle_type: selectedService, fare })
        });
        const data = await res.json();

        if (data.success) {
            activeBooking = {
                ride_id: data.ride_id,
                pickup,
                dropoff,
                fare,
                otp: data.otp,
                fallbackCaptain: data.captain,
                state: "PENDING",
                bookingTime: Date.now()
            };

            // Start polling for driver assignment state change
            if (riderStatusPoller) clearInterval(riderStatusPoller);
            riderStatusPoller = setInterval(pollRiderRideStatus, 1500);
        } else {
            showToast(data.error || "Booking failed.");
            resetRiderBookingView();
        }
    } catch (e) {
        showToast("Error processing request.");
        resetRiderBookingView();
    }
}

// Polling updates logic for Rider tracking screen
async function pollRiderRideStatus() {
    if (!activeBooking || !activeBooking.ride_id) {
        if (riderStatusPoller) clearInterval(riderStatusPoller);
        return;
    }

    try {
        const token = localStorage.getItem("pro_auth_token");
        const headers = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;

        const res = await fetch(`/api/rapido/ride-status?ride_id=${activeBooking.ride_id}`, { headers });
        const data = await res.json();

        if (data.success && data.ride) {
            const ride = data.ride;

            if (ride.status === "PENDING") {
                // If 7 seconds pass and no active driver accepted, trigger simulated driver accept
                if (Date.now() - activeBooking.bookingTime > 7000) {
                    await assignSimulatedCaptain(activeBooking.ride_id, activeBooking.fallbackCaptain);
                }
                return;
            }

            if (ride.status === "ACCEPTED") {
                if (activeBooking.state === "PENDING" || !activeBooking.captainCoords) {
                    playRapidoSound("assigned");
                    document.getElementById("rapido-state-matching").classList.remove("active");
                    document.getElementById("rapido-state-tracking").classList.add("active");

                    document.getElementById("tracking-driver-name").innerText = ride.captain_name;
                    document.getElementById("tracking-driver-rating").innerText = ride.captain_rating;
                    document.getElementById("tracking-vehicle-number").innerText = ride.vehicle_number;
                    document.getElementById("tracking-otp-val").innerText = ride.otp;

                    document.getElementById("tracking-driver-avatar").innerText = ride.captain_name.split(" ").map(n => n[0]).join("");
                    document.getElementById("feedback-driver-avatar").innerText = ride.captain_name.split(" ").map(n => n[0]).join("");
                    document.getElementById("feedback-driver-name").innerText = ride.captain_name;
                    document.getElementById("feedback-vehicle-number").innerText = ride.vehicle_number;

                    activeBooking.state = "EN_ROUTE_PICKUP";
                    activeBooking.captainCoords = { x: 0, y: 0, angle: 0 };

                    startChatPoller(activeBooking.ride_id);
                }

                // If coordinates are pushed by a real driver, override local pathing
                if (ride.driver_id && ride.driver_coords_x !== null && ride.driver_coords_x !== 0) {
                    activeBooking.captainCoords.x = ride.driver_coords_x;
                    activeBooking.captainCoords.y = ride.driver_coords_y;
                    activeBooking.captainCoords.angle = ride.driver_angle || 0;

                    const pickCoords = RAPIDO_LOCATIONS[activeBooking.pickup];
                    const dx = pickCoords.x - ride.driver_coords_x;
                    const dy = pickCoords.y - ride.driver_coords_y;
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    const etaSecs = Math.max(1, Math.round(dist / 6));

                    document.getElementById("tracking-status-text").innerText = "Captain arriving at pickup...";
                    document.getElementById("tracking-eta-val").innerText = `ETA: ${etaSecs} mins`;

                    const currentSpeed = Math.round(36 + Math.sin(Date.now() / 200) * 7);
                    document.getElementById("telemetry-speed").innerText = `${currentSpeed} km/h`;
                    document.getElementById("telemetry-guidance").innerText = `Captain is moving towards your pickup point.`;
                } else {
                    // Solo Simulated Path animation
                    if (!activeBooking.routePath) {
                        animateCaptainToPickup();
                    }
                }
            } else if (ride.status === "ARRIVED_PICKUP") {
                if (activeBooking.state !== "ARRIVED_PICKUP") {
                    activeBooking.state = "ARRIVED_PICKUP";
                    playRapidoSound("arrived");
                    document.getElementById("tracking-status-text").innerText = "Captain has arrived!";
                    document.getElementById("tracking-eta-val").innerText = "Share OTP to start";
                    document.getElementById("telemetry-speed").innerText = "0 km/h";
                    document.getElementById("telemetry-guidance").innerText = "Share the START OTP with Captain.";
                }

                if (ride.driver_id && ride.driver_coords_x !== null && ride.driver_coords_x !== 0) {
                    activeBooking.captainCoords.x = ride.driver_coords_x;
                    activeBooking.captainCoords.y = ride.driver_coords_y;
                    activeBooking.captainCoords.angle = ride.driver_angle || 0;
                }
            } else if (ride.status === "IN_PROGRESS") {
                if (activeBooking.state !== "IN_PROGRESS") {
                    activeBooking.state = "IN_PROGRESS";
                    playRapidoSound("assigned");
                    document.getElementById("tracking-status-text").innerText = "Ride started. OTP verified.";
                    showToast("Trip started! OTP Verified.");
                }

                if (ride.driver_id && ride.driver_coords_x !== null && ride.driver_coords_x !== 0) {
                    activeBooking.captainCoords.x = ride.driver_coords_x;
                    activeBooking.captainCoords.y = ride.driver_coords_y;
                    activeBooking.captainCoords.angle = ride.driver_angle || 0;

                    const dropCoords = RAPIDO_LOCATIONS[activeBooking.dropoff];
                    const dx = dropCoords.x - ride.driver_coords_x;
                    const dy = dropCoords.y - ride.driver_coords_y;
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    const etaSecs = Math.max(1, Math.round(dist / 5));

                    document.getElementById("tracking-status-text").innerText = "Trip in progress. Driving to drop-off...";
                    document.getElementById("tracking-eta-val").innerText = `ETA: ${etaSecs} mins`;

                    const currentSpeed = Math.round(42 + Math.sin(Date.now() / 150) * 6);
                    document.getElementById("telemetry-speed").innerText = `${currentSpeed} km/h`;
                    document.getElementById("telemetry-guidance").innerText = `Navigating streets. Ride safely.`;
                } else {
                    // Fallback to client-side simulated animation path
                    if (!activeBooking.dropoffRoutePath) {
                        animateCaptainToDropoff();
                    }
                }
            } else if (ride.status === "COMPLETED") {
                if (riderStatusPoller) clearInterval(riderStatusPoller);
                if (chatPoller) clearInterval(chatPoller);
                completeActiveTrip();
            }
        }
    } catch (e) {
        console.error("Error polling ride status:", e);
    }
}

async function assignSimulatedCaptain(rideId, captain) {
    try {
        const token = localStorage.getItem("pro_auth_token");
        const headers = { "Content-Type": "application/json" };
        if (token) headers["Authorization"] = `Bearer ${token}`;

        // Mark the status ACCEPTED on backend using complete API
        await fetch("/api/rapido/complete", {
            method: "POST",
            headers,
            body: JSON.stringify({ ride_id: rideId, status: "ACCEPTED" })
        });
    } catch (err) { }
}

function cancelRapidoBooking() {
    resetRiderBookingView();
    showToast("Ride booking request cancelled.");
}

// Ride Assigning fallback setup
function assignCaptainToBooking(rideId, otp, captain, pickup, dropoff, fare) {
    playRapidoSound("assigned");

    document.getElementById("rapido-state-matching").classList.remove("active");
    document.getElementById("rapido-state-tracking").classList.add("active");

    document.getElementById("tracking-driver-name").innerText = captain.name;
    document.getElementById("tracking-driver-rating").innerText = captain.rating;
    document.getElementById("tracking-vehicle-number").innerText = captain.vehicle_number;
    document.getElementById("tracking-otp-val").innerText = otp;

    document.getElementById("tracking-driver-avatar").innerText = captain.name.split(" ").map(n => n[0]).join("");
    document.getElementById("feedback-driver-avatar").innerText = captain.name.split(" ").map(n => n[0]).join("");
    document.getElementById("feedback-driver-name").innerText = captain.name;
    document.getElementById("feedback-vehicle-number").innerText = captain.vehicle_number;

    activeBooking = {
        ride_id: rideId,
        pickup,
        dropoff,
        fare,
        otp,
        captain,
        state: "EN_ROUTE_PICKUP"
    };

    rapidoChatHistory = [];
    document.getElementById("rapidoChatList").innerHTML = `<div class="chat-bubble system">Chat initiated with Captain ${captain.name}.</div>`;

    animateCaptainToPickup();
}

// Animate captain along road segments to pickup point (Simulated flow)
function animateCaptainToPickup() {
    if (!activeBooking) return;

    if (!activeBooking.routePath) {
        const keys = Object.keys(RAPIDO_LOCATIONS).filter(k => k !== activeBooking.pickup);
        const startLoc = keys[Math.floor(Math.random() * keys.length)];
        activeBooking.routePath = getRoutePath(startLoc, activeBooking.pickup);
        activeBooking.currentPathIndex = 0;
        activeBooking.captainCoords = {
            x: activeBooking.routePath[0].x,
            y: activeBooking.routePath[0].y,
            angle: 0
        };
    }

    const path = activeBooking.routePath;
    const currIdx = activeBooking.currentPathIndex;

    if (currIdx + 1 >= path.length) {
        activeBooking.state = "ARRIVED_PICKUP";
        playRapidoSound("arrived");
        document.getElementById("tracking-status-text").innerText = "Captain has arrived!";
        document.getElementById("tracking-eta-val").innerText = "Share OTP to start";
        document.getElementById("telemetry-speed").innerText = "0 km/h";
        document.getElementById("telemetry-guidance").innerText = "Share the 4-digit START OTP with Captain.";

        setTimeout(() => {
            if (activeBooking && activeBooking.state === "ARRIVED_PICKUP") {
                receiveCaptainSimulatedChat("I have arrived at your pickup location. Please share the 4-digit START OTP.");
            }
        }, 1500);

        setTimeout(() => {
            if (activeBooking && activeBooking.state === "ARRIVED_PICKUP") {
                startActiveTrip();
            }
        }, 8000);
        return;
    }

    const targetNode = path[currIdx + 1];
    let cap = activeBooking.captainCoords;

    const dx = targetNode.x - cap.x;
    const dy = targetNode.y - cap.y;
    const dist = Math.sqrt(dx * dx + dy * dy);

    document.getElementById("tracking-status-text").innerText = "Captain arriving at pickup...";

    let remainingPx = dist;
    for (let j = currIdx + 1; j < path.length - 1; j++) {
        const ax = path[j].x - path[j + 1].x;
        const ay = path[j].y - path[j + 1].y;
        remainingPx += Math.sqrt(ax * ax + ay * ay);
    }
    const realDistKm = Math.max(0.2, Math.round((remainingPx / 80) * 10) / 10);
    const etaSecs = Math.max(1, Math.round(realDistKm * 2));

    document.getElementById("tracking-eta-val").innerText = `ETA: ${etaSecs} mins`;

    const currentSpeed = Math.round(36 + Math.sin(Date.now() / 200) * 7);
    document.getElementById("telemetry-speed").innerText = `${currentSpeed} km/h`;

    const destName = targetNode.name || "Main Road";
    document.getElementById("telemetry-guidance").innerText = `Captain proceeding towards ${destName}...`;

    if (dist > 2.5) {
        cap.x += (dx / dist) * 1.1;
        cap.y += (dy / dist) * 1.1;
        cap.angle = Math.atan2(dy, dx);
        setTimeout(animateCaptainToPickup, 30);
    } else {
        activeBooking.currentPathIndex++;
        setTimeout(animateCaptainToPickup, 30);
    }
}

function startActiveTrip() {
    if (!activeBooking) return;
    activeBooking.state = "IN_PROGRESS";
    document.getElementById("tracking-status-text").innerText = "Ride started. OTP verified.";
    showToast("Trip started! OTP Verified.");

    animateCaptainToDropoff();
}

// Animate captain along road segments to dropoff point (Simulated flow)
function animateCaptainToDropoff() {
    if (!activeBooking) return;

    if (activeBooking.state === "IN_PROGRESS" && !activeBooking.dropoffRoutePath) {
        activeBooking.dropoffRoutePath = getRoutePath(activeBooking.pickup, activeBooking.dropoff);
        activeBooking.currentPathIndex = 0;
        activeBooking.captainCoords = {
            x: activeBooking.dropoffRoutePath[0].x,
            y: activeBooking.dropoffRoutePath[0].y,
            angle: 0
        };
    }

    const path = activeBooking.dropoffRoutePath;
    const currIdx = activeBooking.currentPathIndex;

    if (currIdx + 1 >= path.length) {
        completeActiveTrip();
        return;
    }

    const targetNode = path[currIdx + 1];
    let cap = activeBooking.captainCoords;

    const dx = targetNode.x - cap.x;
    const dy = targetNode.y - cap.y;
    const dist = Math.sqrt(dx * dx + dy * dy);

    document.getElementById("tracking-status-text").innerText = "Trip in progress. Driving to drop-off...";

    let remainingPx = dist;
    for (let j = currIdx + 1; j < path.length - 1; j++) {
        const ax = path[j].x - path[j + 1].x;
        const ay = path[j].y - path[j + 1].y;
        remainingPx += Math.sqrt(ax * ax + ay * ay);
    }
    const realDistKm = Math.max(0.1, Math.round((remainingPx / 80) * 10) / 10);
    const etaSecs = Math.max(1, Math.round(realDistKm * 2));

    document.getElementById("tracking-eta-val").innerText = `ETA: ${etaSecs} mins`;

    const currentSpeed = Math.round(42 + Math.sin(Date.now() / 150) * 6);
    document.getElementById("telemetry-speed").innerText = `${currentSpeed} km/h`;

    const destName = targetNode.name || "Dropoff point";
    document.getElementById("telemetry-guidance").innerText = `Proceeding along highway towards ${destName}...`;

    if (dist > 2.5) {
        cap.x += (dx / dist) * 1.0;
        cap.y += (dy / dist) * 1.0;
        cap.angle = Math.atan2(dy, dx);
        setTimeout(animateCaptainToDropoff, 30);
    } else {
        activeBooking.currentPathIndex++;
        setTimeout(animateCaptainToDropoff, 30);
    }
}

async function completeActiveTrip() {
    if (!activeBooking) return;
    playRapidoSound("completed");

    const rideId = activeBooking.ride_id;

    document.getElementById("rapido-state-tracking").classList.remove("active");
    document.getElementById("rapido-state-feedback").classList.add("active");

    setFeedbackRating(0);
    document.getElementById("feedback-comments").value = "";
}

async function cancelActiveTrip() {
    if (activeBooking && activeBooking.ride_id) {
        try {
            const token = localStorage.getItem("pro_auth_token");
            const headers = { "Content-Type": "application/json" };
            if (token) headers["Authorization"] = `Bearer ${token}`;
            await fetch("/api/rapido/complete", {
                method: "POST",
                headers,
                body: JSON.stringify({ ride_id: activeBooking.ride_id, status: "CANCELLED" })
            });
        } catch (e) { }
    }
    resetRiderBookingView();
    showToast("Trip cancelled successfully.");
}

// In-app chat toggler & reply simulator
function toggleRapidoChatView() {
    const chatContent = document.getElementById("rapidoChatBoxContent");
    const arrow = document.getElementById("chat-arrow-icon");
    if (chatContent.style.display === "none") {
        chatContent.style.display = "flex";
        arrow.className = "fa-solid fa-chevron-down";
    } else {
        chatContent.style.display = "none";
        arrow.className = "fa-solid fa-chevron-up";
    }
}

function sendRapidoPresetChat(text) {
    if (rapidoRole === "RIDER") {
        sendRiderChatMessage(text);
    } else {
        sendCaptainChatMessage(text);
    }
}

function sendRapidoCustomChat() {
    const input = document.getElementById("rapidoChatInput");
    const text = input.value.trim();
    if (!text) return;
    sendRiderChatMessage(text);
    input.value = "";
}

function handleRapidoChatKeyPress(e) {
    if (e.key === "Enter") {
        sendRapidoCustomChat();
    }
}

async function sendRiderChatMessage(text) {
    if (activeBooking && activeBooking.ride_id) {
        try {
            const token = localStorage.getItem("pro_auth_token");
            const headers = { "Content-Type": "application/json" };
            if (token) headers["Authorization"] = `Bearer ${token}`;

            await fetch("/api/rapido/chat/send", {
                method: "POST",
                headers,
                body: JSON.stringify({ ride_id: activeBooking.ride_id, message: text })
            });
        } catch (e) { }
    } else {
        // Fallback for solo simulation
        appendChatBubble("sent", text, "rapidoChatList");
        setTimeout(() => {
            if (!activeBooking) return;
            let reply = "Okay, noted.";
            if (activeBooking.state === "EN_ROUTE_PICKUP") {
                const replies = [
                    "Reaching in a minute.",
                    "Coming, on the way.",
                    "Please stand at the exact spot.",
                    "Got your location, coming."
                ];
                reply = replies[Math.floor(Math.random() * replies.length)];
            } else if (activeBooking.state === "ARRIVED_PICKUP") {
                reply = "Okay, please stand near the gate. OTP please?";
            } else if (activeBooking.state === "IN_PROGRESS") {
                reply = "Yes, driving to your dropoff location now.";
            }
            receiveCaptainSimulatedChat(reply);
        }, 1500);
    }
}

function receiveCaptainSimulatedChat(text) {
    appendChatBubble("received", text, "rapidoChatList");
}

function appendChatBubble(role, text, containerId) {
    const list = document.getElementById(containerId);
    if (!list) return;

    const bubble = document.createElement("div");
    bubble.className = `chat-bubble ${role}`;
    bubble.innerText = text;
    list.appendChild(bubble);
    list.scrollTop = list.scrollHeight;
}

// Chat poller for real-time messages database loading
function startChatPoller(rideId) {
    if (chatPoller) clearInterval(chatPoller);
    lastChatMsgCount = 0;

    chatPoller = setInterval(async () => {
        try {
            const token = localStorage.getItem("pro_auth_token");
            const headers = {};
            if (token) headers["Authorization"] = `Bearer ${token}`;

            const res = await fetch(`/api/rapido/chat/messages?ride_id=${rideId}`, { headers });
            const data = await res.json();

            if (data.success && data.messages && data.messages.length > lastChatMsgCount) {
                const containerId = (rapidoRole === "RIDER") ? "rapidoChatList" : "captainChatList";
                const list = document.getElementById(containerId);
                if (list) {
                    list.innerHTML = `<div class="chat-bubble system">Chat initiated with ${rapidoRole === "RIDER" ? 'Captain' : 'Rider'}.</div>`;

                    const myName = localStorage.getItem("pro_auth_user_name") || "";

                    data.messages.forEach(msg => {
                        const isSent = (msg.sender_name === myName);
                        appendChatBubble(isSent ? "sent" : "received", msg.message, containerId);
                    });
                }
                lastChatMsgCount = data.messages.length;
            }
        } catch (e) {
            console.error("Error polling chat messages:", e);
        }
    }, 1500);
}

// Rating feedback API submit
function setFeedbackRating(stars) {
    rapidoFeedbackRating = stars;
    const icons = document.querySelectorAll(".star-rating-selector i");
    icons.forEach((icon, index) => {
        if (index < stars) {
            icon.classList.add("active");
        } else {
            icon.classList.remove("active");
        }
    });
}

async function submitRapidoFeedback() {
    if (rapidoFeedbackRating === 0) {
        showToast("Please select a rating before finishing.");
        return;
    }

    const comments = document.getElementById("feedback-comments").value.trim();
    const rideId = activeBooking ? activeBooking.ride_id : null;

    if (rideId) {
        try {
            const token = localStorage.getItem("pro_auth_token");
            const headers = { "Content-Type": "application/json" };
            if (token) headers["Authorization"] = `Bearer ${token}`;

            await fetch("/api/rapido/complete", {
                method: "POST",
                headers,
                body: JSON.stringify({ ride_id: rideId, status: "COMPLETED", rating: rapidoFeedbackRating, comments })
            });
        } catch (e) {
            console.error("Error saving ride completion feedback:", e);
        }
    }

    resetRiderBookingView();
    showToast("Feedback submitted. Thank you!");
}

// History modal
async function openRapidoHistoryModal() {
    document.getElementById("rapido-history-modal").style.display = "flex";

    try {
        const token = localStorage.getItem("pro_auth_token");
        const headers = { "Content-Type": "application/json" };
        if (token) headers["Authorization"] = `Bearer ${token}`;

        const res = await fetch("/api/rapido/rides", { headers });
        const data = await res.json();

        if (data.success && data.rides) {
            renderRapidoHistory(data.rides);
        }
    } catch (e) {
        showToast("Error loading ride history.");
    }
}

function closeRapidoHistoryModal() {
    document.getElementById("rapido-history-modal").style.display = "none";
}

function renderRapidoHistory(rides) {
    const list = document.getElementById("rapidoHistoryList");
    if (!list) return;

    if (rides.length === 0) {
        list.innerHTML = `<p class="text-center text-muted">No rides completed yet.</p>`;
        return;
    }

    list.innerHTML = rides.map(ride => `
        <div class="history-card">
            <div class="history-card-header">
                <span class="type-tag">${ride.vehicle_type} Ride</span>
                <span class="date-tag">${(ride.created_at || '').substring(0, 16).replace("T", " ") || 'N/A'}</span>
            </div>
            <div class="history-locations">
                <div><span class="dot bg-green"></span> <strong>${ride.pickup}</strong></div>
                <div style="margin-top:6px;"><span class="dot bg-red"></span> <strong>${ride.dropoff}</strong></div>
            </div>
            <div class="history-card-footer">
                <span class="driver-ref">
                    <i class="fa-solid fa-motorcycle"></i> Captain: ${ride.captain_name || 'N/A'} 
                    (${ride.rating ? ride.rating + ' Ã¢Ëœâ€¦' : 'Unrated'})
                </span>
                <span class="fare-val">Ã¢â€šÂ¹${ride.fare}</span>
            </div>
        </div>
    `).join("");
}


// ==========================================================================
// CAPTAIN MODE (DRIVER PERSPECTIVE) SIMULATOR
// ==========================================================================

function toggleRapidoRole() {
    const btn = document.getElementById("rapido-mode-toggle");

    if (rapidoRole === "RIDER") {
        rapidoRole = "CAPTAIN";
        document.getElementById("rapido-rider-body").style.display = "none";
        document.getElementById("rapido-captain-body").style.display = "flex";
        btn.innerHTML = `<i class="fa-solid fa-user"></i> <span>Switch to Rider Mode</span>`;
        btn.style.backgroundColor = "#27272a";
        btn.style.color = "#ffffff";

        resetCaptainView();
        initRapidoCaptainMap();
        fetchDriverStats();
    } else {
        rapidoRole = "RIDER";
        document.getElementById("rapido-rider-body").style.display = "flex";
        document.getElementById("rapido-captain-body").style.display = "none";
        btn.innerHTML = `<i class="fa-solid fa-motorcycle"></i> <span>Switch to Captain Mode</span>`;
        btn.style.backgroundColor = "var(--rapido-yellow)";
        btn.style.color = "var(--rapido-dark)";

        if (captainOffersPoller) clearInterval(captainOffersPoller);

        resetRiderBookingView();
        initRapidoRiderMap();
    }
}

function resetCaptainView() {
    driverActiveTrip = null;
    if (incomingRequestTimer) clearInterval(incomingRequestTimer);
    if (captainOffersPoller) clearInterval(captainOffersPoller);
    if (chatPoller) clearInterval(chatPoller);

    document.querySelectorAll(".captain-state-panel").forEach(p => p.classList.remove("active"));
    document.getElementById("captain-state-idle").classList.add("active");

    document.getElementById("driverOnlineToggle").checked = driverStats.is_online;
    document.getElementById("driverOnlineText").innerText = driverStats.is_online ? "Go Offline" : "Go Online";
    document.getElementById("driverStatusTagText").innerText = driverStats.is_online ? "ONLINE" : "OFFLINE";
    document.getElementById("captain-idle-text").innerText = driverStats.is_online
        ? "Waiting for incoming ride requests... Keep map active."
        : "You are currently offline. Toggle the switch above to start receiving ride requests.";

    document.getElementById("captain-telemetry-speed").innerText = "0 km/h";
}

// Fetch driver metrics
async function fetchDriverStats() {
    try {
        const token = localStorage.getItem("pro_auth_token");
        const headers = { "Content-Type": "application/json" };
        if (token) headers["Authorization"] = `Bearer ${token}`;

        const res = await fetch("/api/rapido/driver/stats", { headers });
        const data = await res.json();

        if (data.success && data.stats) {
            driverStats = data.stats;
            document.getElementById("driverEarnings").innerText = `Ã¢â€šÂ¹${driverStats.total_earnings.toFixed(2)}`;
            document.getElementById("driverRidesCount").innerText = driverStats.total_rides;

            document.getElementById("driverOnlineToggle").checked = driverStats.is_online;
            document.getElementById("driverOnlineText").innerText = driverStats.is_online ? "Go Offline" : "Go Online";
            document.getElementById("driverStatusTagText").innerText = driverStats.is_online ? "ONLINE" : "OFFLINE";

            if (rapidoRole === "CAPTAIN") {
                resetCaptainView();
                if (driverStats.is_online) {
                    startIncomingRequestsLoop();
                }
            }
        }
    } catch (e) {
        console.error("Error loading driver stats:", e);
    }
}

// Toggle Driver status online
async function toggleDriverOnlineStatus() {
    const isOnline = document.getElementById("driverOnlineToggle").checked;

    try {
        const token = localStorage.getItem("pro_auth_token");
        const headers = { "Content-Type": "application/json" };
        if (token) headers["Authorization"] = `Bearer ${token}`;

        const res = await fetch("/api/rapido/driver/toggle", {
            method: "POST",
            headers,
            body: JSON.stringify({ is_online: isOnline })
        });
        const data = await res.json();
        if (data.success) {
            driverStats.is_online = data.is_online;
            resetCaptainView();

            if (driverStats.is_online) {
                window._captainOnlineSince = Date.now();
                startIncomingRequestsLoop();
                showToast("You are now online! Awaiting orders...");
            } else {
                window._captainOnlineSince = null;
                if (captainOffersPoller) clearInterval(captainOffersPoller);
                showToast("You are now offline.");
            }
        }
    } catch (e) {
        showToast("Error updating status.");
        document.getElementById("driverOnlineToggle").checked = !isOnline;
    }
}

function startIncomingRequestsLoop() {
    if (captainOffersPoller) clearInterval(captainOffersPoller);
    captainOffersPoller = setInterval(pollDriverOffers, 2000);
}

// Poll pending database rides for drivers
async function pollDriverOffers() {
    if (!driverStats.is_online || driverActiveTrip || currentIncomingRequest) return;

    try {
        const token = localStorage.getItem("pro_auth_token");
        const headers = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;

        const res = await fetch("/api/rapido/driver/offers", { headers });
        const data = await res.json();

        if (data.success && data.offers && data.offers.length > 0) {
            const offer = data.offers[0];
            currentIncomingRequest = {
                ride_id: offer.id,
                pickup: offer.pickup,
                dropoff: offer.dropoff,
                fare: offer.fare,
                dist: getRouteDistance(offer.pickup, offer.dropoff),
                otp: offer.otp,
                secondsLeft: 15
            };

            playRapidoSound("request");

            document.querySelectorAll(".captain-state-panel").forEach(p => p.classList.remove("active"));
            document.getElementById("captain-state-request").classList.add("active");

            document.getElementById("req-pickup-text").innerText = RAPIDO_LOCATIONS[offer.pickup].name;
            document.getElementById("req-dropoff-text").innerText = RAPIDO_LOCATIONS[offer.dropoff].name;
            document.getElementById("req-earning-text").innerText = `\u20B9${offer.fare.toFixed(2)}`;
            document.getElementById("req-distance-text").innerText = `${currentIncomingRequest.dist} km`;
            document.getElementById("req-countdown-timer").innerText = `15s`;

            // Auto-decline countdown
            const cd = setInterval(() => {
                if (!currentIncomingRequest || currentIncomingRequest.ride_id !== offer.id) {
                    clearInterval(cd);
                    return;
                }
                currentIncomingRequest.secondsLeft--;
                document.getElementById("req-countdown-timer").innerText = `${currentIncomingRequest.secondsLeft}s`;

                if (currentIncomingRequest.secondsLeft <= 0) {
                    clearInterval(cd);
                    declineIncomingRequest();
                }
            }, 1000);
        } else {
            // No real offers found Ã¢â‚¬â€ auto-generate a simulated ride request
            // after the captain has been online for 10+ seconds without any offer
            if (!window._captainOnlineSince) window._captainOnlineSince = Date.now();
            if (Date.now() - window._captainOnlineSince > 10000) {
                generateIncomingRideRequest();
                window._captainOnlineSince = Date.now() + 30000; // next sim in ~30s
            }
        }
    } catch (e) {
        console.error("Error polling driver offers:", e);
    }
}

// Trigger simulated/fallback matches locally
function generateIncomingRideRequest() {
    const keys = Object.keys(RAPIDO_LOCATIONS);
    const pickup = keys[Math.floor(Math.random() * keys.length)];
    let dropoff = keys[Math.floor(Math.random() * keys.length)];
    while (pickup === dropoff) {
        dropoff = keys[Math.floor(Math.random() * keys.length)];
    }

    const dist = getRouteDistance(pickup, dropoff);
    const fare = Math.round(15 + dist * 8);
    const otp = `${Math.floor(1000 + Math.random() * 9000)}`;

    currentIncomingRequest = {
        ride_id: null,
        pickup,
        dropoff,
        fare,
        dist,
        otp,
        secondsLeft: 15
    };

    playRapidoSound("request");

    document.querySelectorAll(".captain-state-panel").forEach(p => p.classList.remove("active"));
    document.getElementById("captain-state-request").classList.add("active");

    document.getElementById("req-pickup-text").innerText = RAPIDO_LOCATIONS[pickup].name;
    document.getElementById("req-dropoff-text").innerText = RAPIDO_LOCATIONS[dropoff].name;
    document.getElementById("req-earning-text").innerText = `\u20B9${fare.toFixed(2)}`;
    document.getElementById("req-distance-text").innerText = `${dist} km`;
    document.getElementById("req-countdown-timer").innerText = `15s`;

    // Auto-decline countdown for simulated requests
    const simCd = setInterval(() => {
        if (!currentIncomingRequest || currentIncomingRequest.otp !== otp) {
            clearInterval(simCd);
            return;
        }
        currentIncomingRequest.secondsLeft--;
        document.getElementById("req-countdown-timer").innerText = `${currentIncomingRequest.secondsLeft}s`;
        if (currentIncomingRequest.secondsLeft <= 0) {
            clearInterval(simCd);
            declineIncomingRequest();
        }
    }, 1000);
}

function declineIncomingRequest() {
    currentIncomingRequest = null;
    resetCaptainView();
    showToast("Request declined.");
}

async function acceptIncomingRequest() {
    if (!currentIncomingRequest) return;

    const rideId = currentIncomingRequest.ride_id;
    if (rideId) {
        try {
            const token = localStorage.getItem("pro_auth_token");
            const headers = { "Content-Type": "application/json" };
            if (token) headers["Authorization"] = `Bearer ${token}`;

            const res = await fetch("/api/rapido/driver/accept", {
                method: "POST",
                headers,
                body: JSON.stringify({ ride_id: rideId })
            });
            const data = await res.json();
            if (!data.success) {
                showToast("Request already accepted by another driver.");
                declineIncomingRequest();
                return;
            }
        } catch (e) {
            showToast("Failed to accept ride offer.");
            declineIncomingRequest();
            return;
        }
    }

    playRapidoSound("assigned");
    showToast("Ride request accepted! Navigate to pickup.");

    driverActiveTrip = {
        ride_id: rideId,
        pickup: currentIncomingRequest.pickup,
        dropoff: currentIncomingRequest.dropoff,
        fare: currentIncomingRequest.fare,
        otp: currentIncomingRequest.otp,
        state: "NAV_PICKUP"
    };

    currentIncomingRequest = null;

    document.querySelectorAll(".captain-state-panel").forEach(p => p.classList.remove("active"));
    document.getElementById("captain-state-driving").classList.add("active");

    document.getElementById("captain-trip-status-text").innerText = "Heading to pickup location...";
    document.getElementById("btn-driver-arrived").style.display = "block";
    document.getElementById("driver-otp-entry-section").style.display = "none";
    document.getElementById("btn-driver-completed").style.display = "none";

    document.getElementById("captainChatList").innerHTML = `<div class="chat-bubble system">Chat initiated with Rider.</div>`;
    document.getElementById("captainChatBoxContent").style.display = "none";
    document.getElementById("captain-chat-arrow-icon").className = "fa-solid fa-chevron-up";

    if (rideId) {
        startChatPoller(rideId);
    }

    animateDriverToPickup();
}

async function updateDriverCoordsOnServer(rideId, x, y, angle) {
    if (!rideId) return;
    try {
        const token = localStorage.getItem("pro_auth_token");
        const headers = { "Content-Type": "application/json" };
        if (token) headers["Authorization"] = `Bearer ${token}`;

        await fetch("/api/rapido/driver/update-coords", {
            method: "POST",
            headers,
            body: JSON.stringify({ ride_id: rideId, x, y, angle })
        });
    } catch (e) { }
}

async function updateDriverStatusOnServer(rideId, status, otpVal) {
    if (!rideId) return { success: true };
    try {
        const token = localStorage.getItem("pro_auth_token");
        const headers = { "Content-Type": "application/json" };
        if (token) headers["Authorization"] = `Bearer ${token}`;

        const res = await fetch("/api/rapido/driver/update-status", {
            method: "POST",
            headers,
            body: JSON.stringify({ ride_id: rideId, status, otp: otpVal })
        });
        return await res.json();
    } catch (e) {
        return { success: false };
    }
}

// Animate driver along road segments to pickup point
function animateDriverToPickup() {
    if (!driverActiveTrip) return;

    if (!driverActiveTrip.routePath) {
        const keys = Object.keys(RAPIDO_LOCATIONS).filter(k => k !== driverActiveTrip.pickup);
        const startLoc = keys[Math.floor(Math.random() * keys.length)];
        driverActiveTrip.routePath = getRoutePath(startLoc, driverActiveTrip.pickup);
        driverActiveTrip.currentPathIndex = 0;
        driverActiveTrip.coords = {
            x: driverActiveTrip.routePath[0].x,
            y: driverActiveTrip.routePath[0].y,
            angle: 0
        };
    }

    const path = driverActiveTrip.routePath;
    const currIdx = driverActiveTrip.currentPathIndex;

    if (currIdx + 1 >= path.length) {
        document.getElementById("captain-trip-status-text").innerText = "Arrived at pickup spot! Verification required.";
        document.getElementById("captain-trip-eta").innerText = "Verify OTP to start";
        document.getElementById("captain-telemetry-speed").innerText = "0 km/h";

        if (!driverActiveTrip.ride_id) {
            setTimeout(() => {
                if (driverActiveTrip && driverActiveTrip.state === "NAV_PICKUP") {
                    appendChatBubble("received", "Hi captain, I am standing near the main gate. Let me know when you reach.", "captainChatList");
                }
            }, 1000);
        }
        return;
    }

    const targetNode = path[currIdx + 1];
    let cap = driverActiveTrip.coords;

    const dx = targetNode.x - cap.x;
    const dy = targetNode.y - cap.y;
    const dist = Math.sqrt(dx * dx + dy * dy);

    document.getElementById("captain-trip-status-text").innerText = "Heading to pickup location...";

    let remainingPx = dist;
    for (let j = currIdx + 1; j < path.length - 1; j++) {
        const ax = path[j].x - path[j + 1].x;
        const ay = path[j].y - path[j + 1].y;
        remainingPx += Math.sqrt(ax * ax + ay * ay);
    }
    const realDistKm = Math.max(0.1, Math.round((remainingPx / 80) * 10) / 10);
    const etaSecs = Math.max(1, Math.round(realDistKm * 2));

    document.getElementById("captain-trip-eta").innerText = `ETA: ${etaSecs} mins`;

    const currentSpeed = Math.round(44 + Math.sin(Date.now() / 180) * 7);
    document.getElementById("captain-telemetry-speed").innerText = `${currentSpeed} km/h`;

    if (dist > 2.5) {
        cap.x += (dx / dist) * 1.3;
        cap.y += (dy / dist) * 1.3;
        cap.angle = Math.atan2(dy, dx);

        updateDriverCoordsOnServer(driverActiveTrip.ride_id, cap.x, cap.y, cap.angle);
        setTimeout(animateDriverToPickup, 30);
    } else {
        driverActiveTrip.currentPathIndex++;

        updateDriverCoordsOnServer(driverActiveTrip.ride_id, cap.x, cap.y, cap.angle);
        setTimeout(animateDriverToPickup, 30);
    }
}

// Driver clicks arrived at pickup
async function setDriverArrivedAtPickup() {
    if (driverActiveTrip && driverActiveTrip.ride_id) {
        await updateDriverStatusOnServer(driverActiveTrip.ride_id, "ARRIVED_PICKUP");
    }

    document.getElementById("btn-driver-arrived").style.display = "none";
    document.getElementById("driver-otp-entry-section").style.display = "flex";
    document.getElementById("driverOtpInput").value = "";
    document.getElementById("driverOtpInput").focus();

    playRapidoSound("arrived");
}

// Verify OTP to start ride
async function verifyDriverOtp() {
    const input = document.getElementById("driverOtpInput").value.trim();
    if (!driverActiveTrip) return;

    if (driverActiveTrip.ride_id) {
        const res = await updateDriverStatusOnServer(driverActiveTrip.ride_id, "IN_PROGRESS", input);
        if (!res.success) {
            showToast("Invalid OTP. Please verify with the rider.");
            return;
        }
    } else {
        if (input !== driverActiveTrip.otp) {
            showToast("Invalid OTP. Please verify with the rider.");
            return;
        }
    }

    driverActiveTrip.state = "DRIVING_DROPOFF";
    showToast("OTP Verified! Starting ride.");
    playRapidoSound("assigned");

    document.getElementById("captain-trip-status-text").innerText = "Trip in progress. Driving to drop-off...";
    document.getElementById("driver-otp-entry-section").style.display = "none";
    document.getElementById("btn-driver-completed").style.display = "block";

    animateDriverToDropoff();
}

// Animate driver along road segments to dropoff point
function animateDriverToDropoff() {
    if (!driverActiveTrip) return;

    if (driverActiveTrip.state === "DRIVING_DROPOFF" && !driverActiveTrip.dropoffRoutePath) {
        driverActiveTrip.dropoffRoutePath = getRoutePath(driverActiveTrip.pickup, driverActiveTrip.dropoff);
        driverActiveTrip.currentPathIndex = 0;
        driverActiveTrip.coords = {
            x: driverActiveTrip.dropoffRoutePath[0].x,
            y: driverActiveTrip.dropoffRoutePath[0].y,
            angle: 0
        };
    }

    const path = driverActiveTrip.dropoffRoutePath;
    const currIdx = driverActiveTrip.currentPathIndex;

    if (currIdx + 1 >= path.length) {
        document.getElementById("captain-trip-status-text").innerText = "Arrived at destination! Collect fare.";
        document.getElementById("captain-trip-eta").innerText = "Collect Cash";
        document.getElementById("captain-telemetry-speed").innerText = "0 km/h";
        return;
    }

    const targetNode = path[currIdx + 1];
    let cap = driverActiveTrip.coords;

    const dx = targetNode.x - cap.x;
    const dy = targetNode.y - cap.y;
    const dist = Math.sqrt(dx * dx + dy * dy);

    document.getElementById("captain-trip-status-text").innerText = "Trip in progress. Driving to drop-off...";

    let remainingPx = dist;
    for (let j = currIdx + 1; j < path.length - 1; j++) {
        const ax = path[j].x - path[j + 1].x;
        const ay = path[j].y - path[j + 1].y;
        remainingPx += Math.sqrt(ax * ax + ay * ay);
    }
    const realDistKm = Math.max(0.1, Math.round((remainingPx / 80) * 10) / 10);
    const etaSecs = Math.max(1, Math.round(realDistKm * 2));

    document.getElementById("captain-trip-eta").innerText = `ETA: ${etaSecs} mins`;

    const currentSpeed = Math.round(40 + Math.sin(Date.now() / 200) * 5);
    document.getElementById("captain-telemetry-speed").innerText = `${currentSpeed} km/h`;

    if (dist > 2.5) {
        cap.x += (dx / dist) * 1.2;
        cap.y += (dy / dist) * 1.2;
        cap.angle = Math.atan2(dy, dx);

        updateDriverCoordsOnServer(driverActiveTrip.ride_id, cap.x, cap.y, cap.angle);
        setTimeout(animateDriverToDropoff, 30);
    } else {
        driverActiveTrip.currentPathIndex++;

        updateDriverCoordsOnServer(driverActiveTrip.ride_id, cap.x, cap.y, cap.angle);
        setTimeout(animateDriverToDropoff, 30);
    }
}

// Driver completes ride
async function setDriverCompletedTrip() {
    if (!driverActiveTrip) return;

    if (driverActiveTrip.ride_id) {
        await updateDriverStatusOnServer(driverActiveTrip.ride_id, "COMPLETED");
    }

    playRapidoSound("completed");

    const fare = driverActiveTrip.fare;

    try {
        const token = localStorage.getItem("pro_auth_token");
        const headers = { "Content-Type": "application/json" };
        if (token) headers["Authorization"] = `Bearer ${token}`;

        const res = await fetch("/api/rapido/driver/add-earning", {
            method: "POST",
            headers,
            body: JSON.stringify({ fare })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`Ride completed! You earned Ã¢â€šÂ¹${fare.toFixed(2)}.`);
            fetchDriverStats();
        }
    } catch (e) {
        showToast("Error updating earnings, but ride marked complete.");
    }

    if (chatPoller) clearInterval(chatPoller);
    driverActiveTrip = null;
    resetCaptainView();
}

// Driver chat panel controls
function toggleCaptainChatView() {
    const chatContent = document.getElementById("captainChatBoxContent");
    const arrow = document.getElementById("captain-chat-arrow-icon");
    if (chatContent.style.display === "none") {
        chatContent.style.display = "flex";
        arrow.className = "fa-solid fa-chevron-down";
    } else {
        chatContent.style.display = "none";
        arrow.className = "fa-solid fa-chevron-up";
    }
}

async function sendCaptainChatMessage(text) {
    if (driverActiveTrip && driverActiveTrip.ride_id) {
        try {
            const token = localStorage.getItem("pro_auth_token");
            const headers = { "Content-Type": "application/json" };
            if (token) headers["Authorization"] = `Bearer ${token}`;

            await fetch("/api/rapido/chat/send", {
                method: "POST",
                headers,
                body: JSON.stringify({ ride_id: driverActiveTrip.ride_id, message: text })
            });
        } catch (e) { }
    } else {
        // Fallback for solo simulation
        appendChatBubble("sent", text, "captainChatList");

        setTimeout(() => {
            if (!driverActiveTrip) return;
            let reply = "Okay, standing near the gate.";
            if (driverActiveTrip.state === "NAV_PICKUP") {
                reply = "Got it, I see you on the map.";
            } else if (driverActiveTrip.state === "DRIVING_DROPOFF") {
                reply = "Okay.";
            }
            appendChatBubble("received", reply, "captainChatList");
        }, 1500);
    }
}

// Driver mode canvas loop
function initRapidoCaptainMap() {
    if (rapidoCaptainMapAnimationId) cancelAnimationFrame(rapidoCaptainMapAnimationId);

    const canvas = document.getElementById("rapidoCaptainMapCanvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    const dpr = window.devicePixelRatio || 1;
    canvas.width = canvas.parentElement.clientWidth * dpr;
    canvas.height = 450 * dpr;
    canvas.style.width = canvas.parentElement.clientWidth + "px";
    canvas.style.height = "450px";
    ctx.scale(dpr, dpr);

    function drawCaptainMap() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Draw Cityscape Background (Dark theme for drivers)
        drawCityBackground(ctx, canvas.width / dpr, 450, true);

        // Draw Locations
        for (let name in RAPIDO_LOCATIONS) {
            const loc = RAPIDO_LOCATIONS[name];
            ctx.fillStyle = "#27272a";
            ctx.beginPath();
            ctx.arc(loc.x, loc.y, 6, 0, Math.PI * 2);
            ctx.fill();
            ctx.strokeStyle = "#a1a1aa";
            ctx.lineWidth = 2.5;
            ctx.stroke();

            // Labels
            ctx.fillStyle = "#a1a1aa";
            ctx.font = "bold 9px Outfit, sans-serif";
            ctx.textAlign = "center";
            ctx.fillText(name, loc.x, loc.y - 12);
        }

        // Draw active driver trip elements
        if (driverActiveTrip) {
            const pick = RAPIDO_LOCATIONS[driverActiveTrip.pickup];
            const drop = RAPIDO_LOCATIONS[driverActiveTrip.dropoff];

            // Draw Pickup
            ctx.fillStyle = "#10b981";
            ctx.beginPath();
            ctx.arc(pick.x, pick.y, 8, 0, Math.PI * 2);
            ctx.fill();
            ctx.strokeStyle = "#ffffff";
            ctx.lineWidth = 2.5;
            ctx.stroke();

            // Draw Drop
            ctx.fillStyle = "#ef4444";
            ctx.beginPath();
            ctx.arc(drop.x, drop.y, 8, 0, Math.PI * 2);
            ctx.fill();
            ctx.strokeStyle = "#ffffff";
            ctx.lineWidth = 2.5;
            ctx.stroke();

            // Draw routing path
            const routePath = driverActiveTrip.state === "DRIVING_DROPOFF"
                ? driverActiveTrip.dropoffRoutePath
                : driverActiveTrip.routePath;

            if (routePath && routePath.length > 0) {
                ctx.strokeStyle = "#10b981";
                ctx.lineWidth = 4.5;
                ctx.lineCap = "round";
                ctx.lineJoin = "round";
                ctx.beginPath();
                ctx.moveTo(routePath[0].x, routePath[0].y);
                for (let j = 1; j < routePath.length; j++) {
                    ctx.lineTo(routePath[j].x, routePath[j].y);
                }
                ctx.stroke();
            }

            // Draw driver position
            if (driverActiveTrip.coords) {
                const drvCoords = driverActiveTrip.coords;

                // Pulsing glow circle
                ctx.fillStyle = "rgba(16,185,129,0.25)";
                ctx.beginPath();
                ctx.arc(drvCoords.x, drvCoords.y, 16 + Math.sin(Date.now() / 150) * 4, 0, Math.PI * 2);
                ctx.fill();

                // Draw rotating custom vehicle shapes (Captain is always BIKE class)
                drawVehicle(ctx, drvCoords.x, drvCoords.y, drvCoords.angle || 0, "BIKE", true);
            }
        }

        rapidoCaptainMapAnimationId = requestAnimationFrame(drawCaptainMap);
    }

    drawCaptainMap();
}

// ==========================================================================
// 10 BACKGROUND THEMES ENGINE
// ==========================================================================

let activeTheme = "water";
let themeAnimationIds = {};
let canvasElements = {};
let canvasContexts = {};

// Performance-optimized global particle system for background canvases
const themeParticles = [];
const PARTICLE_COUNT = 45;

function initParticles(canvas) {
    themeParticles.length = 0;
    if (!canvas) return;
    for (let i = 0; i < PARTICLE_COUNT; i++) {
        themeParticles.push({
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height,
            vx: (Math.random() - 0.5) * 0.4,
            vy: (Math.random() - 0.5) * 0.4,
            radius: Math.random() * 3.5 + 1.5,
            alpha: Math.random() * 0.4 + 0.12,
            pulseSpeed: Math.random() * 0.015 + 0.004,
            pulseDir: Math.random() > 0.5 ? 1 : -1
        });
    }
}

// Theme aliases and normalization mapping (supports solar, cosmic, air, nova, pic1, pic2, and named server themes)
const themeAliasMap = {
    "solar": "water",
    "futuristic": "water",
    "cosmic": "7th",
    "air": "8th",
    "nova": "10th",
    "aurora": "theme1",
    "nebula": "theme2",
    "prism": "theme3",
    "vortex": "theme4",
    "eclipse": "theme5",
    "zenith": "theme6",
    "mirage": "theme7",
    "radiance": "theme8",
    "solstice": "theme9",
    "horizon": "theme10",
    "flux": "theme11",
    "cascade": "theme12",
    "astral": "theme13",
    "lumina": "theme14",
    "oasis": "theme15",
    "summit": "theme16",
    "haven": "theme17",
    "elysium": "theme19",
    "solitude": "theme20",
    "pic1": "theme15",
    "pic2": "theme16",
    "pic3": "theme17",
    "pic5": "theme19",
    "pic6": "theme20"
};

function normalizeTheme(name) {
    if (!name) return "water";
    const lower = String(name).toLowerCase().trim();
    return themeAliasMap[lower] || lower;
}

// Complete list of all themes for rotation
const themeRotationList = [
    // Original order first - the themes that shipped with the project - then
    // the ones added later.
    "water", "flow", "glassflow", "waterflow", "8th",
    "theme1", "theme2", "theme3", "theme4", "theme5", "theme6", "theme7",
    "theme8", "theme9", "theme10", "theme11", "theme12", "theme13", "theme14",
    "theme15", "theme16", "theme17", "theme19", "theme20", "10th", "7th",
    "auroraveil", "ember", "sakura", "neongrid", "deeptide",
    "templegold", "sapphire", "ivorypearl", "emerald", "graphite"
];
let themeRotationIntervalId = null;
// Off by default: a theme now changes only when someone picks one.
// The previous 5s default meant any deliberate choice was replaced
// seconds later, which read as the picker not working.
let themeRotationIntervalTime = 0;

// Initialize theme switcher on DOM load
document.addEventListener("DOMContentLoaded", () => {
    // Make sure default active theme class is set
    const landingView = document.getElementById("landing-view");
    if (landingView && !landingView.classList.contains("theme-water")) {
        landingView.classList.add("theme-water");
    }

    // Sync theme select buttons active state
    const themeButtons = document.querySelectorAll(".theme-select-btn");
    const currentCanonical = normalizeTheme(activeTheme);
    themeButtons.forEach(btn => {
        const btnTheme = btn.getAttribute("data-theme");
        if (btnTheme === activeTheme || normalizeTheme(btnTheme) === currentCanonical) {
            btn.classList.add("active");
        } else {
            btn.classList.remove("active");
        }
    });

    // Sync auto-rotate interval buttons active state
    const intervalSeconds = themeRotationIntervalTime / 1000;
    const intervalButtons = document.querySelectorAll(".timer-opt-btn");
    intervalButtons.forEach(btn => {
        const val = parseInt(btn.getAttribute("data-interval"), 10);
        if (val === intervalSeconds) {
            btn.classList.add("active");
        } else {
            btn.classList.remove("active");
        }
    });

    // Reopen on whichever theme was last chosen
    try {
        const savedTheme = localStorage.getItem("selected_backdrop_theme");
        if (savedTheme) {
            switchBackdropTheme(savedTheme);
        }
    } catch (e) { }

    try {
        const savedSliderIndex = localStorage.getItem("theme_rotation_slider_index");
        if (savedSliderIndex !== null && intervalMap[savedSliderIndex]) {
            const slider = document.getElementById("themeIntervalSlider");
            if (slider) slider.value = savedSliderIndex;
            updateSliderDisplay(savedSliderIndex);
            changeThemeInterval(intervalMap[savedSliderIndex].value);
        }
    } catch (e) { }

    // Set up canvas elements and listeners for all theme canvases
    const themeCanvases = [
        "flowCanvas", "glassflowCanvas", "waterflowCanvas", "7thCanvas", "8thCanvas", "10thCanvas",
        "theme1Canvas", "theme2Canvas", "theme3Canvas", "theme4Canvas", "theme5Canvas", "theme6Canvas", "theme7Canvas",
        "theme8Canvas", "theme9Canvas", "theme10Canvas", "theme11Canvas", "theme12Canvas", "theme13Canvas", "theme14Canvas",
        "theme15Canvas", "theme16Canvas", "theme17Canvas", "theme19Canvas", "theme20Canvas"
    ];
    themeCanvases.forEach(id => {
        const canvas = document.getElementById(id);
        if (canvas) {
            canvasElements[id] = canvas;
            canvasContexts[id] = canvas.getContext("2d");
            resizeThemeCanvas(canvas);
        }
    });

    window.addEventListener("resize", () => {
        Object.values(canvasElements).forEach(canvas => resizeThemeCanvas(canvas));
    });

    // Start background loops
    initThemeLoops();

    // Optimize video loads: Pause all videos initially, then play only active one
    const allVideos = document.querySelectorAll(".theme-layer video");
    allVideos.forEach(vid => {
        try {
            vid.pause();
        } catch (e) { }
    });
    const canonical = normalizeTheme(activeTheme);
    const activeLayer = document.querySelector(`.layer--${canonical}`) || document.querySelector(`.layer--${activeTheme}`);
    if (activeLayer) {
        const activeVideo = activeLayer.querySelector("video");
        if (activeVideo) {
            try {
                if (isThemeAnimationsEnabled) {
                    activeVideo.play();
                } else {
                    activeVideo.pause();
                }
            } catch (e) { }
        }
    }

    // Start auto-rotate timer automatically on load
    startThemeRotation();
});

function resizeThemeCanvas(canvas) {
    if (canvas) {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }
}

function switchBackdropTheme(theme, isAuto = false) {
    activeTheme = theme;
    const canonicalTheme = normalizeTheme(theme);

    // Toggle active class on landing view container
    const landingView = document.getElementById("landing-view");
    if (landingView) {
        // Remove all previous theme classes
        const themes = [
            "water", "flow", "glassflow", "waterflow", "7th", "8th", "9th", "10th",
            "cosmic", "air", "nova",
            "theme1", "theme2", "theme3", "theme4", "theme5", "theme6", "theme7",
            "theme8", "theme9", "theme10", "theme11", "theme12", "theme13", "theme14",
            "theme15", "theme16", "theme17", "theme19", "theme20",
            "pic1", "pic2", "pic3", "pic5", "pic6",
            "oasis", "summit", "haven", "elysium", "solitude",
            "auroraveil", "ember", "sakura", "neongrid", "deeptide", "cinema",
            "templegold", "sapphire", "ivorypearl", "emerald", "graphite"
        ];
        themes.forEach(t => landingView.classList.remove(`theme-${t}`));
        landingView.classList.add(`theme-${canonicalTheme}`);
        if (theme !== canonicalTheme) {
            landingView.classList.add(`theme-${theme}`);
        }
    }

    // Performance Optimization: Play active theme video and pause all others
    const allVideos = document.querySelectorAll(".theme-layer video");
    allVideos.forEach(vid => {
        try {
            vid.pause();
        } catch (e) { }
    });
    const activeLayer = document.querySelector(`.layer--${canonicalTheme}`) || document.querySelector(`.layer--${theme}`);
    if (activeLayer) {
        const activeVideo = activeLayer.querySelector("video");
        if (activeVideo) {
            try {
                activeVideo.currentTime = 0;
                if (isThemeAnimationsEnabled && !isThemeMotionPaused) {
                    activeVideo.play();
                } else {
                    activeVideo.pause();
                }
            } catch (e) { }
        }
    }

    // Update theme select dropdown value if exists
    const themeDropdown = document.getElementById("themeSelectDropdown");
    if (themeDropdown) {
        themeDropdown.value = canonicalTheme;
    }

    // Update active button indicators in sidebar menu
    const buttons = document.querySelectorAll(".theme-select-btn");
    buttons.forEach(btn => {
        const btnTheme = btn.getAttribute("data-theme");
        if (btnTheme === theme || btnTheme === canonicalTheme || normalizeTheme(btnTheme) === canonicalTheme) {
            btn.classList.add("active");
        } else {
            btn.classList.remove("active");
        }
    });

    // Start target loops and resize
    const canvasId = getCanvasIdForTheme(canonicalTheme) || getCanvasIdForTheme(theme);
    if (canvasId && canvasElements[canvasId]) {
        const canvas = canvasElements[canvasId];
        resizeThemeCanvas(canvas);
        initParticles(canvas);
    }

    // A deliberate pick wins over the carousel.
    //
    // This used to call startThemeRotation() so the user "got the full
    // duration" of their choice - but with auto-rotate defaulting to 5s that
    // meant every theme you selected was thrown away five seconds later, which
    // reads as the picker simply not working. Choosing a theme is an explicit
    // preference, so it now stops the rotation and is remembered across visits.
    // Auto-rotate stays available from the slider directly underneath.
    if (!isAuto) {
        stopThemeRotation();
        setRotationSliderToNone();
        try {
            localStorage.setItem("selected_backdrop_theme", theme);
        } catch (e) { }
    }
}

// Keeps the AUTO-ROTATE control honest after a manual pick turns rotation off
function setRotationSliderToNone() {
    themeRotationIntervalTime = 0;
    const slider = document.getElementById("themeIntervalSlider");
    if (slider) slider.value = 0;
    if (typeof updateSliderDisplay === 'function') updateSliderDisplay(0);
    try {
        localStorage.setItem("theme_rotation_slider_index", 0);
    } catch (e) { }
}

// ==========================================================================
// CINEMA VIEW - the page opened by the white "O" ecosystem tile.
// The portrait is the page background; see #cinema-view in index.html.
// ==========================================================================
// ==========================================================================
// CINEMA PAGE - administrative access
//
// Deliberately unlike the Red App's panel, which compares the admin id and
// password against literals held in client-side JavaScript. Anyone can read
// those from view-source, so they are not a credential check at all. This
// form posts to /api/auth/login, where the password is verified against a
// PBKDF2 hash and the admin flag is read from the database.
// ==========================================================================


function toggleCinemaAdminPassword() {
    const input = document.getElementById('cinemaAdminPassword');
    const btn = document.getElementById('cinemaAdminEye');
    if (!input || !btn) return;
    const show = input.type === 'password';
    input.type = show ? 'text' : 'password';
    btn.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
    const icon = btn.querySelector('i');
    if (icon) icon.className = show ? 'fa-solid fa-eye-slash' : 'fa-solid fa-eye';
}

function setCinemaAdminNote(message, ok) {
    const note = document.getElementById('cinemaAdminNote');
    if (!note) return;
    note.textContent = message;
    note.hidden = !message;
    note.classList.toggle('is-ok', !!ok);
    note.classList.toggle('is-error', !ok && !!message);
}

async function submitCinemaAdmin(event) {
    event.preventDefault();

    const emailEl = document.getElementById('cinemaAdminEmail');
    const passEl = document.getElementById('cinemaAdminPassword');
    const submit = document.getElementById('cinemaAdminSubmit');
    if (!emailEl || !passEl || !submit) return false;

    const email = emailEl.value.trim();
    const password = passEl.value;
    if (!email || !password) {
        setCinemaAdminNote('Enter your email and password.', false);
        return false;
    }

    submit.disabled = true;
    submit.textContent = 'Checking...';
    setCinemaAdminNote('', true);

    try {
        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: email, password: password })
        });
        const data = await res.json().catch(() => ({}));

        if (res.status === 429) {
            setCinemaAdminNote('Too many attempts. Try again shortly.', false);
            return false;
        }
        if (!res.ok || !data.success || !data.token) {
            // Same message whichever field was wrong, so this cannot be used
            // to discover which email addresses exist.
            setCinemaAdminNote(data.error || 'Invalid email or password.', false);
            return false;
        }

        const isAdmin = !!(data.user && data.user.isAdmin);
        if (!isAdmin) {
            setCinemaAdminNote('That account does not have administrator access.', false);
            return false;
        }

        try {
            localStorage.setItem('pro_auth_token', data.token);
        } catch (e) { }

        setCinemaAdminNote('Signed in. Opening the dashboard...', true);
        setTimeout(function () { window.location.href = '/admin-dashboard'; }, 600);
        return false;
    } catch (err) {
        setCinemaAdminNote('Could not reach the server. Try again.', false);
        return false;
    } finally {
        submit.disabled = false;
        submit.textContent = 'Login';
        passEl.value = '';
    }
}

function openCinemaView() {
    if (typeof checkAppLock === 'function' && checkAppLock()) return;
    showView("cinema-view");
}

// ==========================================================================
// CINEMA BACKDROP - the matching landing-page theme, selectable from Themes
// Applies the same portrait as the landing backdrop; calling it again returns
// to whichever theme was on screen before.
// ==========================================================================
let themeBeforeCinema = null;

function toggleCinemaBackdrop() {
    const landingView = document.getElementById("landing-view");
    if (!landingView) return;

    if (landingView.classList.contains("theme-cinema")) {
        switchBackdropTheme(themeBeforeCinema || "water");
        themeBeforeCinema = null;
        return;
    }

    themeBeforeCinema = activeTheme;
    // isAuto = true so switchBackdropTheme does not restart the rotation timer,
    // then halt rotation outright - the portrait should stay put until dismissed.
    switchBackdropTheme("cinema", true);
    stopThemeRotation();
}

function getCanvasIdForTheme(theme) {
    const canonical = normalizeTheme(theme);
    const map = {
        "flow": "flowCanvas",
        "glassflow": "glassflowCanvas",
        "waterflow": "waterflowCanvas",
        "7th": "7thCanvas",
        "8th": "8thCanvas",
        "10th": "10thCanvas",
        "theme1": "theme1Canvas",
        "theme2": "theme2Canvas",
        "theme3": "theme3Canvas",
        "theme4": "theme4Canvas",
        "theme5": "theme5Canvas",
        "theme6": "theme6Canvas",
        "theme7": "theme7Canvas",
        "theme8": "theme8Canvas",
        "theme9": "theme9Canvas",
        "theme10": "theme10Canvas",
        "theme11": "theme11Canvas",
        "theme12": "theme12Canvas",
        "theme13": "theme13Canvas",
        "theme14": "theme14Canvas",
        "theme15": "theme15Canvas",
        "theme16": "theme16Canvas",
        "theme17": "theme17Canvas",
        "theme19": "theme19Canvas",
        "theme20": "theme20Canvas",
        "pic1": "theme15Canvas",
        "pic2": "theme16Canvas",
        "pic3": "theme17Canvas",
        "pic5": "theme19Canvas",
        "pic6": "theme20Canvas"
    };
    return map[canonical] || map[theme] || null;
}

function initThemeLoops() {
    // Global mouse coordinates for interactive parallax offsets
    let mouseX = window.innerWidth / 2;
    let mouseY = window.innerHeight / 2;
    window.addEventListener("mousemove", (e) => {
        mouseX = e.clientX;
        mouseY = e.clientY;
    });

    let currentOffsetX = 0;
    let currentOffsetY = 0;

    function runGlobalThemeLoop() {
        if (isThemeMotionPaused || !isThemeAnimationsEnabled) {
            requestAnimationFrame(runGlobalThemeLoop);
            return;
        }

        const canonical = normalizeTheme(activeTheme);
        const canvasId = getCanvasIdForTheme(canonical) || getCanvasIdForTheme(activeTheme);
        if (canvasId) {
            const canvas = canvasElements[canvasId];
            const ctx = canvasContexts[canvasId];
            if (canvas && ctx) {
                // Clear active canvas
                ctx.clearRect(0, 0, canvas.width, canvas.height);

                // Get accent colors based on theme
                let colors = ["#8b5cf6", "#4f46e5", "#ec4899"];
                if (canonical === "flow" || canonical === "theme2") {
                    colors = ["#ff7700", "#7c3aed", "#f59e0b"];
                } else if (canonical === "glassflow" || canonical === "theme3") {
                    colors = ["#a5b4fc", "#c084fc", "#f472b6"];
                } else if (canonical === "waterflow" || canonical === "theme4") {
                    colors = ["#06b6d4", "#10b881", "#3b82f6"];
                } else if (canonical === "theme5") {
                    colors = ["#ffa000", "#ff6f00", "#e65100"];
                } else if (canonical === "7th" || canonical === "theme6") {
                    colors = ["#d946ef", "#4f46e5", "#818cf8"];
                } else if (canonical === "8th" || canonical === "theme7") {
                    colors = ["#38bdf8", "#3b82f6", "#0ea5e9"];
                } else if (canonical === "10th" || canonical === "theme1") {
                    colors = ["#a855f7", "#ec4899", "#8b5cf6"];
                } else if (canonical === "theme8") {
                    colors = ["#10b981", "#059669", "#34d399"];
                } else if (canonical === "theme9") {
                    colors = ["#f43f5e", "#fb7185", "#e11d48"];
                } else if (canonical === "theme10") {
                    colors = ["#6366f1", "#8b5cf6", "#a855f7"];
                } else if (canonical === "theme11") {
                    colors = ["#0284c7", "#38bdf8", "#0ea5e9"];
                } else if (canonical === "theme12") {
                    colors = ["#d97706", "#f59e0b", "#fbbf24"];
                } else if (canonical === "theme13") {
                    colors = ["#c026d3", "#e879f9", "#ec4899"];
                } else if (canonical === "theme14") {
                    colors = ["#14b8a6", "#2dd4bf", "#06b6d4"];
                } else if (canonical === "theme15" || canonical === "pic1") {
                    colors = ["#f59e0b", "#ef4444", "#ec4899"];
                } else if (canonical === "theme16" || canonical === "pic2") {
                    colors = ["#06b6d4", "#3b82f6", "#8b5cf6"];
                } else if (canonical === "theme17" || canonical === "pic3") {
                    colors = ["#10b981", "#3b82f6", "#06b6d4"];
                } else if (canonical === "theme19" || canonical === "pic5") {
                    colors = ["#eab308", "#f97316", "#ef4444"];
                } else if (canonical === "theme20" || canonical === "pic6") {
                    colors = ["#6366f1", "#a855f7", "#ec4899"];
                }

                // Initialize particles if empty
                if (themeParticles.length === 0) {
                    initParticles(canvas);
                }

                // Render and update
                themeParticles.forEach(p => {
                    // Pulse alpha
                    p.alpha += p.pulseSpeed * p.pulseDir;
                    if (p.alpha > 0.6 || p.alpha < 0.1) {
                        p.pulseDir *= -1;
                    }

                    // Mouse gravity attraction
                    const dx = mouseX - p.x;
                    const dy = mouseY - p.y;
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    if (dist < 300) {
                        const force = (300 - dist) / 300 * 0.08;
                        p.vx += (dx / dist) * force;
                        p.vy += (dy / dist) * force;
                    }

                    // Friction
                    p.vx *= 0.98;
                    p.vy *= 0.98;

                    // Update positions
                    p.x += p.vx;
                    p.y += p.vy;

                    // Wrap boundaries
                    if (p.x < 0) p.x = canvas.width;
                    if (p.x > canvas.width) p.x = 0;
                    if (p.y < 0) p.y = canvas.height;
                    if (p.y > canvas.height) p.y = 0;

                    // Draw radial gradient particle
                    ctx.beginPath();
                    const grad = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.radius * 2);
                    const color = colors[Math.floor(p.radius * 10) % colors.length];
                    grad.addColorStop(0, color);
                    grad.addColorStop(0.5, color);
                    grad.addColorStop(1, "transparent");

                    ctx.fillStyle = grad;
                    ctx.globalAlpha = p.alpha;
                    ctx.arc(p.x, p.y, p.radius * 2.2, 0, Math.PI * 2);
                    ctx.fill();
                });
                ctx.globalAlpha = 1.0;
            }
        }

        // Smooth Lerp for Parallax (Crucial for performance feel)
        const targetOffsetX = (mouseX - window.innerWidth / 2) * 0.04;
        const targetOffsetY = (mouseY - window.innerHeight / 2) * 0.04;
        currentOffsetX += (targetOffsetX - currentOffsetX) * 0.08;
        currentOffsetY += (targetOffsetY - currentOffsetY) * 0.08;

        // Apply smooth parallax universally
        if (canonical === "water") {
            const waterLayer = document.querySelector(".layer--water") || document.querySelector(".layer--theme1");
            if (waterLayer) {
                waterLayer.style.transform = `translate(${currentOffsetX}px, ${currentOffsetY}px) scale(1.05)`;
            }
        } else {
            const bgMedia = document.querySelector(`.theme-layer.layer--${canonical} .theme-bg-video, .theme-layer.layer--${canonical} .theme-bg-image`) ||
                document.querySelector(`.theme-layer.layer--${activeTheme} .theme-bg-video, .theme-layer.layer--${activeTheme} .theme-bg-image`);
            if (bgMedia) {
                bgMedia.style.transform = `translate(calc(-50% + ${currentOffsetX}px), calc(-50% + ${currentOffsetY}px)) scale(1.05)`;
            }
        }

        requestAnimationFrame(runGlobalThemeLoop);
    }
    runGlobalThemeLoop();
}

// Downside Settings Panel Handlers
// Preview videos are preload="metadata", which loads dimensions but decodes no
// frame, so every tile in the picker rendered as an empty black rectangle.
// Nudging currentTime forces one frame to decode and paint, turning each tile
// into a real thumbnail of its theme.
function primeThemePreviewFrames() {
    document.querySelectorAll('.theme-preview-video').forEach(video => {
        if (video.dataset.framePrimed) return;
        video.dataset.framePrimed = '1';
        const seek = () => {
            try {
                if (video.readyState >= 1 && video.currentTime < 0.05) {
                    video.currentTime = Math.min(0.6, (video.duration || 2) * 0.25);
                }
            } catch (e) { }
        };
        if (video.readyState >= 1) {
            seek();
        } else {
            video.addEventListener('loadedmetadata', seek, { once: true });
            try { video.load(); } catch (e) { }
        }
    });
}

function toggleSettingsPanel(event) {
    if (event) event.stopPropagation();
    const panel = document.getElementById("settingsPopoverPanel");
    if (panel) {
        panel.classList.toggle("active");
        if (panel.classList.contains("active")) {
            primeThemePreviewFrames();
        }
    }
}

function closeSettingsPanel() {
    const panel = document.getElementById("settingsPopoverPanel");
    if (panel) {
        panel.classList.remove("active");
    }
}

// Auto-close popover when clicking outside
document.addEventListener("click", (e) => {
    const panel = document.getElementById("settingsPopoverPanel");
    const btn = document.getElementById("settingsFloatingBtn");
    if (panel && panel.classList.contains("active")) {
        if (!panel.contains(e.target) && e.target !== btn && !btn.contains(e.target)) {
            closeSettingsPanel();
        }
    }
});

// Theme Rotation Logic
function startThemeRotation() {
    if (themeRotationIntervalId) {
        clearInterval(themeRotationIntervalId);
        themeRotationIntervalId = null;
    }
    if (!isThemeAnimationsEnabled || themeRotationIntervalTime <= 0) return;
    themeRotationIntervalId = setInterval(() => {
        let nextIdx;
        const currentCanonical = normalizeTheme(activeTheme);
        do {
            nextIdx = Math.floor(Math.random() * themeRotationList.length);
        } while (normalizeTheme(themeRotationList[nextIdx]) === currentCanonical && themeRotationList.length > 1);
        switchBackdropTheme(themeRotationList[nextIdx], true);
    }, themeRotationIntervalTime);
}

function stopThemeRotation() {
    if (themeRotationIntervalId) {
        clearInterval(themeRotationIntervalId);
        themeRotationIntervalId = null;
    }
}

const intervalMap = [
    { value: 0, label: "None" },
    { value: 5, label: "5s" },
    { value: 15, label: "15s" },
    { value: 30, label: "30s" },
    { value: 60, label: "1 min" },
    { value: 300, label: "5 min" },
    { value: 900, label: "15 min" },
    { value: 1800, label: "30 min" },
    { value: 3600, label: "1 hour" },
    { value: 10800, label: "3 hours" },
    { value: 21600, label: "6 hours" },
    { value: 43200, label: "12 hours" },
    { value: 86400, label: "24 hours" }
];

function updateSliderDisplay(sliderIndex) {
    const display = document.getElementById("sliderValueDisplay");
    if (display && intervalMap[sliderIndex]) {
        display.innerText = intervalMap[sliderIndex].label;
    }
}

function applySliderInterval(sliderIndex) {
    if (intervalMap[sliderIndex]) {
        const seconds = intervalMap[sliderIndex].value;
        try {
            localStorage.setItem("theme_rotation_slider_index", sliderIndex);
        } catch (e) { }
        changeThemeInterval(seconds);
    }
}

function changeThemeInterval(seconds) {
    themeRotationIntervalTime = seconds * 1000;

    if (seconds > 0 && isThemeAnimationsEnabled) {
        startThemeRotation();
    } else {
        stopThemeRotation();
    }
}

// LocalStorage persistence bindings for the custom About Us text area
document.addEventListener("DOMContentLoaded", () => {
    const revealTextarea = document.getElementById("aboutRevealTextarea");
    if (revealTextarea) {
        const savedText = localStorage.getItem("aboutRevealCustomText");
        if (savedText) {
            revealTextarea.value = savedText;
        } else {
            revealTextarea.value = "The Group of Joining Hands is a community initiative for social welfare, empowerment, and networking.";
        }

        revealTextarea.addEventListener("input", (e) => {
            localStorage.setItem("aboutRevealCustomText", e.target.value);
        });
    }

    try {
        const savedTypography = localStorage.getItem("typography_style");
        if (savedTypography === "unified") {
            setTypographyStyle("unified");
        } else {
            setTypographyStyle("split");
        }
    } catch (e) { }
});

function setTypographyStyle(style) {
    if (typeof finishHeroTypewriter === 'function') {
        finishHeroTypewriter();
    }
    document.querySelectorAll('.timer-opt-btn').forEach(b => {
        if (b.id === 'btnStyleSplit' || b.id === 'btnStyleUnified') b.classList.remove('active');
    });

    // Hide all typography layouts first
    const layouts = [
        '.split-title-layout', '.unified-title-layout',
        '.split-slogan-layout', '.unified-slogan-layout'
    ];
    layouts.forEach(selector => {
        const el = document.querySelector(selector);
        if (el) el.style.display = 'none';
    });

    try {
        localStorage.setItem("typography_style", style);
    } catch (e) { }

    if (style === 'unified') {
        const btn = document.getElementById('btnStyleUnified');
        if (btn) btn.classList.add('active');
        const ut = document.querySelector('.unified-title-layout');
        const us = document.querySelector('.unified-slogan-layout');
        if (ut) ut.style.display = 'flex';
        if (us) us.style.display = 'flex';
    } else {
        // 'split' (Elegant) is default
        const btn = document.getElementById('btnStyleSplit');
        if (btn) btn.classList.add('active');
        const st = document.querySelector('.split-title-layout');
        const ss = document.querySelector('.split-slogan-layout');
        if (st) st.style.display = 'flex';
        if (ss) ss.style.display = 'flex';
    }
}

// Theme Animations Toggle Controller
function setThemeAnimations(enabled) {
    isThemeAnimationsEnabled = enabled;
    try {
        localStorage.setItem("theme_animations_enabled", enabled ? "true" : "false");
    } catch (e) { }

    const btnOn = document.getElementById("btnThemeAnimOn");
    const btnOff = document.getElementById("btnThemeAnimOff");
    if (btnOn && btnOff) {
        if (enabled) {
            btnOn.classList.add("active");
            btnOff.classList.remove("active");
        } else {
            btnOn.classList.remove("active");
            btnOff.classList.add("active");
        }
    }

    const landingView = document.getElementById("landing-view");
    if (landingView) {
        if (!enabled) {
            landingView.classList.add("theme-animations-disabled");
        } else {
            landingView.classList.remove("theme-animations-disabled");
        }
    }

    const allVideos = document.querySelectorAll(".theme-layer video");
    if (!enabled) {
        // Freeze active video immediately on its exact current frame
        allVideos.forEach(vid => {
            try { vid.pause(); } catch (e) { }
        });
        // Freeze auto-rotation so it pauses on the exact theme currently displayed
        stopThemeRotation();
    } else {
        // Resume video playback for the active theme from the paused frame
        if (!isThemeMotionPaused) {
            const canonical = normalizeTheme(activeTheme);
            const activeLayer = document.querySelector(`.layer--${canonical}`) || document.querySelector(`.layer--${activeTheme}`);
            if (activeLayer) {
                const activeVideo = activeLayer.querySelector("video");
                if (activeVideo) {
                    try { activeVideo.play(); } catch (e) { }
                }
            }
        }
        // Resume theme rotation if an interval was configured
        if (typeof themeRotationIntervalTime !== 'undefined' && themeRotationIntervalTime > 0) {
            startThemeRotation();
        }
    }
}

// Restore saved theme animations preference on page load
document.addEventListener("DOMContentLoaded", () => {
    try {
        const savedAnimState = localStorage.getItem("theme_animations_enabled");
        if (savedAnimState === "false") {
            setThemeAnimations(false);
        }
    } catch (e) { }
});








// Hover playback for the theme tiles lives in THEME HOVER PREVIEW below.





document.addEventListener('click', function (e) {
    const landingView = document.getElementById('landing-view');
    if (!landingView || !landingView.classList.contains('menu-active')) return;
    if (e.target.closest('.ecosystem-tile--menu')) return;
    closeLandingSidebar();
});



/* ==========================================================================
   THEME HOVER PREVIEW
   Hovering a theme tile plays that theme for five seconds and names it, so
   the 37 tiles can be told apart without committing to one.
   ========================================================================== */

const THEME_PREVIEW_MS = 5000;
const THEME_PREVIEW_INTENT_MS = 110;   // sweeping the grid shouldn't start 37 videos
let themePreviewIntentTimer = null;
let themePreviewStopTimer = null;
let themePreviewActiveBtn = null;

function themePreviewReducedMotion() {
    return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
}

function clearThemePreviewTimers() {
    if (themePreviewIntentTimer) {
        clearTimeout(themePreviewIntentTimer);
        themePreviewIntentTimer = null;
    }
    if (themePreviewStopTimer) {
        clearTimeout(themePreviewStopTimer);
        themePreviewStopTimer = null;
    }
}

function stopThemePreview(btn) {
    const target = btn || themePreviewActiveBtn;
    if (!target) return;
    target.classList.remove('theme-previewing');
    const video = target.querySelector('.theme-preview-video');
    if (video) {
        try {
            video.pause();
            // back to the primed still frame so the tile still reads as its theme
            video.currentTime = Math.min(0.6, (video.duration || 2) * 0.25);
        } catch (e) { }
    }
    if (target === themePreviewActiveBtn) themePreviewActiveBtn = null;
}

function startThemePreview(btn) {
    if (!btn) return;
    if (themePreviewActiveBtn && themePreviewActiveBtn !== btn) {
        stopThemePreview(themePreviewActiveBtn);
    }
    themePreviewActiveBtn = btn;
    btn.classList.add('theme-previewing');

    const video = btn.querySelector('.theme-preview-video');
    if (video && !themePreviewReducedMotion()) {
        const attemptPlay = () => {
            const played = video.play();
            if (played && played.catch) {
                played.catch(() => {
                    // Not enough buffered yet - try once more when data lands
                    video.addEventListener('canplay', () => {
                        if (!btn.classList.contains('theme-previewing')) return;
                        const retry = video.play();
                        if (retry && retry.catch) retry.catch(() => { });
                    }, { once: true });
                });
            }
        };
        try {
            video.muted = true;
            video.loop = true;
            if (video.readyState >= 2) video.currentTime = 0;
            attemptPlay();
        } catch (e) { }
    }

    themePreviewStopTimer = setTimeout(() => {
        themePreviewStopTimer = null;
        stopThemePreview(btn);
    }, THEME_PREVIEW_MS);
}

function bindThemePreview(btn) {
    if (btn.dataset.previewBound) return;
    btn.dataset.previewBound = '1';

    // The caption reads from the badge so the name lives in one place
    const badge = btn.querySelector('.theme-btn-badge');
    const name = (badge && badge.textContent.trim()) || btn.getAttribute('title') || '';
    if (name) btn.setAttribute('data-theme-name', name);

    const enter = () => {
        clearThemePreviewTimers();
        themePreviewIntentTimer = setTimeout(() => {
            themePreviewIntentTimer = null;
            startThemePreview(btn);
        }, THEME_PREVIEW_INTENT_MS);
    };
    const leave = () => {
        clearThemePreviewTimers();
        stopThemePreview(btn);
    };

    btn.addEventListener('mouseenter', enter);
    btn.addEventListener('mouseleave', leave);
    btn.addEventListener('focus', enter);
    btn.addEventListener('blur', leave);
}

function initThemeHoverPreviews() {
    document.querySelectorAll('.sidebar-themes-grid .theme-select-btn').forEach(bindThemePreview);
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initThemeHoverPreviews);
} else {
    initThemeHoverPreviews();
}
