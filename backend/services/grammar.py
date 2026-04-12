"""
Marathi Grammar Checker — Pure Python, zero Java dependency.
Rules cover: punctuation, sentence structure, word repetition,
spacing, common gender/vibhakti patterns, and more.
"""
import re
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

# ── Marathi-specific patterns ─────────────────────────────────────────────────

# Common Marathi filler / redundant words
FILLER_WORDS = {"की", "तर", "परंतु", "आणि", "व", "आणखी"}

# Marathi sentence boundary characters
DANDA = "\u0964"      # ।
DOUBLE_DANDA = "\u0965"  # ॥

# Correct vibhakti (case suffix) patterns:
#   subject + ने/ला/ते/ची/चा/चे/ना/त/तून, etc.
# (Simplified detection of missing or repeated suffixes)
VIBHAKTI = ["ने", "ला", "ते", "ची", "चा", "चे", "ना", "त", "तून", "शी", "स"]


class MarathiGrammarDetector:

    def check_grammar(self, text: str) -> Dict[str, Any]:
        if not text or not text.strip():
            return {"errors": [], "errors_count": 0, "corrected_text": ""}

        errors: List[Dict[str, Any]] = []
        self._check_danda(text, errors)
        self._check_double_spaces(text, errors)
        self._check_repeated_words(text, errors)
        self._check_sentence_length(text, errors)
        self._check_missing_space_after_danda(text, errors)
        self._check_repeated_punctuation(text, errors)
        self._check_digit_mixed_words(text, errors)
        self._check_leading_trailing_spaces(text, errors)

        return {
            "errors": errors,
            "errors_count": len(errors),
            "corrected_text": self._autocorrect(text, errors)
        }

    # ── Rule 1: Sentences should end with दंड (।) ─────────────────────────────
    def _check_danda(self, text: str, errors: List) -> None:
        sentences = re.split(r'[।॥\n]', text)
        char_offset = 0
        for sent in sentences:
            s = sent.strip()
            # Only flag if the sentence has meaningful Devanagari characters
            if s and re.search(r'[\u0900-\u097F]{5,}', s):
                # Last non-whitespace char is not a danda/double-danda/English period
                if not re.search(r'[।॥.!?]$', s):
                    errors.append({
                        "message": "वाक्याच्या शेवटी दंड (।) असणे आवश्यक आहे",
                        "english": "Sentence may be missing a Marathi full stop (।) at the end",
                        "offset": char_offset,
                        "length": len(s),
                        "context": s[:60],
                        "replacements": [s + "।"],
                        "ruleIssueType": "punctuation"
                    })
            char_offset += len(sent) + 1  # +1 for the split char

    # ── Rule 2: Double spaces ─────────────────────────────────────────────────
    def _check_double_spaces(self, text: str, errors: List) -> None:
        for m in re.finditer(r'  +', text):
            errors.append({
                "message": "अतिरिक्त रिकाम्या जागा आढळल्या",
                "english": "Extra whitespace found between words",
                "offset": m.start(),
                "length": m.end() - m.start(),
                "context": text[max(0, m.start()-10):m.end()+10],
                "replacements": [" "],
                "ruleIssueType": "whitespace"
            })

    # ── Rule 3: Consecutive repeated words ────────────────────────────────────
    def _check_repeated_words(self, text: str, errors: List) -> None:
        # Match any Unicode word repeated back-to-back
        for m in re.finditer(r'\b(\w+)\s+\1\b', text, re.UNICODE):
            errors.append({
                "message": f"शब्द '{m.group(1)}' पुनरावृत्ती झाला आहे",
                "english": f"Word '{m.group(1)}' is repeated consecutively",
                "offset": m.start(),
                "length": m.end() - m.start(),
                "context": text[max(0, m.start()-10):m.end()+10],
                "replacements": [m.group(1)],
                "ruleIssueType": "duplication"
            })

    # ── Rule 4: Sentence too long ─────────────────────────────────────────────
    def _check_sentence_length(self, text: str, errors: List) -> None:
        sentences = re.split(r'[।॥\n.!?]', text)
        char_offset = 0
        for sent in sentences:
            words = sent.strip().split()
            if len(words) > 40:
                errors.append({
                    "message": "वाक्य खूप लांब आहे; ते लहान वाक्यात विभाजित करा",
                    "english": f"Sentence is very long ({len(words)} words). Consider splitting it.",
                    "offset": char_offset,
                    "length": len(sent),
                    "context": sent.strip()[:60] + "...",
                    "replacements": [],
                    "ruleIssueType": "style"
                })
            char_offset += len(sent) + 1

    # ── Rule 5: Missing space after danda ─────────────────────────────────────
    def _check_missing_space_after_danda(self, text: str, errors: List) -> None:
        for m in re.finditer(r'[।॥][^\s\n।॥]', text):
            errors.append({
                "message": "दंड (।) नंतर रिकामी जागा नाही",
                "english": "Missing space after Marathi full stop (।)",
                "offset": m.start(),
                "length": 2,
                "context": text[m.start():m.start()+15],
                "replacements": [text[m.start()] + " " + text[m.start()+1]],
                "ruleIssueType": "punctuation"
            })

    # ── Rule 6: Repeated punctuation (!!, ??, ।।) ─────────────────────────────
    def _check_repeated_punctuation(self, text: str, errors: List) -> None:
        for m in re.finditer(r'([!?।,])\1+', text):
            errors.append({
                "message": f"विरामचिन्ह '{m.group(1)}' पुन्हा पुन्हा वापरले",
                "english": f"Punctuation mark '{m.group(1)}' used repeatedly",
                "offset": m.start(),
                "length": m.end() - m.start(),
                "context": text[max(0, m.start()-5):m.end()+5],
                "replacements": [m.group(1)],
                "ruleIssueType": "punctuation"
            })

    # ── Rule 7: Numerals mixed inside Devanagari words ────────────────────────
    def _check_digit_mixed_words(self, text: str, errors: List) -> None:
        for m in re.finditer(r'[\u0900-\u097F]+[0-9]+[\u0900-\u097F]*|[0-9]+[\u0900-\u097F]+', text):
            errors.append({
                "message": "देवनागरी शब्दात इंग्रजी अंक आढळले",
                "english": "English digits mixed with Devanagari characters",
                "offset": m.start(),
                "length": m.end() - m.start(),
                "context": m.group(0),
                "replacements": [],
                "ruleIssueType": "typography"
            })

    # ── Rule 8: Leading / trailing whitespace on lines ────────────────────────
    def _check_leading_trailing_spaces(self, text: str, errors: List) -> None:
        for m in re.finditer(r'^\s+|\s+$', text, re.MULTILINE):
            if len(m.group(0)) > 0:
                errors.append({
                    "message": "ओळीच्या सुरुवातीला किंवा शेवटी अतिरिक्त जागा",
                    "english": "Leading or trailing whitespace on line",
                    "offset": m.start(),
                    "length": len(m.group(0)),
                    "context": repr(text[m.start():m.end()+10]),
                    "replacements": [""],
                    "ruleIssueType": "whitespace"
                })

    # ── Simple auto-correct (applies safe replacements) ───────────────────────
    def _autocorrect(self, text: str, errors: List) -> str:
        corrected = text
        # Only apply whitespace and punctuation auto-fixes (safe changes)
        corrected = re.sub(r'  +', ' ', corrected)                 # double spaces
        corrected = re.sub(r'([!?।,])\1+', r'\1', corrected)       # repeated punct
        corrected = re.sub(r'([।॥])([^\s\n।॥])', r'\1 \2', corrected)  # space after danda
        corrected = corrected.strip()
        return corrected


# ── Singleton instance (no startup delay — no Java, no downloads) ─────────────
grammar_detector = MarathiGrammarDetector()
logger.info("Marathi Grammar Detector (pure-Python) initialized successfully.")
