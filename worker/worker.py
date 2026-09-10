import time
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from worker.monitor.checker import check_http
from worker.monitor.ssl import check_ssl
from worker.monitor.domain import check_domain
from worker.alerts.email import send_alert

API = "http://localhost:8000/api/sites"
CHECK_INTERVAL = 900
MAX_WORKERS = 10


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def send_log(site_id, data):
    try:
        requests.post(f"{API}/{site_id}/logs", json=data, timeout=5)
    except Exception as e:
        log(f"❌ Log send failed: {e}")


def process_site(site):
    site_id = site["id"]
    url = site["url"]

    result = {
        "site_id": site_id,
        "url": url,
        "status": "DOWN",
        "response_time": 0,
        "ssl_days": -1,
        "domain_days": -1
    }

    try:
        log(f"🌐 Checking: {url}")

        http = check_http(url)
        result["status"] = http["status"]
        result["response_time"] = http["response_time"]

        ssl_days = check_ssl(url)
        domain_days = check_domain(url)

        result["ssl_days"] = ssl_days
        result["domain_days"] = domain_days

        log_message = f"""
STATUS: {result['status']}
RESPONSE: {result['response_time']} ms
SSL: {ssl_days} days
DOMAIN: {domain_days} days
"""

        # ALERTS
        if result["status"] == "DOWN":
            send_alert(f"{url} DOWN")

        if ssl_days != -1 and ssl_days < 10:
            send_alert(f"{url} SSL expiring")

        if domain_days != -1 and domain_days < 10:
            send_alert(f"{url} DOMAIN expiring")

        # SAVE LOG
        send_log(site_id, {
            "status": result["status"],
            "response_time": result["response_time"],
            "ssl_days": ssl_days,
            "domain_days": domain_days,
            "message": log_message.strip()
        })

    except Exception as e:
        log(f"❌ Error: {e}")

    return result


def run():
    log("🚀 Worker started")

    while True:
        try:
            res = requests.get(API)
            sites = res.json()

            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = [executor.submit(process_site, s) for s in sites]

                for f in as_completed(futures):
                    r = f.result()

                    requests.post(
                        f"{API}/{r['site_id']}/status",
                        json={
                            "status": r["status"],
                            "response_time_ms": r["response_time"],
                            "ssl_days": r["ssl_days"],
                            "domain_days": r["domain_days"]
                        }
                    )

                    log(f"✅ Updated: {r['url']}")

        except Exception as e:
            log(f"❌ Worker error: {e}")

        log("😴 Sleeping...\n")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    run()