/* ============================================================
   CyberLaw Bot — Frontend Application
   ============================================================ */

const API_URL = "/api/query";
const FEEDBACK_URL = "/api/feedback";

// ── DOM elements ──
const chatArea = document.getElementById("chatArea");
const messagesDiv = document.getElementById("messages");
const welcomeScreen = document.getElementById("welcomeScreen");
const questionInput = document.getElementById("questionInput");
const sendBtn = document.getElementById("sendBtn");
const micBtn = document.getElementById("micBtn");
const newChatBtn = document.getElementById("newChatBtn");
const statusBadge = document.getElementById("statusBadge");
const suggestionBtns = document.querySelectorAll(".suggestion-card");

let isLoading = false;
let currentLang = (localStorage.getItem("cyberlaw_lang") === "ur") ? "ur" : "en";
let sessionId = crypto.randomUUID ? crypto.randomUUID() : Date.now().toString(36) + Math.random().toString(36).slice(2);

// ── UI translations (English / Urdu) ──
const SUGGESTIONS = [
    { en: "What are the punishments for cyberbullying under PECA 2016?", ur: "PECA 2016 کے تحت سائبر بُلنگ کی سزائیں کیا ہیں؟" },
    { en: "Which sections of the PPC deal with online fraud?", ur: "PPC کی کون سی دفعات آن لائن فراڈ سے متعلق ہیں؟" },
    { en: "How do I file a cybercrime complaint in Pakistan?", ur: "پاکستان میں سائبر کرائم کی شکایت کیسے درج کرائیں؟" },
    { en: "How can I protect myself from cyber harassment?", ur: "سائبر ہراسانی سے کیسے بچیں؟" },
];

const I18N = {
    en: {
        brand1: "CyberLaw", brand2: "Bot",
        hero_pre: "Welcome to", hero_brand: "CyberLaw Bot",
        hero_sub: "Ask about Criminal Law, PECA, PPC & CrPC in English or Urdu.",
        placeholder: "Ask a legal question…",
        disclaimer: "CyberLaw Bot provides legal information, not legal advice. Always consult a qualified lawyer.",
        footer_about: "About", footer_privacy: "Privacy", footer_terms: "Terms",
        new_chat: "New Chat", status_online: "Online", status_offline: "Offline", status_nodb: "No DB",
        info_title: "About CyberLaw Bot", mic_title: "Speak your question", mic_stop: "Stop listening", send_title: "Send question", close: "Close",
        copy: "📋 Copy", copied: "✅ Copied!", listen: "🔊 Listen", stop: "⏹ Stop", listen_title: "Read this answer aloud",
        fb_label: "Was this helpful?", fb_thanks: "Thanks for your feedback!", fb_helpful: "Helpful", fb_not: "Not helpful",
        hl_head: "If this is urgent or you feel unsafe, please get help now:",
        cp_title: "Ready to report this cybercrime?", cp_btn: "File a complaint (FIA / NCCIA)",
        cp_note: "You will leave CyberLaw Bot and continue on the official government site.",
        fu_title: "Suggested next:",
        followups: ["What is the punishment for this offence?", "Is bail possible in this case?", "How can I protect myself from this?"],
        tp_title: "🔍 RAG sources used", tp_count: "chunks retrieved", ref_heading: "📚 Sources", relevance: "relevance",
        modal_about: "About CyberLaw Bot", modal_privacy: "Privacy Policy", modal_terms: "Terms of Use",
        toast_mic_unsupported: "Voice input isn't supported in this browser. Try Chrome or Edge.",
        toast_mic_insecure: "Voice input needs HTTPS or localhost. Please type your question instead.",
        toast_mic_unavailable: "Voice input isn't available here.",
        toast_mic_blocked: "Microphone permission blocked. Allow mic access and try again.",
        toast_mic_error: "Voice input didn't work. Please type your question.",
        toast_tts_coming: "Urdu voice audio is a coming-soon feature. English answers can be listened to now.",
        toast_audio_unsupported: "Audio playback isn't supported in this browser.",
        toast_tts_rate: "Too many audio requests. Please wait a moment.",
        toast_tts_fail: "Urdu audio unavailable right now.",
    },
    ur: {
        brand1: "سائبر لا", brand2: "بوٹ",
        hero_pre: "خوش آمدید", hero_brand: "سائبر لا بوٹ",
        hero_sub: "فوجداری قانون، PECA، PPC اور CrPC کے بارے میں اردو یا انگریزی میں سوال کریں۔",
        placeholder: "…اپنا قانونی سوال یہاں لکھیں",
        disclaimer: "سائبر لا بوٹ صرف قانونی معلومات فراہم کرتا ہے، قانونی مشورہ نہیں۔ ہمیشہ کسی مستند وکیل سے مشورہ کریں۔",
        footer_about: "تعارف", footer_privacy: "رازداری", footer_terms: "شرائط",
        new_chat: "نئی گفتگو", status_online: "آن لائن", status_offline: "آف لائن", status_nodb: "ڈی بی نہیں",
        info_title: "سائبر لا بوٹ کے بارے میں", mic_title: "اپنا سوال بولیں", mic_stop: "سننا بند کریں", send_title: "سوال بھیجیں", close: "بند کریں",
        copy: "📋 کاپی کریں", copied: "✅ کاپی ہو گیا!", listen: "🔊 سنیں", stop: "⏹ روکیں", listen_title: "یہ جواب بلند آواز سے پڑھیں",
        fb_label: "کیا یہ مددگار تھا؟", fb_thanks: "آپ کی رائے کا شکریہ!", fb_helpful: "مددگار", fb_not: "غیر مددگار",
        hl_head: "اگر معاملہ ہنگامی ہے یا آپ غیر محفوظ محسوس کرتے ہیں تو ابھی مدد حاصل کریں:",
        cp_title: "کیا آپ اس سائبر کرائم کی شکایت درج کرنا چاہتے ہیں؟", cp_btn: "شکایت درج کریں (FIA / NCCIA)",
        cp_note: "آپ سائبر لا بوٹ چھوڑ کر سرکاری ویب سائٹ پر جائیں گے۔",
        fu_title: "اگلے تجویز کردہ سوالات:",
        followups: ["اس جرم کی سزا کیا ہے؟", "کیا اس معاملے میں ضمانت ممکن ہے؟", "اس سے بچاؤ کیسے ممکن ہے؟"],
        tp_title: "🔍 استعمال شدہ ذرائع", tp_count: "ذرائع حاصل کیے گئے", ref_heading: "📚 ذرائع", relevance: "مطابقت",
        modal_about: "سائبر لا بوٹ کے بارے میں", modal_privacy: "رازداری کی پالیسی", modal_terms: "استعمال کی شرائط",
        toast_mic_unsupported: "اس براؤزر میں وائس ان پٹ سپورٹ نہیں ہے۔ Chrome یا Edge آزمائیں۔",
        toast_mic_insecure: "وائس ان پٹ کے لیے HTTPS یا localhost درکار ہے۔ براہ کرم اپنا سوال ٹائپ کریں۔",
        toast_mic_unavailable: "یہاں وائس ان پٹ دستیاب نہیں۔",
        toast_mic_blocked: "مائیک کی اجازت بند ہے۔ مائیک کی اجازت دیں اور دوبارہ کوشش کریں۔",
        toast_mic_error: "وائس ان پٹ کام نہیں کیا۔ براہ کرم اپنا سوال ٹائپ کریں۔",
        toast_tts_coming: "اردو آواز جلد آرہی ہے۔ فی الحال انگریزی جوابات سنے جا سکتے ہیں۔",
        toast_audio_unsupported: "اس براؤزر میں آواز چلانا سپورٹ نہیں ہے۔",
        toast_tts_rate: "بہت زیادہ آواز کی درخواستیں۔ براہ کرم تھوڑی دیر انتظار کریں۔",
        toast_tts_fail: "فی الحال اردو آواز دستیاب نہیں۔",
    },
};
function t(key) {
    const d = I18N[currentLang] || I18N.en;
    return d[key] != null ? d[key] : (I18N.en[key] != null ? I18N.en[key] : key);
}

