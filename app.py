from __future__ import annotations

import csv
import io
import os
import random
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from flask import Flask, jsonify, request, Response


app = Flask(__name__)


# -------------------------
# Phase 1 (Aceestver-1.0.py)
# -------------------------
# Baseline program catalog: workout + diet plan per program.

PROGRAMS: dict[str, dict[str, Any]] = {
    "Fat Loss (FL)": {
        "workout": (
            "Mon: 5x5 Back Squat + AMRAP\n"
            "Tue: EMOM 20min Assault Bike\n"
            "Wed: Bench Press + 21-15-9\n"
            "Thu: 10RFT Deadlifts/Box Jumps\n"
            "Fri: 30min Active Recovery"
        ),
        "diet": (
            "B: 3 Egg Whites + Oats Idli\n"
            "L: Grilled Chicken + Brown Rice\n"
            "D: Fish Curry + Millet Roti\n"
            "Target: 2,000 kcal"
        ),
        "color": "#e74c3c",
    },
    "Muscle Gain (MG)": {
        "workout": (
            "Mon: Squat 5x5\n"
            "Tue: Bench 5x5\n"
            "Wed: Deadlift 4x6\n"
            "Thu: Front Squat 4x8\n"
            "Fri: Incline Press 4x10\n"
            "Sat: Barbell Rows 4x10"
        ),
        "diet": (
            "B: 4 Eggs + PB Oats\n"
            "L: Chicken Biryani (250g Chicken)\n"
            "D: Mutton Curry + Jeera Rice\n"
            "Target: 3,200 kcal"
        ),
        "color": "#2ecc71",
    },
    "Beginner (BG)": {
        "workout": (
            "Circuit Training: Air Squats, Ring Rows, Push-ups.\n"
            "Focus: Technique Mastery & Form (90% Threshold)"
        ),
        "diet": (
            "Balanced Tamil Meals: Idli-Sambar, Rice-Dal, Chapati.\n"
            "Protein: 120g/day"
        ),
        "color": "#3498db",
    },
}


# -------------------------
# Phase 2 (Aceestver1.1.2.py)
# -------------------------
# In-memory client capture + CSV export + adherence chart data.
# Calorie factors are internal-only and used to return estimated_calories in client responses.

PROGRAM_CALORIE_FACTOR: dict[str, int] = {
    "Fat Loss (FL)": 22,
    "Muscle Gain (MG)": 35,
    "Beginner (BG)": 26,
}

# -------------------------
# Phase 4 (Aceestver2.0.1.py)
# -------------------------
# Replace in-memory client store with SQLite persistence.

DB_PATH = os.environ.get("ACEEST_DB_PATH", "aceest_fitness.db")


