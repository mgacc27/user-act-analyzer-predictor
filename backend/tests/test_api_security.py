from app.core.security import create_access_token, decode_token

def test_login_ok(client):
    r = client.post("/api/v1/auth/token", data={"username": "analyst", "password": "analyst"})
    assert r.status_code == 200
    assert decode_token(r.json()["access_token"])["role"] == "USER"

def test_login_bad_password(client):
    assert client.post("/api/v1/auth/token",
                       data={"username": "analyst", "password": "wrong"}).status_code == 401

def test_expired_token_rejected(client):
    tok = create_access_token("u-1", "USER", ttl_minutes=-1)
    r = client.get("/api/v1/metrics", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401

def test_import_requires_token(client, sample_csv):
    assert client.post("/api/v1/data/import",
                       files={"file": ("l.csv", sample_csv)}).status_code == 401

def test_import_csv_ok(client, auth, sample_csv, sample_rows):
    r = client.post("/api/v1/data/import", files={"file": ("l.csv", sample_csv)}, headers=auth)
    assert r.status_code == 201
    body = r.json()
    assert body["imported"] == len(sample_rows) and body["anomalies_marked"] >= 1

def test_import_corrupted_422(client, auth):
    r = client.post("/api/v1/data/import", files={"file": ("b.json", b"{broken")}, headers=auth)
    assert r.status_code == 422 and "поврежд" in r.json()["detail"]

def test_import_wrong_format_422(client, auth):
    r = client.post("/api/v1/data/import", files={"file": ("l.txt", b"x")}, headers=auth)
    assert r.status_code == 422

def test_metrics_endpoint(client, auth, sample_csv):
    client.post("/api/v1/data/import", files={"file": ("l.csv", sample_csv)}, headers=auth)
    body = client.get("/api/v1/metrics", headers=auth).json()
    assert {"dau", "mau", "avg_session_sec", "events_by_type"} <= set(body)

def test_forecast_endpoint(client, auth, sample_csv):
    client.post("/api/v1/data/import", files={"file": ("l.csv", sample_csv)}, headers=auth)
    body = client.get("/api/v1/forecast/predict?days=14", headers=auth).json()
    assert len(body["points"]) == 14 and "mape" in body and "elapsed_sec" in body

def test_forecast_horizon_cap(client, auth):
    assert client.get("/api/v1/forecast/predict?days=30", headers=auth).status_code == 422

def test_report_pdf_magic(client, auth, sample_csv):
    client.post("/api/v1/data/import", files={"file": ("l.csv", sample_csv)}, headers=auth)
    r = client.get("/api/v1/reports/export?format=pdf", headers=auth)
    assert r.status_code == 200 and r.content[:4] == b"%PDF"

def test_report_xlsx_magic(client, auth, sample_csv):
    client.post("/api/v1/data/import", files={"file": ("l.csv", sample_csv)}, headers=auth)
    r = client.get("/api/v1/reports/export?format=xlsx", headers=auth)
    assert r.status_code == 200 and r.content[:2] == b"PK"

def test_rbac_user_forbidden_from_admin(client, auth):
    assert client.get("/api/v1/admin/performance", headers=auth).status_code == 403

def test_rbac_admin_ok(client):
    tok = client.post("/api/v1/auth/token",
                      data={"username": "admin", "password": "admin"}).json()["access_token"]
    assert client.get("/api/v1/admin/performance",
                      headers={"Authorization": f"Bearer {tok}"}).status_code == 200