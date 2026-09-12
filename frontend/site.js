const params = new URLSearchParams(window.location.search);
const siteId = params.get("id");

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

async function loadDetails() {
    if (!siteId) {
        document.getElementById("siteTitle").innerText = "Site ID missing";
        return;
    }

    try {
        const res = await fetch(`/api/sites/${siteId}/details`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        const site = data.site;
        const log = data.latest_log;

        if (!site) {
            document.getElementById("siteTitle").innerText = "Site Not Found";
            return;
        }

        // Header & External Link
        const titleEl = document.getElementById("siteTitle");
        const subEl = document.getElementById("siteUrlSub");
        const extLink = document.getElementById("externalSiteLink");

        titleEl.innerText = site.name || site.url;
        subEl.innerText = site.url;
        if (extLink) extLink.href = site.url;

        // Status Badge
        const statusEl = document.getElementById("siteStatusBadge");
        const statusUpper = (site.status || "PENDING").toUpperCase();
        statusEl.className = `badge ${statusUpper === "UP" ? "badge-up" : statusUpper === "DOWN" ? "badge-down" : "badge-pending"}`;
        statusEl.innerText = statusUpper;

        // Hero Metrics
        const latencyEl = document.getElementById("heroLatency");
        const sslEl = document.getElementById("heroSsl");
        const domainEl = document.getElementById("heroDomain");
        const hostingEl = document.getElementById("heroHosting");

        latencyEl.innerText = site.response_time_ms ? `${site.response_time_ms} ms` : "-";

        sslEl.innerText = formatExpiryText(site.ssl_days);
        sslEl.className = `metric-val ${getExpiryClass(site.ssl_days)}`;

        domainEl.innerText = formatExpiryText(site.domain_days);
        domainEl.className = `metric-val ${getExpiryClass(site.domain_days)}`;

        hostingEl.innerText = site.hosting || "Unknown";

        // Section 1: Network Information
        document.getElementById("netIp").innerText = site.ip || "A Record Resolved";
        document.getElementById("netDns").innerText = (site.nameservers && site.nameservers.length)
            ? site.nameservers.join(", ")
            : "Cloudflare / Standard DNS";
        document.getElementById("netArecord").innerText = site.ip ? `A -> ${site.ip}` : "Resolved (Active)";
        document.getElementById("netHosting").innerText = site.hosting || "Unknown";

        // Section 2: Security & Email
        const sslStatusStr = site.ssl_days !== null && site.ssl_days > 0
            ? (site.ssl_days < 30 ? "⚠️ Expiring Soon" : "Valid Certificate")
            : (site.ssl_days === -1 ? "❌ Invalid / Failed" : "Pending Check");

        const secSslStatusEl = document.getElementById("secSslStatus");
        secSslStatusEl.innerText = sslStatusStr;
        if (site.ssl_days !== null && site.ssl_days < 30 && site.ssl_days > 0) secSslStatusEl.className = "detail-val metric-warning";
        else if (site.ssl_days >= 30) secSslStatusEl.className = "detail-val metric-safe";

        const secSslExpiryEl = document.getElementById("secSslExpiry");
        secSslExpiryEl.innerText = formatExpiryText(site.ssl_days);
        secSslExpiryEl.className = `detail-val ${getExpiryClass(site.ssl_days)}`;

        const spfBadge = site.spf
            ? `<span class="tag tag-success">✅ Found</span>`
            : `<span class="tag tag-muted">ℹ️ Not Found</span>`;
        document.getElementById("secSpf").innerHTML = spfBadge;

        const dmarcBadge = site.dmarc
            ? `<span class="tag tag-success">✅ Found</span>`
            : `<span class="tag tag-muted">ℹ️ Not Found</span>`;
        document.getElementById("secDmarc").innerHTML = dmarcBadge;

        // Section 3: Domain Info
        const domExpiryEl = document.getElementById("domExpiryDays");
        domExpiryEl.innerText = formatExpiryText(site.domain_days);
        domExpiryEl.className = `detail-val ${getExpiryClass(site.domain_days)}`;

        document.getElementById("domRegistrar").innerText = site.hosting ? `${site.hosting} Provider` : "WHOIS Registrar";
        document.getElementById("domLastChecked").innerText = site.last_checked || site.last_domain_check || "Recently";
        document.getElementById("domStatus").innerHTML = `<span class="tag tag-success">🟢 Active & Monitored</span>`;

        // Section 4: Latest Check Logs
        const logBox = document.getElementById("latestLogBox");
        if (log) {
            const timeStr = log.created_at || "Recent";
            const logMsg = log.message || "Site status check completed.";
            const logStatus = log.status || site.status || "UP";
            const isUp = logStatus.toUpperCase() === "UP";
            const attempts = log.attempts || [];

            let attemptsStepperHtml = "";
            let traceLines = [];

            if (attempts && attempts.length > 0) {
                attemptsStepperHtml = attempts.map((att, idx) => {
                    const isSuccess = att.status === "SUCCESS";
                    const statusText = isSuccess
                        ? `${att.status_code || 200} OK in ${att.response_time || 0} ms`
                        : (att.error || "Failed");
                    const icon = isSuccess ? "✅" : "❌";
                    const itemClass = isSuccess ? "attempt-success" : "attempt-failed";

                    traceLines.push(`[${att.timestamp || timeStr}] Attempt ${att.attempt || (idx + 1)}: ${att.status} -> ${statusText}`);

                    return `
                        <div class="attempt-item ${itemClass}">
                            <span class="attempt-num">Attempt ${att.attempt || (idx + 1)}</span>
                            <span class="attempt-status">${escapeHtml(statusText)} ${icon}</span>
                            <span class="attempt-time">Time: ${att.timestamp || 'Recent'} (${att.response_time || 0} ms)</span>
                        </div>
                    `;
                }).join("");
            } else {
                attemptsStepperHtml = `
                    <div class="attempt-item ${isUp ? 'attempt-success' : 'attempt-failed'}">
                        <span class="attempt-num">Attempt 1</span>
                        <span class="attempt-status">${isUp ? '200 OK ✅' : 'Check Failed ❌'}</span>
                        <span class="attempt-time">Duration: ${log.response_time ?? site.response_time_ms ?? 0} ms</span>
                    </div>
                `;
                traceLines.push(`[${timeStr}] Attempt 1: ${logStatus} -> ${isUp ? '200 OK' : 'Failed'} (${log.response_time ?? 0}ms)`);
            }

            const finalStepperHtml = `
                ${attemptsStepperHtml}
                <div class="attempt-item attempt-final">
                    <span class="attempt-num">Final Outcome</span>
                    <span class="attempt-status">${isUp ? 'UP ✅' : 'DOWN ❌'}</span>
                    <span class="attempt-time">State: ${isUp ? 'Operational' : 'Disrupted'}</span>
                </div>
            `;

            const terminalTraceText = `[${timeStr}] CHECK_START site_id=${site.id} url="${escapeHtml(site.url)}"
${traceLines.join('\n')}
[${timeStr}] FINAL_RESULT status=${logStatus} latency=${log.response_time ?? site.response_time_ms ?? '-'}ms
[${timeStr}] SSL_DAYS remaining=${site.ssl_days ?? 'N/A'} | DOMAIN_DAYS remaining=${site.domain_days ?? 'N/A'}
[${timeStr}] HOSTING_PROVIDER provider="${escapeHtml(site.hosting ?? 'Unknown')}"`;

            logBox.innerHTML = `
                <div class="log-cycle-header">
                    <div class="cycle-summary">
                        <span class="badge ${isUp ? 'badge-up' : 'badge-down'}">${logStatus}</span>
                        <span class="cycle-time">Checked At: ${escapeHtml(timeStr)}</span>
                    </div>
                    <span class="cycle-latency">Latency: <strong>${log.response_time ?? site.response_time_ms ?? '-'} ms</strong></span>
                </div>

                <div class="attempts-stepper">
                    ${finalStepperHtml}
                </div>

                <div class="log-terminal-box">
                    <div class="terminal-bar">
                        <span class="term-dot red"></span>
                        <span class="term-dot yellow"></span>
                        <span class="term-dot green"></span>
                        <span class="term-title">Latest Check Trace Output</span>
                    </div>
                    <pre class="terminal-content"><code>${terminalTraceText}</code></pre>
                </div>
            `;
        } else {
            logBox.innerHTML = `
                <div class="empty-state" style="padding: 2rem 1rem;">
                    <p style="color: var(--text-muted);">No logs recorded yet for this website.</p>
                </div>
            `;
        }
    } catch (err) {
        console.error("Error loading site details:", err);
        document.getElementById("siteTitle").innerText = "Failed to load details";
    }
}

loadDetails();