@contextmanager
def _db():
    """
    Yield a SQLite connection and always close it (avoids ResourceWarning leaks).
    Commits on success, rolls back on exception.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with _db() as conn:
        # Phase 4 schema (Aceestver2.0.1.py-inspired), with assignment constraints:
        # - Do not store calories (derived field only)
        # - Do not enforce UNIQUE on name (id is the primary key)
        #
        # Ensure base clients table exists (Phase 4+). We keep calories derived only.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                age INTEGER,
                height_cm REAL,
                weight REAL,
                program TEXT,
                adherence INTEGER,
                notes TEXT,
                target_weight_kg REAL,
                target_adherence INTEGER
            )
            """
        )

        # Older DB files (e.g. from Tkinter prototypes) may already have `clients` with fewer
        # columns. CREATE TABLE IF NOT EXISTS does not upgrade them — add missing columns.
        _client_cols = {r["name"] for r in conn.execute("PRAGMA table_info(clients)").fetchall()}
        for col_name, col_type in (
            ("name", "TEXT"),
            ("age", "INTEGER"),
            ("height_cm", "REAL"),
            ("weight", "REAL"),
            ("program", "TEXT"),
            ("adherence", "INTEGER"),
            ("notes", "TEXT"),
            ("target_weight_kg", "REAL"),
            ("target_adherence", "INTEGER"),
        ):
            if col_name not in _client_cols:
                conn.execute(f"ALTER TABLE clients ADD COLUMN {col_name} {col_type}")
                _client_cols.add(col_name)

        # Tkinter-era DBs often store height as `height`; map into `height_cm` when both exist.
        if "height" in _client_cols and "height_cm" in _client_cols:
            conn.execute(
                "UPDATE clients SET height_cm = height "
                "WHERE (height_cm IS NULL OR height_cm = 0) AND height IS NOT NULL AND height != 0"
            )

        # Phase 8 (Aceestver-3.1.2.py): add membership_expiry field (do not drop data)
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(clients)").fetchall()]
        if "membership_expiry" not in cols:
            conn.execute("ALTER TABLE clients ADD COLUMN membership_expiry TEXT")

        # Phase 9 (Aceestver-3.2.4.py): refactor membership fields
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(clients)").fetchall()]
        if "membership_status" not in cols:
            conn.execute("ALTER TABLE clients ADD COLUMN membership_status TEXT")
        if "membership_end" not in cols:
            conn.execute("ALTER TABLE clients ADD COLUMN membership_end TEXT")

        # Backfill: carry forward any existing membership_expiry values.
        if "membership_expiry" in cols:
            conn.execute(
                "UPDATE clients SET membership_end = membership_expiry "
                "WHERE (membership_end IS NULL OR membership_end = '') "
                "AND membership_expiry IS NOT NULL AND membership_expiry != ''"
            )
        # Default status for existing rows if missing
        conn.execute(
            "UPDATE clients SET membership_status = 'Active' "
            "WHERE membership_status IS NULL OR membership_status = ''"
        )

        # Phase 6 (Aceestver-2.2.1.py): progress table for charting
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT,
                week TEXT,
                adherence INTEGER
            )
            """
        )

        # Phase 7 (Aceestver-2.2.4.py): workouts, exercises, and metrics tables
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS workouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT,
                date TEXT,
                workout_type TEXT,
                duration_min INTEGER,
                notes TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workout_id INTEGER,
                name TEXT,
                sets INTEGER,
                reps INTEGER,
                weight REAL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT,
                date TEXT,
                weight REAL,
                waist REAL,
                bodyfat REAL
            )
            """
        )

        # Phase 8 (Aceestver-3.1.2.py): users table for login
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT,
                role TEXT
            )
            """
        )
        conn.execute(
            "INSERT OR IGNORE INTO users (username, password, role) VALUES ('admin','admin','Admin')"
        )


init_db()


@dataclass
class Client:
    name: str
    age: int = 0
    height_cm: float = 0.0
    weight_kg: float = 0.0
    program: str = ""
    adherence: int = 0
    notes: str = ""
    target_weight_kg: float = 0.0
    target_adherence: int = 0
    membership_status: str = "Active"
    membership_end: str = ""

    def to_dict(self) -> dict[str, Any]:
        estimated_calories = None
        if self.weight_kg > 0 and self.program in PROGRAM_CALORIE_FACTOR:
            estimated_calories = int(self.weight_kg * PROGRAM_CALORIE_FACTOR[self.program])
        return {
            "name": self.name,
            "age": self.age,
            "weight_kg": self.weight_kg,
            "program": self.program,
            "adherence": self.adherence,
            "notes": self.notes,
            "estimated_calories": estimated_calories,
            "height_cm": self.height_cm,
            "target_weight_kg": self.target_weight_kg,
            "target_adherence": self.target_adherence,
            "membership_status": self.membership_status,
            "membership_end": self.membership_end,
        }


@dataclass(frozen=True)
class ApiError(Exception):
    status_code: int
    message: str


@app.errorhandler(ApiError)
def handle_api_error(err: ApiError):
    return jsonify({"error": err.message}), err.status_code


@app.get("/")
def home():
    return jsonify(
        {
            "service": "ACEest Fitness & Gym API",
            "phase": 10,
            "version_source": "Aceestver-3.2.4.py",
            "endpoints": [
                "/health",
                "/programs",
                "/programs/<name>",
                "/clients",
                "/clients/<name>",
                "PATCH /clients/<name>",
                "/clients/export.csv",
                "/clients/<name>/report.pdf",
                "/analytics/adherence",
                "/analytics/adherence/<client_name>",
                "/workouts",
                "/workouts?client_name=",
                "/metrics",
                "/analytics/weight-trend?client_name=",
                "/bmi?client_name=",
                "/auth/login",
                "/ai/program",
                "/membership/status?client_name=",
            ],
        }
    )


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/programs")
def list_programs():
    return jsonify({"programs": [{"name": name, **data} for name, data in PROGRAMS.items()]})


@app.get("/programs/<string:name>")
def get_program(name: str):
    if name not in PROGRAMS:
        raise ApiError(404, f"Program not found: {name}")
    return jsonify({"name": name, **PROGRAMS[name]})


@app.get("/clients")
def list_clients():
    with _db() as conn:
        rows = conn.execute(
            "SELECT id, name, age, height_cm, weight, program, adherence, notes, "
            "target_weight_kg, target_adherence, membership_status, membership_end "
            "FROM clients ORDER BY name, id"
        ).fetchall()
    clients: list[dict[str, Any]] = []
    for r in rows:
        program = r["program"] or ""
        weight_kg = float(r["weight"] or 0.0)
        estimated_calories = None
        if weight_kg > 0 and program in PROGRAM_CALORIE_FACTOR:
            estimated_calories = int(weight_kg * PROGRAM_CALORIE_FACTOR[program])
        clients.append(
            {
                "name": r["name"],
                "age": r["age"] or 0,
                "height_cm": float(r["height_cm"] or 0.0),
                "weight_kg": weight_kg,
                "program": program,
                "adherence": int(r["adherence"] or 0),
                "notes": r["notes"] or "",
                "estimated_calories": estimated_calories,
                "target_weight_kg": float(r["target_weight_kg"] or 0.0),
                "target_adherence": int(r["target_adherence"] or 0),
                "membership_status": r["membership_status"] or "Active",
                "membership_end": r["membership_end"] or "",
            }
        )
    return jsonify({"clients": clients})


@app.post("/clients")
def save_client():
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name") or "").strip()
    program = str(payload.get("program") or "").strip()
    if not name or not program:
        raise ApiError(400, "Fields 'name' and 'program' are required")
    if program not in PROGRAMS:
        raise ApiError(400, f"Unknown program: {program}")

    age = int(payload.get("age") or 0)
    height_cm = float(payload.get("height_cm") or 0.0)
    weight_kg = float(payload.get("weight_kg") or 0.0)
    adherence = int(payload.get("adherence") or 0)
    notes = str(payload.get("notes") or "")
    target_weight_kg = float(payload.get("target_weight_kg") or 0.0)
    target_adherence = int(payload.get("target_adherence") or 0)
    membership_status = str(payload.get("membership_status") or "").strip() or "Active"
    membership_end = str(payload.get("membership_end") or "")

    with _db() as conn:
        conn.execute(
            """
            INSERT INTO clients (
              name, age, height_cm, weight, program, adherence, notes, target_weight_kg, target_adherence,
              membership_status, membership_end
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                age,
                height_cm,
                weight_kg,
                program,
                adherence,
                notes,
                target_weight_kg,
                target_adherence,
                membership_status,
                membership_end,
            ),
        )

        # Phase 6 support: capture adherence into progress history for charting
        week = datetime.now().strftime("Week %U - %Y")
        conn.execute(
            "INSERT INTO progress (client_name, week, adherence) VALUES (?, ?, ?)",
            (name, week, adherence),
        )

    client = Client(
        name=name,
        age=age,
        height_cm=height_cm,
        weight_kg=weight_kg,
        program=program,
        adherence=adherence,
        notes=notes,
        target_weight_kg=target_weight_kg,
        target_adherence=target_adherence,
        membership_status=membership_status,
        membership_end=membership_end,
    )
    return jsonify({"client": client.to_dict()}), 201


