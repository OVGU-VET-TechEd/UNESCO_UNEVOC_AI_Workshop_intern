# Validation of model output and of summary Markdown files; deterministic rendering.
import datetime
import json
import re

from harness.config import ROOT

META_FIELDS = [
    ("title", "Title"),
    ("issuing_body", "Issuing body"),
    ("country_or_region", "Country / region"),
    ("year", "Year"),
    ("document_type", "Document type"),
]
TABLE_FIELDS = ["Source file", "Issuing body", "Country / region", "Year", "Document type"]


def load_style_rules():
    path = ROOT / "config" / "style_rules.json"
    if path.exists():
        with path.open(encoding="utf-8-sig") as fh:
            return json.load(fh)
    return {"min_words": 40, "banned_terms": [], "discouraged_terms": []}


def word_count(text):
    return len((text or "").split())


def strip_think(text):
    return re.sub(r"<think>.*?</think>", "", text or "", flags=re.S)


def extract_json(raw):
    text = strip_think(raw).strip()
    if not text:
        raise ValueError("the model returned an empty response")
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    raise ValueError("the response was not a valid JSON object")


def _term_found(term, text):
    pattern = r"(?<![\w-])" + re.escape(term.lower()) + r"(?![\w-])"
    return re.search(pattern, text.lower()) is not None


def check_summary_text(summary, max_words, rules):
    errors, warnings = [], []
    count = word_count(summary)
    if count > max_words:
        errors.append("summary has %d words; the maximum is %d" % (count, max_words))
    elif count < int(rules.get("min_words", 40)):
        warnings.append("summary is short (%d words)" % count)
    if re.search(r"^\s*([-*\u2022]|\d+[.)])\s", summary, re.M):
        errors.append("summary must not contain bullet points or numbered lists")
    if len([p for p in re.split(r"\n\s*\n", summary.strip()) if p.strip()]) > 1:
        errors.append("summary must be a single paragraph")
    if "!" in summary:
        errors.append("summary must not contain exclamation marks")
    for term in rules.get("banned_terms", []):
        if _term_found(term, summary):
            errors.append("remove the non-neutral expression '%s'" % term)
    regex = rules.get("first_person_regex")
    if regex:
        hit = re.search(regex, summary)
        if hit:
            errors.append("use third person only (found '%s')" % hit.group(0))
    for term in rules.get("discouraged_terms", []):
        if _term_found(term, summary):
            warnings.append("consider replacing '%s' with a more neutral wording" % term)
    return errors, warnings


def _flat(value):
    if isinstance(value, (list, tuple)):
        value = ", ".join(str(v) for v in value)
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def normalise_payload(obj, max_words, rules):
    if not isinstance(obj, dict):
        return None, ["the JSON must be an object with the requested keys"], []
    data = {}
    for key, _label in META_FIELDS:
        value = _flat(obj.get(key))
        data[key] = value if value and value.lower() not in ("none", "null", "n/a", "unknown") else "Not stated"
    raw_summary = obj.get("summary", "")
    if isinstance(raw_summary, list):
        raw_summary = " ".join(str(s) for s in raw_summary)
    raw_summary = str(raw_summary or "").strip()
    errors, warnings = [], []
    if not raw_summary:
        errors.append("the 'summary' field is empty")
    else:
        errors, warnings = check_summary_text(raw_summary, max_words, rules)
    data["summary"] = re.sub(r"\s+", " ", raw_summary)
    keywords = obj.get("keywords", [])
    if isinstance(keywords, str):
        keywords = re.split(r"[;,]", keywords)
    cleaned = []
    for keyword in keywords or []:
        keyword = _flat(keyword).strip(" .")
        if keyword and keyword.lower() not in [k.lower() for k in cleaned]:
            cleaned.append(keyword)
    data["keywords"] = cleaned[:5]
    if len(cleaned) < 3:
        warnings.append("fewer than 3 keywords")
    return data, errors, warnings


def trim_to_limit(summary, max_words):
    # Returns (text, mode) with mode in None | "sentence" | "hard".
    if word_count(summary) <= max_words:
        return summary, None
    sentences = re.split(r"(?<=[.!?])\s+", summary.strip())
    while len(sentences) > 1 and word_count(" ".join(sentences)) > max_words:
        sentences.pop()
    text = " ".join(sentences)
    if word_count(text) <= max_words:
        return text, "sentence"
    text = " ".join(text.split()[:max_words]).rstrip(",;:-")
    if not text.endswith((".", "?")):
        text += "."
    return text, "hard"


def _cell(value):
    value = _flat(value).replace("|", "\\|")
    return value or "Not stated"


def render_markdown(data, source_name, agent_name, model, max_words):
    title = data.get("title") or "Not stated"
    if title == "Not stated":
        title = source_name.rsplit(".", 1)[0]
    keywords = "; ".join(data.get("keywords") or []) or "Not stated"
    lines = [
        "# %s" % _flat(title),
        "",
        "| Field | Value |",
        "|---|---|",
        "| Source file | %s |" % _cell(source_name),
        "| Issuing body | %s |" % _cell(data.get("issuing_body")),
        "| Country / region | %s |" % _cell(data.get("country_or_region")),
        "| Year | %s |" % _cell(data.get("year")),
        "| Document type | %s |" % _cell(data.get("document_type")),
        "",
        "## Summary",
        "",
        data.get("summary", "").strip(),
        "",
        "## Keywords",
        "",
        keywords,
        "",
        "---",
        "",
        "*Word count: %d/%d | Generated: %s | Agent: %s | Model: %s*" % (
            word_count(data.get("summary", "")), max_words, datetime.date.today().isoformat(), agent_name, model),
        "",
    ]
    return "\n".join(lines)


def parse_summary_markdown(text):
    result = {"title": None, "fields": {}, "summary": None, "keywords": None}
    title = re.search(r"^#\s+(.+)$", text, re.M)
    if title:
        result["title"] = title.group(1).strip()
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]
        if len(cells) == 2 and cells[0] not in ("Field", "") and not set(cells[0]) <= set("-: "):
            result["fields"][cells[0]] = cells[1].replace("\\|", "|")
    for block in re.split(r"^##\s+", text, flags=re.M)[1:]:
        heading, _, body = block.partition("\n")
        body = re.split(r"^\s*---\s*$", body, maxsplit=1, flags=re.M)[0].strip()
        if heading.strip().lower() == "summary":
            result["summary"] = body
        elif heading.strip().lower() == "keywords":
            result["keywords"] = [k.strip() for k in body.split(";") if k.strip()]
    return result


def validate_markdown_file(path, max_words, rules):
    text = path.read_text(encoding="utf-8-sig")
    parsed = parse_summary_markdown(text)
    errors, warnings = [], []
    if not parsed["title"]:
        errors.append("missing level-1 title line ('# Title')")
    for field_name in TABLE_FIELDS:
        if not parsed["fields"].get(field_name):
            errors.append("missing table field '%s'" % field_name)
    if parsed["summary"] is None:
        errors.append("missing '## Summary' section")
        count = 0
    else:
        count = word_count(parsed["summary"])
        e, w = check_summary_text(parsed["summary"], max_words, rules)
        errors += e
        warnings += w
    if parsed["keywords"] is None:
        errors.append("missing '## Keywords' section")
    elif not 3 <= len(parsed["keywords"]) <= 5:
        warnings.append("expected 3 to 5 keywords, found %d" % len(parsed["keywords"]))
    return errors, warnings, count, parsed
