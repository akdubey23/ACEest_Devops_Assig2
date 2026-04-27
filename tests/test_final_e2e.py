"""
Final end-to-end API coverage (ACEest Fitness & Gym).
Uses an isolated temporary SQLite DB per test run.
Exercises every HTTP route in app.py in a single realistic flow.
"""

import importlib
import os
import sys


def _make_client(tmp_path):
    db_path = tmp_path / "test_aceest_e2e.db"
    os.environ["ACEEST_DB_PATH"] = str(db_path)
    sys.modules.pop("app", None)
    app_module = importlib.import_module("app")
    return app_module.app.test_client()


def test_final_end_to_end_api_coverage(tmp_path):
    """
    Full-stack flow: discovery, programs, clients CRUD, CSV, PDF, workouts,
    aggregate + per-client analytics, metrics, BMI, auth, AI program, membership.
    """
    client = _make_client(tmp_path)
    name = "E2EClient"

    # --- Discovery (GET /) ---
    home = client.get("/")
    assert home.status_code == 200
    home_j = home.get_json()
    assert home_j.get("phase") == 10
    assert "Aceestver-3.2.4.py" in home_j.get("version_source", "")
    ep = home_j.get("endpoints", [])
    assert "/health" in ep and "/programs" in ep

    # 1. Health check
    h = client.get("/health")
    assert h.status_code == 200
    assert h.get_json()["status"] == "ok"

    # Programs catalog (GET /programs, GET /programs/<name>)
    pr = client.get("/programs")
    assert pr.status_code == 200
    prog_names = [p["name"] for p in pr.get_json()["programs"]]
    assert "Fat Loss (FL)" in prog_names
    pr_one = client.get("/programs/Fat Loss (FL)")
    assert pr_one.status_code == 200
    assert "workout" in pr_one.get_json()

    # 2. Create client
    create = client.post(
        "/clients",
        json={
            "name": name,
            "age": 28,
            "height_cm": 170.0,
            "weight_kg": 70.0,
            "program": "Fat Loss (FL)",
            "adherence": 75,
            "notes": "initial",
            "target_weight_kg": 62.0,
            "target_adherence": 90,
            "membership_status": "Active",
            "membership_end": "2026-12-31",
        },
    )
    assert create.status_code == 201

    # List clients (GET /clients)
    lst = client.get("/clients")
    assert lst.status_code == 200
    assert any(c["name"] == name for c in lst.get_json()["clients"])

    # 3. Get client
    g = client.get(f"/clients/{name}")
    assert g.status_code == 200
    assert g.get_json()["client"]["name"] == name

    # 4. Update client (PATCH)
    p1 = client.patch(
        f"/clients/{name}",
        json={"weight_kg": 68.0, "notes": "after patch", "adherence": 80},
    )
    assert p1.status_code == 200
    assert p1.get_json()["client"]["notes"] == "after patch"
    p2 = client.patch(f"/clients/{name}", json={"adherence": 85})
    assert p2.status_code == 200

    # Workouts (POST /workouts, GET /workouts) — before metrics / BMI
    w_resp = client.post(
        "/workouts",
        json={
            "client_name": name,
            "date": "2026-04-01",
            "workout_type": "Strength",
            "duration_min": 45,
            "notes": "e2e session",
            "exercises": [{"name": "Squat", "sets": 3, "reps": 5, "weight": 60.0}],
        },
    )
    assert w_resp.status_code == 201
    list_w = client.get(f"/workouts?client_name={name}")
    assert list_w.status_code == 200
    workouts = list_w.get_json()["workouts"]
    assert len(workouts) >= 1
    assert workouts[0]["workout_type"] == "Strength"

    # 5. Export CSV
    csv_resp = client.get("/clients/export.csv")
    assert csv_resp.status_code == 200
    assert "text/csv" in csv_resp.headers.get("Content-Type", "")
    assert name in csv_resp.get_data(as_text=True)

    # 6. Generate PDF (binary magic)
    pdf_resp = client.get(f"/clients/{name}/report.pdf")
    assert pdf_resp.status_code == 200
    assert "pdf" in pdf_resp.headers.get("Content-Type", "").lower()
    assert pdf_resp.get_data()[:4] == b"%PDF"

    # Aggregate adherence chart (GET /analytics/adherence)
    agg = client.get("/analytics/adherence")
    assert agg.status_code == 200
    agg_j = agg.get_json()
    assert name in agg_j["labels"]
    assert len(agg_j["values"]) == len(agg_j["labels"])

    # 7. Per-client adherence series (GET /analytics/adherence/<client_name>)
    ad = client.get(f"/analytics/adherence/{name}")
    assert ad.status_code == 200
    series = ad.get_json()["series"]
    assert len(series) >= 2

    # Metrics for weight trend + BMI
    assert (
        client.post(
            "/metrics",
            json={
                "client_name": name,
                "date": "2026-04-01",
                "weight": 68.0,
                "waist": 80.0,
                "bodyfat": 20.0,
            },
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/metrics",
            json={
                "client_name": name,
                "date": "2026-04-02",
                "weight": 67.5,
                "waist": 79.5,
                "bodyfat": 19.5,
            },
        ).status_code
        == 201
    )

    # 8. Weight trend
    wt = client.get(f"/analytics/weight-trend?client_name={name}")
    assert wt.status_code == 200
    assert len(wt.get_json()["series"]) >= 2

    # 9. BMI
    bmi = client.get(f"/bmi?client_name={name}")
    assert bmi.status_code == 200
    bj = bmi.get_json()
    assert "bmi" in bj and "category" in bj and "risk" in bj

    # 10. Auth login
    login = client.post("/auth/login", json={"username": "admin", "password": "admin"})
    assert login.status_code == 200
    assert login.get_json()["role"] == "Admin"

    # 11. AI program
    ai = client.post("/ai/program", json={"client_name": name, "experience": "beginner"})
    assert ai.status_code == 200
    ai_j = ai.get_json()
    assert "focus" in ai_j and len(ai_j["plan"]) >= 1
    assert "day" in ai_j["plan"][0] and "exercise" in ai_j["plan"][0]

    # 12. Membership status
    ms = client.get(f"/membership/status?client_name={name}")
    assert ms.status_code == 200
    mj = ms.get_json()
    assert mj["membership_status"] == "Active"
    assert mj["membership_end"] == "2026-12-31"
