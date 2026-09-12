import time
import requests
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import whois
from urllib.parse import urlparse
import socket

from worker.monitor.checker import check_http
from worker.monitor.ssl import check_ssl
from worker.monitor.domain import check_domain
from datetime import datetime, timedelta


API = "http://localhost:8000/api/sites"
CHECK_INTERVAL = 900
MAX_WORKERS = 10

def retry(func, retries=3, delay=1):
    for attempt in range(retries):
        try:
            result = func()

            # reject bad values
            if result not in [None, -1, "Unknown"]:
                return result

        except Exception as e:
            log(f"Retry {attempt+1} failed: {e}")

        time.sleep(delay)

    return None
def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
def should_refresh(last_checked):
    if not last_checked:
        return True
    try:
        last = datetime.fromisoformat(last_checked)
        return datetime.utcnow() - last > timedelta(hours=24)
    except:
        return True

# -------------------------------
# SAFE WHOIS (HOSTING)
# -------------------------------
def get_hosting_provider(url):
    try:
        # -------------------------------
        # 1. Extract domain
        # -------------------------------
        domain = urlparse(url).netloc.replace("www.", "")

        # -------------------------------
        # 2. Resolve IP
        # -------------------------------
        ip = socket.gethostbyname(domain)

        # -------------------------------
        # 3. ASN lookup (REAL hosting info)
        # -------------------------------
        try:
            res = requests.get(f"https://ipinfo.io/{ip}/json", timeout=5)
            data = res.json()

            org = data.get("org")  # e.g. "AS13335 Cloudflare, Inc."

            if org:
                # Clean output
                return org.replace("AS", "").strip()

        except Exception:
            pass

        return "Unknown"

    except Exception:
        return "Unknown"

def safe_check(func, retries=3):
    for _ in range(retries):
        try:
            val = func()
            if val not in [None, -1, "Unknown"]:
                return val
        except:
            pass
    return None
# -------------------------------
# DAILY CHECK DECIDER
# -------------------------------

def should_run_daily(last_checked):
    if not last_checked:
        return True

    try:
        # ✅ Fix SQLite format (replace space with T)
        last_checked = last_checked.replace(" ", "T")

        last = datetime.fromisoformat(last_checked)

        return datetime.utcnow() - last > timedelta(hours=24)

    except Exception as e:
        print("⚠️ Date parse error:", last_checked, e)
        return True


# -------------------------------
# PROCESS SITE
# -------------------------------
def process_site(site):
    site_id = site["id"]
    url = site["url"]

    result = {
        "site_id": site_id,
        "url": url,

        # ALWAYS FILLED
        "status": site.get("status", "DOWN"),
        "response_time": site.get("response_time_ms", 0),

        # DEFAULT = OLD VALUES (IMPORTANT)
        "ssl_days": site.get("ssl_days"),
        "domain_days": site.get("domain_days"),
        "hosting": site.get("hosting"),

        # timestamps (only update if new values found)
        "last_ssl_check": site.get("last_ssl_check"),
        "last_domain_check": site.get("last_domain_check"),
        "last_hosting_check": site.get("last_hosting_check"),
    }

    try:
        log(f"🌐 Checking: {url}")

        # ---------------- ALWAYS CHECK ----------------
        http = check_http(url)
        result["status"] = http["status"]
        result["response_time"] = http["response_time"]
        result["attempts"] = http.get("attempts", [])

        now = datetime.utcnow().isoformat()

        # ---------------- SSL (DAILY + FIRST RUN + SAFE) ----------------
        if should_run_daily(site.get("last_ssl_check")) or site.get("ssl_days") is None:
            ssl_val = safe_check(lambda: check_ssl(url))

            if ssl_val is not None and ssl_val != -1:
                result["ssl_days"] = ssl_val
                result["last_ssl_check"] = now


        # ---------------- DOMAIN (DAILY + FIRST RUN + SAFE) ----------------
        if should_run_daily(site.get("last_domain_check")) or site.get("domain_days") is None:
            domain_val = safe_check(lambda: check_domain(url))

            if domain_val is not None and domain_val != -1:
                result["domain_days"] = domain_val
                result["last_domain_check"] = now


        # ---------------- HOSTING (DAILY + FIRST RUN + SAFE) ----------------
        if should_run_daily(site.get("last_hosting_check")) or not site.get("hosting"):
            hosting_val = safe_check(lambda: get_hosting_provider(url))

            if hosting_val and hosting_val != "Unknown":
                result["hosting"] = hosting_val
                result["last_hosting_check"] = now

        # ---------------- DEBUG ----------------
        log(f"""
📊 DEBUG RESULT:
URL: {url}
HTTP: {result["status"]} ({result["response_time"]} ms)
ATTEMPTS: {len(result["attempts"])}

SSL: {result["ssl_days"]}
DOM: {result["domain_days"]}
HOSTING: {result["hosting"]}
""")

    except Exception as e:
        log(f"❌ Error checking {url}: {e}")

    return result


# -------------------------------
# MAIN LOOP
# -------------------------------
def run():
    log("🚀 Worker started")

    while True:
        start_time = time.time()

        try:
            res = requests.get(API, timeout=10)
            sites = res.json()

            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = [executor.submit(process_site, s) for s in sites]

                for f in as_completed(futures):
                    result = f.result()

                    requests.post(
                        f"{API}/{result['site_id']}/status",
                        json={
                            "status": result["status"],
                            "response_time_ms": result["response_time"],
                            "ssl_days": result["ssl_days"],
                            "domain_days": result["domain_days"],
                            "hosting": result["hosting"],
                            "attempts": result.get("attempts", []),

                            "ssl_updated": result["last_ssl_check"] is not None,
                            "domain_updated": result["last_domain_check"] is not None,
                            "hosting_updated": result["last_hosting_check"] is not None
                        }
                    )

                    log(f"✅ Updated: {result['url']}")

        except Exception as e:
            log(f"❌ Worker error: {e}")

        sleep_time = max(0, CHECK_INTERVAL - (time.time() - start_time))
        log(f"😴 Sleeping {int(sleep_time)} sec\n")
        time.sleep(sleep_time)


if __name__ == "__main__":
    run()