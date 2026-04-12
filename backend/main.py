from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import uvicorn
import logging
import io
import pdfplumber
import os

logger = logging.getLogger(__name__)

from services.plagiarism import plagiarism_detector
from services.grammar import grammar_detector

app = FastAPI(title="Marathi Plagiarism & Grammar API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Helpers ──────────────────────────────────────────────────────────────────

async def extract_text(upload: UploadFile) -> str:
    """Extract text from either a .txt or .pdf UploadFile."""
    content = await upload.read()
    name = upload.filename or ""

    if name.lower().endswith(".pdf"):
        try:
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                text = "\n".join(
                    page.extract_text() or "" for page in pdf.pages
                )
            if not text.strip():
                raise HTTPException(status_code=400, detail="Could not extract text from PDF. Make sure it is not scanned/image-only.")
            return text
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"PDF parsing error: {e}")

    # Treat as plain text
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File is not valid UTF-8 text.")


# ── Endpoints ─────────────────────────────────────────────────────────────────

# Serve the main HTML page at the root URL
@app.get("/")
async def serve_index():
    index_path = os.path.join(os.path.dirname(__file__), "../frontend/index.html")
    return FileResponse(index_path)

class AnalyzeTextRequest(BaseModel):
    text: str
    reference_text: Optional[str] = None

@app.post("/api/analyze")
async def analyze_text(request: AnalyzeTextRequest):
    text = request.text
    ref = request.reference_text
    logger.info(f"[/api/analyze] text_len={len(text)} | has_reference={bool(ref and ref.strip())}")
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    if ref and ref.strip():
        plagiarism_results = plagiarism_detector.detect_plagiarism_custom(text, ref)
    else:
        plagiarism_results = plagiarism_detector.detect_plagiarism_single(text)

    grammar_results = grammar_detector.check_grammar(text)

    return {"plagiarism": plagiarism_results, "grammar": grammar_results}


@app.post("/api/analyze/file")
async def analyze_file(
    file: UploadFile = File(...),
    reference_file: Optional[UploadFile] = File(None),
    reference_text: Optional[str] = Form(None)
):
    # Validate extensions
    allowed = (".txt", ".pdf")
    if not any(file.filename.lower().endswith(e) for e in allowed):
        raise HTTPException(status_code=400, detail="Only .txt or .pdf files are supported.")

    text = await extract_text(file)

    # Resolve reference text
    ref_text = None
    if reference_file and reference_file.filename:
        ref_text = await extract_text(reference_file)
    elif reference_text and reference_text.strip():
        ref_text = reference_text.strip()

    if ref_text:
        plagiarism_results = plagiarism_detector.detect_plagiarism_custom(text, ref_text)
    else:
        plagiarism_results = plagiarism_detector.detect_plagiarism_single(text)

    grammar_results = grammar_detector.check_grammar(text)

    return {"text": text[:2000], "plagiarism": plagiarism_results, "grammar": grammar_results}

# Mount the rest of the frontend folder (CSS, JS, etc.)
frontend_dir = os.path.join(os.path.dirname(__file__), "../frontend")
app.mount("/", StaticFiles(directory=frontend_dir), name="frontend")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
