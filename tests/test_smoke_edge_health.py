import os
import urllib.request
import json


def test_health_smoke():
    # This assumes edge is running at localhost:8000
    url = os.environ.get("EDGE_URL", "http://localhost:8000/health")
    with urllib.request.urlopen(url, timeout=5) as resp:
        body = resp.read().decode("utf-8")
    data = json.loads(body)
    assert data["status"] == "ok"
