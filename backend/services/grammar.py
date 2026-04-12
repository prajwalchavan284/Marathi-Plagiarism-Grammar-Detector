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
DANDA = "."      # Modern Marathi uses English period
DOUBLE_DANDA = "."

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
    {"pattern": r"तो\s+(पोरगी|मुलगी|आई|बहीण|आजी|काकी|मावशी|ताई|वहिनी|बायको)",
     "english": "Gender mismatch: 'तो' (he/masculine) used with a feminine noun",
     "marathi": "लिंग चुकीचे: 'तो' पुल्लिंग आहे, परंतु पुढील शब्द स्त्रीलिंग आहे",
     "hint": "Use 'ती' for feminine nouns (e.g., 'ती मुलगी')"},
    # Masculine verb form + feminine subject
    {"pattern": r"ती\s+[^\n।॥]+\s+(गेला|आला|केला|बसला|उठला|पडला|धावला|हसला|रडला|बोलला)",
     "english": "Gender mismatch: 'ती' (feminine) with a masculine verb form",
     "marathi": "लिंग चुकीचे: 'ती' सोबत पुल्लिंग क्रियापद वापरले",
     "hint": "Use feminine verb form (e.g., गेली, आली, केली)"},
    # Feminine verb form + masculine subject
    {"pattern": r"तो\s+[^\n।॥]+\s+(गेली|आली|केली|बसली|उठली|पडली|धावली|हसली|रडली|बोलली)",
     "english": "Gender mismatch: 'तो' (masculine) with a feminine verb form",
     "marathi": "लिंग चुकीचे: 'तो' सोबत स्त्रीलिंग क्रियापद वापरले",
     "hint": "Use masculine verb form (e.g., गेला, आला, केला)"},
]

# ── Common Wrong Word Pairs (Confusable Words) ────────────────────────────────
COMMON_CONFUSABLES = [
    {"pattern": r"शेती\s+करतो\s+आम्ही", "hint": "आम्ही शेती करतो",
     "english": "Unusual word order: subject should come before verb",
     "marathi": "मराठीत कर्ता आधी येतो (आम्ही शेती करतो)"},
    {"pattern": r"त्याचा\s+आई", "hint": "त्याची आई",
     "english": "Incorrect prepositional gender (त्याची आई)",
     "marathi": "'आय' स्त्रीलिंगी असल्याने 'त्याची आई' लिहा"},
    {"pattern": r"तिची\s+मुलगा", "hint": "तिचा मुलगा",
     "english": "Incorrect prepositional gender (तिचा मुलगा)",
     "marathi": "'मुलगा' पुल्लिंगी असल्याने 'तिचा मुलगा' लिहा"},
]

# ── Orthography (Rhasva/Deergha) Errors ───────────────────────────────────────
ORTHOGRAPHY_ERRORS = [
    {"pattern": r"नाहि", "hint": "नाही", "english": "Spelling error (Rhasva/Deergha)", "marathi": "'नाही' असे लिहा (दीर्घ 'ही')"},
    {"pattern": r"आणी", "hint": "आणि", "english": "Spelling error (Rhasva/Deergha)", "marathi": "'आणि' असे लिहा (ह्रस्व 'णि')"},
    {"pattern": r"परंतू", "hint": "परंतु", "english": "Spelling error (Rhasva/Deergha)", "marathi": "'परंतु' असे लिहा (ह्रस्व 'तु')"},
    {"pattern": r"माहीती", "hint": "माहिती", "english": "Spelling error (Rhasva/Deergha)", "marathi": "'माहिती' असे लिहा (ह्रस्व 'हि')"},
    {"pattern": r"हळुहळु", "hint": "हळूहळू", "english": "Spelling error (Rhasva/Deergha)", "marathi": "'हळूहळू' असे लिहा"},
    {"pattern": r"महीना", "hint": "महिना", "english": "Spelling error (Rhasva/Deergha)", "marathi": "'महिना' असे लिहा (ह्रस्व 'हि')"},
    {"pattern": r"पाणि", "hint": "पाणी", "english": "Spelling error (Rhasva/Deergha)", "marathi": "'पाणी' दीर्घ 'णी' असते"},
]

