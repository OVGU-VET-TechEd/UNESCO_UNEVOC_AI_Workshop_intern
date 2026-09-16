# Agent definitions: agents/<name>.agent.md = front matter (settings) + body (system prompt).
import re
from dataclasses import dataclass, field
from pathlib import Path

from harness.config import ROOT

AGENT_DIR = ROOT / "agents"


@dataclass
class Agent:
    name: str
    description: str
    system_prompt: str
    settings: dict = field(default_factory=dict)
    path: Path = None

    def get(self, key, default=None):
        value = self.settings.get(key, default)
        return default if value is None or value == "" else value


def _coerce(raw):
    value = raw.strip()
    if " #" in value and not value.startswith(("'", '"')):
        value = value.split(" #", 1)[0].strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        return [_coerce(item) for item in value[1:-1].split(",") if item.strip()]
    lowered = value.lower()
    if lowered in ("true", "yes"):
        return True
    if lowered in ("false", "no"):
        return False
    for cast in (int, float):
        try:
            return cast(value)
        except ValueError:
            pass
    return value


def parse_front_matter(text):
    match = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)(.*)$", text, re.S)
    if not match:
        return {}, text
    meta = {}
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        meta[key.strip()] = _coerce(value)
    return meta, match.group(2)


def agent_path(name_or_path):
    candidate = Path(name_or_path)
    if candidate.suffix == ".md" and candidate.exists():
        return candidate
    candidate = AGENT_DIR / (str(name_or_path) + ".agent.md")
    if candidate.exists():
        return candidate
    raise FileNotFoundError("Agent '%s' not found in %s" % (name_or_path, AGENT_DIR))


def load_agent(name_or_path):
    path = agent_path(name_or_path)
    meta, body = parse_front_matter(path.read_text(encoding="utf-8-sig"))
    includes = meta.get("include", [])
    if isinstance(includes, str):
        includes = [includes]
    parts = [body.strip()]
    for rel in includes:
        inc_path = ROOT / rel
        if not inc_path.exists():
            raise FileNotFoundError("Agent '%s' includes missing file %s" % (path.name, rel))
        parts.append(inc_path.read_text(encoding="utf-8-sig").strip())
    name = meta.get("name") or path.name.replace(".agent.md", "")
    return Agent(name=name, description=meta.get("description", ""),
                 system_prompt="\n\n".join(p for p in parts if p), settings=meta, path=path)


def list_agents():
    agents = []
    for path in sorted(AGENT_DIR.glob("*.agent.md")):
        if path.name.startswith("_"):
            continue
        agents.append(load_agent(path))
    return agents


def read_prompt(agent, key, default_rel):
    rel = agent.get(key, default_rel)
    path = ROOT / rel
    if not path.exists():
        raise FileNotFoundError("Prompt file not found: %s" % rel)
    return path.read_text(encoding="utf-8-sig")


def fill(template, **values):
    # Replace {{KEY}} placeholders; TEXT is replaced last so document text is never re-processed.
    text_value = values.pop("TEXT", None)
    for key, value in values.items():
        template = template.replace("{{%s}}" % key, str(value))
    if text_value is not None:
        template = template.replace("{{TEXT}}", str(text_value))
    return template
