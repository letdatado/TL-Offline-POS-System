import requests


def _safe_json(resp):
    try:
        return resp.json()
    except Exception:
        return {"raw": resp.text}


def get_json(base_url, path, timeout_seconds=6):
    url = base_url.rstrip("/") + path
    try:
        resp = requests.get(url, timeout=timeout_seconds)
        ok = resp.status_code >= 200 and resp.status_code < 300
        return ok, resp.status_code, _safe_json(resp)
    except Exception as exc:
        return False, 0, {"error": str(exc)}


def post_json(base_url, path, payload, timeout_seconds=10):
    url = base_url.rstrip("/") + path
    try:
        resp = requests.post(url, json=payload, timeout=timeout_seconds)
        ok = resp.status_code >= 200 and resp.status_code < 300
        return ok, resp.status_code, _safe_json(resp)
    except Exception as exc:
        return False, 0, {"error": str(exc)}


def post_no_body(base_url, path, timeout_seconds=10):
    url = base_url.rstrip("/") + path
    try:
        resp = requests.post(url, timeout=timeout_seconds)
        ok = resp.status_code >= 200 and resp.status_code < 300
        return ok, resp.status_code, _safe_json(resp)
    except Exception as exc:
        return False, 0, {"error": str(exc)}
    
def post_json_with_headers(base_url, path, payload, headers_dict, timeout_seconds=10):
    url = base_url.rstrip("/") + path
    try:
        resp = requests.post(url, json=payload, headers=headers_dict, timeout=timeout_seconds)
        ok = resp.status_code >= 200 and resp.status_code < 300
        return ok, resp.status_code, _safe_json(resp)
    except Exception as exc:
        return False, 0, {"error": str(exc)}


def post_no_body_with_headers(base_url, path, headers_dict, timeout_seconds=10):
    url = base_url.rstrip("/") + path
    try:
        resp = requests.post(url, headers=headers_dict, timeout=timeout_seconds)
        ok = resp.status_code >= 200 and resp.status_code < 300
        return ok, resp.status_code, _safe_json(resp)
    except Exception as exc:
        return False, 0, {"error": str(exc)}