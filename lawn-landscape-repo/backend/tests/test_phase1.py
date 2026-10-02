import io

from app.addresses import normalize_address


def test_login_required_and_wrong_password(client):
    assert client.get("/api/customers").status_code == 401
    assert client.post("/api/auth/login", json={"password": "nope"}).status_code == 401
    assert client.post("/api/auth/login", json={"password": "test-password"}).status_code == 200
    assert client.get("/api/customers").status_code == 200


def test_login_throttle(client):
    for _ in range(5):
        assert client.post("/api/auth/login", json={"password": "bad"}).status_code == 401
    assert client.post("/api/auth/login", json={"password": "test-password"}).status_code == 429


def test_change_password(authed):
    r = authed.post("/api/auth/password", json={"current_password": "x", "new_password": "longenough1"})
    assert r.status_code == 400
    r = authed.post("/api/auth/password", json={"current_password": "test-password", "new_password": "longenough1"})
    assert r.status_code == 200
    authed.post("/api/auth/logout")
    assert authed.post("/api/auth/login", json={"password": "test-password"}).status_code == 401
    assert authed.post("/api/auth/login", json={"password": "longenough1"}).status_code == 200
    authed.post("/api/auth/password", json={"current_password": "longenough1", "new_password": "test-password"})


def test_normalize_address():
    a = normalize_address("1213 Arbor Lane, Pacific, Missouri 63069-1234")
    b = normalize_address("1213 arbor ln pacific MO 63069")
    assert a == b


def test_customer_crud_and_search(authed):
    r = authed.post("/api/customers", json={
        "name": "Jane Smith", "email": " Jane@Example.com ", "phone": "636-555-0100",
        "properties": [{"address": "1213 Arbor Ln, Pacific, MO 63069", "billing_mode": "per_visit",
                        "per_visit_price": 55}]})
    assert r.status_code == 201
    c = r.json()
    assert c["email"] == "jane@example.com"
    assert c["properties"][0]["billing_mode"] == "per_visit"
    assert authed.get("/api/customers", params={"q": "arbor"}).json()[0]["name"] == "Jane Smith"
    assert authed.get("/api/customers", params={"q": "zzz"}).json() == []
    r = authed.post(f"/api/customers/{c['id']}/properties", json={"address": "9 Elm St, Pacific, MO"})
    assert r.status_code == 201
    pid = r.json()["id"]
    r = authed.put(f"/api/properties/{pid}", json={"address": "10 Elm St, Pacific, MO", "billing_mode": "monthly_flat", "monthly_rate": 150})
    assert r.json()["monthly_rate"] == 150
    assert authed.put(f"/api/customers/{c['id']}", json={"name": "Jane S", "active": False}).json()["active"] is False
    assert authed.get("/api/customers").json() == []
    assert len(authed.get("/api/customers", params={"include_inactive": True}).json()) == 1
    assert authed.delete(f"/api/customers/{c['id']}").status_code == 204
    assert authed.get(f"/api/customers/{c['id']}").status_code == 404


def test_invalid_billing_mode_rejected(authed):
    r = authed.post("/api/customers", json={"name": "A", "properties": [{"address": "1 Main St", "billing_mode": "weekly"}]})
    assert r.status_code == 422


def _upload(client, text):
    return client.post("/api/import/preview", files={"file": ("c.csv", io.BytesIO(text.encode()), "text/csv")})


CSV = """Name,Email,Phone,Address,City,State,Zip,Monthly Rate
Jane Smith,jane@example.com,636-555-0100,1213 Arbor Ln,Pacific,MO,63069,$180
Bob Jones,,636-555-0101,"45 Oak St, Washington, MO 63090",,,,
,nobody@example.com,,2 Pine St,,,,
Bad Email,not-an-email,,3 Pine St,,,,
"""


def test_import_preview_and_commit(authed):
    r = _upload(authed, CSV)
    assert r.status_code == 200
    body = r.json()
    status = {row["line"]: row["status"] for row in body["rows"]}
    assert status == {2: "new", 3: "new", 4: "error", 5: "error"}
    jane = body["rows"][0]
    assert jane["address"] == "1213 Arbor Ln, Pacific, MO 63069"
    assert jane["monthly_rate"] == 180
    assert any("No email" in w for w in body["rows"][1]["warnings"])
    # preview writes nothing
    assert authed.get("/api/customers").json() == []

    good = [row for row in body["rows"] if row["status"] != "error"]
    r = authed.post("/api/import/commit", json={"rows": good})
    assert r.json() == {"customers_created": 2, "properties_created": 2, "skipped_duplicates": 0, "errors": 0}
    assert len(authed.get("/api/customers").json()) == 2


def test_import_duplicate_rules(authed):
    authed.post("/api/import/commit", json={"rows": [
        {"line": 2, "name": "Jane Smith", "email": "jane@example.com", "address": "1213 Arbor Ln, Pacific, MO 63069"}]})
    csv_text = """name,email,address
Jane Smith,JANE@example.com,"1213 Arbor Lane, Pacific, Missouri 63069"
Jane Smith,jane@example.com,"77 Second St, Pacific, MO 63069"
Jane Smith,jane@example.com,"77 Second Street, Pacific, MO 63069"
"""
    body = _upload(authed, csv_text).json()
    assert [r["status"] for r in body["rows"]] == ["duplicate", "new_property", "duplicate"]
    r = authed.post("/api/import/commit", json={"rows": body["rows"]})
    assert r.json()["properties_created"] == 1
    customers = authed.get("/api/customers").json()
    assert len(customers) == 1 and customers[0]["property_count"] == 2


def test_import_needs_name_column_and_template(authed):
    assert _upload(authed, "email,address\na@b.co,1 Main\n").status_code == 400
    t = authed.get("/api/import/template")
    assert t.status_code == 200 and t.text.startswith("name,email")
    # the template itself imports cleanly
    body = _upload(authed, t.text).json()
    assert [r["status"] for r in body["rows"]] == ["new", "new"]
    assert body["rows"][1]["billing_mode"] == "per_visit"


def test_settings_and_gmail_secret(authed):
    s = authed.get("/api/settings").json()
    assert s["base_address"] == "1213 Arbor Ln, Pacific, MO 63069"
    assert s["gmail_password_set"] is False and s["tax_rate_percent"] == 0
    payload = {"business_name": "Drew Lawn", "timezone": "America/Chicago",
               "base_address": "1213 Arbor Ln, Pacific, MO 63069", "late_fee_type": "percent",
               "late_fee_value": 1.5, "late_fee_grace_days": 15, "tax_rate_percent": 8.1,
               "gmail_address": "me@gmail.com", "gmail_app_password": "abcd efgh ijkl mnop"}
    out = authed.put("/api/settings", json=payload).json()
    assert out["gmail_password_set"] is True and "gmail_app_password" not in out
    assert out["late_fee_type"] == "percent" and out["tax_rate_percent"] == 8.1
    # leaving the password out keeps it; the stored value is encrypted
    payload.pop("gmail_app_password")
    assert authed.put("/api/settings", json=payload).json()["gmail_password_set"] is True
    from app.db import SessionLocal
    from app.models import Settings
    from app.security import decrypt_secret
    with SessionLocal() as db:
        enc = db.query(Settings).one().gmail_app_password_enc
    assert "abcd" not in enc and decrypt_secret(enc) == "abcdefghijklmnop"
    payload["gmail_app_password"] = ""
    assert authed.put("/api/settings", json=payload).json()["gmail_password_set"] is False
    payload["timezone"] = "Mars/Base"
    assert authed.put("/api/settings", json=payload).status_code == 400
