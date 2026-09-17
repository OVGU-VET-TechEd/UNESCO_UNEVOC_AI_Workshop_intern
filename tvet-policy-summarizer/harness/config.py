# Configuration loading: config/harness.json, .env file and environment variables.
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DEFAULTS = {
    "input_dir": "input",
    "output_dir": "output",
    "work_dir": "work",
    "log_dir": "logs",
    "report_dir": "reports",
    "default_agent": "tvet-policy-summarizer",
    "default_reviewer": "tvet-summary-reviewer",
    "backends": {
        "ollama": {"host": "http://127.0.0.1:11434", "num_ctx": 8192, "timeout": 900, "keep_alive": "10m"},
        "openai_compatible": {"base_url": "http://127.0.0.1:11434/v1", "api_key_env": "OPENAI_API_KEY",
                              "json_mode": True, "timeout": 300, "extra_headers": {}},
        "mock": {},
    },
}


def _merge(base, extra):
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value
    return base


def load_dotenv(path=None):
    # Minimal .env reader: KEY=VALUE lines; existing environment variables win.
    env_path = Path(path) if path else ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value


def normalise_ollama_host(host):
    host = host.strip().rstrip("/")
    if not host.startswith(("http://", "https://")):
        host = "http://" + host
    host = host.replace("0.0.0.0", "127.0.0.1")
    scheme, rest = host.split("://", 1)
    if ":" not in rest.split("/")[0]:
        rest = rest.split("/")[0] + ":11434"
    return scheme + "://" + rest


def load_config(path=None):
    load_dotenv()
    cfg = json.loads(json.dumps(DEFAULTS))
    cfg_path = Path(path) if path else ROOT / "config" / "harness.json"
    if cfg_path.exists():
        with cfg_path.open(encoding="utf-8-sig") as fh:
            _merge(cfg, json.load(fh))
    if os.environ.get("OLLAMA_HOST"):
        cfg["backends"]["ollama"]["host"] = normalise_ollama_host(os.environ["OLLAMA_HOST"])
    return cfg


def resolve_dir(cfg, key):
    path = Path(cfg[key])
    if not path.is_absolute():
        path = ROOT / path
    return path
