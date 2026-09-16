# Command line interface: python -m harness <command>
import argparse
import datetime
import json
import platform
import sys
import time
from pathlib import Path

from harness import __version__
from harness.agents import AGENT_DIR, list_agents, load_agent
from harness.backends import BackendError, get_backend
from harness.config import ROOT, load_config, resolve_dir
from harness.pdf_text import PdfExtractionError, clean_text, extract_pages, join_pages
from harness.pipeline import Reviewer, SkipFile, Summarizer
from harness.validate import load_style_rules, render_markdown, validate_markdown_file


def _safe_console():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except Exception:
            pass


def _pdfs(folder):
    if not folder.exists():
        return []
    return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".pdf")


def _summary_files(folder):
    if not folder.exists():
        return []
    return sorted(p for p in folder.glob("*.md") if not p.name.startswith(("_", "README")))


def _log(cfg, record):
    log_dir = resolve_dir(cfg, "log_dir")
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / ("runs_%s.jsonl" % datetime.date.today().strftime("%Y%m"))
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def _backend_ready(backend):
    try:
        ok, names = backend.check()
    except BackendError as exc:
        print("[error] %s" % exc)
        if backend.name == "ollama":
            print("        Start Ollama (Ollama app or 'ollama serve') and try again.")
        return False
    if not ok:
        print("[error] Model '%s' is not available on backend '%s'." % (backend.model, backend.name))
        if names:
            print("        Available: %s" % ", ".join(names[:15]))
        if backend.name == "ollama":
            print("        Run: ollama pull %s" % backend.model)
        return False
    return True


def cmd_run(args):
    cfg = load_config()
    agent = load_agent(args.agent or cfg["default_agent"])
    if agent.get("task", "policy_summary") != "policy_summary":
        print("[error] Agent '%s' has task '%s'; 'run' needs a policy_summary agent." % (agent.name, agent.get("task")))
        return 2
    backend = get_backend(cfg, agent, args.backend, args.model)
    input_dir, output_dir = resolve_dir(cfg, "input_dir"), resolve_dir(cfg, "output_dir")
    files = [Path(f) for f in args.files] if args.files else _pdfs(input_dir)
    if not files:
        print("No PDF files found in %s" % input_dir)
        return 1
    print("Agent: %s | backend: %s | model: %s | files: %d" % (agent.name, backend.name, backend.model, len(files)))
    if not _backend_ready(backend):
        return 2
    output_dir.mkdir(parents=True, exist_ok=True)
    summarizer = Summarizer(agent, backend, load_style_rules(), verbose=not args.quiet)
    counts = {"ok": 0, "auto_trimmed": 0, "needs_review": 0, "skipped": 0, "failed": 0}
    for index, pdf in enumerate(files, 1):
        out = output_dir / (pdf.stem + agent.get("output_suffix", ".summary.md"))
        if out.exists() and not args.overwrite:
            print("[%d/%d] %s -> exists, skipped (use --overwrite)" % (index, len(files), pdf.name))
            counts["skipped"] += 1
            continue
        print("[%d/%d] %s" % (index, len(files), pdf.name), flush=True)
        started = time.time()
        record = {"time": datetime.datetime.now().isoformat(timespec="seconds"), "file": pdf.name,
                  "agent": agent.name, "backend": backend.name, "model": backend.model}
        try:
            if not pdf.exists():
                raise PdfExtractionError("file not found: %s" % pdf)
            result = summarizer.summarize(pdf)
            markdown = render_markdown(result["data"], pdf.name, agent.name, backend.model, summarizer.max_words)
            out.write_text(markdown, encoding="utf-8")
            counts[result["status"]] += 1
            record.update({k: result[k] for k in ("status", "attempts", "warnings", "errors", "pages", "chars", "material")})
            record["output"] = str(out.relative_to(ROOT)) if out.is_relative_to(ROOT) else str(out)
            print("    -> %s [%s]" % (out.name, result["status"]))
            for warning in result["warnings"]:
                print("       warning: %s" % warning)
        except SkipFile as exc:
            counts["skipped"] += 1
            record.update({"status": "skipped", "reason": str(exc)})
            print("    -> skipped: %s" % exc)
        except (BackendError, PdfExtractionError, ValueError) as exc:
            counts["failed"] += 1
            record.update({"status": "failed", "reason": str(exc)})
            print("    -> failed: %s" % exc)
        record["seconds"] = round(time.time() - started, 1)
        _log(cfg, record)
    print("\nDone: " + ", ".join("%s=%d" % kv for kv in counts.items()))
    if counts["needs_review"]:
        print("Files marked needs_review should be checked manually or with: python -m harness review")
    return 0 if counts["failed"] == 0 else 1