@app.get("/clients/<string:name>")
def get_client(name: str):
    with _db() as conn:
        r = conn.execute(
            "SELECT id, name, age, height_cm, weight, program, adherence, notes, "
            "target_weight_kg, target_adherence, membership_status, membership_end "
            "FROM clients WHERE name=? ORDER BY id DESC LIMIT 1",
            (name,),
        ).fetchone()
    if not r:
        raise ApiError(404, f"Client not found: {name}")
    program = r["program"] or ""
    weight_kg = float(r["weight"] or 0.0)
    estimated_calories = None
    if weight_kg > 0 and program in PROGRAM_CALORIE_FACTOR:
        estimated_calories = int(weight_kg * PROGRAM_CALORIE_FACTOR[program])
    return jsonify(
        {
            "client": {
                "name": r["name"],
                "age": r["age"] or 0,
                "height_cm": float(r["height_cm"] or 0.0),
                "weight_kg": weight_kg,
                "program": program,
                "adherence": int(r["adherence"] or 0),
                "notes": r["notes"] or "",
                "estimated_calories": estimated_calories,
                "target_weight_kg": float(r["target_weight_kg"] or 0.0),
                "target_adherence": int(r["target_adherence"] or 0),
                "membership_status": r["membership_status"] or "Active",
                "membership_end": r["membership_end"] or "",
            }
        }
    )


