# PDF text extraction and chunking.
import re


class PdfExtractionError(Exception):
    pass


def _chars(pages):
    return sum(len(p.strip()) for p in pages)


def extract_pages(pdf_path):
    pages, error = [], None
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise PdfExtractionError("pypdf is not installed. Run: pip install -r requirements.txt") from exc
    try:
        reader = PdfReader(str(pdf_path))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception as exc:
                raise PdfExtractionError("PDF is password protected: %s" % pdf_path) from exc
        for page in reader.pages:
            try:
                pages.append(page.extract_text() or "")
            except Exception:
                pages.append("")
    except PdfExtractionError:
        raise
    except Exception as exc:
        error = exc
    if _chars(pages) < 200:
        try:
            import pdfplumber
            with pdfplumber.open(str(pdf_path)) as pdf:
                alternative = [(page.extract_text() or "") for page in pdf.pages]
            if _chars(alternative) > _chars(pages):
                pages, error = alternative, None
        except Exception:
            pass
    if not pages and error is not None:
        raise PdfExtractionError("Could not read %s: %s" % (pdf_path, error))
    return pages


def join_pages(pages):
    return "\n\n".join("[Page %d]\n%s" % (i, text.strip()) for i, text in enumerate(pages, 1) if text.strip())


def clean_text(text):
    text = text.replace("\u00ad", "").replace("\x00", "")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text, size=6000, overlap=300):
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, current = [], ""
    for para in paragraphs:
        while len(para) > size:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(para[:size])
            para = para[size - overlap:]
        if len(current) + len(para) + 2 > size and current:
            chunks.append(current)
            current = current[-overlap:] + "\n\n" + para if overlap else para
        else:
            current = (current + "\n\n" + para) if current else para
    if current.strip():
        chunks.append(current)
    return chunks


def select_chunks(chunks, max_chunks):
    # Keep the opening chunks (title, issuer, objectives) and spread the rest evenly.
    if max_chunks <= 0 or len(chunks) <= max_chunks:
        return chunks
    head = chunks[:2]
    rest = chunks[2:]
    slots = max_chunks - len(head)
    step = len(rest) / float(slots)
    picked = [rest[int(i * step)] for i in range(slots)]
    return head + picked
