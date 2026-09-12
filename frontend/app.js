const API = "/api/sites";
const LOG_API = "/api/sites";

let allSites = [];
let currentFilter = "all";
let searchQuery = "";
console.log("APP LOADED", Date.now());
async function fetchSites() {
    try {
        const res = await fetch(API);
        allSites = await res.json();
        console.log("FETCH CALLED");
        applyFilterAndRender();
        updateStats(allSites);
    } catch (err) {
        console.error("Error fetching sites:", err);
    }
}

function setFilter(filterType) {
    currentFilter = filterType;

    // Update active tab buttons UI
    document.querySelectorAll(".filter-btn").forEach((btn) => {
        if (btn.getAttribute("data-filter") === filterType) {
            btn.classList.add("active");
        } else {
            btn.classList.remove("active");
        }
    });

    applyFilterAndRender();
}

function handleSearch() {
    const input = document.getElementById("searchInput");
    searchQuery = input ? input.value.toLowerCase() : "";
    applyFilterAndRender();
}

function applyFilterAndRender() {
    let filtered = allSites.filter((site) => {
        const statusUpper = (site.status || "").toUpperCase();

        // 1. Status Filter
        if (currentFilter === "up" && statusUpper !== "UP") return false;
        if (currentFilter === "down" && statusUpper !== "DOWN") return false;
        if (currentFilter === "warning") {
            const lowSsl = site.ssl_days !== null && site.ssl_days < 10;
            const lowDomain = site.domain_days !== null &&
                site.domain_days < 10;
            if (!lowSsl && !lowDomain) return false;
        }

        // 2. Search Query Filter
        if (searchQuery) {
            const nameMatch = (site.name || "").toLowerCase().includes(
                searchQuery,
            );
            const urlMatch = (site.url || "").toLowerCase().includes(
                searchQuery,
            );
            if (!nameMatch && !urlMatch) return false;
        }

        return true;
    });

    renderSites(filtered);
}

function renderSites(sites) {
    const container = document.getElementById("sites");

    if (!container) {
        console.error("❌ #sites missing");
        return;
    }

    container.innerHTML = "";

    if (!sites || sites.length === 0) {
        container.innerHTML =
            `<div class="empty-state"><p>No websites found</p></div>`;
        return;
    }

    sites.forEach((site) => {
        const statusClass = site.status === "UP"
            ? "up"
            : site.status === "DOWN"
            ? "down"
            : "warn";

        const card = document.createElement("div");
        card.className = `site-card ${statusClass}`;

        card.innerHTML = `
            <div class="site-header">
                <a href="${
            escapeHtml(site.url)
        }" target="_blank" class="site-url">
                    ${escapeHtml(site.name)}
                </a>
                <span class="badge ${statusClass}">
                    ${site.status}
                </span>
                <button class="delete-btn" data-id="${site.id}" title="Delete site">
    <svg viewBox="0 0 24 24">
        <path d="M6 7h12M9 7V5h6v2M8 7l1 12h6l1-12"
              stroke="currentColor"
              stroke-width="1.6"
              stroke-linecap="round"
              fill="none"/>
    </svg>
</button>
            </div>

            <div class="metrics">
                <div>
                    <span>Latency</span>
                    <strong>${site.response_time_ms ?? "-"} ms</strong>
                </div>
                <div>
                    <span>SSL</span>
                    <strong class="${getExpiryClass(site.ssl_days)}">${
            formatExpiryText(site.ssl_days)
        }</strong>
                </div>
                <div>
                    <span>Domain</span>
                    <strong class="${getExpiryClass(site.domain_days)}">${
            formatExpiryText(site.domain_days)
        }</strong>
                </div>
            </div>
            

            <div class="meta-row">
                <span class="meta-label">Hosting:</span>
                <span class="meta-value" title="${site.hosting ?? "Unknown"}">
                    ${site.hosting ?? "Unknown"}
                </span>
            </div>
            </div>
        `;
        card.addEventListener("click", () => {
            window.location.href = `/site.html?id=${site.id}`;
        });

        // ✅ DELETE BUTTON HANDLER
        const deleteBtn = card.querySelector(".delete-btn");

        if (deleteBtn) {
            deleteBtn.addEventListener("click", async (e) => {
                e.stopPropagation(); // ❗ prevents card click (logs modal)

                const confirmDelete = confirm(
                    "Are you sure you want to delete this site?",
                );
                if (!confirmDelete) return;

                try {
                    await fetch(`/api/sites/${site.id}`, {
                        method: "DELETE",
                    });

                    fetchSites(); // refresh UI
                } catch (err) {
                    console.error("Delete failed:", err);
                }
            });
        }
        // Click card -> Open dedicated Logs View / Modal
        card.addEventListener("click", (e) => {
            if (e.target.tagName === "A") return;
            openLogs(site.id, site.name);
        });

        container.appendChild(card);
    });
}

function updateStats(sites) {
    const totalEl = document.getElementById("statTotal");
    const upEl = document.getElementById("statUp");
    const downEl = document.getElementById("statDown");
    const warnEl = document.getElementById("statWarning");

    if (totalEl) totalEl.innerText = sites.length;

    const up = sites.filter((s) => s.status === "UP").length;
    const down = sites.filter((s) => s.status === "DOWN").length;
    const warn = sites.filter((s) =>
        (s.ssl_days !== null && s.ssl_days < 10) ||
        (s.domain_days !== null && s.domain_days < 10)
    ).length;

    if (upEl) upEl.innerText = up;
    if (downEl) downEl.innerText = down;
    if (warnEl) warnEl.innerText = warn;
}