@app.patch("/clients/<string:name>")
def update_client(name: str):
    """Partial update of the latest client row for this name."""
    payload = request.get_json(silent=True) or {}
    with _db() as conn:
        r = conn.execute(
            "SELECT id, name, age, height_cm, weight, program, adherence, notes, "
            "target_weight_kg, target_adherence, membership_status, membership_end "
            "FROM clients WHERE name=? ORDER BY id DESC LIMIT 1",
            (name,),
        ).fetchone()
    if not r:
        raise ApiError(404, f"Client not found: {name}")

    def _coerce_int(key: str, current: int) -> int:
        if key not in payload:
            return current
        return int(payload[key] or 0)

    def _coerce_float(key: str, current: float) -> float:
        if key not in payload:
            return current
        return float(payload[key] or 0.0)

    def _coerce_str(key: str, current: str) -> str:
        if key not in payload:
            return current
        return str(payload[key] or "")

    age = _coerce_int("age", int(r["age"] or 0))
    height_cm = _coerce_float("height_cm", float(r["height_cm"] or 0.0))
    weight_kg = _coerce_float("weight_kg", float(r["weight"] or 0.0))
    notes = _coerce_str("notes", r["notes"] or "")
    target_weight_kg = _coerce_float("target_weight_kg", float(r["target_weight_kg"] or 0.0))
    target_adherence = _coerce_int("target_adherence", int(r["target_adherence"] or 0))
    membership_status = _coerce_str("membership_status", r["membership_status"] or "Active").strip() or "Active"
    membership_end = _coerce_str("membership_end", r["membership_end"] or "")

    program = str(r["program"] or "")
    if "program" in payload:
        program = str(payload.get("program") or "").strip()
        if not program:
            raise ApiError(400, "Field 'program' cannot be empty")
        if program not in PROGRAMS:
            raise ApiError(400, f"Unknown program: {program}")

    adherence = _coerce_int("adherence", int(r["adherence"] or 0))

    with _db() as conn:
        conn.execute(
            """
            UPDATE clients SET
              age=?, height_cm=?, weight=?, program=?, adherence=?, notes=?,
              target_weight_kg=?, target_adherence=?, membership_status=?, membership_end=?
            WHERE id=?
            """,
            (
                age,
                height_cm,
                weight_kg,
                program,
                adherence,
                notes,
                target_weight_kg,
                target_adherence,
                membership_status,
                membership_end,
                r["id"],
            ),
        )
        if "adherence" in payload:
            week = datetime.now().strftime("Week %U - %Y")
            conn.execute(
                "INSERT INTO progress (client_name, week, adherence) VALUES (?, ?, ?)",
                (name, week, adherence),
            )

    return get_client(name)


