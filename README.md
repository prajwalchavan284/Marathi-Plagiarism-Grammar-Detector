# मराठी DeepCheck — Marathi Plagiarism & Grammar Detection Engine

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-2.x-EE4C2C?logo=pytorch&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-blue)

A full-stack plagiarism detection and grammar analysis system built specifically for **Marathi (मराठी)** text. Combines a multi-signal NLP ensemble (TF-IDF, Sentence-BERT, n-gram Jaccard) with a 23+ category rule-based grammar engine — all served behind a FastAPI backend and a clean, minimal frontend.

---

## Architecture

```
.
├── backend/
│   ├── main.py                  # FastAPI app, routes, middleware
│   └── services/
│       ├── plagiarism.py        # Ensemble plagiarism detector
│       └── grammar.py           # Rule-based Marathi grammar engine
├── frontend/
│   ├── index.html               # SPA entry point
│   ├── script.js                # Client-side logic & API calls
│   ├── style.css                # UI styling (Apple-inspired design)
│   └── config.js                # API base URL config
├── plag_project.ipynb           # Research notebook
├── requirements.txt
└── .gitignore
```

## How It Works

### Plagiarism Detection Pipeline

The detector doesn't rely on a single similarity metric. It runs a **weighted ensemble** of four independent signals and fuses them into one final score:

| Signal | Weight | Method |
|---|---|---|
| Sentence-BERT | 0.50 | Multilingual transformer embeddings (`paraphrase-multilingual-MiniLM-L12-v2`) |
| TF-IDF Cosine | 0.25 | Bag-of-words with character + word n-grams (1,3) |
| N-gram Jaccard | 0.20 | Word-level 5-gram overlap via Jaccard index |
| Length Penalty | −0.05 | Penalizes score when texts differ significantly in length |

For **custom reference comparisons**, it goes deeper — splitting both texts into sentences, computing per-sentence similarity matrices, and aggregating the top-half coverage scores into a final plagiarism percentage.

```
Score = clip(0.25·TF-IDF + 0.50·BERT + 0.20·Jaccard − 0.05·LenPenalty, 0, 1)
```

### Grammar Engine

A fully **offline, zero-dependency** (no API calls, no internet) rule-based grammar engine covering 23+ Marathi-specific categories:

- **Orthography** — spelling corrections, sandhi joins, repeated words, punctuation
- **Morphology** — vibhakti (case marker) errors, negation patterns, redundant postposition stacking
- **Syntax** — subject-verb GNP agreement, demonstrative/relative pronoun gender, adjective-noun gender, possessive-noun gender, auxiliary verb agreement, SOV word order, clause pairing (`जर…तर`, `जेव्हा…तेव्हा`)
- **Lexical** — dialect normalization (non-standard → standard forms)
- **Surface** — extra whitespace, repeated punctuation, mixed-script digits, sentence length warnings

Includes a `hard_repair()` method that auto-corrects text by applying all rules in priority order.

Each error is scored with category-based weights to produce a final **grammar score (0–100)**.

## Tech Stack

| Layer | Tech |
|---|---|
| Backend | **FastAPI** + Uvicorn (ASGI) |
| NLP Models | `sentence-transformers` (HuggingFace), `scikit-learn` TF-IDF |
| Deep Learning | PyTorch (BERT inference) |
| PDF Parsing | `pdfplumber` |
| Frontend | Vanilla HTML/CSS/JS — no framework overhead |
| Serving | Static files served via FastAPI's `StaticFiles` mount |

## Getting Started

### Prerequisites

- Python 3.10+
- pip

### Setup

```bash
git clone https://github.com/prajwalchavan284/Marathi-Plagiarism-Grammar-Detector.git
cd Marathi-Plagiarism-Grammar-Detector

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r backend/requirements.txt
```

> **Note:** First run will download the Sentence-BERT model (~470MB). Cached locally after that.

### Run

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Open `http://localhost:8000` — the frontend is served automatically.

## API Reference

### `POST /api/analyze`

Analyze raw text via JSON payload.

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "text": "मी शाळेला गेलो.",
    "reference_text": "मी शाळेत गेलो."
  }'
```

| Field | Type | Required | Description |
|---|---|---|---|
| `text` | string | ✅ | Text to analyze |
| `reference_text` | string | ❌ | Optional reference for comparison |

### `POST /api/analyze/file`

Upload `.txt` or `.pdf` files via `multipart/form-data`.

```bash
curl -X POST http://localhost:8000/api/analyze/file \
  -F "file=@document.pdf" \
  -F "reference_file=@original.pdf"
```

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | file | ✅ | Target document (.txt/.pdf) |
| `reference_file` | file | ❌ | Reference document |
| `reference_text` | string | ❌ | Reference as plain text |

### Response Schema

```json
{
  "plagiarism": {
    "is_plagiarized": false,
    "max_similarity": 12.45,
    "matched_document": null,
    "detailed_results": [...]
  },
  "grammar": {
    "errors": [...],
    "errors_count": 2,
    "corrected_text": "...",
    "grammar_score": 85.0,
    "metrics": {
      "word_count": 42,
      "unique_words": 38,
      "type_token_ratio": 0.9048,
      "reading_level": "Professional",
      "processing_ms": 12.5
    }
  }
}
```

## Configuration

Plagiarism thresholds and model params are configured via `PlagiarismConfig`:

```python
@dataclass
class PlagiarismConfig:
    tfidf_weight: float = 0.4
    bert_weight: float = 0.6
    threshold: float = 0.55       # similarity cutoff
    max_features: int = 8000      # TF-IDF vocab size
    ngram_range: tuple = (1, 3)   # character n-gram range
    batch_size: int = 16          # BERT encoding batch size
    cache_embeddings: bool = True # cache corpus embeddings
```

## Roadmap

- [ ] OCR support for scanned PDFs (Tesseract/EasyOCR)
- [ ] Batch file upload and comparison
- [ ] Exportable reports (PDF/JSON)
- [ ] User authentication & history
- [ ] Docker containerization

---

Built with ☕ and Python.