// ── Voice I/O (Web Speech API) feature detection ──
const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
const SR_SUPPORTED = !!SpeechRec;
const TTS_SUPPORTED = ("speechSynthesis" in window);
// Future scope: server-side Urdu audio costs Gemini API credits; keep OFF for now.
const SERVER_TTS_ENABLED = false;
// "Suggested next" follow-up chips are parked for now; flip to true to bring them back.
const FOLLOWUPS_ENABLED = false;
let recognition = null;
let isListening = false;
let speakingBtn = null;
let ttsAudio = null;  // server-generated Urdu audio element

// TTS voice list loads asynchronously in most browsers; keep a cached copy.
let ttsVoices = [];
function refreshTtsVoices() {
    if (TTS_SUPPORTED) ttsVoices = speechSynthesis.getVoices() || [];
}
if (TTS_SUPPORTED) {
    refreshTtsVoices();
    speechSynthesis.addEventListener("voiceschanged", refreshTtsVoices);
}

// ── Initialise ──
function init() {
    sendBtn.addEventListener("click", handleSend);

    questionInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    });

    // Auto-resize textarea
    questionInput.addEventListener("input", autoResize);

    // Suggestion cards
    suggestionBtns.forEach((card) => {
        card.addEventListener("click", () => {
            questionInput.value = card.dataset.question;
            handleSend();
        });
    });

    // New chat button
    newChatBtn.addEventListener("click", resetChat);

    // Language toggle (English / Urdu)
    initLanguageSwitch();

    // Voice input (mic -> speech-to-text)
    initSpeechInput();

    // About / Privacy / Terms modals
    initModals();

    // Health check
    checkHealth();
}

// ── Auto-resize textarea ──
function autoResize() {
    questionInput.style.height = "auto";
    questionInput.style.height = Math.min(questionInput.scrollHeight, 120) + "px";
}

// ── Health check ──
async function checkHealth() {
    try {
        const r = await fetch("/api/health");
        const data = await r.json();
        if (!data.database_loaded) {
            setStatus("status_nodb", false);
        } else {
            setStatus("status_online", true);
        }
    } catch {
        setStatus("status_offline", false);
    }
}

let currentStatusKey = "status_online";
let currentStatusOk = true;
function setStatus(key, ok) {
    currentStatusKey = key;
    currentStatusOk = !!ok;
    const dot = statusBadge.querySelector(".status-dot");
    const text = statusBadge.querySelector(".status-label");
    text.textContent = t(key);
    if (!ok) {
        dot.style.background = "#f87171";
        dot.style.boxShadow = "0 0 6px #f87171";
        text.style.color = "#f87171";
        statusBadge.style.borderColor = "rgba(248,113,113,0.15)";
        statusBadge.style.background = "rgba(248,113,113,0.08)";
    } else {
        dot.style.background = "";
        dot.style.boxShadow = "";
        text.style.color = "";
        statusBadge.style.borderColor = "";
        statusBadge.style.background = "";
    }
}