@app.get("/clients/export.csv")
def export_clients_csv():
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Name", "Age", "Weight", "Program", "Adherence", "Notes"])
    with _db() as conn:
        rows = conn.execute(
            "SELECT id, name, age, weight, program, adherence, notes FROM clients ORDER BY name, id"
        ).fetchall()
    for r in rows:
        writer.writerow(
            [
                r["name"],
                r["age"] or 0,
                float(r["weight"] or 0.0),
                r["program"] or "",
                int(r["adherence"] or 0),
                r["notes"] or "",
            ]
        )
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=clients.csv"},
    )


@app.get("/analytics/adherence")
def adherence_chart_data():
    with _db() as conn:
        rows = conn.execute("SELECT name, adherence FROM clients ORDER BY name").fetchall()
    return jsonify({"labels": [r["name"] for r in rows], "values": [int(r["adherence"] or 0) for r in rows]})


# -------------------------
# Phase 6 (Aceestver-2.2.1.py)
# -------------------------


@app.get("/analytics/adherence/<string:client_name>")
def adherence_series(client_name: str):
    with _db() as conn:
        rows = conn.execute(
            "SELECT week, adherence FROM progress WHERE client_name=? ORDER BY id",
            (client_name,),
        ).fetchall()
    return jsonify(
        {
            "client": client_name,
            "series": [{"week": r["week"], "adherence": int(r["adherence"] or 0)} for r in rows],
        }
    )


# -------------------------
# Phase 7 (Aceestver-2.2.4.py)
# -------------------------


@app.post("/workouts")
def create_workout():
    payload = request.get_json(silent=True) or {}
    client_name = str(payload.get("client_name") or "").strip()
    if not client_name:
        raise ApiError(400, "Field 'client_name' is required")

    workout_date = str(payload.get("date") or date.today().isoformat())
    workout_type = str(payload.get("workout_type") or "").strip()
    if not workout_type:
        raise ApiError(400, "Field 'workout_type' is required")

    duration_min = int(payload.get("duration_min") or 0)
    notes = str(payload.get("notes") or "")
    exercises = payload.get("exercises") or []

    with _db() as conn:
        cur = conn.execute(
            "INSERT INTO workouts (client_name, date, workout_type, duration_min, notes) VALUES (?,?,?,?,?)",
            (client_name, workout_date, workout_type, duration_min, notes),
        )
        workout_id = cur.lastrowid

        for ex in exercises:
            ex_name = str(ex.get("name") or "").strip()
            if not ex_name:
                continue
            conn.execute(
                "INSERT INTO exercises (workout_id, name, sets, reps, weight) VALUES (?,?,?,?,?)",
                (
                    workout_id,
                    ex_name,
                    int(ex.get("sets") or 0),
                    int(ex.get("reps") or 0),
                    float(ex.get("weight") or 0.0),
                ),
            )

    return jsonify({"workout_id": workout_id}), 201


@app.get("/workouts")
def list_workouts():
    client_name = str(request.args.get("client_name") or "").strip()
    if not client_name:
        raise ApiError(400, "Query param 'client_name' is required")

    with _db() as conn:
        rows = conn.execute(
            "SELECT id, date, workout_type, duration_min, notes "
            "FROM workouts WHERE client_name=? ORDER BY date DESC, id DESC",
            (client_name,),
        ).fetchall()

    return jsonify(
        {
            "client": client_name,
            "workouts": [
                {
                    "id": r["id"],
                    "date": r["date"],
                    "workout_type": r["workout_type"],
                    "duration_min": int(r["duration_min"] or 0),
                    "notes": r["notes"] or "",
                }
                for r in rows
            ],
        }
    )


