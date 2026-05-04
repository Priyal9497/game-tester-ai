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

    // Quick stat elements (Chat tab sidebar)
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

    // New sidebar elements
    const gameTypeVal     = document.getElementById("game-type-val");
    const gameDescVal     = document.getElementById("game-desc-val");
    const verdictVal      = document.getElementById("verdict-val");
    const verdictConfVal  = document.getElementById("verdict-conf-val");

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

    // New dashboard elements
    const dGameType   = document.getElementById("d-game-type");
    const dGameDesc   = document.getElementById("d-game-desc");
    const dVerdictVal = document.getElementById("d-verdict-val");
    const dVerdictConf= document.getElementById("d-verdict-conf");
    const dVerdictReason = document.getElementById("d-verdict-reason");
    const dTestsList  = document.getElementById("d-tests-list");

    // ── State ────────────────────────────────────
    let isTesting        = false;
    let lastMetrics      = null;
    let hasGameContext   = false;   // track if a game has been analyzed
    let currentGameUrl   = null;    // track current game URL

    // ── Helper ───────────────────────────────────
    function getTime() {
        return new Date().toLocaleTimeString([], {
            hour: "2-digit", minute: "2-digit"
        });
    }

    function isUrl(text) {
        return text.startsWith("http://") || text.startsWith("https://");
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
    const lineCtx  = document.getElementById("performanceChart").getContext("2d");
    const lineChart = new Chart(lineCtx, {
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

    // ── Update Input Placeholder ─────────────────
    function updateInputMode() {
        if (hasGameContext) {
            userInput.placeholder =
                `Ask about ${currentGameUrl ? new URL(currentGameUrl).hostname : 'this game'}, or paste a new URL...`;
            sendBtn.querySelector("span").textContent = "Send";
        } else {
            userInput.placeholder = "Paste game URL here... (e.g. https://chromedino.com)";
            sendBtn.querySelector("span").textContent = "Analyze";
        }
    }

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

    function appendChatMessage(text, hasContext = false) {
        const wrapper = document.createElement("div");
        wrapper.className = "message bot-message chat-msg";

        const icon = document.createElement("div");
        icon.className   = "msg-icon";
        // Show different icon if answering about specific game
        icon.textContent = hasContext ? "🎮" : "💬";

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

    function appendLoadingMessage(isUrl = true) {
        const wrapper = document.createElement("div");
        wrapper.className = "message bot-message loading-msg";
        wrapper.id        = "loading-msg";

        const icon = document.createElement("div");
        icon.className   = "msg-icon";
        icon.textContent = "🤖";

        const content = document.createElement("div");
        content.className = "msg-content";

        if (isUrl) {
            content.innerHTML = `
                <p>🚀 Opening browser and running test...</p>
                <p style="font-size:0.8rem;color:var(--text-muted);margin-top:4px;">
                    Analyzing game: detecting type, testing AI, checking fairness...
                </p>
                <div class="loading-dots">
                    <span></span><span></span><span></span>
                </div>
            `;
        } else {
            content.innerHTML = `
                <p>💭 Thinking about your question...</p>
                <div class="loading-dots">
                    <span></span><span></span><span></span>
                </div>
            `;
        }

        wrapper.appendChild(icon);
        wrapper.appendChild(content);
        chatMessages.appendChild(wrapper);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return wrapper;
    }

    // ── Verdict Badge Helper ─────────────────────
    function getVerdictBadge(verdict) {
        const configs = {
            "Human":     { emoji: "👤", color: "#10b981", bg: "rgba(16,185,129,0.15)" },
            "AI/Bot":    { emoji: "🤖", color: "#8b5cf6", bg: "rgba(139,92,246,0.15)" },
            "Uncertain": { emoji: "❓", color: "#eab308", bg: "rgba(234,179,8,0.15)"  }
        };
        return configs[verdict] || configs["Uncertain"];
    }

    // ── Dashboard Update ─────────────────────────
    function updateDashboard(metrics, humanVerdict) {
        lastMetrics = metrics;

        const time_s    = metrics.time_survived || 0;
        const actions   = metrics.actions        || 0;
        const errors    = metrics.errors         || 0;
        const perf      = metrics.performance    || "Low";
        const scores    = metrics.scores         || [0];
        const pageInfo  = metrics.page_info      || {};
        const gameType  = metrics.game_type      || {};
        const aiTests   = metrics.ai_tests_performed || [];
        const aps       = time_s > 0 ? (actions / time_s).toFixed(2) : "0";

        // ── Chat tab sidebar stats ─────────────────────────────
        animateValue(timeVal,    `${time_s}s`);
        animateValue(actionsVal, actions);
        animateValue(apsVal,     aps);
        animateValue(errorsVal,  errors);

        const perfConfig = getPerfConfig(perf);
        perfVal.textContent         = `${perfConfig.emoji} ${perf}`;
        perfVal.style.color         = perfConfig.color;
        perfBarFill.style.width     = perfConfig.barWidth;
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

        // ── Game type in sidebar ───────────────────────────────
        if (gameTypeVal && gameType.primary_type) {
            gameTypeVal.textContent = gameType.primary_type;
        }
        if (gameDescVal && gameType.description) {
            gameDescVal.textContent = gameType.description;
        }

        // ── Human/AI verdict in sidebar ────────────────────────
        if (humanVerdict && verdictVal) {
            const vConfig = getVerdictBadge(humanVerdict.verdict);
            verdictVal.textContent   = `${vConfig.emoji} ${humanVerdict.verdict}`;
            verdictVal.style.color   = vConfig.color;

            if (verdictConfVal) {
                verdictConfVal.textContent = `Confidence: ${humanVerdict.confidence}`;
            }
        }

        // ── Dashboard tab stats ────────────────────────────────
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

        dPageTitle.textContent = pageInfo.title        || "—";
        dCanvas.textContent    = pageInfo.has_canvas
            ? `✅ Yes (${pageInfo.canvas_count || 0})`
            : "❌ No";
        dGameEl.textContent    = pageInfo.has_game_elements
            ? "✅ Detected"
            : "❌ None";
        dPageReady.textContent = pageInfo.page_ready   ? "✅ Yes" : "⚠️ No";
        dUrl.textContent       = metrics.url           || "—";
        dTestedAt.textContent  = metrics.tested_at
            ? new Date(metrics.tested_at).toLocaleString()
            : "—";

        // ── Game type in dashboard ─────────────────────────────
        if (dGameType && gameType.primary_type) {
            dGameType.textContent = `${gameType.primary_type} (${gameType.confidence} confidence)`;
        }
        if (dGameDesc && gameType.description) {
            dGameDesc.textContent = gameType.description;
        }

        // ── Human/AI verdict in dashboard ──────────────────────
        if (humanVerdict && dVerdictVal) {
            const vConfig = getVerdictBadge(humanVerdict.verdict);
            dVerdictVal.textContent  = `${vConfig.emoji} ${humanVerdict.verdict}`;
            dVerdictVal.style.color  = vConfig.color;
            dVerdictVal.style.background = vConfig.bg;
            dVerdictVal.style.padding    = "4px 12px";
            dVerdictVal.style.borderRadius = "20px";
            dVerdictVal.style.fontWeight   = "700";
        }
        if (humanVerdict && dVerdictConf) {
            dVerdictConf.textContent = `Confidence: ${humanVerdict.confidence}`;
        }
        if (humanVerdict && dVerdictReason) {
            dVerdictReason.textContent = humanVerdict.reason || "";
        }

        // ── AI Tests list in dashboard ─────────────────────────
        if (dTestsList && aiTests.length > 0) {
            dTestsList.innerHTML = aiTests.map(test => `
                <div class="ai-test-item">
                    <span class="test-check">✓</span>
                    <span class="test-name">${test}</span>
                </div>
            `).join("");
        }

        // ── Line Chart ─────────────────────────────────────────
        const labels = scores.map((_, i) => `Step ${i}`);
        lineChart.data.labels           = labels;
        lineChart.data.datasets[0].data = scores;
        lineChart.update("active");

        // ── Radar Chart ────────────────────────────────────────
        const timeScore      = Math.min((time_s / 30) * 100, 100);
        const actionScore    = Math.min((actions / 25) * 100, 100);
        const speedScore     = Math.min(parseFloat(aps) * 40, 100);
        const stabilityScore = Math.max(100 - (errors * 20), 0);
        const scoreVal       = scores.length > 1
            ? Math.min((scores[scores.length - 1] / 200) * 100, 100)
            : 0;

        radarChart.data.datasets[0].data = [
            timeScore, actionScore, speedScore, stabilityScore, scoreVal
        ];
        radarChart.update("active");
    }

    function getPerfConfig(perf) {
        const configs = {
            "High":    { emoji: "🟢", color: "#22c55e", barWidth: "90%", badgeClass: "good"     },
            "Medium":  { emoji: "🟡", color: "#eab308", barWidth: "55%", badgeClass: "warn"     },
            "Low":     { emoji: "🔴", color: "#ef4444", barWidth: "25%", badgeClass: "bad"      },
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

    // ── Handle Send ──────────────────────────────
    async function handleSend() {
        if (isTesting) {
            showToast("Please wait for current operation...", "info");
            return;
        }

        const text = userInput.value.trim();

        if (!text) {
            if (hasGameContext) {
                showToast("Ask a question about the game", "error");
            } else {
                showToast("Please enter a game URL", "error");
            }
            userInput.focus();
            return;
        }

        // ── Determine if URL or chat question ─────────────────
        const inputIsUrl = isUrl(text);

        // If no game context yet and not a URL - prompt user
        if (!hasGameContext && !inputIsUrl) {
            showToast("Please enter a game URL first to analyze", "info");
            appendChatMessage(
                "Please paste a game URL first so I can analyze it!\n\n" +
                "Example: https://chromedino.com\n\n" +
                "After analysis, you can ask me anything about the game! 🎮"
            );
            userInput.value = "";
            return;
        }

        isTesting          = true;
        sendBtn.disabled   = true;
        userInput.disabled = true;

        const messageToSend = text;
        userInput.value     = "";

        appendMessage(messageToSend, "user");

        // Show different loading based on URL vs question
        const loadingMsg = appendLoadingMessage(inputIsUrl);

        console.log("Sending:", messageToSend);

        const controller = new AbortController();
        const timeoutId  = setTimeout(
            () => controller.abort(),
            inputIsUrl ? 120000 : 30000  // 2min for URL, 30s for chat
        );

        try {
            const response = await fetch("/test", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Accept":       "application/json"
                },
                body:   JSON.stringify({ message: messageToSend }),
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

            // ── Handle response types ──────────────────────────
            if (data.type === "error") {
                appendMessage(data.reply, "bot", "error-msg");
                showToast("Error occurred", "error");

            } else if (data.type === "chat") {
                // ── Chat response (follow-up question) ────────
                appendChatMessage(data.reply, data.has_context || false);
                showToast("AI responded", "info");

                // Update context state
                if (data.game_context) {
                    hasGameContext = true;
                }

            } else if (data.type === "test_result") {
                // ── Test result response ───────────────────────
                const humanVerdict = data.human_verdict || null;
                const gameContext  = data.game_context  || null;

                if (data.metrics && data.metrics.performance === "NotGame") {
                    appendMessage(data.reply, "bot", "error-msg");
                    showToast("This doesn't appear to be a game link", "error");
                    hasGameContext  = false;
                    currentGameUrl  = null;

                } else {
                    appendMessage(data.reply, "bot", "result-msg");
                    updateDashboard(data.metrics, humanVerdict);
                    showToast("Analysis complete! You can now ask questions.", "success");

                    // ── Update state - game is now analyzed ───
                    hasGameContext  = true;
                    currentGameUrl  = data.metrics?.url || messageToSend;
                    updateInputMode();

                    // ── Show game info toast ───────────────────
                    const gt = data.metrics?.game_type;
                    if (gt && gt.primary_type) {
                        setTimeout(() => {
                            showToast(`Game detected: ${gt.primary_type}`, "info");
                        }, 1000);
                    }

                    // ── Show verdict toast ─────────────────────
                    if (humanVerdict) {
                        setTimeout(() => {
                            const emoji = humanVerdict.verdict === "Human" ? "👤" : "🤖";
                            showToast(
                                `${emoji} Played by: ${humanVerdict.verdict} (${humanVerdict.confidence} confidence)`,
                                humanVerdict.verdict === "Human" ? "success" : "info"
                            );
                        }, 2000);
                    }

                    // ── Auto-switch to dashboard after delay ───
                    setTimeout(() => {
                        const dashboardTab = document.querySelector('[data-tab="dashboard"]');
                        if (dashboardTab) {
                            tabs.forEach(t   => t.classList.remove("active"));
                            panels.forEach(p => p.classList.remove("active"));
                            dashboardTab.classList.add("active");
                            document.getElementById("tab-dashboard").classList.add("active");
                        }
                    }, 2500);
                }

            } else {
                // ── Fallback ───────────────────────────────────
                appendMessage(
                    data.reply || "Operation completed.",
                    "bot", "result-msg"
                );
                if (data.metrics) {
                    updateDashboard(data.metrics, data.human_verdict);
                }
                showToast("Done!", "success");
            }

        } catch (error) {
            clearTimeout(timeoutId);
            console.error("Fetch error:", error);

            if (loadingMsg && loadingMsg.parentNode) {
                loadingMsg.remove();
            }

            if (error.name === "AbortError") {
                appendMessage(
                    inputIsUrl
                        ? "Request timed out after 2 minutes. The test took too long."
                        : "Request timed out. Please try again.",
                    "bot", "error-msg"
                );
                showToast("Request timed out", "error");

            } else if (
                error.message.includes("Failed to fetch") ||
                error.message.includes("NetworkError")
            ) {
                appendMessage(
                    "Cannot connect to server. Make sure the backend is running.",
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

        // Reset game context on clear
        hasGameContext = false;
        currentGameUrl = null;
        updateInputMode();

        showToast("Chat cleared", "info");
    });

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
                const el     = document.createElement("div");
                el.className = `history-item ${item.success ? "success" : "failed"}`;

                const time = item.timestamp
                    ? new Date(item.timestamp).toLocaleString()
                    : "—";

                const perf       = item.metrics?.performance || null;
                const verdict    = item.human_verdict?.verdict || null;
                const gameType   = item.metrics?.game_type?.primary_type || null;
                const perfBadge  = perf
                    ? `<span class="hi-badge badge-${perf.toLowerCase()}">${perf}</span>`
                    : "";
                const verdictBadge = verdict
                    ? `<span class="hi-badge verdict-badge">${
                          verdict === "Human" ? "👤" : "🤖"
                      } ${verdict}</span>`
                    : "";
                const typeBadge  = gameType
                    ? `<span class="hi-badge type-badge">🎮 ${gameType}</span>`
                    : "";

                el.innerHTML = `
                    <div class="hi-left">
                        <span class="hi-url">${escapeHtml(item.url)}</span>
                        <span class="hi-meta">
                            ${time}
                            ${item.metrics
                                ? ` • ${item.metrics.time_survived}s • ${item.metrics.actions} actions`
                                : ""}
                            ${item.error ? ` • Error: ${item.error}` : ""}
                        </span>
                        <div class="hi-badges-row">
                            ${typeBadge}
                        </div>
                    </div>
                    <div class="hi-right">
                        ${verdictBadge}
                        ${perfBadge}
                        <span class="hi-badge ${item.success ? "badge-success" : "badge-failed"}">
                            ${item.success ? "✅ Passed" : "❌ Failed"}
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
        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        const icons = { success: "✅", error: "❌", info: "ℹ️" };
        toast.innerHTML = `
            <span>${icons[type] || "ℹ️"}</span>
            <span>${message}</span>
        `;
        toastContainer.appendChild(toast);
        setTimeout(() => {
            toast.style.animation = "toastOut 0.3s ease forwards";
            setTimeout(() => toast.remove(), 300);
        }, 3500);
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
    updateInputMode();
    showToast("TestProbe AI v3.0 ready!", "success");
    addInteractiveEffects();

});