// ── Reset chat ──
function resetChat() {
    // Clear server-side session history
    fetch("/api/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
    }).catch(() => { }); // fire-and-forget

    // Generate new session ID for the fresh conversation
    sessionId = crypto.randomUUID ? crypto.randomUUID() : Date.now().toString(36) + Math.random().toString(36).slice(2);

    messagesDiv.innerHTML = "";
    welcomeScreen.style.display = "flex";
    questionInput.value = "";
    questionInput.style.height = "auto";
    questionInput.focus();
}

// ── Send question ──
async function handleSend() {
    const question = questionInput.value.trim();
    if (!question || isLoading) return;

    isLoading = true;
    sendBtn.disabled = true;
    questionInput.value = "";
    questionInput.style.height = "auto";

    // Hide welcome
    welcomeScreen.style.display = "none";

    // User bubble
    addMessage("user", question);

    // Typing indicator
    const typingId = addTypingIndicator();

    const t0 = performance.now();

    try {
        const response = await fetch(API_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question, top_k: 6, session_id: sessionId, language: currentLang }),
        });

        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || `Server error ${response.status}`);
        }

        const data = await response.json();

        // Track the session ID from server
        if (data.session_id) {
            sessionId = data.session_id;
        }

        const elapsedMs = Math.round(performance.now() - t0);
        removeTypingIndicator(typingId);
        addMessage("ai", data.answer, {
            references: data.references || [],
            retrieved: data.retrieved || [],
            elapsedMs: elapsedMs,
            helplines: data.helplines || [],
            complaint: data.complaint || null,
            question: question,
            language: data.language || currentLang,
        });
    } catch (error) {
        removeTypingIndicator(typingId);
        addMessage("ai", `⚠️ ${error.message}`, { isError: true });
    } finally {
        isLoading = false;
        sendBtn.disabled = false;
        questionInput.focus();
    }
}

// ── Add a chat message ──
function addMessage(type, content, meta = {}) {
    const { references = [], retrieved = [], elapsedMs = null, isError = false, helplines = [], complaint = null, question = null, language = null } = meta;
    const msg = document.createElement("div");
    msg.className = `message ${type}-message`;

    const bubble = document.createElement("div");
    bubble.className = "bubble";

    if (type === "ai") {
        // Avatar (brand logo)
        const avatar = document.createElement("div");
        avatar.className = "avatar";
        avatar.innerHTML = '<img src="/static/logo.png" alt="">';
        msg.appendChild(avatar);

        // Content
        if (isError) {
            bubble.innerHTML = `<p class="error-text">${escapeHTML(content)}</p>`;
        } else {
            // Scope RTL/Urdu styling to the answer text only, so the English UI
            // chrome below it (meta chips, sources, buttons) stays LTR.
            const answerDiv = document.createElement("div");
            answerDiv.className = "answer-text";
            answerDiv.innerHTML = renderMarkdown(content);
            if (language === "ur" || isUrdu(content)) {
                answerDiv.classList.add("rtl");
            }
            bubble.appendChild(answerDiv);

            // Urgent-situation helpline card (rendered at the top for prominence)
            if (helplines && helplines.length > 0) {
                bubble.insertBefore(buildHelplineCard(helplines), answerDiv);
            }

            // Official complaint link for reportable cyber offences
            if (complaint && complaint.url) {
                bubble.insertBefore(buildComplaintCard(complaint), answerDiv.nextSibling);
            }

            // Answer meta: latency + retrieval confidence
            const metaRow = buildAnswerMeta(retrieved, elapsedMs);
            if (metaRow) {
                bubble.appendChild(metaRow);
            }

            // RAG transparency panel (retrieved statute chunks)
            if (retrieved && retrieved.length > 0) {
                bubble.appendChild(buildTransparencyPanel(retrieved));
            }

            // References
            if (references && references.length > 0) {
                const refsDiv = document.createElement("div");
                refsDiv.className = "references";
                refsDiv.innerHTML = `<h4 data-i18n="ref_heading">${t("ref_heading")}</h4><div class="ref-list"></div>`;
                const refList = refsDiv.querySelector(".ref-list");

                references.forEach((ref) => {
                    const chip = document.createElement("a");
                    chip.className = "ref-chip";
                    chip.href = ref.url;
                    chip.target = "_blank";
                    chip.rel = "noopener";
                    chip.innerHTML =
                        `<span class="ref-label">${escapeHTML(ref.label)}</span>` +
                        `<span class="ref-page">p.${ref.page}</span>`;
                    refList.appendChild(chip);
                });

                bubble.appendChild(refsDiv);
            }

            // Answer actions: copy + listen (text-to-speech)
            const actions = document.createElement("div");
            actions.className = "answer-actions";

            const copyBtn = document.createElement("button");
            copyBtn.className = "copy-btn";
            copyBtn.dataset.i18n = "copy";
            copyBtn.textContent = t("copy");
            copyBtn.addEventListener("click", () => {
                navigator.clipboard.writeText(content).then(() => {
                    copyBtn.textContent = t("copied");
                    copyBtn.classList.add("copied");
                    setTimeout(() => {
                        copyBtn.textContent = t("copy");
                        copyBtn.classList.remove("copied");
                    }, 2000);
                });
            });
            actions.appendChild(copyBtn);

            if (TTS_SUPPORTED) {
                const speakBtn = document.createElement("button");
                speakBtn.className = "speak-btn";
                speakBtn.dataset.i18n = "listen";
                speakBtn.dataset.i18nTitle = "listen_title";
                speakBtn.textContent = t("listen");
                speakBtn.title = t("listen_title");
                speakBtn.addEventListener("click", () => {
                    toggleSpeak(speakBtn, plainForSpeech(content), (language === "ur" ? "ur" : "en"));
                });
                actions.appendChild(speakBtn);
            }

            bubble.appendChild(actions);

            // Feedback (thumbs up/down) - feeds the Phase 3 eval set
            bubble.appendChild(buildFeedbackBar(question));

            // Suggested follow-up questions (parked: see FOLLOWUPS_ENABLED)
            if (FOLLOWUPS_ENABLED) {
                bubble.appendChild(buildFollowups());
            }
        }
    } else {
        // User bubble – plain text
        bubble.textContent = content;
        if (isUrdu(content)) {
            bubble.classList.add("rtl");
        }
    }

    msg.appendChild(bubble);
    messagesDiv.appendChild(msg);
    scrollToBottom();
}

