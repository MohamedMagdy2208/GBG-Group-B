"""
SQLite database layer for the Lost & Found system.

Tables: lost_reports, found_items, match_results, notifications_log
Provides full CRUD operations and demo data seeding.
"""

import os
import sqlite3
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

import config

# ─── Connection helper ───────────────────────────────────────────────

def _get_connection() -> sqlite3.Connection:
    """Return a connection to the SQLite database (auto-creates data/ dir)."""
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


# ─── Table creation ──────────────────────────────────────────────────

def init_db() -> None:
    """Create all tables if they don't exist."""
    conn = _get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS lost_reports (
                case_id          TEXT PRIMARY KEY,
                passenger_name   TEXT NOT NULL,
                contact_email    TEXT NOT NULL,
                contact_phone    TEXT DEFAULT '',
                item_description TEXT NOT NULL,
                item_category    TEXT DEFAULT 'other',
                item_color       TEXT DEFAULT '',
                item_brand       TEXT DEFAULT '',
                location_last_seen TEXT DEFAULT '',
                time_last_seen   TEXT,
                optional_photo_path TEXT,
                status           TEXT DEFAULT 'active',
                created_at       TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS found_items (
                found_id         TEXT PRIMARY KEY,
                staff_id         TEXT NOT NULL,
                item_description TEXT DEFAULT '',
                item_category    TEXT DEFAULT 'other',
                item_color       TEXT DEFAULT '',
                item_brand       TEXT DEFAULT '',
                location_found   TEXT DEFAULT '',
                time_found       TEXT,
                photo_path       TEXT,
                optional_notes   TEXT DEFAULT '',
                status           TEXT DEFAULT 'unclaimed',
                created_at       TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS match_results (
                match_id         TEXT PRIMARY KEY,
                lost_case_id     TEXT NOT NULL,
                found_item_id    TEXT NOT NULL,
                confidence_score REAL NOT NULL,
                match_reasons    TEXT DEFAULT '[]',
                status           TEXT DEFAULT 'pending',
                reviewed_by      TEXT,
                reviewed_at      TEXT,
                UNIQUE(lost_case_id, found_item_id),
                FOREIGN KEY (lost_case_id)  REFERENCES lost_reports(case_id),
                FOREIGN KEY (found_item_id) REFERENCES found_items(found_id)
            );

            CREATE TABLE IF NOT EXISTS notifications_log (
                notification_id  TEXT PRIMARY KEY,
                case_id          TEXT NOT NULL,
                match_id         TEXT NOT NULL,
                passenger_email  TEXT NOT NULL,
                confidence_score REAL NOT NULL,
                found_item_description TEXT DEFAULT '',
                message          TEXT DEFAULT '',
                sent_at          TEXT NOT NULL,
                FOREIGN KEY (case_id)  REFERENCES lost_reports(case_id),
                FOREIGN KEY (match_id) REFERENCES match_results(match_id)
            );

            -- Performance indexes
            CREATE INDEX IF NOT EXISTS idx_lost_status ON lost_reports(status);
            CREATE INDEX IF NOT EXISTS idx_lost_created ON lost_reports(created_at);
            CREATE INDEX IF NOT EXISTS idx_found_status ON found_items(status);
            CREATE INDEX IF NOT EXISTS idx_found_created ON found_items(created_at);
            CREATE INDEX IF NOT EXISTS idx_match_lost ON match_results(lost_case_id);
            CREATE INDEX IF NOT EXISTS idx_match_found ON match_results(found_item_id);
            CREATE INDEX IF NOT EXISTS idx_match_status ON match_results(status);
            CREATE INDEX IF NOT EXISTS idx_notif_case ON notifications_log(case_id);
        """)
        conn.commit()
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════
# LOST REPORTS CRUD
# ═══════════════════════════════════════════════════════════════════

def insert_lost_report(data: dict) -> str:
    """Insert a lost report and return the case_id."""
    conn = _get_connection()
    case_id = data.get("case_id", str(uuid4()))
    try:
        conn.execute(
            """INSERT INTO lost_reports
               (case_id, passenger_name, contact_email, contact_phone,
                item_description, item_category, item_color, item_brand,
                location_last_seen, time_last_seen, optional_photo_path,
                status, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                case_id,
                data["passenger_name"],
                data["contact_email"],
                data.get("contact_phone", ""),
                data["item_description"],
                data.get("item_category", "other"),
                data.get("item_color", ""),
                data.get("item_brand", ""),
                data.get("location_last_seen", ""),
                data.get("time_last_seen", ""),
                data.get("optional_photo_path"),
                data.get("status", "active"),
                data.get("created_at", datetime.utcnow().isoformat()),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return case_id


def get_all_lost_reports(status_filter: Optional[str] = None) -> list[dict]:
    """Return all lost reports, optionally filtered by status."""
    conn = _get_connection()
    try:
        if status_filter:
            rows = conn.execute(
                "SELECT * FROM lost_reports WHERE status = ? ORDER BY created_at DESC", (status_filter,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM lost_reports ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_lost_report(case_id: str) -> Optional[dict]:
    """Return a single lost report by case_id."""
    conn = _get_connection()
    try:
        row = conn.execute("SELECT * FROM lost_reports WHERE case_id = ?", (case_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_lost_report_status(case_id: str, status: str) -> None:
    """Update the status of a lost report."""
    conn = _get_connection()
    try:
        conn.execute("UPDATE lost_reports SET status = ? WHERE case_id = ?", (status, case_id))
        conn.commit()
    finally:
        conn.close()


def delete_lost_report(case_id: str) -> None:
    """Delete a lost report."""
    conn = _get_connection()
    try:
        conn.execute("DELETE FROM lost_reports WHERE case_id = ?", (case_id,))
        conn.commit()
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════
# FOUND ITEMS CRUD
# ═══════════════════════════════════════════════════════════════════

def insert_found_item(data: dict) -> str:
    """Insert a found item and return the found_id."""
    conn = _get_connection()
    found_id = data.get("found_id", str(uuid4()))
    try:
        conn.execute(
            """INSERT INTO found_items
               (found_id, staff_id, item_description, item_category, item_color,
                item_brand, location_found, time_found, photo_path,
                optional_notes, status, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                found_id,
                data["staff_id"],
                data.get("item_description", ""),
                data.get("item_category", "other"),
                data.get("item_color", ""),
                data.get("item_brand", ""),
                data.get("location_found", ""),
                data.get("time_found", ""),
                data.get("photo_path"),
                data.get("optional_notes", ""),
                data.get("status", "unclaimed"),
                data.get("created_at", datetime.utcnow().isoformat()),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return found_id


def get_all_found_items(status_filter: Optional[str] = None) -> list[dict]:
    """Return all found items, optionally filtered by status."""
    conn = _get_connection()
    try:
        if status_filter:
            rows = conn.execute(
                "SELECT * FROM found_items WHERE status = ? ORDER BY created_at DESC", (status_filter,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM found_items ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_found_item(found_id: str) -> Optional[dict]:
    """Return a single found item by found_id."""
    conn = _get_connection()
    try:
        row = conn.execute("SELECT * FROM found_items WHERE found_id = ?", (found_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_found_item_status(found_id: str, status: str) -> None:
    """Update the status of a found item."""
    conn = _get_connection()
    try:
        conn.execute("UPDATE found_items SET status = ? WHERE found_id = ?", (status, found_id))
        conn.commit()
    finally:
        conn.close()


def delete_found_item(found_id: str) -> None:
    """Delete a found item."""
    conn = _get_connection()
    try:
        conn.execute("DELETE FROM found_items WHERE found_id = ?", (found_id,))
        conn.commit()
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════
# MATCH RESULTS CRUD
# ═══════════════════════════════════════════════════════════════════

def insert_match_result(data: dict) -> str:
    """Insert or update a match result. Prevents duplicates for same lost+found pair."""
    conn = _get_connection()
    match_id = data.get("match_id", str(uuid4()))
    try:
        conn.execute(
            """INSERT OR REPLACE INTO match_results
               (match_id, lost_case_id, found_item_id, confidence_score,
                match_reasons, status, reviewed_by, reviewed_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                match_id,
                data["lost_case_id"],
                data["found_item_id"],
                data["confidence_score"],
                data.get("match_reasons", "[]"),
                data.get("status", "pending"),
                data.get("reviewed_by"),
                data.get("reviewed_at"),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return match_id


def get_all_match_results(status_filter: Optional[str] = None) -> list[dict]:
    """Return all match results, optionally filtered by status."""
    conn = _get_connection()
    try:
        if status_filter:
            rows = conn.execute(
                "SELECT * FROM match_results WHERE status = ? ORDER BY confidence_score DESC",
                (status_filter,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM match_results ORDER BY confidence_score DESC"
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_matches_for_lost_report(case_id: str) -> list[dict]:
    """Return all matches for a specific lost report."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM match_results WHERE lost_case_id = ? ORDER BY confidence_score DESC",
            (case_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_match_status(match_id: str, status: str, reviewed_by: str = "") -> None:
    """Update match status (confirm/reject) and record reviewer."""
    conn = _get_connection()
    try:
        conn.execute(
            "UPDATE match_results SET status = ?, reviewed_by = ?, reviewed_at = ? WHERE match_id = ?",
            (status, reviewed_by, datetime.utcnow().isoformat(), match_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_match_result(match_id: str) -> None:
    """Delete a match result."""
    conn = _get_connection()
    try:
        conn.execute("DELETE FROM match_results WHERE match_id = ?", (match_id,))
        conn.commit()
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════
# NOTIFICATIONS LOG CRUD
# ═══════════════════════════════════════════════════════════════════

def insert_notification(data: dict) -> str:
    """Insert a notification log entry and return the notification_id."""
    conn = _get_connection()
    notification_id = data.get("notification_id", str(uuid4()))
    try:
        conn.execute(
            """INSERT INTO notifications_log
               (notification_id, case_id, match_id, passenger_email,
                confidence_score, found_item_description, message, sent_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                notification_id,
                data["case_id"],
                data["match_id"],
                data["passenger_email"],
                data["confidence_score"],
                data.get("found_item_description", ""),
                data.get("message", ""),
                data.get("sent_at", datetime.utcnow().isoformat()),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return notification_id


def get_all_notifications() -> list[dict]:
    """Return all notification log entries."""
    conn = _get_connection()
    try:
        rows = conn.execute("SELECT * FROM notifications_log ORDER BY sent_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════
# DEMO DATA SEEDING
# ═══════════════════════════════════════════════════════════════════

def seed_demo_data() -> None:
    """Seed the database with 5 sample lost reports and 5 found items."""
    conn = _get_connection()
    existing = conn.execute("SELECT COUNT(*) FROM lost_reports").fetchone()[0]
    conn.close()
    if existing > 0:
        return  # already seeded

    now = datetime.utcnow()

    lost_reports = [
        {
            "case_id": "a1b2c3d4-0001-4000-8000-000000000001",
            "passenger_name": "Ahmed Hassan",
            "contact_email": "ahmed.hassan@email.com",
            "contact_phone": "+201001234567",
            "item_description": "Black leather wallet with gold initials AH engraved on the front. Contains credit cards and Egyptian ID.",
            "item_category": "wallet",
            "item_color": "black",
            "item_brand": "Montblanc",
            "location_last_seen": "Terminal 2",
            "time_last_seen": (now - timedelta(hours=6)).isoformat(),
            "status": "active",
            "created_at": (now - timedelta(hours=5)).isoformat(),
        },
        {
            "case_id": "a1b2c3d4-0002-4000-8000-000000000002",
            "passenger_name": "Sarah Johnson",
            "contact_email": "sarah.j@email.com",
            "contact_phone": "+14155551234",
            "item_description": "Silver MacBook Pro 14-inch with a blue laptop sleeve. Has a sticker of a cat on the back cover.",
            "item_category": "laptop",
            "item_color": "silver",
            "item_brand": "Apple",
            "location_last_seen": "Gates B",
            "time_last_seen": (now - timedelta(hours=12)).isoformat(),
            "status": "active",
            "created_at": (now - timedelta(hours=10)).isoformat(),
        },
        {
            "case_id": "a1b2c3d4-0003-4000-8000-000000000003",
            "passenger_name": "Mohamed Ali",
            "contact_email": "m.ali@email.com",
            "contact_phone": "+971501234567",
            "item_description": "Expensive gold watch with scratches on the face. Might be a Rolex or similar luxury brand.",
            "item_category": "watch",
            "item_color": "gold",
            "item_brand": "unknown",
            "location_last_seen": "Security",
            "time_last_seen": (now - timedelta(hours=24)).isoformat(),
            "status": "active",
            "created_at": (now - timedelta(hours=22)).isoformat(),
        },
        {
            "case_id": "a1b2c3d4-0004-4000-8000-000000000004",
            "passenger_name": "Emma Wilson",
            "contact_email": "emma.w@email.com",
            "contact_phone": "+447911123456",
            "item_description": "Navy blue rolling suitcase, medium size, with a red ribbon tied to the handle. Brand is Samsonite.",
            "item_category": "luggage",
            "item_color": "blue",
            "item_brand": "Samsonite",
            "location_last_seen": "Baggage Claim",
            "time_last_seen": (now - timedelta(hours=8)).isoformat(),
            "status": "active",
            "created_at": (now - timedelta(hours=7)).isoformat(),
        },
        {
            "case_id": "a1b2c3d4-0005-4000-8000-000000000005",
            "passenger_name": "Yuki Tanaka",
            "contact_email": "yuki.t@email.com",
            "contact_phone": "+81901234567",
            "item_description": "White AirPods Pro case, 2nd generation. Has a small Hello Kitty keychain attached.",
            "item_category": "headphones",
            "item_color": "white",
            "item_brand": "Apple",
            "location_last_seen": "Lounge",
            "time_last_seen": (now - timedelta(hours=3)).isoformat(),
            "status": "active",
            "created_at": (now - timedelta(hours=2)).isoformat(),
        },
    ]

    found_items = [
        {
            "found_id": "f1e2d3c4-0001-4000-8000-000000000001",
            "staff_id": "STAFF-101",
            "item_description": "Black leather billfold wallet with gold monogram. Found on seat at gate B7. Contains multiple cards.",
            "item_category": "wallet",
            "item_color": "black",
            "item_brand": "Montblanc",
            "location_found": "Terminal 2",
            "time_found": (now - timedelta(hours=5, minutes=30)).isoformat(),
            "optional_notes": "Found under seat at gate B7. Looks high-end.",
            "status": "unclaimed",
            "created_at": (now - timedelta(hours=5)).isoformat(),
        },
        {
            "found_id": "f1e2d3c4-0002-4000-8000-000000000002",
            "staff_id": "STAFF-204",
            "item_description": "Rolex Submariner, gold with minor surface wear on crystal. Clasp is slightly loose.",
            "item_category": "watch",
            "item_color": "gold",
            "item_brand": "Rolex",
            "location_found": "Security",
            "time_found": (now - timedelta(hours=23)).isoformat(),
            "optional_notes": "Found in a tray at security checkpoint 3.",
            "status": "unclaimed",
            "created_at": (now - timedelta(hours=22, minutes=30)).isoformat(),
        },
        {
            "found_id": "f1e2d3c4-0003-4000-8000-000000000003",
            "staff_id": "STAFF-107",
            "item_description": "Dark blue Samsonite carry-on suitcase with wheels. Red fabric ribbon on handle. Some scuff marks.",
            "item_category": "luggage",
            "item_color": "navy blue",
            "item_brand": "Samsonite",
            "location_found": "Baggage Claim",
            "time_found": (now - timedelta(hours=7, minutes=45)).isoformat(),
            "optional_notes": "Left on carousel 3 after last flight cleared.",
            "status": "unclaimed",
            "created_at": (now - timedelta(hours=7)).isoformat(),
        },
        {
            "found_id": "f1e2d3c4-0004-4000-8000-000000000004",
            "staff_id": "STAFF-305",
            "item_description": "iPhone 15 Pro Max in titanium finish. Cracked screen protector. No phone case.",
            "item_category": "phone",
            "item_color": "titanium",
            "item_brand": "Apple",
            "location_found": "Food Court",
            "time_found": (now - timedelta(hours=4)).isoformat(),
            "optional_notes": "Found on a table near Starbucks. Phone is locked.",
            "status": "unclaimed",
            "created_at": (now - timedelta(hours=3, minutes=30)).isoformat(),
        },
        {
            "found_id": "f1e2d3c4-0005-4000-8000-000000000005",
            "staff_id": "STAFF-102",
            "item_description": "White Apple AirPods Pro charging case. Has a small cartoon character keychain (pink/white).",
            "item_category": "headphones",
            "item_color": "white",
            "item_brand": "Apple",
            "location_found": "Lounge",
            "time_found": (now - timedelta(hours=2, minutes=30)).isoformat(),
            "optional_notes": "Found between couch cushions in the VIP lounge.",
            "status": "unclaimed",
            "created_at": (now - timedelta(hours=2)).isoformat(),
        },
    ]

    for report in lost_reports:
        insert_lost_report(report)

    for item in found_items:
        insert_found_item(item)
