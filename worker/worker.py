import http
import time
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import whois
from urllib.parse import urlparse
from worker.monitor.checker import check_http
from worker.monitor.ssl import check_ssl
from worker.monitor.domain import check_domain
from worker.alerts.email import send_alert


API = "http://localhost:8000/api/sites"
CHECK_INTERVAL = 900   # ✅ 15 minutes
MAX_WORKERS = 10


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


# -------------------------------
# SEND LOG TO BACKEND
# -------------------------------
def send_log(site_id, data):
    try:
        requests.post(
            f"{API}/{site_id}/logs",
            json=data,
            timeout=5
        )
    except Exception as e:
        log(f"❌ Log send failed: {e}")
def get_hosting_provider(url):
    try:
        domain = urlparse(url).netloc.replace("www.", "")
        w = whois.whois(domain)

        # Try org / registrar
        if w.org:
            return w.org
        if w.registrar:
            return w.registrar

        return "Unknown"
    except Exception:
        return "Unknown"

# -------------------------------
# PROCESS SINGLE SITE
# -------------------------------
def process_site(site):
    site_id = site["id"]
    url = site["url"]

    result = {
        "site_id": site_id,
        "url": url,
        "status": "DOWN",
        "response_time": 0,
        "ssl_days": -1,
        "domain_days": -1,
        "hosting": "Unknown"
    }

    try:
        log(f"🌐 Checking: {url}")

        # ---------------- HTTP CHECK ----------------
        http = check_http(url)
        
        result["status"] = http["status"]
        result["response_time"] = http["response_time"]

        # ---------------- SSL + DOMAIN ----------------
        ssl_days = check_ssl(url)
        domain_days = check_domain(url)
        hosting = get_hosting_provider(url)
        result["ssl_days"] = ssl_days
        result["domain_days"] = domain_days
        # ✅ Only update if meaningful
        if hosting and hosting != "Unknown":
            result["hosting"] = hosting
        else:
            # preserve existing value from DB
            result["hosting"] = site.get("hosting", "Unknown")
        # ---------------- LOG MESSAGE ----------------
        log_message = f"Checked successfully in {result['response_time']} ms"


        # ---------------- ALERTS ----------------
        try:
            if result["status"] == "DOWN":
                send_alert(f"{url} DOWN")

            if ssl_days != -1 and ssl_days < 10:
                send_alert(f"{url} SSL expiring")

            if domain_days != -1 and domain_days < 10:
                send_alert(f"{url} DOMAIN expiring")

        except Exception as e:
            log(f"⚠️ Alert failed: {e}")

        # ---------------- SAVE LOG ----------------
        send_log(site_id, {
            "status": result["status"],
            "response_time": result["response_time"],
            "ssl_days": ssl_days,
            "domain_days": domain_days,
            "hosting": result["hosting"],
            "message": log_message.strip()
        })

    except Exception as e:
        log(f"❌ Error checking {url}: {e}")

    return result


# -------------------------------
# MAIN WORKER LOOP
# -------------------------------
def run():
    log("🚀 Worker started")

    while True:
        start_time = time.time()

        try:
            log("🔄 Fetching sites...")

            res = requests.get(API, timeout=10)
            sites = res.json()

            if not sites:
                log("⚠️ No sites found")
                time.sleep(CHECK_INTERVAL)
                continue

            log(f"✅ Found {len(sites)} sites")

            # ---------------- PARALLEL CHECK ----------------
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = [executor.submit(process_site, s) for s in sites]

                for f in as_completed(futures):
                    result = f.result()

                    # ---------------- UPDATE STATUS ----------------
                    try:
                        requests.post(
                            f"{API}/{result['site_id']}/status",
                            json={
                                "status": result["status"],
                                "response_time_ms": result["response_time"],
                                "ssl_days": result["ssl_days"],
                                "domain_days": result["domain_days"],
                                "hosting": result["hosting"]
                            },
                            timeout=5
                        )
                        log(f"✅ Updated: {result['url']}")

                    except Exception as e:
                        log(f"❌ Status update failed: {e}")

        except Exception as e:
            log(f"❌ Worker error: {e}")

        # ---------------- SMART SLEEP ----------------
        elapsed = time.time() - start_time
        sleep_time = max(0, CHECK_INTERVAL - elapsed)

        log(f"😴 Sleeping for {int(sleep_time)} seconds (~15 min)\n")
        time.sleep(sleep_time)


# -------------------------------
# ENTRY POINT
# -------------------------------
if __name__ == "__main__":
    run()