from fastapi import logger
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.database import *
from pydantic import BaseModel
import os

from worker.monitor.checker import check_http
from worker.monitor.ssl import check_ssl
from worker.monitor.domain import check_domain
from worker.worker import get_hosting_provider

app = FastAPI()
init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class Site(BaseModel):
    name: str
    url: str

def run_recompute_hosting():
    sites = get_all_sites()
    print(f"🔥 TOTAL SITES: {len(sites)}")

    for site in sites:
        site_id = site["id"]
        url = site["url"]

        print(f"➡️ Processing: {url}")

        try:
            hosting = get_hosting_provider(url)
            print(f"🏢 Hosting: {hosting}")

            update_status(
    site_id,
    site.get("status", "UNKNOWN"),
    site.get("response_time_ms", 0),
    None,
    None,
    hosting,
    False,   # ssl_updated
    False,   # domain_updated
    True     # hosting_updated ✅ IMPORTANT
)

            print(f"✅ Updated: {url}")

        except Exception as e:
            print(f"❌ Error: {url} → {e}")
# -------------------------------
# INITIAL CHECK (ON ADD)
# -------------------------------
def check_new_site(site_id, url):
    print(f"🚀 NEW SITE CHECK TRIGGERED: {url}")
    http = check_http(url)
    ssl = check_ssl(url)
    domain = check_domain(url)
    hosting = get_hosting_provider(url)

    print(f"""
NEW SITE RESULT:
SSL: {ssl}
DOMAIN: {domain}
HOSTING: {hosting}
""")
    update_status(
        site_id,
        http["status"],
        http["response_time"],
        ssl,
        domain,
        hosting,
        ssl_updated=(ssl is not None and ssl != -1),
        domain_updated=(domain is not None and domain != -1),
        hosting_updated=(hosting is not None and hosting != "Unknown"),
        attempts=http.get("attempts")
    )


@app.get("/api/sites")
def get_sites():
    return get_all_sites()


@app.post("/api/sites")
def create_site(site: Site, background_tasks: BackgroundTasks):
    add_site(site.name, site.url)

    sites = get_all_sites()
    new_site = next((s for s in sites if s["url"] == site.url), None)

    if new_site:
        background_tasks.add_task(check_new_site, new_site["id"], site.url)

    return {"message": "added"}


@app.delete("/api/sites/{site_id}")
def remove_site(site_id: int):
    delete_site(site_id)
    return {"message": "deleted"}


@app.post("/api/sites/{site_id}/status")
def update_site_status(site_id: int, data: dict):
    update_status(
        site_id,
        data["status"],
        data["response_time_ms"],
        data.get("ssl_days"),
        data.get("domain_days"),
        data.get("hosting"),
        ssl_updated=data.get("ssl_updated", False),
        domain_updated=data.get("domain_updated", False),
        hosting_updated=data.get("hosting_updated", False),
        attempts=data.get("attempts")
    )

    return {"message": "updated"}


@app.get("/api/sites/{site_id}/details")
def get_site_details(site_id: int):
    conn = get_connection()

    site = conn.execute(
        "SELECT * FROM websites WHERE id=?",
        (site_id,)
    ).fetchone()

    log = conn.execute("""
        SELECT *
        FROM logs
        WHERE site_id=?
        ORDER BY created_at DESC
        LIMIT 1
    """, (site_id,)).fetchone()

    conn.close()

    site_dict = dict(site) if site else None
    if site_dict and site_dict.get("url"):
        try:
            from urllib.parse import urlparse
            from worker.monitor.dns import get_dns_info
            parsed_domain = urlparse(site_dict["url"]).netloc or site_dict["url"]
            parsed_domain = parsed_domain.split(":")[0]
            dns_info = get_dns_info(parsed_domain)
            if dns_info:
                site_dict["ip"] = dns_info.get("ip")
                site_dict["nameservers"] = dns_info.get("nameservers") or []
                site_dict["spf"] = dns_info.get("spf")
                site_dict["dmarc"] = dns_info.get("dmarc")
        except Exception as e:
            print(f"DNS lookup notice for site {site_id}:", e)

    log_dict = dict(log) if log else None
    if log_dict and log_dict.get("attempts"):
        if isinstance(log_dict["attempts"], str):
            try:
                log_dict["attempts"] = json.loads(log_dict["attempts"])
            except Exception:
                pass

    return {
        "site": site_dict,
        "latest_log": log_dict
    }


@app.post("/api/recompute-hosting")
def recompute_hosting(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_recompute_hosting)
    return {"message": "Hosting recompute started in background"}


@app.get("/api/sites/{site_id}/logs")
def get_logs(site_id: int):
    conn = get_connection()

    rows = conn.execute("""
        SELECT *
        FROM logs
        WHERE site_id=?
        ORDER BY created_at DESC
        LIMIT 1
    """, (site_id,)).fetchall()

    conn.close()

    result_logs = []
    for r in rows:
        d = dict(r)
        if d.get("attempts") and isinstance(d["attempts"], str):
            try:
                d["attempts"] = json.loads(d["attempts"])
            except Exception:
                pass
        result_logs.append(d)

    return result_logs
# ---------------- FRONTEND ----------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")