// ── Answer meta row: latency + retrieval confidence ──
function buildAnswerMeta(retrieved, elapsedMs) {
    const chips = [];

    if (elapsedMs != null) {
        chips.push(`<span class="meta-chip latency-chip">⏱ ${(elapsedMs / 1000).toFixed(1)}s</span>`);
    }

    if (retrieved && retrieved.length > 0 && retrieved[0].similarity != null) {
        const pct = Math.round(retrieved[0].similarity * 100);
        const level = pct >= 75 ? "high" : (pct >= 55 ? "med" : "low");
        chips.push(`<span class="meta-chip conf-chip conf-${level}">🎯 ${pct}% ${t("relevance")}</span>`);
    }

    if (chips.length === 0) return null;

    const row = document.createElement("div");
    row.className = "answer-meta";
    row.innerHTML = chips.join("");
    return row;
}

// ── RAG transparency panel: shows the actual retrieved statute chunks ──
function buildTransparencyPanel(retrieved) {
    const panel = document.createElement("details");
    panel.className = "transparency-panel";

    const summary = document.createElement("summary");
    summary.innerHTML =
        `<span class="tp-title" data-i18n="tp_title">${t("tp_title")}</span>` +
        `<span class="tp-count">${retrieved.length} ${t("tp_count")}</span>`;
    panel.appendChild(summary);

    const list = document.createElement("div");
    list.className = "tp-list";

    retrieved.forEach((r, i) => {
        const md = r.metadata || {};
        const sim = r.similarity != null ? Math.round(r.similarity * 100) : null;

        const item = document.createElement("div");
        item.className = "tp-item";
        item.innerHTML =
            `<div class="tp-item-head">` +
            `<span class="tp-rank">#${i + 1}</span>` +
            `<span class="tp-law">${escapeHTML(md.law || "")}</span>` +
            `<span class="tp-section">§ ${escapeHTML(String(md.section || ""))}</span>` +
            (sim != null ? `<span class="tp-sim">${sim}%</span>` : "") +
            `</div>` +
            `<div class="tp-snippet">${escapeHTML(r.snippet || "")}</div>`;
        list.appendChild(item);
    });

    panel.appendChild(list);
    return panel;
}

// ── Urgent helpline card ──
function buildHelplineCard(helplines) {
    const card = document.createElement("div");
    card.className = "helpline-card";
    card.setAttribute("role", "note");

    const items = helplines.map((h) => {
        const tel = String(h.number || "").replace(/[^0-9+]/g, "");
        return `<a class="hl-item" href="tel:${escapeHTML(tel)}">` +
            `<span class="hl-name">${escapeHTML(h.name || "")}</span>` +
            `<span class="hl-num">${escapeHTML(h.number || "")}</span>` +
            (h.note ? `<span class="hl-note">${escapeHTML(h.note)}</span>` : "") +
            `</a>`;
    }).join("");

    card.innerHTML =
        `<div class="hl-head"><span class="hl-icon">🆘</span>` +
        `<span data-i18n="hl_head">${t("hl_head")}</span></div>` +
        `<div class="hl-list">${items}</div>`;
    return card;
}

// ── Official complaint card (FIA / NCCIA) ──
function buildComplaintCard(c) {
    const card = document.createElement("div");
    card.className = "complaint-card";
    card.setAttribute("role", "note");
    card.innerHTML =
        `<div class="cp-head"><span class="cp-icon" aria-hidden="true">` +
        `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="12" y1="18" x2="12" y2="12"></line><line x1="9" y1="15" x2="15" y2="15"></line></svg>` +
        `</span><span data-i18n="cp_title">${t("cp_title")}</span></div>` +
        `<a class="cp-btn" href="${escapeHTML(c.url)}" target="_blank" rel="noopener noreferrer">` +
        `<span data-i18n="cp_btn">${t("cp_btn")}</span>` +
        `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg></a>` +
        `<p class="cp-note" data-i18n="cp_note">${t("cp_note")}</p>`;
    return card;
}

// ── Suggested follow-up questions ──
function buildFollowups() {
    const row = document.createElement("div");
    row.className = "followup-row";
    const title = document.createElement("span");
    title.className = "followup-title";
    title.dataset.i18n = "fu_title";
    title.textContent = t("fu_title");
    row.appendChild(title);
    const list = (I18N[currentLang] && I18N[currentLang].followups) || I18N.en.followups;
    list.forEach((q, i) => {
        const b = document.createElement("button");
        b.type = "button";
        b.className = "followup-chip";
        b.dataset.fuIndex = String(i);
        b.textContent = q;
        b.addEventListener("click", () => {
            questionInput.value = b.textContent;
            handleSend();
        });
        row.appendChild(b);
    });
    return row;
}

