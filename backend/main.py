from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.database import *
from pydantic import BaseModel
import os

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


@app.get("/api/sites")
def get_sites():
    return get_all_sites()


@app.post("/api/sites")
def create_site(site: Site):
    add_site(site.name, site.url)
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

    return [dict(r) for r in rows]


# ---------------- FRONTEND ----------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")