@app.post("/metrics")
def create_metrics():
    payload = request.get_json(silent=True) or {}
    client_name = str(payload.get("client_name") or "").strip()
    if not client_name:
        raise ApiError(400, "Field 'client_name' is required")

    metrics_date = str(payload.get("date") or date.today().isoformat())
    weight = payload.get("weight")
    waist = payload.get("waist")
    bodyfat = payload.get("bodyfat")

    with _db() as conn:
        conn.execute(
            "INSERT INTO metrics (client_name, date, weight, waist, bodyfat) VALUES (?,?,?,?,?)",
            (client_name, metrics_date, weight, waist, bodyfat),
        )

    return jsonify({"status": "saved"}), 201


@app.get("/analytics/weight-trend")
def weight_trend():
    client_name = str(request.args.get("client_name") or "").strip()
    if not client_name:
        raise ApiError(400, "Query param 'client_name' is required")

    with _db() as conn:
        rows = conn.execute(
            "SELECT date, weight FROM metrics WHERE client_name=? AND weight IS NOT NULL ORDER BY date",
            (client_name,),
        ).fetchall()

    return jsonify({"client": client_name, "series": [{"date": r["date"], "weight": r["weight"]} for r in rows]})


@app.get("/bmi")
def bmi_info():
    client_name = str(request.args.get("client_name") or "").strip()
    if not client_name:
        raise ApiError(400, "Query param 'client_name' is required")

    with _db() as conn:
        r = conn.execute(
            "SELECT height_cm, weight FROM clients WHERE name=? ORDER BY id DESC LIMIT 1",
            (client_name,),
        ).fetchone()
    if not r:
        raise ApiError(404, f"Client not found: {client_name}")

    height_cm = float(r["height_cm"] or 0.0)
    weight_kg = float(r["weight"] or 0.0)
    if height_cm <= 0 or weight_kg <= 0:
        raise ApiError(400, "Client must have valid height_cm and weight_kg to compute BMI")

    h_m = height_cm / 100.0
    bmi = round(weight_kg / (h_m * h_m), 1)

    if bmi < 18.5:
        category = "Underweight"
        risk = "Potential nutrient deficiency, low energy."
    elif bmi < 25:
        category = "Normal"
        risk = "Low risk if active and strong."
    elif bmi < 30:
        category = "Overweight"
        risk = "Moderate risk; focus on adherence and progressive activity."
    else:
        category = "Obese"
        risk = "Higher risk; prioritize fat loss, consistency, and supervision."

    return jsonify({"client": client_name, "bmi": bmi, "category": category, "risk": risk})


# -------------------------
# Phase 8 (Aceestver-3.1.2.py)
# -------------------------


@app.post("/auth/login")
def auth_login():
    payload = request.get_json(silent=True) or {}
    username = str(payload.get("username") or "").strip()
    password = str(payload.get("password") or "").strip()
    if not username or not password:
        raise ApiError(400, "Fields 'username' and 'password' are required")

    with _db() as conn:
        row = conn.execute(
            "SELECT role FROM users WHERE username=? AND password=?",
            (username, password),
        ).fetchone()
    if not row:
        raise ApiError(401, "Invalid credentials")
    return jsonify({"username": username, "role": row["role"]})


