from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.database import *
from pydantic import BaseModel
import os
from datetime import datetime
import pytz
from worker.monitor.checker import check_http
from worker.monitor.ssl import check_ssl
from worker.monitor.domain import check_domain
from worker.worker import get_hosting_provider
from fastapi import BackgroundTasks
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

def check_new_site(site_id, url):
    http = check_http(url)
    ssl_days = check_ssl(url)
    domain_days = check_domain(url)
    hosting = get_hosting_provider(url)

    update_status(
        site_id,
        http["status"],
        http["response_time"],
        ssl_days,
        domain_days,
        hosting
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
        background_tasks.add_task(
            check_new_site,
            new_site["id"],
            site.url
        )

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
    data.get("hosting")
)
    return {"message": "updated"}


# ✅ SAVE LOG
@app.post("/api/sites/{site_id}/logs")
async def add_log(site_id: int, request: Request):
    data = await request.json()

    conn = get_connection()
    conn.execute("""
        INSERT INTO logs (site_id, status, response_time, ssl_days, domain_days, message)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        site_id,
        data["status"],
        data["response_time"],
        data["ssl_days"],
        data["domain_days"],
        data["message"]
    ))
    conn.commit()
    conn.close()

    return {"message": "log saved"}


@app.get("/api/sites/{site_id}/logs")
def get_logs(site_id: int):
    conn = get_connection()
    rows = conn.execute("""
        SELECT status, response_time, ssl_days, domain_days, message, created_at
        FROM logs
        WHERE site_id = ?
        ORDER BY created_at DESC
        LIMIT 50
    """, (site_id,)).fetchall()
    conn.close()

    pacific = pytz.timezone("US/Pacific")

    result = []
    for r in rows:
        row = dict(r)

        # Convert to Pacific Time
        dt = datetime.fromisoformat(row["created_at"])
        dt_pacific = dt.astimezone(pacific)

        # Format: Sep 10, 06:35 AM
        row["created_at"] = dt_pacific.strftime("%b %d, %I:%M %p")

        result.append(row)

    return result

# ---------------- FRONTEND ----------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")