// ── Feedback bar (thumbs up/down) ──
function buildFeedbackBar(question) {
    const bar = document.createElement("div");
    bar.className = "feedback-bar";
    bar.innerHTML =
        `<span class="fb-label" data-i18n="fb_label">${t("fb_label")}</span>` +
        `<button class="fb-btn" data-vote="1" data-i18n-title="fb_helpful" data-i18n-aria="fb_helpful" title="${t("fb_helpful")}" aria-label="${t("fb_helpful")}">👍</button>` +
        `<button class="fb-btn" data-vote="-1" data-i18n-title="fb_not" data-i18n-aria="fb_not" title="${t("fb_not")}" aria-label="${t("fb_not")}">👎</button>`;

    const label = bar.querySelector(".fb-label");
    const btns = bar.querySelectorAll(".fb-btn");
    btns.forEach((b) => {
        b.addEventListener("click", async () => {
            const vote = parseInt(b.getAttribute("data-vote"), 10);
            btns.forEach((x) => { x.disabled = true; });
            b.classList.add("fb-selected");
            label.textContent = t("fb_thanks");
            label.removeAttribute("data-i18n");
            try {
                await fetch(FEEDBACK_URL, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ vote: vote, question: question || null }),
                });
            } catch (e) { /* non-blocking */ }
        });
    });
    return bar;
}

// ── Modal (About / Privacy / Terms) ──
const modalOverlay = document.getElementById("modalOverlay");
const modalTitle = document.getElementById("modalTitle");
const modalClose = document.getElementById("modalClose");
const MODAL_TITLES = { about: "About CyberLaw Bot", privacy: "Privacy Policy", terms: "Terms of Use" };
let currentModalKey = null;

function openModal(key) {
    if (!modalOverlay) return;
    currentModalKey = key;
    document.querySelectorAll(".modal-view").forEach((v) => { v.hidden = true; });
    const view = document.getElementById("view-" + key);
    if (view) view.hidden = false;
    if (modalTitle) modalTitle.textContent = t("modal_" + key) || "CyberLaw Bot";
    modalOverlay.hidden = false;
    document.body.classList.add("modal-open");
    if (modalClose) modalClose.focus();
}

function closeModal() {
    if (!modalOverlay) return;
    modalOverlay.hidden = true;
    document.body.classList.remove("modal-open");
}

function initModals() {
    document.querySelectorAll("[data-modal]").forEach((el) => {
        el.addEventListener("click", () => openModal(el.getAttribute("data-modal")));
    });
    if (modalClose) modalClose.addEventListener("click", closeModal);
    if (modalOverlay) {
        modalOverlay.addEventListener("click", (e) => {
            if (e.target === modalOverlay) closeModal();
        });
    }
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && modalOverlay && !modalOverlay.hidden) closeModal();
    });
}

// ── Language switch (English / Urdu) ──
function initLanguageSwitch() {
    document.querySelectorAll(".lang-btn").forEach((btn) => {
        btn.addEventListener("click", () => setLanguage(btn.getAttribute("data-lang")));
    });
    setLanguage(currentLang);  // apply persisted / default choice on load
}

function setLanguage(lang) {
    currentLang = (lang === "ur") ? "ur" : "en";
    try { localStorage.setItem("cyberlaw_lang", currentLang); } catch (e) { /* private mode */ }

    document.querySelectorAll(".lang-btn").forEach((btn) => {
        const on = btn.getAttribute("data-lang") === currentLang;
        btn.classList.toggle("active", on);
        btn.setAttribute("aria-pressed", on ? "true" : "false");
    });

    applyLanguage();
}

// Original English modal markup, captured once so we can restore it.
let MODAL_ORIG = null;
function captureModalOriginals() {
    if (MODAL_ORIG) return;
    MODAL_ORIG = {};
    ["about", "privacy", "terms"].forEach((k) => {
        const v = document.getElementById("view-" + k);
        if (v) MODAL_ORIG[k] = v.innerHTML;
    });
}

function setText(sel, text) { const el = document.querySelector(sel); if (el) el.textContent = text; }
function setAttr(sel, attr, val) { const el = document.querySelector(sel); if (el) el.setAttribute(attr, val); }

