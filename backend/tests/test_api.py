import json
import time


def test_reading_is_open_without_sign_in(client):
    for path in ("/api/status", "/api/offices", "/api/items", "/api/issues", "/api/gaps", "/api/reports", "/api/sectors", "/api/mentions", "/api/developments"):
        assert client.get(path).status_code == 200, path


def test_all_nine_jurisdictions(client):
    codes = [o["code"] for o in client.get("/api/offices").json()]
    assert codes == ["CTH", "NSW", "VIC", "QLD", "SA", "WA", "TAS", "ACT", "NT"]


def test_scans_need_a_session(client):
    assert client.post("/api/scans").status_code == 401


def test_document_exports_are_not_built_yet(client):
    assert client.get("/api/export/brief.docx").status_code == 501


def test_filters(client):
    vic = client.get("/api/items", params={"jur": "VIC", "period": "2w"}).json()
    assert vic and all(i["jur"] == "VIC" and i["date"] >= "2026-10-17" for i in vic)
    health = client.get("/api/items", params={"sector": "Health"}).json()
    assert health and all(i["theme"] == "Health" for i in health)


def test_csv_export(client):
    r = client.get("/api/export/gaps.csv", params={"jur": "VIC"})
    assert r.headers["content-type"].startswith("text/csv")
    assert r.text.splitlines()[0].startswith("office,issue,sector")


def wait_for_scan(client, run_id):
    for _ in range(200):
        snap = client.get(f"/api/scans/{run_id}").json()
        if snap["done"]:
            return snap
        time.sleep(0.02)
    raise AssertionError("scan did not finish")


def test_scan_reveals_new_items_and_updates_status(signed_in):
    before = len(signed_in.get("/api/items").json())
    assert signed_in.get("/api/status").json()["hansardTo"] == "2026-10-29"
    run = signed_in.post("/api/scans").json()
    assert signed_in.post("/api/scans").json()["id"] == run["id"], "only one scan at a time"
    snap = wait_for_scan(signed_in, run["id"])
    assert snap["summary"]["newItems"] == 5
    assert len(signed_in.get("/api/items").json()) == before + 5
    status = signed_in.get("/api/status").json()
    assert status["refreshed"] and status["hansardTo"] == "2026-10-30"


def test_scan_events_stream_until_done(signed_in):
    run = signed_in.post("/api/scans").json()
    events = []
    with signed_in.stream("GET", f"/api/scans/{run['id']}/events") as r:
        for line in r.iter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
    assert events[-1]["done"] and events[-1]["step"] == 10
    assert events[-1]["sources"][0]["state"] == "done"