def cmd_extract(args):
    cfg = load_config()
    input_dir = resolve_dir(cfg, "input_dir")
    target = resolve_dir(cfg, "work_dir") / "extracted"
    target.mkdir(parents=True, exist_ok=True)
    files = [Path(f) for f in args.files] if args.files else _pdfs(input_dir)
    if not files:
        print("No PDF files found in %s" % input_dir)
        return 1
    status = 0
    for pdf in files:
        try:
            pages = extract_pages(pdf)
            text = clean_text(join_pages(pages))
            out = target / (pdf.stem + ".txt")
            out.write_text("SOURCE FILE: %s\nPAGES: %d\n\n%s\n" % (pdf.name, len(pages), text), encoding="utf-8")
            note = "  WARNING: little or no text - scanned PDF? run OCR first" if len(text) < 300 else ""
            print("%s -> work/extracted/%s (%d pages, %d chars)%s" % (pdf.name, out.name, len(pages), len(text), note))
        except PdfExtractionError as exc:
            status = 1
            print("%s -> failed: %s" % (pdf.name, exc))
    return status


def cmd_validate(args):
    cfg = load_config()
    agent = load_agent(args.agent or cfg["default_agent"])
    max_words = int(agent.get("max_words", 80))
    rules = load_style_rules()
    files = [Path(f) for f in args.files] if args.files else _summary_files(resolve_dir(cfg, "output_dir"))
    if not files:
        print("No summary files to validate.")
        return 1
    failed = 0
    for path in files:
        errors, warnings, count, _parsed = validate_markdown_file(path, max_words, rules)
        label = "FAIL" if errors else "PASS"
        print("[%s] %s (%d/%d words)" % (label, path.name, count, max_words))
        for error in errors:
            print("       error: %s" % error)
        for warning in warnings:
            print("       warning: %s" % warning)
        failed += bool(errors)
    print("\n%d of %d files passed." % (len(files) - failed, len(files)))
    return 1 if failed else 0


def cmd_review(args):
    cfg = load_config()
    agent = load_agent(args.agent or cfg["default_reviewer"])
    backend = get_backend(cfg, agent, args.backend, args.model)
    files = [Path(f) for f in args.files] if args.files else _summary_files(resolve_dir(cfg, "output_dir"))
    if not files:
        print("No summary files to review.")
        return 1
    if not _backend_ready(backend):
        return 2
    rules = load_style_rules()
    reviewer = Reviewer(agent, backend, rules)
    report_dir = resolve_dir(cfg, "report_dir")
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    lines = ["# Review report %s" % stamp, "", "Agent: %s | Model: %s" % (agent.name, backend.model), ""]
    for path in files:
        _e, _w, count, parsed = validate_markdown_file(path, reviewer.max_words, rules)
        if not parsed["summary"]:
            print("%s -> no summary section, skipped" % path.name)
            continue
        print("Reviewing %s ..." % path.name, flush=True)
        try:
            result = reviewer.review(parsed["summary"])
        except (BackendError, ValueError) as exc:
            print("    failed: %s" % exc)
            lines += ["## %s" % path.name, "", "Review failed: %s" % exc, ""]
            continue
        verdict = "OK" if result["model_neutral"] and not result["rule_errors"] else "CHECK"
        print("    %s" % verdict)
        lines += ["## %s - %s" % (path.name, verdict), "", "- Word count: %d" % count,
                  "- Model judges neutral: %s" % result["model_neutral"]]
        lines += ["- Rule error: %s" % e for e in result["rule_errors"]]
        lines += ["- Rule warning: %s" % w for w in result["rule_warnings"]]
        lines += ["- Model issue: %s" % i for i in result["model_issues"]]
        if result["suggested_revision"]:
            lines += ["", "Suggested revision (not applied):", "", "> " + result["suggested_revision"]]
        lines.append("")
    report = report_dir / ("review_%s.md" % stamp)
    report.write_text("\n".join(lines), encoding="utf-8")
    print("\nReport: %s" % report)
    return 0


