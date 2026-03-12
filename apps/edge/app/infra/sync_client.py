import json
import urllib.request
import urllib.error


def post_json(url, payload_dict, headers_dict=None, timeout_seconds=10):
    """
    Simple HTTP JSON POST using standard library.
    Returns (ok: bool, status_code: int, response_text: str)
    """
    data = json.dumps(payload_dict, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(url=url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")

    if headers_dict is not None:
        for k in headers_dict:
            v = headers_dict[k]
            req.add_header(k, v)

    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            status_code = int(resp.status)
            body = resp.read().decode("utf-8")
            return True, status_code, body
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8")
        except Exception:
            body = ""
        return False, int(e.code), body
    except Exception as exc:
        return False, 0, str(exc)