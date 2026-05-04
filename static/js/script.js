/* ════════════════════════════════════════════════
   TestProbe AI - Main Script v3.0
   ════════════════════════════════════════════════ */

document.addEventListener("DOMContentLoaded", () => {

    // ── DOM Elements ─────────────────────────────
    const chatMessages      = document.getElementById("chat-messages");
    const userInput         = document.getElementById("user-input");
    const sendBtn           = document.getElementById("send-btn");
    const clearChatBtn      = document.getElementById("clear-chat-btn");
    const toastContainer    = document.getElementById("toast-container");
    const historyList       = document.getElementById("history-list");
    const totalTestsEl      = document.getElementById("total-tests");
    const refreshHistoryBtn = document.getElementById("refresh-history-btn");

    // Quick stat elements (Chat tab)
    const timeVal         = document.getElementById("time-val");
    const actionsVal      = document.getElementById("actions-val");
    const apsVal          = document.getElementById("aps-val");
    const errorsVal       = document.getElementById("errors-val");
    const perfVal         = document.getElementById("perf-val");
    const perfBarFill     = document.getElementById("perf-bar-fill");
    const statusIndicator = document.getElementById("status-indicator");
    const canvasVal       = document.getElementById("canvas-val");
    const gameElVal       = document.getElementById("game-el-val");
    const testedAtVal     = document.getElementById("tested-at-val");

    // Dashboard elements
    const dTimeVal    = document.getElementById("d-time-val");
    const dActionsVal = document.getElementById("d-actions-val");
    const dApsVal     = document.getElementById("d-aps-val");
    const dErrorsVal  = document.getElementById("d-errors-val");
    const dPerfVal    = document.getElementById("d-perf-val");
    const dPerfCard   = document.getElementById("d-perf-card");
    const chartBadge  = document.getElementById("chart-badge");
    const dPageTitle  = document.getElementById("d-page-title");
    const dCanvas     = document.getElementById("d-canvas");
    const dGameEl     = document.getElementById("d-game-el");
    const dPageReady  = document.getElementById("d-page-ready");
    const dUrl        = document.getElementById("d-url");
    const dTestedAt   = document.getElementById("d-tested-at");

    // ── State ────────────────────────────────────
    let isTesting  = false;
    let lastMetrics = null;

    // ── Helper ───────────────────────────────────
    function getTime() {
        return new Date().toLocaleTimeString([], {
            hour: "2-digit", minute: "2-digit"
        });
    }

    // ── Tab Navigation ───────────────────────────
    const tabs   = document.querySelectorAll(".nav-tab");
    const panels = document.querySelectorAll(".tab-panel");

    tabs.forEach(tab => {
        tab.addEventListener("click", () => {
            const target = tab.dataset.tab;

            tabs.forEach(t   => t.classList.remove("active"));
            panels.forEach(p => p.classList.remove("active"));

            tab.classList.add("active");
            document.getElementById(`tab-${target}`).classList.add("active");

            if (target === "history") loadHistory();
        });
    });

    // ── Chart.js Setup ───────────────────────────
    const chartDefaults = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                labels: {
                    color: "#8899bb",
                    font: { family: "Inter", size: 11 }
                }
            }
        }
    };

    // Line Chart
    const lineCtx   = document.getElementById("performanceChart").getContext("2d");
    const lineChart  = new Chart(lineCtx, {
        type: "line",
        data: {
            labels: [],
            datasets: [{
                label: "Score Over Time",
                data: [],
                borderColor: "#38bdf8",
                backgroundColor: "rgba(56,189,248,0.08)",
                borderWidth: 2.5,
                tension: 0.4,
                fill: true,
                pointBackgroundColor: "#0ea5e9",
                pointRadius: 4,
                pointHoverRadius: 6
            }]
        },
        options: {
            ...chartDefaults,
            scales: {
                y: {
                    beginAtZero: true,
                    grid:  { color: "rgba(255,255,255,0.04)" },
                    ticks: { color: "#8899bb", font: { size: 11 } }
                },
                x: {
                    grid:  { color: "rgba(255,255,255,0.04)" },
                    ticks: { color: "#8899bb", font: { size: 11 } }
                }
            }
        }
    });

    // Radar Chart
    const radarCtx  = document.getElementById("radarChart").getContext("2d");
    const radarChart = new Chart(radarCtx, {
        type: "radar",
        data: {
            labels: ["Time", "Actions", "Speed", "Stability", "Score"],
            datasets: [{
                label: "Performance",
                data: [0, 0, 0, 0, 0],
                borderColor: "#38bdf8",
                backgroundColor: "rgba(56,189,248,0.1)",
                borderWidth: 2,
                pointBackgroundColor: "#0ea5e9",
                pointRadius: 4
            }]
        },
        options: {
            ...chartDefaults,
            scales: {
                r: {
                    beginAtZero: true,
                    max: 100,
                    grid:        { color: "rgba(255,255,255,0.06)" },
                    angleLines:  { color: "rgba(255,255,255,0.06)" },
                    ticks:       { display: false },
                    pointLabels: {
                        color: "#8899bb",
                        font:  { size: 11 }
                    }
                }
            }
        }
    });

    // ── Message Functions ────────────────────────
    function appendMessage(text, type = "bot", extraClass = "") {
        const isUser  = type === "user";
        const wrapper = document.createElement("div");
        wrapper.className = `message ${isUser ? "user-message" : "bot-message"} ${extraClass}`;

        const icon = document.createElement("div");
        icon.className   = "msg-icon";
        icon.textContent = isUser ? "👤" : "🤖";

        const content = document.createElement("div");
        content.className = "msg-content";

        const textEl = document.createElement("p");
        textEl.style.whiteSpace = "pre-wrap";
        textEl.textContent      = text;

        const timeEl = document.createElement("span");
        timeEl.className   = "msg-time";
        timeEl.textContent = getTime();

        content.appendChild(textEl);
        content.appendChild(timeEl);
        wrapper.appendChild(icon);
        wrapper.appendChild(content);

        chatMessages.appendChild(wrapper);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return wrapper;
    }

    function appendChatMessage(text) {
        const wrapper = document.createElement("div");
        wrapper.className = "message bot-message chat-msg";

        const icon = document.createElement("div");
        icon.className   = "msg-icon";
        icon.textContent = "💬";

        const content = document.createElement("div");
        content.className = "msg-content";

        const textEl = document.createElement("p");
        textEl.style.whiteSpace = "pre-wrap";
        textEl.textContent      = text;

        const timeEl = document.createElement("span");
        timeEl.className   = "msg-time";
        timeEl.textContent = getTime();

        content.appendChild(textEl);
        content.appendChild(timeEl);
        wrapper.appendChild(icon);
        wrapper.appendChild(content);

        chatMessages.appendChild(wrapper);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function appendLoadingMessage() {
        const wrapper = document.createElement("div");
        wrapper.className = "message bot-message loading-msg";
        wrapper.id        = "loading-msg";

        const icon = document.createElement("div");
        icon.className   = "msg-icon";
        icon.textContent = "🤖";

        const content = document.createElement("div");
        content.className = "msg-content";
        content.innerHTML = `
            <p>🚀 Opening browser and running test...</p>
            <p style="font-size:0.8rem;color:var(--text-muted);margin-top:4px;">
                This may take 15-30 seconds. Please wait.
            </p>
            <div class="loading-dots">
                <span></span><span></span><span></span>
            </div>
        `;

        wrapper.appendChild(icon);
        wrapper.appendChild(content);
        chatMessages.appendChild(wrapper);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return wrapper;
    }

    // ── Dashboard Update ─────────────────────────
    function updateDashboard(metrics) {
        lastMetrics = metrics;

        const time_s   = metrics.time_survived || 0;
        const actions  = metrics.actions        || 0;
        const errors   = metrics.errors         || 0;
        const perf     = metrics.performance    || "Low";
        const scores   = metrics.scores         || [0];
        const pageInfo = metrics.page_info      || {};
        const aps      = time_s > 0
            ? (actions / time_s).toFixed(2)
            : "0";

        // Chat tab stats
        animateValue(timeVal,    `${time_s}s`);
        animateValue(actionsVal, actions);
        animateValue(apsVal,     aps);
        animateValue(errorsVal,  errors);

        const perfConfig = getPerfConfig(perf);
        perfVal.textContent       = `${perfConfig.emoji} ${perf}`;
        perfVal.style.color       = perfConfig.color;
        perfBarFill.style.width   = perfConfig.barWidth;
        perfBarFill.style.background = perfConfig.color;

        statusIndicator.className = "status-indicator";
        statusIndicator.classList.add(`status-${perf.toLowerCase()}`);

        canvasVal.textContent   = pageInfo.has_canvas
            ? `✅ Yes (${pageInfo.canvas_count || 0})`
            : "❌ No";
        gameElVal.textContent   = pageInfo.has_game_elements
            ? "✅ Detected"
            : "❌ None";
        testedAtVal.textContent = metrics.tested_at
            ? new Date(metrics.tested_at).toLocaleTimeString()
            : "—";

        // Dashboard tab stats
        animateValue(dTimeVal,    `${time_s}s`);
        animateValue(dActionsVal, actions);
        animateValue(dApsVal,     aps);
        animateValue(dErrorsVal,  errors);
        animateValue(dPerfVal,    `${perfConfig.emoji} ${perf}`);
        dPerfVal.style.color = perfConfig.color;

        dPerfCard.className = "metric-big-card perf-metric";
        dPerfCard.classList.add(`${perf.toLowerCase()}-perf`);

        chartBadge.textContent = perf;
        chartBadge.className   = `chart-badge ${perfConfig.badgeClass}`;

        dPageTitle.textContent = pageInfo.title       || "—";
        dCanvas.textContent    = pageInfo.has_canvas
            ? `✅ Yes (${pageInfo.canvas_count || 0})`
            : "❌ No";
        dGameEl.textContent    = pageInfo.has_game_elements
            ? "✅ Detected"
            : "❌ None";
        dPageReady.textContent = pageInfo.page_ready  ? "✅ Yes" : "⚠️ No";
        dUrl.textContent       = metrics.url          || "—";
        dTestedAt.textContent  = metrics.tested_at
            ? new Date(metrics.tested_at).toLocaleString()
            : "—";

        // Line Chart
        const labels = scores.map((_, i) => `Step ${i}`);
        lineChart.data.labels              = labels;
        lineChart.data.datasets[0].data    = scores;
        lineChart.update("active");

        // Radar Chart
        const timeScore     = Math.min((time_s / 30) * 100, 100);
        const actionScore   = Math.min((actions / 25) * 100, 100);
        const speedScore    = Math.min(parseFloat(aps) * 40, 100);
        const stabilityScore = Math.max(100 - (errors * 20), 0);
        const scoreVal      = scores.length > 1
            ? Math.min((scores[scores.length - 1] / 200) * 100, 100)
            : 0;

        radarChart.data.datasets[0].data = [
            timeScore, actionScore, speedScore, stabilityScore, scoreVal
        ];
        radarChart.update("active");
    }

    function getPerfConfig(perf) {
        const configs = {
            "High":    { emoji: "🟢", color: "#22c55e", barWidth: "90%", badgeClass: "good" },
            "Medium":  { emoji: "🟡", color: "#eab308", barWidth: "55%", badgeClass: "warn" },
            "Low":     { emoji: "🔴", color: "#ef4444", barWidth: "25%", badgeClass: "bad" },
            "NotGame": { emoji: "❌", color: "#a78bfa", barWidth: "0%",  badgeClass: "not-game" }
        };
        return configs[perf] || configs["Low"];
    }

    function animateValue(el, value) {
        if (!el) return;
        el.textContent = value;
        el.classList.remove("metric-updated");
        void el.offsetWidth;
        el.classList.add("metric-updated");
    }

    // ── URL Validation ───────────────────────────
    function isValidUrl(str) {
        try {
            const url = new URL(str);
            return url.protocol === "http:" || url.protocol === "https:";
        } catch {
            return false;
        }
    }

    // ── Handle Send ──────────────────────────────
    async function handleSend() {
        if (isTesting) {
            showToast("Test already running. Please wait...", "info");
            return;
        }

        const text = userInput.value.trim();

        if (!text) {
            showToast("Please enter a game URL", "error");
            userInput.focus();
            return;
        }

        if (!text.startsWith("http://") && !text.startsWith("https://")) {
            showToast("Please enter a valid URL starting with https://", "error");
            userInput.style.borderColor = "#ef4444";
            setTimeout(() => { userInput.style.borderColor = ""; }, 2000);
            return;
        }

        if (!isValidUrl(text)) {
            showToast("Please enter a valid URL (https://...)", "error");
            userInput.style.borderColor = "#ef4444";
            setTimeout(() => { userInput.style.borderColor = ""; }, 2000);
            return;
        }

        isTesting          = true;
        sendBtn.disabled   = true;
        userInput.disabled = true;

        const urlToTest  = text;
        userInput.value  = "";

        appendMessage(urlToTest, "user");
        const loadingMsg = appendLoadingMessage();

        console.log("Sending request for:", urlToTest);

        const controller = new AbortController();
        const timeoutId  = setTimeout(() => controller.abort(), 120000);

        try {
            const response = await fetch("/test", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Accept":       "application/json"
                },
                body:   JSON.stringify({ message: urlToTest }),
                signal: controller.signal
            });

            clearTimeout(timeoutId);
            console.log("Response status:", response.status);

            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }

            const data = await response.json();
            console.log("Data received:", data);

            if (loadingMsg && loadingMsg.parentNode) {
                loadingMsg.remove();
            }

            if (data.type === "error") {
                appendMessage(data.reply, "bot", "error-msg");
                showToast("Error occurred", "error");

            } else if (data.type === "chat") {
                appendChatMessage(data.reply);
                showToast("AI responded", "info");

            } else if (data.type === "test_result") {
                if (data.metrics && data.metrics.performance === "NotGame") {
                    appendMessage(data.reply, "bot", "error-msg");
                    showToast("This doesn't appear to be a game link", "error");
                } else {
                    appendMessage(data.reply, "bot", "result-msg");
                    updateDashboard(data.metrics);
                    showToast("Test completed successfully!", "success");

                    setTimeout(() => {
                        const dashboardTab = document.querySelector('[data-tab="dashboard"]');
                        if (dashboardTab) {
                            tabs.forEach(t   => t.classList.remove("active"));
                            panels.forEach(p => p.classList.remove("active"));
                            dashboardTab.classList.add("active");
                            document.getElementById("tab-dashboard").classList.add("active");
                        }
                    }, 1500);
                }
            } else {
                appendMessage(
                    data.reply || "Test completed. Check dashboard for results.",
                    "bot",
                    "result-msg"
                );
                if (data.metrics) {
                    updateDashboard(data.metrics);
                }
                showToast("Test completed!", "success");
            }

        } catch (error) {
            clearTimeout(timeoutId);
            console.error("Fetch error:", error);

            if (loadingMsg && loadingMsg.parentNode) {
                loadingMsg.remove();
            }

            if (error.name === "AbortError") {
                appendMessage(
                    "Request timed out after 2 minutes. The test took too long.",
                    "bot", "error-msg"
                );
                showToast("Request timed out", "error");

            } else if (
                error.message.includes("Failed to fetch") ||
                error.message.includes("NetworkError")
            ) {
                appendMessage(
                    "Cannot connect to the server. Make sure the backend is running.",
                    "bot", "error-msg"
                );
                showToast("Connection error", "error");

            } else {
                appendMessage(`Error: ${error.message}`, "bot", "error-msg");
                showToast("Error occurred", "error");
            }

        } finally {
            isTesting          = false;
            sendBtn.disabled   = false;
            userInput.disabled = false;
            userInput.focus();
        }
    }

    // ── Event Listeners ──────────────────────────
    sendBtn.addEventListener("click", handleSend);

    userInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
        if (e.key === "Escape") {
            userInput.value = "";
        }
    });

    clearChatBtn.addEventListener("click", () => {
        const msgs = chatMessages.querySelectorAll(".message:not(.welcome-msg)");
        msgs.forEach(m => m.remove());
        showToast("Chat cleared", "info");
    });

    // Input focus scale effect
    userInput.addEventListener("focus", () => {
        userInput.parentElement.style.transform = "scale(1.02)";
    });
    userInput.addEventListener("blur", () => {
        userInput.parentElement.style.transform = "scale(1)";
    });

    // ── History ──────────────────────────────────
    async function loadHistory() {
        try {
            const res = await fetch("/history");
            if (!res.ok) return;
            const data = await res.json();

            totalTestsEl.textContent = `${data.total} tests run`;
            historyList.innerHTML    = "";

            if (!data.history || data.history.length === 0) {
                historyList.innerHTML = `
                    <div class="history-empty">
                        <div class="empty-icon">📋</div>
                        <p>No tests run yet</p>
                        <p class="empty-sub">Run your first test in the Chat tab</p>
                    </div>
                `;
                return;
            }

            [...data.history].reverse().forEach(item => {
                const el   = document.createElement("div");
                el.className = `history-item ${item.success ? "success" : "failed"}`;

                const time = item.timestamp
                    ? new Date(item.timestamp).toLocaleString()
                    : "—";

                const perf      = item.metrics?.performance || null;
                const perfBadge = perf
                    ? `<span class="hi-badge badge-${perf.toLowerCase()}">${perf}</span>`
                    : "";

                el.innerHTML = `
                    <div class="hi-left">
                        <span class="hi-url">${escapeHtml(item.url)}</span>
                        <span class="hi-meta">
                            ${time}
                            ${item.metrics
                                ? ` • Time: ${item.metrics.time_survived}s • Actions: ${item.metrics.actions}`
                                : ""}
                            ${item.error ? ` • Error: ${item.error}` : ""}
                        </span>
                    </div>
                    <div class="hi-right">
                        ${perfBadge}
                        <span class="hi-badge ${item.success ? "badge-success" : "badge-failed"}">
                            ${item.success ? "Passed" : "Failed"}
                        </span>
                    </div>
                `;
                historyList.appendChild(el);
            });

        } catch (err) {
            console.error("History load error:", err);
        }
    }

    function escapeHtml(text) {
        const div      = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    refreshHistoryBtn.addEventListener("click", () => {
        loadHistory();
        showToast("History refreshed", "info");
    });

    // ── Toast Notifications ──────────────────────
    function showToast(message, type = "info") {
        if (!toastContainer) return;

        const toast  = document.createElement("div");
        toast.className = `toast ${type}`;

        const icons  = { success: "✅", error: "❌", info: "ℹ️" };
        toast.innerHTML = `
            <span>${icons[type] || "ℹ️"}</span>
            <span>${message}</span>
        `;

        toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = "toastOut 0.3s ease forwards";
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    // ── Interactive Effects ──────────────────────
    function addInteractiveEffects() {
        const cards = document.querySelectorAll(
            ".metric-big-card, .stat-card, .pi-item, .history-item"
        );
        cards.forEach(card => {
            card.addEventListener("mouseenter", () => {
                card.style.transition = "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)";
            });
        });
    }

    // ── Init ─────────────────────────────────────
    userInput.focus();
    showToast("TestProbe AI ready!", "success");
    addInteractiveEffects();

}); // ← Single DOMContentLoaded - no duplicates