def cmd_check(args):
    cfg = load_config()
    problems = 0
    print("Harness %s | Python %s | %s" % (__version__, platform.python_version(), platform.platform()))
    try:
        import pypdf
        print("[ok]   pypdf %s" % pypdf.__version__)
    except ImportError:
        problems += 1
        print("[fail] pypdf missing - pip install -r requirements.txt")
    try:
        import pdfplumber  # noqa: F401
        print("[ok]   pdfplumber (optional fallback)")
    except ImportError:
        print("[info] pdfplumber not installed (optional)")
    agents = list_agents()
    print("[ok]   %d agent(s): %s" % (len(agents), ", ".join(a.name for a in agents)))
    for key in ("input_dir", "output_dir"):
        folder = resolve_dir(cfg, key)
        print("[%s] %s: %s" % ("ok  " if folder.exists() else "fail", key, folder))
        problems += not folder.exists()
    print("[info] PDFs waiting in input: %d" % len(_pdfs(resolve_dir(cfg, "input_dir"))))
    seen = set()
    for agent in agents:
        backend = get_backend(cfg, agent, args.backend, args.model)
        key = (backend.name, backend.model)
        if key in seen:
            continue
        seen.add(key)
        try:
            ok, names = backend.check()
            print("[%s] backend %s, model %s%s" % ("ok  " if ok else "fail", backend.name, backend.model,
                                                  "" if ok else " not found (ollama pull %s)" % backend.model))
            problems += not ok
        except BackendError as exc:
            problems += 1
            print("[fail] backend %s: %s" % (backend.name, exc))
    print("\n%s" % ("All checks passed." if not problems else "%d problem(s) found." % problems))
    return 1 if problems else 0


def cmd_agents(args):
    for agent in list_agents():
        print("%-28s task=%-15s backend=%-18s model=%s" % (agent.name, agent.get("task", "policy_summary"),
                                                           agent.get("backend", "ollama"), agent.get("model")))
        if agent.description:
            print("    %s" % agent.description)
    return 0


def cmd_new_agent(args):
    template = AGENT_DIR / "_template.agent.md"
    target = AGENT_DIR / ("%s.agent.md" % args.name)
    if target.exists():
        print("[error] %s already exists" % target)
        return 1
    cfg = load_config()
    default_model = load_agent(cfg["default_agent"]).get("model", "llama3.2:3b")
    text = template.read_text(encoding="utf-8").replace("{{AGENT_NAME}}", args.name).replace("{{DEFAULT_MODEL}}", default_model)
    target.write_text(text, encoding="utf-8")
    print("Created %s - edit the front matter and system prompt." % target)
    return 0


def build_parser():
    parser = argparse.ArgumentParser(prog="python -m harness", description="TVET policy summariser agent harness")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command")

    def common(p, files_help):
        p.add_argument("files", nargs="*", help=files_help)
        p.add_argument("--agent", help="agent name or path to *.agent.md")
        p.add_argument("--backend", help="override backend: ollama | openai_compatible | mock")
        p.add_argument("--model", help="override model name")

    p = sub.add_parser("run", help="summarise PDFs from input/ into output/")
    common(p, "specific PDF files (default: all PDFs in input/)")
    p.add_argument("--overwrite", action="store_true", help="replace existing summaries")
    p.add_argument("--quiet", action="store_true", help="less progress output")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("extract", help="extract PDF text to work/extracted/ (for Copilot or Continue)")
    p.add_argument("files", nargs="*")
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser("validate", help="check summary files against the standard")
    common(p, "summary files (default: all in output/)")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("review", help="second-pass neutrality review with the reviewer agent")
    common(p, "summary files (default: all in output/)")
    p.set_defaults(func=cmd_review)

    p = sub.add_parser("check", help="health check of packages, folders, backend and models")
    p.add_argument("--backend")
    p.add_argument("--model")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("agents", help="list agent definitions")
    p.set_defaults(func=cmd_agents)

    p = sub.add_parser("new-agent", help="create a new agent file from the template")
    p.add_argument("name")
    p.set_defaults(func=cmd_new_agent)
    return parser


def main(argv=None):
    _safe_console()
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    try:
        return args.func(args)
    except (FileNotFoundError, ValueError) as exc:
        print("[error] %s" % exc)
        return 2
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130
