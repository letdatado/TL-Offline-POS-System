import os


def _read_env_file(path):
    """
    Tiny .env loader (no external deps).
    Supports simple KEY=VALUE lines.
    """
    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i = i + 1

        if line == "":
            continue
        if line.startswith("#"):
            continue

        if "=" not in line:
            continue

        parts = line.split("=", 1)
        key = parts[0].strip()
        value = parts[1].strip()

        # Strip surrounding quotes if present
        if len(value) >= 2:
            if (value[0] == '"' and value[-1] == '"') or (value[0] == "'" and value[-1] == "'"):
                value = value[1:-1]

        # Don't overwrite existing env vars
        if os.environ.get(key) is None:
            os.environ[key] = value


# Load .env from this demo_ui folder
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_ENV_PATH = os.path.join(os.path.dirname(_BASE_DIR), ".env")
_read_env_file(_ENV_PATH)


def get_settings():
    edge_url = os.environ.get("EDGE_URL", "http://localhost:8000").rstrip("/")
    cloud_url = os.environ.get("CLOUD_URL", "http://localhost:9000").rstrip("/")
    title = os.environ.get("APP_TITLE", "TL Offline POS Demo")
    cloud_api_key = os.environ.get("CLOUD_API_KEY", "").strip()
    cloud_admin_key = os.environ.get("CLOUD_ADMIN_API_KEY", "").strip()

    ui_auth_enabled_raw = os.environ.get("UI_AUTH_ENABLED", "true").strip().lower()
    ui_auth_enabled = True
    if ui_auth_enabled_raw in ["0", "false", "no", "off"]:
        ui_auth_enabled = False

    ui_admin_username = os.environ.get("UI_ADMIN_USERNAME", "admin").strip()
    ui_admin_password = os.environ.get("UI_ADMIN_PASSWORD", "").strip()

    ui_viewer_username = os.environ.get("UI_VIEWER_USERNAME", "viewer").strip()
    ui_viewer_password = os.environ.get("UI_VIEWER_PASSWORD", "").strip()
    
    return {
        "EDGE_URL": edge_url,
        "CLOUD_URL": cloud_url,
        "APP_TITLE": title,
        "CLOUD_API_KEY": cloud_api_key,
        "CLOUD_ADMIN_API_KEY": cloud_admin_key,

        "UI_AUTH_ENABLED": ui_auth_enabled,
        "UI_ADMIN_USERNAME": ui_admin_username,
        "UI_ADMIN_PASSWORD": ui_admin_password,
        "UI_VIEWER_USERNAME": ui_viewer_username,
        "UI_VIEWER_PASSWORD": ui_viewer_password,
    }