// Translate every visible UI string for the selected language.
function applyLanguage() {
    const ur = currentLang === "ur";
    document.documentElement.lang = ur ? "ur" : "en";
    document.documentElement.dir = ur ? "rtl" : "ltr";
    document.body.classList.toggle("rtl-ui", ur);

    // Input
    questionInput.placeholder = t("placeholder");
    questionInput.dir = ur ? "rtl" : "ltr";

    // Header / hero / footer chrome
    setText(".header-text .brand-green", t("brand1"));
    setText(".header-text .brand-dark", t("brand2"));
    setText(".welcome-screen h2 .hero-pre", t("hero_pre"));
    setText(".welcome-screen h2 .hero-brand", t("hero_brand"));
    setText(".welcome-sub", t("hero_sub"));
    setText(".disclaimer span", t("disclaimer"));
    setText("#newChatBtn span", t("new_chat"));
    setAttr("#aboutBtn", "title", t("info_title")); setAttr("#aboutBtn", "aria-label", t("info_title"));
    setAttr("#micBtn", "title", t("mic_title")); setAttr("#micBtn", "aria-label", t("mic_title"));
    setAttr("#sendBtn", "title", t("send_title")); setAttr("#sendBtn", "aria-label", t("send_title"));
    setAttr("#modalClose", "title", t("close")); setAttr("#modalClose", "aria-label", t("close"));
    setText(".footer-link[data-modal='about']", t("footer_about"));
    setText(".footer-link[data-modal='privacy']", t("footer_privacy"));
    setText(".footer-link[data-modal='terms']", t("footer_terms"));

    // Status
    setStatus(currentStatusKey, currentStatusOk);

    // Suggestion cards
    suggestionBtns.forEach((card, i) => {
        const s = SUGGESTIONS[i]; if (!s) return;
        const q = ur ? s.ur : s.en;
        card.dataset.question = q;
        const txt = card.querySelector(".sug-text");
        if (txt) {
            txt.textContent = q;
            const isUr = ur || isUrdu(q);
            txt.classList.toggle("urdu", isUr);
            txt.dir = isUr ? "rtl" : "ltr";
        }
    });

    // Modals (English keeps original markup; Urdu uses translated markup)
    captureModalOriginals();
    ["about", "privacy", "terms"].forEach((k) => {
        const v = document.getElementById("view-" + k);
        if (v) v.innerHTML = ur ? URDU_MODALS[k] : (MODAL_ORIG[k] || "");
    });
    if (modalTitle && currentModalKey) modalTitle.textContent = t("modal_" + currentModalKey);

    // Sweep already-rendered dynamic labels
    document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.getAttribute("data-i18n")); });
    document.querySelectorAll("[data-i18n-title]").forEach((el) => { el.title = t(el.getAttribute("data-i18n-title")); });
    document.querySelectorAll("[data-i18n-aria]").forEach((el) => { el.setAttribute("aria-label", t(el.getAttribute("data-i18n-aria"))); });
    document.querySelectorAll(".followup-chip").forEach((el) => {
        const i = parseInt(el.getAttribute("data-fu-index"), 10);
        const list = (I18N[currentLang] && I18N[currentLang].followups) || I18N.en.followups;
        if (!isNaN(i) && list[i]) el.textContent = list[i];
    });
}

const URDU_MODALS = {
    about:
        `<h3>سائبر لا بوٹ کیا ہے؟</h3>` +
        `<p>ایک AI معاون جو پاکستانی فوجداری قانون — <strong>ضابطہ فوجداری (CrPC)</strong>، <strong>پاکستان پینل کوڈ (PPC)</strong>، <strong>PECA 2016</strong> اور <strong>PECA 2025 ترمیم</strong> — پر اردو اور انگریزی میں سوالات کے جواب دیتا ہے۔</p>` +
        `<h3>یہ کیسے کام کرتا ہے (Retrieval-Augmented Generation)</h3>` +
        `<ol><li>آپ کے سوال کو عددی ایمبیڈنگ میں تبدیل کیا جاتا ہے۔</li>` +
        `<li>قانونی دفعات کے <strong>2,373</strong> انڈیکس شدہ اقتباسات کے کسٹم ویکٹر انڈیکس سے سب سے متعلقہ دفعات تلاش کی جاتی ہیں۔</li>` +
        `<li>Gemini صرف انہی دفعات کی بنیاد پر جواب لکھتا ہے اور انہیں بطور حوالہ درج کرتا ہے۔</li></ol>` +
        `<p>ہر جواب اپنے استعمال شدہ ٹھیک ذرائع دکھاتا ہے تاکہ آپ ہر دعویٰ کی تصدیق کر سکیں۔</p>` +
        `<h3>ٹیک اسٹیک</h3>` +
        `<p>FastAPI بیک اینڈ · Google Gemini (ایمبیڈنگ + جنریشن) · کسٹم NumPy کوسائن مماثلت ویکٹر سرچ۔ نہ LangChain ہے نہ کوئی بیرونی ویکٹر ڈیٹابیس — ریٹریول انجن ہاتھ سے بنایا گیا ہے۔ عام جواب کا وقت 5 سیکنڈ سے کم ہے۔</p>` +
        `<h3>اہم</h3>` +
        `<p>سائبر لا بوٹ قانونی <strong>معلومات</strong> فراہم کرتا ہے، قانونی مشورہ نہیں، اور وکیل-موکل تعلق قائم نہیں کرتا۔ عمل کرنے سے پہلے ہمیشہ کسی مستند وکیل اور سروری ذرائع سے تصدیق کریں۔</p>`,
    privacy:
        `<h3>آپ کی رازداری</h3>` +
        `<ul><li><strong>کوئی اکاؤنٹ، کوئی لاگ ان، کوئی ذاتی ڈیٹا جمع نہیں۔</strong></li>` +
        `<li><strong>کوئی PII محفوظ نہیں۔</strong> گفتگو صرف موجودہ سیشن کے لیے سرور کی میموری میں رہتی ہے اور کبھی ڈیٹابیس میں لکھی نہیں جاتی۔ "نئی گفتگو" پر یا سرور دوبارہ چلنے پر یہ ختم ہو جاتی ہے۔</li>` +
        `<li><strong>کوئی کوکیز، ٹریکرز یا اینالیٹکس نہیں۔</strong></li>` +
        `<li><strong>فیڈبیک گمنام ہے۔</strong> اگر آپ جواب کو ریٹ کریں تو ہم صرف ووٹ، ٹائم اسٹیمپ اور سوال کا یک طرفہ ہیش محفوظ کرتے ہیں — کبھی خام متن نہیں، کبھی آپ کی شناخت نہیں۔</li></ul>` +
        `<h3>فریق ثالث</h3>` +
        `<p>جواب بنانے کے لیے آپ کا سوال Google Gemini کو بھیجا جاتا ہے، جو Google کی شرائط کے تابع ہے۔ ہم کسی اور فریق ثالث کے ساتھ ڈیٹا شیئر نہیں کرتے۔</p>` +
        `<h3>براہ کرم شیئر نہ کریں</h3>` +
        `<p>کسی کی نجی یا شناختی معلومات (نام، CNIC نمبر، فون نمبر، پتے) درج نہ کریں۔ قانون کے بارے میں عمومی انداز میں سوال کریں۔</p>`,
    terms:
        `<h3>استعمال کی شرائط</h3>` +
        `<ul><li><strong>صرف معلومات — قانونی مشورہ نہیں۔</strong> سائبر لا بوٹ کے استعمال سے وکیل-موکل تعلق قائم نہیں ہوتا۔</li>` +
        `<li><strong>عمل سے پہلے تصدیق کریں۔</strong> قوانین اور دفعہ نمبر بدلتے رہتے ہیں؛ ہمیشہ سروری ذرائع اور کسی مستند وکیل سے تصدیق کریں۔</li>` +
        `<li><strong>کوئی ذمہ داری نہیں۔</strong> یہ ٹول ہیکاتھون ڈیمانسٹریشن کے لیے "جیسا ہے" فراہم کیا گیا ہے۔ اس کے آؤٹ پٹ کی بنیاد پر کیے گئے کسی عمل کی ہم ذمہ داری نہیں لیتے۔</li>` +
        `<li><strong>صرف قانونی استعمال۔</strong> اسے کسی غیر قانونی سرگرمی کی منصوبہ بندی یا چھپانے کے لیے استعمال نہ کریں، اور دوسروں کا نجی ڈیٹا جمع نہ کروائیں۔</li>` +
        `<li><strong>ہنگامی صورتحال۔</strong> اگر آپ یا کوئی اور خطرے میں ہے تو فوراً پولیس (15) یا متعلقہ ہیلپ لائن سے رابطہ کریں — اس بوٹ پر انحصار نہ کریں۔</li></ul>`,
};