// LOGS MODAL HANDLERS
async function openLogs(siteId, siteName) {
    const modal = document.getElementById("logsModal");
    const container = document.getElementById("logsContainer");

    if (!modal || !container) return;

    const heading = document.getElementById("logsModalTitle") ||
        modal.querySelector("h3") || modal.querySelector("h2");
    if (heading) {
        heading.textContent = `Logs: ${siteName || "Site #" + siteId}`;
    }

    container.innerHTML = "<p>Loading logs...</p>";
    modal.classList.remove("hidden");

    try {
        const res = await fetch(`${LOG_API}/${siteId}/logs`);
        const logs = await res.json();

        if (!logs || logs.length === 0) {
            container.innerHTML =
                "<p style='color: var(--text-muted); padding: 1rem 0;'>No activity logs recorded yet.</p>";
            return;
        }

        container.innerHTML = logs.map((log) => `
            <div class="log-item">
                <small>${log.created_at}</small>
                <div><strong>${log.status}</strong> (${log.response_time} ms)</div>
                <div>SSL: ${log.ssl_days ?? "-"} days | Domain: ${
            log.domain_days ?? "-"
        } days</div>
                <div>${escapeHtml(log.message || "")}</div>
            </div>
        `).join("");
    } catch (err) {
        console.error("Error fetching logs:", err);
        container.innerHTML = "<p>❌ Failed to load logs</p>";
    }
}

function closeLogs() {
    const modal = document.getElementById("logsModal");
    if (modal) {
        modal.classList.add("hidden");
    }
}
async function deleteSite(e, siteId, siteName) {
    e.stopPropagation();

    if (!confirm(`Delete ${siteName}?`)) return;

    await fetch(`${API}/${siteId}`, {
        method: "DELETE",
    });

    fetchSites();
}
// ADD SITE HANDLER
async function handleAddSite(e) {
    if (e && e.preventDefault) e.preventDefault();

    const name = document.getElementById("siteName")?.value ||
        document.getElementById("name")?.value;
    const url = document.getElementById("siteUrl")?.value ||
        document.getElementById("url")?.value;

    if (!name || !url) return alert("Enter name and URL");

    let formattedUrl = url.trim();
    if (!/^https?:\/\//i.test(formattedUrl)) {
        formattedUrl = "https://" + formattedUrl;
    }

    await fetch(API, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name.trim(), url: formattedUrl }),
    });

    if (document.getElementById("siteName")) {
        document.getElementById("siteName").value = "";
    }
    if (document.getElementById("siteUrl")) {
        document.getElementById("siteUrl").value = "";
    }

    fetchSites();
}

function getExpiryClass(days) {
    if (days === null || days === undefined || days === -1) return "";
    if (days < 30) return "metric-danger";
    if (days < 60) return "metric-warning";
    return "metric-safe";
}

function formatExpiryText(days) {
    if (days === null || days === undefined || days === -1) return "-";
    return `${days} days`;
}

function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/[&<>"']/g, (m) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
    }[m]));
}

// REFRESH HOSTING HANDLERS
async function handleRefreshHosting() {
    const btn = document.getElementById("refreshHostingBtn");
    if (!btn || btn.disabled) return;

    updateHostingBtnState(true);
    showToast("Hosting refresh started in background", "info");

    try {
        const response = await fetch("/api/recompute-hosting", {
            method: "POST",
        });

        if (!response.ok) {
            throw new Error(`Server returned status ${response.status}`);
        }

        // Wait ~4 seconds for background hosting recompute task to process DB updates
        await new Promise((resolve) => setTimeout(resolve, 4000));

        // Refresh UI with updated hosting info
        await fetchSites();
        showToast("Hosting updated successfully", "success");
    } catch (err) {
        console.error("Failed to recompute hosting:", err);
        showToast("Failed to refresh hosting", "danger");
    } finally {
        updateHostingBtnState(false);
    }
}

function updateHostingBtnState(isLoading) {
    const btn = document.getElementById("refreshHostingBtn");
    const icon = document.getElementById("refreshHostingIcon");
    const text = document.getElementById("refreshHostingText");

    if (!btn) return;

    btn.disabled = isLoading;
    if (isLoading) {
        if (icon) icon.className = "spin-icon";
        if (text) text.textContent = "Refreshing...";
    } else {
        if (icon) icon.className = "";
        if (text) text.textContent = "Refresh Hosting";
    }
}

function showToast(message, type = "info") {
    const container = document.getElementById("toastContainer");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;

    let icon = "ℹ️";
    if (type === "success") icon = "✅";
    if (type === "danger") icon = "❌";
    if (type === "warning") icon = "⚠️";

    toast.innerHTML = `<span>${icon}</span> <span>${
        escapeHtml(message)
    }</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transition = "opacity 0.3s ease";
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function forceRefresh() {
    fetchSites();
}

// AUTO REFRESH (Every 60sec)
setInterval(fetchSites, 60000);

// INITIAL LOAD
fetchSites();