@app.post("/ai/program")
def ai_program():
    payload = request.get_json(silent=True) or {}
    client_name = str(payload.get("client_name") or "").strip()
    experience = str(payload.get("experience") or "").strip().lower()
    if not client_name:
        raise ApiError(400, "Field 'client_name' is required")
    if experience not in {"beginner", "intermediate", "advanced"}:
        raise ApiError(400, "Field 'experience' must be beginner|intermediate|advanced")

    with _db() as conn:
        row = conn.execute(
            "SELECT program FROM clients WHERE name=? ORDER BY id DESC LIMIT 1",
            (client_name,),
        ).fetchone()
    if not row:
        raise ApiError(404, f"Client not found: {client_name}")
    program_name = row["program"] or ""

    exercises_pool = {
        "Hypertrophy": [
            "Leg Press",
            "Incline Dumbbell Press",
            "Lat Pulldown",
            "Lateral Raise",
            "Bicep Curl",
            "Tricep Extension",
        ],
        "Conditioning": [
            "Running",
            "Cycling",
            "Rowing",
            "Burpees",
            "Jump Rope",
            "Kettlebell Swings",
        ],
        "Full Body": [
            "Push-Up",
            "Pull-Up",
            "Lunge",
            "Plank",
            "Dumbbell Row",
            "Dumbbell Press",
        ],
    }

    focus = "Full Body"
    if "Fat Loss" in program_name:
        focus = "Conditioning"
    elif "Muscle Gain" in program_name:
        focus = "Hypertrophy"

    if experience == "beginner":
        sets_range, reps_range, days = (2, 3), (8, 12), 3
    elif experience == "intermediate":
        sets_range, reps_range, days = (3, 4), (8, 15), 4
    else:
        sets_range, reps_range, days = (4, 5), (6, 15), 5

    weekly_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"][:days]
    plan: list[dict[str, Any]] = []
    for day in weekly_days:
        exercises = random.sample(exercises_pool[focus], k=3 if days < 4 else 4)
        for ex in exercises:
            plan.append(
                {
                    "day": day,
                    "exercise": ex,
                    "sets": random.randint(*sets_range),
                    "reps": random.randint(*reps_range),
                }
            )

    return jsonify({"client": client_name, "focus": focus, "plan": plan})


@app.get("/clients/<string:name>/report.pdf")
def export_pdf_report(name: str):
    try:
        from fpdf import FPDF
        from fpdf.enums import XPos, YPos
    except Exception as e:  # pragma: no cover
        raise ApiError(500, f"PDF dependency missing (pip install fpdf2): {e}") from e

    with _db() as conn:
        row = conn.execute(
            "SELECT name, age, height_cm, weight, program, membership_status, membership_end "
            "FROM clients WHERE name=? ORDER BY id DESC LIMIT 1",
            (name,),
        ).fetchone()
    if not row:
        raise ApiError(404, f"Client not found: {name}")

    pdf = FPDF()
    pdf.add_page()
    # fpdf2 built-in fonts: Helvetica / Times / Courier (not Arial on all installs)
    nx, ny = XPos.LMARGIN, YPos.NEXT
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, f"Client Report - {row['name']}", new_x=nx, new_y=ny, align="C")
    pdf.set_font("Helvetica", "", 12)
    pdf.ln(10)
    pdf.cell(0, 10, f"Name: {row['name']}", new_x=nx, new_y=ny)
    pdf.cell(0, 10, f"Age: {row['age']}", new_x=nx, new_y=ny)
    pdf.cell(0, 10, f"Height: {row['height_cm']} cm", new_x=nx, new_y=ny)
    pdf.cell(0, 10, f"Weight: {row['weight']} kg", new_x=nx, new_y=ny)
    pdf.cell(0, 10, f"Program: {row['program']}", new_x=nx, new_y=ny)
    pdf.cell(0, 10, f"Membership: {row['membership_status'] or 'Active'}", new_x=nx, new_y=ny)
    pdf.cell(0, 10, f"Membership End: {row['membership_end'] or ''}", new_x=nx, new_y=ny)

    out = pdf.output()
    pdf_bytes = bytes(out) if out is not None else b""
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={name}_report.pdf"},
    )


@app.get("/membership/status")
def membership_status():
    client_name = str(request.args.get("client_name") or "").strip()
    if not client_name:
        raise ApiError(400, "Query param 'client_name' is required")

    with _db() as conn:
        row = conn.execute(
            "SELECT membership_status, membership_end "
            "FROM clients WHERE name=? ORDER BY id DESC LIMIT 1",
            (client_name,),
        ).fetchone()
    if not row:
        raise ApiError(404, f"Client not found: {client_name}")

    status = row["membership_status"] or "Active"
    end = row["membership_end"] or ""
    return jsonify({"client": client_name, "membership_status": status, "membership_end": end})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