// ── Voice input: speech-to-text (mic) ──
function initSpeechInput() {
    if (!micBtn) return;
    // Keep the mic visible on every device; if it can't run here we explain on tap.
    micBtn.addEventListener("click", toggleListening);
}

function toggleListening() {
    if (isListening) { stopListening(); } else { startListening(); }
}

function startListening() {
    if (!SR_SUPPORTED) {
        showToast(t("toast_mic_unsupported"), "error");
        return;
    }
    if (!window.isSecureContext) {
        showToast(t("toast_mic_insecure"), "error");
        return;
    }
    try {
        recognition = new SpeechRec();
    } catch (e) {
        showToast(t("toast_mic_unavailable"), "error");
        return;
    }
    recognition.lang = (currentLang === "ur") ? "ur-PK" : "en-US";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.continuous = false;

    recognition.onstart = () => {
        isListening = true;
        micBtn.classList.add("listening");
        micBtn.title = t("mic_stop");
    };
    recognition.onresult = (e) => {
        const transcript = (e.results[0][0].transcript || "").trim();
        if (!transcript) return;
        const cur = questionInput.value.trim();
        questionInput.value = cur ? (cur + " " + transcript) : transcript;
        autoResize();
        questionInput.focus();
    };
    recognition.onerror = (e) => {
        showToast(micErrorText(e.error), "error");
        micBtn.classList.add("error");
        setTimeout(() => micBtn.classList.remove("error"), 450);
    };
    recognition.onend = () => {
        isListening = false;
        micBtn.classList.remove("listening");
        micBtn.title = t("mic_title");
    };

    try { recognition.start(); } catch (e) { /* already started */ }
}

function stopListening() {
    if (recognition) { try { recognition.stop(); } catch (e) { /* ignore */ } }
}

function micErrorText(code) {
    if (code === "not-allowed" || code === "service-not-allowed") return t("toast_mic_blocked");
    return t("toast_mic_error");
}

// ── Voice output: text-to-speech (listen) ──
function toggleSpeak(btn, text, language) {
    const isUrdu = (language === "ur");

    // Clicking the active button stops playback (local or server audio).
    if (speakingBtn === btn) {
        stopAllSpeech();
        resetSpeakBtn(btn);
        speakingBtn = null;
        return;
    }

    stopAllSpeech();
    if (speakingBtn) resetSpeakBtn(speakingBtn);

    // Urdu: free on-device voice if present; server audio is future scope (off).
    if (isUrdu) {
        const decide = () => {
            if (pickVoice("ur-PK")) speakLocal(btn, text, "ur-PK");
            else if (SERVER_TTS_ENABLED) serverSpeak(btn, text, "ur");
            else showToast(t("toast_tts_coming"));
        };
        if (TTS_SUPPORTED && (!ttsVoices || !ttsVoices.length)) {
            let fired = false;
            const go = () => { if (!fired) { fired = true; decide(); } };
            speechSynthesis.addEventListener("voiceschanged", go, { once: true });
            setTimeout(go, 600);
        } else {
            decide();
        }
        return;
    }

    // English: on-device voice is instant and free.
    if (!TTS_SUPPORTED) {
        if (SERVER_TTS_ENABLED) serverSpeak(btn, text, "en");
        else showToast(t("toast_audio_unsupported"));
        return;
    }
    speakLocal(btn, text, "en-US");
}

function speakLocal(btn, text, langTag) {
    const voice = pickVoice(langTag);
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = langTag;
    if (voice) utter.voice = voice;
    utter.rate = 0.95;
    utter.onend = () => { resetSpeakBtn(btn); if (speakingBtn === btn) speakingBtn = null; };
    utter.onerror = () => { resetSpeakBtn(btn); if (speakingBtn === btn) speakingBtn = null; };

    btn.textContent = t("stop");
    btn.classList.add("speaking");
    speakingBtn = btn;
    speechSynthesis.speak(utter);
}

