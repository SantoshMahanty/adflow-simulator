const body = document.body;
const sidebarToggle = document.querySelector("[data-sidebar-toggle]");
const modalBackdrop = document.querySelector("[data-modal-backdrop]");
const sidebarStorageKey = "adflow-sidebar-collapsed";

function applySidebarPreference() {
    const collapsed = window.localStorage.getItem(sidebarStorageKey) === "true";
    if (window.innerWidth > 1100) {
        body.classList.toggle("sidebar-collapsed", collapsed);
        body.classList.remove("sidebar-open");
    } else {
        body.classList.remove("sidebar-collapsed");
    }
}

function toggleSidebar() {
    if (window.innerWidth > 1100) {
        const nextState = !body.classList.contains("sidebar-collapsed");
        body.classList.toggle("sidebar-collapsed", nextState);
        window.localStorage.setItem(sidebarStorageKey, String(nextState));
    } else {
        body.classList.toggle("sidebar-open");
    }
}

function closeModal() {
    if (modalBackdrop) {
        modalBackdrop.classList.remove("is-visible");
        modalBackdrop.setAttribute("aria-hidden", "true");
        body.classList.remove("modal-open");
    }
}

function openModal() {
    if (modalBackdrop) {
        modalBackdrop.classList.add("is-visible");
        modalBackdrop.setAttribute("aria-hidden", "false");
        body.classList.add("modal-open");
    }
}

if (sidebarToggle) {
    sidebarToggle.addEventListener("click", toggleSidebar);
}

window.addEventListener("resize", applySidebarPreference);
applySidebarPreference();

if (modalBackdrop) {
    modalBackdrop.addEventListener("click", event => {
        if (event.target === modalBackdrop) {
            closeModal();
        }
    });
}

document.addEventListener("click", event => {
    if (event.target.closest("[data-modal-open]")) {
        openModal();
        return;
    }

    if (event.target.closest("[data-modal-close]")) {
        closeModal();
    }
});

document.addEventListener("keydown", event => {
    if (event.key === "Escape") {
        closeModal();
        body.classList.remove("sidebar-open");
    }
});

function renderBarChart(node, data) {
    const max = Math.max(...data.map(item => item.value || 0), 1);
    node.innerHTML = data.map((item, index) => {
        const width = Math.max((item.value / max) * 100, 4);
        const colors = [
            "linear-gradient(90deg, #2563eb, #6cb6ff)",
            "linear-gradient(90deg, #13805f, #58c4a1)",
            "linear-gradient(90deg, #c47b14, #f7b85a)",
            "linear-gradient(90deg, #7c3aed, #a78bfa)"
        ];
        return `
            <div class="chart-bar">
                <span class="chart-bar-label" title="${item.label}">${item.label}</span>
                <div class="chart-bar-track">
                    <div class="chart-bar-fill" style="width:${width}%; background:${colors[index % colors.length]}"></div>
                </div>
                <strong class="chart-value">${item.value}</strong>
            </div>
        `;
    }).join("");
}

function renderDonutList(node, data) {
    const total = data.reduce((sum, item) => sum + (item.value || 0), 0) || 1;
    node.innerHTML = `
        <div class="chart-donut-list">
            ${data.map(item => `
                <div class="chart-donut-item">
                    <div class="muted">${item.label}</div>
                    <div class="winner-name">${item.value}</div>
                    <div>${Math.round((item.value / total) * 100)}% of total</div>
                </div>
            `).join("")}
        </div>
    `;
}

document.querySelectorAll("[data-chart]").forEach(node => {
    try {
        const data = JSON.parse(node.dataset.series || "[]");
        if (!Array.isArray(data) || !data.length) {
            node.innerHTML = "<div class='empty-state'>No chart data available.</div>";
            return;
        }
        if (node.dataset.chart === "donut") {
            renderDonutList(node, data);
        } else {
            renderBarChart(node, data);
        }
    } catch (error) {
        node.innerHTML = "<div class='empty-state'>Chart failed to render.</div>";
    }
});