# ── Pluralization (वचन) Errors ────────────────────────────────────────────────
PLURALIZATION_ERRORS = [
    {"pattern": r"अनेक\s+लोकं", "hint": "अनेक लोक", "english": "Incorrect pluralization. 'लोक' is already plural.", "marathi": "'अनेक लोक' लिहा. 'लोकं' हा शब्द व्याकरणात चुकीचा आहे."},
    {"pattern": r"सगळे\s+माणसं", "hint": "सगळी माणसं किंवा सगळे पुरुष", "english": "Incorrect adjective-noun pluralization.", "marathi": "'सगळी माणसं' किंवा 'सगळे पुरुष' लिहा."},
]

# ── Marathi verb-subject agreement table ──────────────────────────────────────
# Pattern: wrong_subject + wrong_verb_ending
VERB_SUBJECT_ERRORS = [
    # आम्ही / आपण with singular verb
    {"pattern": r"(आम्ही|आपण)\s+[^\n।॥]*\s+(\S+ला|\S+ली)",
     "english": "Verb agreement error: plural subject 'आम्ही/आपण' with singular verb",
     "marathi": "क्रियापद अनुबंध चुकीचे: अनेकवचन कर्त्यासाठी अनेकवचन क्रियापद वापरा",
     "hint": "Use plural verb form ending in 'लो' or 'ले' for आम्ही"},
    # मी with plural verb
    {"pattern": r"मी\s+[^\n।॥]*\s+(\S+लो|\S+ले)",
     "english": "Verb agreement error: 'मी' (I) with plural verb form",
     "marathi": "क्रियापद अनुबंध चुकीचे: 'मी' सोबत एकवचन क्रियापद वापरा",
     "hint": "Use singular verb form (e.g. गेलो, गेलो नाही)"},
    # ते (plural) with singular verb
    {"pattern": r"ते\s+[^\n।॥]*\s+(गेला|आला|केला|बसला|गेली|आली|केली)",
     "english": "Verb agreement error: plural subject 'ते' with singular verb",
     "marathi": "क्रियापद अनुबंध चुकीचे: 'ते' अनेकवचनी आहे, अनेकवचनी क्रियापद वापरा",
     "hint": "Use plural verb form (e.g. गेले, आले)"},
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
        self._check_confusables(text, errors)
        self._check_orthography(text, errors)
        self._check_pluralization(text, errors)

        return {
            "errors": errors,
            "errors_count": len(errors),
            "corrected_text": self._autocorrect(text, errors)
        }

    # ── Rule 1: Sentences should end with Period (.) ──────────────────────────
    def _check_danda(self, text: str, errors: List) -> None:
        sentences = re.split(r'[।॥\n.]', text)
        char_offset = 0
        for sent in sentences:
            s = sent.strip()
            # Only flag if the sentence has meaningful Devanagari characters
            if s and re.search(r'[\u0900-\u097F]{5,}', s):
                # Last non-whitespace char is not a period, danda or question mark
                if not re.search(r'[।॥.!?]$', s):
                    errors.append({
                        "message": "वाक्याच्या शेवटी पूर्णविराम (.) असणे आवश्यक आहे",
                        "english": "Sentence missing a full stop (.) at the end",
                        "offset": char_offset,
                        "length": len(s),
                        "context": s[:60],
                        "replacements": [s + "."],
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

    # ── Rule 5: Missing space after period ────────────────────────────────────
    def _check_missing_space_after_danda(self, text: str, errors: List) -> None:
        for m in re.finditer(r'[.।॥][^\s\n।॥.!?]', text):
            # Ignore numbers like 3.14
            if not re.match(r'\d\.\d', text[m.start()-1:m.start()+2]):
                errors.append({
                    "message": "पूर्णविरामानंतर (.) रिकामी जागा नाही",
                    "english": "Missing space after full stop (.)",
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

    # ── Auto-correct Engine ───────────────────────────────────────────────────
    def _autocorrect(self, text: str, errors: List) -> str:
        if not errors:
            return text
            
        corrected = text
        # Apply strict string replacement based on exact offsets in reverse order 
        # so earlier offsets don't shift when we replace later text.
        
        # Sort errors by offset descending
        sorted_errors = sorted(errors, key=lambda x: x["offset"], reverse=True)
        
        for e in sorted_errors:
            if e["replacements"] and e["replacements"][0] and e["ruleIssueType"] in ["spelling", "whitespace"]:
                # Only forcefully inject direct word replacements for spelling and spacing. 
                # Grammar hints are advice, not 1-to-1 word drop-ins.
                rep = e["replacements"][0]
                start = e["offset"]
                end = start + e["length"]
                corrected = corrected[:start] + rep + corrected[end:]

        # Finally apply safe global whitespace/punctuation fixes
        corrected = re.sub(r'  +', ' ', corrected)                 # double spaces
        corrected = re.sub(r'([!?।,])\1+', r'\1', corrected)       # repeated punct
        corrected = re.sub(r'([।॥.])([^\s\n।॥.!?])', r'\1 \2', corrected)  # space after period
        # Fix missing periods
        if [e for e in errors if "missing a full stop" in e["english"]]:
             if not re.search(r'[।॥.!?]$', corrected.strip()):
                  corrected = corrected.strip() + "."
        
        return corrected.strip()

    # ── Universal Regex Helper for Devanagari ─────────────────────────────────
    def _apply_rule(self, rule: Dict[str, str], text: str, errors: List, issue_type: str) -> None:
        """Helper to apply regex rules using custom Devanagari word boundaries."""
        # Custom bounds: Start/Space/Punctuation ... pattern ... End/Space/Punctuation
        regex_str = r"(^|\s|[।॥.,!?])(" + rule["pattern"] + r")($|\s|[।॥.,!?])"
        for m in re.finditer(regex_str, text):
            offset = m.start(2)
            length = m.end(2) - offset
            errors.append({
                "message": rule["marathi"],
                "english": rule["english"],
                "offset": offset,
                "length": length,
                "context": text[max(0, offset-10):min(len(text), offset+length+10)],
                "replacements": [rule.get("hint", "")],
                "ruleIssueType": issue_type
            })

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
                    "context": text[max(0, m.start()-10):min(len(text), m.end()+10)],
                    "replacements": [rule.get("hint", "")],
                    "ruleIssueType": "grammar"
                })

    # ── Rule 11: Confusable Words & Translitisisms ────────────────────────────
    def _check_confusables(self, text: str, errors: List) -> None:
        for rule in COMMON_CONFUSABLES:
            for m in re.finditer(rule["pattern"], text):
                errors.append({
                    "message": rule["marathi"],
                    "english": rule["english"],
                    "offset": m.start(),
                    "length": m.end() - m.start(),
                    "context": text[max(0, m.start()-10):min(len(text), m.end()+10)],
                    "replacements": [rule.get("hint", "")],
                    "ruleIssueType": "grammar"
                })

    # ── Rule 12: Orthography (Rhasva/Deergha) ─────────────────────────────────
    def _check_orthography(self, text: str, errors: List) -> None:
        for rule in ORTHOGRAPHY_ERRORS:
            # We add \b to ensure word bounds, but \b fails on Devanagari often, 
            # so we match explicitly surrounded by whitespace or punctuation
            regex_str = r"(^|\s|[।॥.,!?])(" + rule["pattern"].replace(r"\b", "") + r")($|\s|[।॥.,!?])"
            for m in re.finditer(regex_str, text):
                # Group 2 is the actual matched word
                offset = m.start(2)
                length = m.end(2) - offset
                errors.append({
                    "message": rule["marathi"],
                    "english": rule["english"],
                    "offset": offset,
                    "length": length,
                    "context": text[max(0, offset-10):min(len(text), offset+length+10)],
                    "replacements": [rule.get("hint", "")],
                    "ruleIssueType": "spelling"
                })

    # ── Rule 13: Pluralization (vachan) ───────────────────────────────────────
    def _check_pluralization(self, text: str, errors: List) -> None:
        for rule in PLURALIZATION_ERRORS:
            for m in re.finditer(rule["pattern"], text):
                errors.append({
                    "message": rule["marathi"],
                    "english": rule["english"],
                    "offset": m.start(),
                    "length": m.end() - m.start(),
                    "context": text[max(0, m.start()-10):min(len(text), m.end()+10)],
                    "replacements": [rule.get("hint", "")],
                    "ruleIssueType": "grammar"
                })



# ── Singleton instance (no startup delay — no Java, no downloads) ─────────────
grammar_detector = MarathiGrammarDetector()
logger.info("Marathi Grammar Detector (pure-Python) initialized successfully.")