function resetSpeakBtn(btn) {
    if (!btn) return;
    btn.textContent = t("listen");
    btn.classList.remove("speaking");
}

function stopAllSpeech() {
    if (ttsAudio) {
        try { ttsAudio.pause(); } catch (e) { /* ignore */ }
        ttsAudio = null;
    }
    if (TTS_SUPPORTED) speechSynthesis.cancel();
}

// Play Urdu audio generated server-side by Gemini TTS (works on any browser).
async function serverSpeak(btn, text, lang) {
    lang = lang || "ur";
    btn.textContent = "…";
    btn.classList.add("speaking");
    speakingBtn = btn;
    try {
        const res = await fetch("/api/tts", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: text, language: lang }),
        });
        if (res.status === 429) {
            resetSpeakBtn(btn);
            if (speakingBtn === btn) speakingBtn = null;
            showToast(t("toast_tts_rate"), "error");
            return;
        }
        if (!res.ok) throw new Error("tts http " + res.status);
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        ttsAudio = new Audio(url);
        ttsAudio.onended = () => {
            resetSpeakBtn(btn);
            if (speakingBtn === btn) speakingBtn = null;
            URL.revokeObjectURL(url);
        };
        ttsAudio.onerror = () => {
            resetSpeakBtn(btn);
            if (speakingBtn === btn) speakingBtn = null;
            showToast(t("toast_tts_fail"), "error");
        };
        await ttsAudio.play();
    } catch (e) {
        resetSpeakBtn(btn);
        if (speakingBtn === btn) speakingBtn = null;
        showToast(t("toast_tts_fail"), "error");
    }
}

function pickVoice(lang) {
    const voices = (TTS_SUPPORTED && ttsVoices.length)
        ? ttsVoices
        : (window.speechSynthesis ? speechSynthesis.getVoices() : []);
    if (!voices || !voices.length) return null;
    const base = String(lang).split("-")[0].toLowerCase();
    const norm = (s) => String(s || "").toLowerCase();
    return voices.find((v) => norm(v.lang) === norm(lang)) ||
        voices.find((v) => norm(v.lang).startsWith(base)) ||
        (base === "ur" ? voices.find((v) => norm(v.name).includes("urdu") || v.name.includes("اردو")) : null) ||
        null;
}

// Strip lightweight markdown so the answer reads naturally aloud.
function plainForSpeech(md) {
    return String(md || "")
        .replace(/\*\*(.+?)\*\*/g, "$1")
        .replace(/\*(.+?)\*/g, "$1")
        .replace(/`(.+?)`/g, "$1")
        .replace(/^[\-\*]\s+/gm, "")
        .replace(/^\d+\.\s+/gm, "")
        .replace(/\n{2,}/g, ". ")
        .replace(/\n/g, " ")
        .replace(/\s{2,}/g, " ")
        .trim();
}

// ── Toast (transient, non-blocking notices) ──
function showToast(msg, kind) {
    let t = document.getElementById("toast");
    if (!t) {
        t = document.createElement("div");
        t.id = "toast";
        document.body.appendChild(t);
    }
    t.textContent = msg;
    t.className = "toast show" + (kind ? " toast-" + kind : "");
    clearTimeout(t._timer);
    t._timer = setTimeout(() => { t.className = "toast"; }, 3400);
}

// ── Typing indicator ──
function addTypingIndicator() {
    const id = "typing-" + Date.now();

    const msg = document.createElement("div");
    msg.className = "message ai-message";
    msg.id = id;

    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.innerHTML = '<img src="/static/logo.png" alt="">';

    const bubble = document.createElement("div");
    bubble.className = "bubble typing-bubble";
    bubble.innerHTML = `
        <div class="typing-indicator">
            <span></span><span></span><span></span>
        </div>`;

    msg.appendChild(avatar);
    msg.appendChild(bubble);
    messagesDiv.appendChild(msg);
    scrollToBottom();
    return id;
}

function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

// ── Markdown renderer (lightweight) ──
function renderMarkdown(text) {
    if (!text) return "";

    let html = escapeHTML(text);

    // Bold
    html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    // Italic
    html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");
    // Inline code
    html = html.replace(/`(.+?)`/g, "<code>$1</code>");

    // Unordered lists (lines starting with - or *)
    html = html.replace(/^[\-\*]\s+(.+)$/gm, "<li>$1</li>");
    // Ordered lists (lines starting with 1. 2. etc)
    html = html.replace(/^\d+\.\s+(.+)$/gm, "<li>$1</li>");
    // Wrap consecutive <li> in <ul>
    html = html.replace(/((?:<li>.*<\/li>\n?)+)/g, "<ul>$1</ul>");

    // Paragraphs
    html = html.replace(/\n\n+/g, "</p><p>");
    html = html.replace(/\n/g, "<br>");

    return "<p>" + html + "</p>";
}

// ── Helpers ──
function escapeHTML(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

function isUrdu(text) {
    // Detect Urdu/Arabic script characters
    const urduChars = (text.match(/[\u0600-\u06FF\uFB50-\uFDFF\uFE70-\uFEFF]/g) || []).length;
    return urduChars > text.length * 0.3;
}

function scrollToBottom() {
    requestAnimationFrame(() => {
        chatArea.scrollTo({
            top: chatArea.scrollHeight,
            behavior: "smooth",
        });
    });
}

// ── Start ──
init();
// Safety: re-apply once everything (fonts, async voices) is ready.
window.addEventListener("load", () => applyLanguage());
