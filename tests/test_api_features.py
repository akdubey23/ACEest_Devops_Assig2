"""
BDD-style feature grouping for the ACEest Fitness API.
Each *class* is a logical feature (Cucumber-style); methods are scenarios.
Allure drives feature/story in Allure reports; class names drive JUnit / HTML dashboard.
"""

from __future__ import annotations

import allure


@allure.feature("Discovery & health")
class TestDiscoveryAndHealth:
    @allure.story("Service metadata")
    @allure.title("Home lists phase, version source, and key endpoints")
    def test_home_lists_endpoints(self, aceest_client):
        r = aceest_client.get("/")
        assert r.status_code == 200
        body = r.get_json()
        assert body.get("phase") == 10
        ep = body.get("endpoints", [])
        assert "/health" in ep and "/programs" in ep

    @allure.story("Liveness")
    @allure.title("Health endpoint returns ok")
    def test_health_ok(self, aceest_client):
        r = aceest_client.get("/health")
        assert r.status_code == 200
        assert r.get_json()["status"] == "ok"


@allure.feature("Programs catalog")
class TestProgramsCatalog:
    @allure.story("Catalog & detail")
    @allure.title("Programs list and single program return workout and diet")
    def test_programs_catalog_and_detail(self, aceest_client):
        r = aceest_client.get("/programs")
        assert r.status_code == 200
        names = [p["name"] for p in r.get_json()["programs"]]
        assert "Fat Loss (FL)" in names
        assert "Muscle Gain (MG)" in names
        one = aceest_client.get("/programs/Beginner (BG)")
        assert one.status_code == 200
        j = one.get_json()
        assert "workout" in j and "diet" in j


@allure.feature("Client management")
class TestClientManagement:
    @allure.story("Create & read")
    @allure.title("POST client then GET by name")
    def test_create_and_get_client(self, aceest_client):
        name = "FeatureClient1"
        c = aceest_client.post(
            "/clients",
            json={
                "name": name,
                "age": 30,
                "height_cm": 175.0,
                "weight_kg": 72.0,
                "program": "Fat Loss (FL)",
                "adherence": 70,
                "notes": "bdd",
                "target_weight_kg": 65.0,
                "target_adherence": 85,
                "membership_status": "Active",
                "membership_end": "2026-12-31",
            },
        )
        assert c.status_code == 201
        g = aceest_client.get(f"/clients/{name}")
        assert g.status_code == 200
        assert g.get_json()["client"]["name"] == name

    @allure.story("Update")
    @allure.title("PATCH client updates notes")
    def test_patch_client_updates_notes(self, aceest_client):
        name = "FeatureClient2"
        assert (
            aceest_client.post(
                "/clients",
                json={
                    "name": name,
                    "age": 25,
                    "height_cm": 160.0,
                    "weight_kg": 55.0,
                    "program": "Beginner (BG)",
                    "adherence": 60,
                    "notes": "before",
                    "target_weight_kg": 52.0,
                    "target_adherence": 80,
                    "membership_status": "Active",
                    "membership_end": "2026-06-01",
                },
            ).status_code
            == 201
        )
        p = aceest_client.patch(f"/clients/{name}", json={"notes": "after patch"})
        assert p.status_code == 200
        assert p.get_json()["client"]["notes"] == "after patch"

    @allure.story("Export")
    @allure.title("CSV export includes registered client")
    def test_csv_export_contains_client(self, aceest_client):
        name = "CsvFeatureClient"
        assert (
            aceest_client.post(
                "/clients",
                json={
                    "name": name,
                    "age": 40,
                    "height_cm": 180.0,
                    "weight_kg": 85.0,
                    "program": "Muscle Gain (MG)",
                    "adherence": 65,
                    "notes": "csv",
                    "target_weight_kg": 88.0,
                    "target_adherence": 75,
                    "membership_status": "Active",
                    "membership_end": "2027-01-01",
                },
            ).status_code
            == 201
        )
        csv_r = aceest_client.get("/clients/export.csv")
        assert csv_r.status_code == 200
        assert name in csv_r.get_data(as_text=True)


@allure.feature("Workouts")
class TestWorkouts:
    @allure.story("Logging")
    @allure.title("POST workout and list by client")
    def test_post_and_list_workout(self, aceest_client):
        name = "WorkoutClient"
        assert (
            aceest_client.post(
                "/clients",
                json={
                    "name": name,
                    "age": 32,
                    "height_cm": 172.0,
                    "weight_kg": 78.0,
                    "program": "Fat Loss (FL)",
                    "adherence": 80,
                    "notes": "w",
                    "target_weight_kg": 70.0,
                    "target_adherence": 90,
                    "membership_status": "Active",
                    "membership_end": "2026-08-01",
                },
            ).status_code
            == 201
        )
        w = aceest_client.post(
            "/workouts",
            json={
                "client_name": name,
                "date": "2026-04-01",
                "workout_type": "Cardio",
                "duration_min": 30,
                "notes": "treadmill",
                "exercises": [{"name": "Run", "sets": 1, "reps": 1, "weight": 0.0}],
            },
        )
        assert w.status_code == 201
        lst = aceest_client.get(f"/workouts?client_name={name}")
        assert lst.status_code == 200
        assert len(lst.get_json()["workouts"]) >= 1


@allure.feature("Analytics & PDF")
class TestAnalyticsAndReporting:
    @allure.story("Reporting")
    @allure.title("PDF report returns valid PDF bytes")
    def test_client_pdf_report(self, aceest_client):
        name = "PdfClient"
        assert (
            aceest_client.post(
                "/clients",
                json={
                    "name": name,
                    "age": 29,
                    "height_cm": 168.0,
                    "weight_kg": 62.0,
                    "program": "Beginner (BG)",
                    "adherence": 88,
                    "notes": "pdf",
                    "target_weight_kg": 58.0,
                    "target_adherence": 92,
                    "membership_status": "Active",
                    "membership_end": "2026-09-01",
                },
            ).status_code
            == 201
        )
        pdf = aceest_client.get(f"/clients/{name}/report.pdf")
        assert pdf.status_code == 200
        assert pdf.get_data()[:4] == b"%PDF"


@allure.feature("Security & membership")
class TestSecurityAndMembership:
    @allure.story("Authentication")
    @allure.title("Admin login returns Admin role")
    def test_auth_login_admin(self, aceest_client):
        r = aceest_client.post("/auth/login", json={"username": "admin", "password": "admin"})
        assert r.status_code == 200
        assert r.get_json()["role"] == "Admin"

    @allure.story("Membership")
    @allure.title("Membership status reflects client record")
    def test_membership_status_active(self, aceest_client):
        name = "MemberClient"
        assert (
            aceest_client.post(
                "/clients",
                json={
                    "name": name,
                    "age": 27,
                    "height_cm": 165.0,
                    "weight_kg": 58.0,
                    "program": "Fat Loss (FL)",
                    "adherence": 90,
                    "notes": "m",
                    "target_weight_kg": 54.0,
                    "target_adherence": 95,
                    "membership_status": "Active",
                    "membership_end": "2026-11-15",
                },
            ).status_code
            == 201
        )
        r = aceest_client.get(f"/membership/status?client_name={name}")
        assert r.status_code == 200
        j = r.get_json()
        assert j["membership_status"] == "Active"
        assert j["membership_end"] == "2026-11-15"
