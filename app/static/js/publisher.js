const publisherContext = window.publisherPageContext || {};
const debugPanel = document.querySelector("[data-debug-panel]");
const debugBody = document.querySelector("[data-debug-body]");
const debugToggle = document.querySelector("[data-debug-toggle]");
const debugEntries = new Map();
const slotNodes = Array.from(document.querySelectorAll("[data-ad-slot]"));
const highlightedSlotId = publisherContext.highlightSlot || "";

function toggleDebugPanel() {
    if (!debugPanel) {
        return;
    }
    debugPanel.classList.toggle("is-open");
}

function focusHighlightedSlot() {
    if (!highlightedSlotId) {
        return;
    }

    const highlightedSlot = slotNodes.find(slotNode => slotNode.dataset.slotId === highlightedSlotId);
    if (!highlightedSlot) {
        return;
    }

    window.setTimeout(() => {
        highlightedSlot.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 120);
}

function clientDevice() {
    return window.innerWidth <= 820 ? "mobile" : "desktop";
}

function shouldRequestSlot(slotNode, device) {
    const slotPosition = slotNode.dataset.position || "";
    const slotSize = slotNode.dataset.size || "";
    if (slotPosition === "video") {
        return false;
    }
    if (device === "mobile" && slotSize === "728x90") {
        return false;
    }
    return true;
}

function ensureDebugEntry(slotId) {
    let entry = debugEntries.get(slotId);
    if (entry) {
        return entry;
    }

    entry = document.createElement("article");
    entry.className = "publisher-debug-card";
    entry.dataset.slotId = slotId;
    entry.innerHTML = `
        <div class="publisher-debug-row">
            <strong>${slotId}</strong>
            <span class="soft-chip">Pending</span>
        </div>
        <div class="publisher-debug-meta">Waiting for request.</div>
    `;

    if (debugBody && debugBody.querySelector(".empty-state")) {
        debugBody.innerHTML = "";
    }
    debugBody?.appendChild(entry);
    debugEntries.set(slotId, entry);
    return entry;
}

function renderCandidateMarkup(candidates) {
    if (!candidates || !candidates.length) {
        return "";
    }

    return `
        <div class="publisher-debug-candidates">
            ${candidates.map(candidate => `
                <div class="publisher-debug-candidate">
                    <div class="publisher-debug-row">
                        <strong>${candidate.lineItem}</strong>
                        <span class="soft-chip ${candidate.eligible ? "soft-chip-success" : ""}">P${candidate.priority} - W${candidate.weight}</span>
                    </div>
                    <div class="publisher-debug-meta">${candidate.reason || "No reason provided."}</div>
                    ${candidate.rejectedChecks && candidate.rejectedChecks.length ? `
                        <ul class="publisher-debug-list">
                            ${candidate.rejectedChecks.map(reason => `<li>${reason}</li>`).join("")}
                        </ul>
                    ` : ""}
                </div>
            `).join("")}
        </div>
    `;
}

function updateDebugEntry(slotId, state) {
    const entry = ensureDebugEntry(slotId);
    const impressionState = state.impressionFired ? "Yes" : "No";
    const diagnosticsLink = state.auctionUrl
        ? `<div><span>Diagnostics</span><strong><a href="${state.auctionUrl}" target="_blank" rel="noopener">Open request</a></strong></div>`
        : "";
    const chipLabel = state.filled ? "Creative" : state.responseType === "house" ? "House" : "No Fill";
    entry.innerHTML = `
        <div class="publisher-debug-row">
            <strong>${state.requestedSlot || slotId}</strong>
            <span class="soft-chip ${state.filled ? "soft-chip-success" : "soft-chip-strong"}">${chipLabel}</span>
        </div>
        <div class="publisher-debug-meta">
            Size ${state.requestedSize || "-"} - Device ${state.device || "-"} - Impression fired ${impressionState}
        </div>
        <div class="publisher-debug-details">
            <div><span>Line item</span><strong>${state.lineItem || "None"}</strong></div>
            <div><span>Creative</span><strong>${state.creative || "None"}</strong></div>
            <div><span>Reason</span><strong>${state.reason || "Waiting for response."}</strong></div>
            ${diagnosticsLink}
        </div>
        ${renderCandidateMarkup(state.candidates)}
    `;
}

function rewriteTrackedLinks(node, clickUrl) {
    if (!clickUrl || !node) {
        return;
    }
    node.querySelectorAll("a[href]").forEach(anchor => {
        anchor.href = clickUrl;
    });
}

function renderedCreativeNode(stage, response) {
    if (!stage || !response || !response.filled) {
        return null;
    }
    return stage.querySelector(`[data-rendered-creative][data-request-id="${response.request_id}"][data-creative-id="${response.creative_id}"]`);
}

function fireImpressionWhenVisible(slotNode, response, state) {
    const stage = slotNode.querySelector("[data-slot-stage]");
    if (!renderedCreativeNode(stage, response)) {
        return;
    }

    const markFired = () => {
        state.impressionFired = true;
        updateDebugEntry(response.slot_id || slotNode.dataset.slotId, state);
    };

    const fire = () => {
        const requestOptions = response.impression_url
            ? {}
            : {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(response.impression_payload),
            };
        const impressionTarget = response.impression_url || "/track/impression";
        fetch(impressionTarget, requestOptions)
            .then(impressionResponse => impressionResponse.json())
            .then(result => {
                if (result.ok) {
                    markFired();
                }
            })
            .catch(() => {});
    };

    if (!("IntersectionObserver" in window)) {
        fire();
        return;
    }

    const observer = new IntersectionObserver(entries => {
        entries.forEach(entry => {
            if (entry.isIntersecting && entry.intersectionRatio >= 0.6) {
                observer.disconnect();
                fire();
            }
        });
    }, { threshold: [0.6] });

    observer.observe(slotNode);
}

function renderSlot(slotNode, response) {
    const stage = slotNode.querySelector("[data-slot-stage]");
    if (!stage) {
        return;
    }

    stage.innerHTML = response.html;
    rewriteTrackedLinks(stage, response.click_url);

    if (response.filled && !renderedCreativeNode(stage, response)) {
        stage.innerHTML = `
            <div class="publisher-slot-placeholder">
                <strong>Render validation failed</strong>
                <span>The winning creative markup did not mount correctly.</span>
            </div>
        `;
        updateDebugEntry(slotNode.dataset.slotId, {
            filled: false,
            responseType: "error",
            requestedSlot: slotNode.dataset.slotId,
            requestedSize: slotNode.dataset.size,
            lineItem: null,
            creative: null,
            reason: "Winning creative did not render into the slot.",
            device: clientDevice(),
            impressionFired: false,
            auctionUrl: response.auction_url,
            candidates: [],
        });
        return;
    }

    const debug = response.debug || {};
    const state = {
        filled: Boolean(response.filled),
        responseType: response.response_type,
        requestedSlot: debug.requested_slot || slotNode.dataset.slotId,
        requestedSize: debug.requested_size || slotNode.dataset.size,
        lineItem: debug.selected_line_item,
        creative: debug.selected_creative,
        reason: debug.reason,
        device: debug.device || clientDevice(),
        impressionFired: false,
        auctionUrl: response.auction_url,
        candidates: (debug.candidates || []).map(candidate => ({
            lineItem: candidate.line_item,
            priority: candidate.priority,
            weight: candidate.weight,
            eligible: candidate.eligible,
            reason: candidate.reason,
            rejectedChecks: candidate.rejected_checks || [],
        })),
    };
    updateDebugEntry(slotNode.dataset.slotId, state);

    if (response.filled && (response.impression_payload || response.impression_url)) {
        fireImpressionWhenVisible(slotNode, response, state);
    }
}

function loadSlot(slotNode) {
    const device = clientDevice();
    if (!shouldRequestSlot(slotNode, device)) {
        slotNode.classList.add("slot-skipped");
        slotNode.querySelector("[data-slot-stage]").innerHTML = `
            <div class="publisher-slot-placeholder">
                <strong>Skipped for ${device}</strong>
                <span>${slotNode.dataset.slotId}</span>
            </div>
        `;
        return;
    }

    const params = new URLSearchParams({
        ad_unit_code: slotNode.dataset.slotId || "",
        slot_id: slotNode.dataset.slotId || "",
        page: slotNode.dataset.pageType || publisherContext.pageType || "",
        page_url: slotNode.dataset.pageUrl || publisherContext.pageUrl || window.location.href,
        size: slotNode.dataset.size || "",
        device_type: device,
        category: slotNode.dataset.category || publisherContext.category || "",
        slot_position: slotNode.dataset.position || "",
        geo: publisherContext.geo || "delhi_ncr",
        audience: publisherContext.audience || "sports_fans",
        timestamp: new Date().toISOString(),
        kv_language: "en",
        kv_theme: slotNode.dataset.category || publisherContext.category || "general",
    });
    if (publisherContext.sessionDebug) {
        params.set("debug", "1");
    }

    fetch(`/publisher/ad?${params.toString()}`)
        .then(response => response.json())
        .then(payload => {
            renderSlot(slotNode, payload);
        })
        .catch(() => {
            const stage = slotNode.querySelector("[data-slot-stage]");
            stage.innerHTML = `
                <div class="publisher-slot-placeholder">
                    <strong>Ad request failed</strong>
                    <span>Check the backend and try again.</span>
                </div>
            `;
            updateDebugEntry(slotNode.dataset.slotId, {
                filled: false,
                responseType: "error",
                requestedSlot: slotNode.dataset.slotId,
                requestedSize: slotNode.dataset.size,
                lineItem: null,
                creative: null,
                reason: "The /serve-ad request failed.",
                device,
                impressionFired: false,
                candidates: [],
            });
        });
}

if (debugToggle) {
    debugToggle.addEventListener("click", toggleDebugPanel);
}

if (debugPanel && debugPanel.dataset.debugDefault === "1") {
    debugPanel.classList.add("is-open");
}

slotNodes.forEach(loadSlot);
focusHighlightedSlot();
