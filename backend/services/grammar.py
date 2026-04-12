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

# Marathi sentence boundary characters
DANDA = "\u0964"      # ।
DOUBLE_DANDA = "\u0965"  # ॥

# ── Gender Agreement Pairs ────────────────────────────────────────────────────
# Format: (feminine_pronoun, masculine_noun) → should raise an error
# Each tuple: (wrong_pair_pattern, correct_alternatives, error_description)
GENDER_MISMATCH_PAIRS = [
    # Feminine pronoun + masculine noun
    {"pattern": r"ती\s+(पोरगा|मुलगा|भाऊ|बाप|दादा|आजोबा|काका|नवरा|भाऊजी|मुलगा)",
     "english": "Gender mismatch: 'ती' (she/feminine) used with a masculine noun",
     "marathi": "लिंग चुकीचे: 'ती' स्त्रीलिंग आहे, परंतु पुढील शब्द पुल्लिंग आहे",
     "hint": "Use 'तो' for masculine nouns (e.g., 'तो पोरगा')"},
    # Masculine pronoun + feminine noun
    {"pattern": r"तो\s+(पोरगी|मुलगी|आई|बहीण|आजी|काकी|मावशी|ताई|वहिनी)",
     "english": "Gender mismatch: 'तो' (he/masculine) used with a feminine noun",
     "marathi": "लिंग चुकीचे: 'तो' पुल्लिंग आहे, परंतु पुढील शब्द स्त्रीलिंग आहे",
     "hint": "Use 'ती' for feminine nouns (e.g., 'ती मुलगी')"},
    # Masculine verb form + feminine subject
    {"pattern": r"ती\s+\S+\s+(गेला|आला|केला|बसला|उठला|पडला|धावला|हसला|रडला|बोलला)",
     "english": "Gender mismatch: 'ती' (feminine) with a masculine verb form",
     "marathi": "लिंग चुकीचे: 'ती' सोबत पुल्लिंग क्रियापद वापरले",
     "hint": "Use feminine verb form (e.g., गेली, आली, केली)"},
    # Feminine verb form + masculine subject
    {"pattern": r"तो\s+\S+\s+(गेली|आली|केली|बसली|उठली|पडली|धावली|हसली|रडली|बोलली)",
     "english": "Gender mismatch: 'तो' (masculine) with a feminine verb form",
     "marathi": "लिंग चुकीचे: 'तो' सोबत स्त्रीलिंग क्रियापद वापरले",
     "hint": "Use masculine verb form (e.g., गेला, आला, केला)"},
]

# ── Common Wrong Word Pairs (Confusable Words) ────────────────────────────────
COMMON_CONFUSABLES = [
    {"wrong": "शेती करतो आम्ही",    "right": "आम्ही शेती करतो",
     "english": "Unusual word order: subject should come before verb in Marathi",
     "marathi": "शब्द क्रम चुकीचा: मराठीत कर्ता आधी येतो"},
]

# ── Marathi verb-subject agreement table ──────────────────────────────────────
# Pattern: wrong_subject + wrong_verb_ending
VERB_SUBJECT_ERRORS = [
    # आम्ही / आपण with singular verb
    {"pattern": r"(आम्ही|आपण)\s+(\S+ला|\S+ली)\b",
     "english": "Verb agreement error: plural subject 'आम्ही/आपण' with singular verb",
     "marathi": "क्रियापद अनुबंध चुकीचे: अनेकवचन कर्त्यासाठी अनेकवचन क्रियापद वापरा",
     "hint": "Use plural verb form ending in 'लो' or 'लो' for आम्ही"},
    # मी with plural verb
    {"pattern": r"मी\s+(\S+लो|\S+लो)\b",
     "english": "Verb agreement error: 'मी' (I) with plural verb form",
     "marathi": "क्रियापद अनुबंध चुकीचे: 'मी' सोबत एकवचन क्रियापद वापरा"},
]


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
        self._check_gender_agreement(text, errors)
        self._check_verb_subject_agreement(text, errors)

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

    # ── Rule 9: Gender Agreement ──────────────────────────────────────────────
    def _check_gender_agreement(self, text: str, errors: List) -> None:
        for rule in GENDER_MISMATCH_PAIRS:
            for m in re.finditer(rule["pattern"], text):
                errors.append({
                    "message": rule["marathi"],
                    "english": rule["english"],
                    "offset": m.start(),
                    "length": m.end() - m.start(),
                    "context": text[max(0, m.start()-10):m.end()+10],
                    "replacements": [rule.get("hint", "")],
                    "ruleIssueType": "grammar"
                })

    # ── Rule 10: Verb-Subject Agreement ───────────────────────────────────────
    def _check_verb_subject_agreement(self, text: str, errors: List) -> None:
        for rule in VERB_SUBJECT_ERRORS:
            for m in re.finditer(rule["pattern"], text):
                errors.append({
                    "message": rule["marathi"],
                    "english": rule["english"],
                    "offset": m.start(),
                    "length": m.end() - m.start(),
                    "context": text[max(0, m.start()-10):m.end()+10],
                    "replacements": [rule.get("hint", "")],
                    "ruleIssueType": "grammar"
                })



# ── Singleton instance (no startup delay — no Java, no downloads) ─────────────
grammar_detector = MarathiGrammarDetector()
logger.info("Marathi Grammar Detector (pure-Python) initialized successfully.")
