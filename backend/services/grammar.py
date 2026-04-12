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
    {"pattern": r"ती(\s+)(पोरगा|मुलगा|भाऊ|बाप|दादा|आजोबा|काका|नवरा|भाऊजी|मुलगा)",
     "english": "Gender mismatch: 'ती' (she/feminine) used with a masculine noun",
     "marathi": "लिंग चुकीचे: 'ती' स्त्रीलिंग आहे, परंतु पुढील शब्द पुल्लिंग आहे",
     "hint": "Use 'तो' for masculine nouns (e.g., 'तो पोरगा')",
     "replace": r"तो\1\2"},
    # Masculine pronoun + feminine noun
    {"pattern": r"तो(\s+)(पोरगी|मुलगी|आई|बहीण|आजी|काकी|मावशी|ताई|वहिनी|बायको)",
     "english": "Gender mismatch: 'तो' (he/masculine) used with a feminine noun",
     "marathi": "लिंग चुकीचे: 'तो' पुल्लिंग आहे, परंतु पुढील शब्द स्त्रीलिंग आहे",
     "hint": "Use 'ती' for feminine nouns (e.g., 'ती मुलगी')",
     "replace": r"ती\1\2"},
    # Masculine verb form + feminine subject
    {"pattern": r"ती(\s+[^\n।॥]+\s+)(गेला|आला|केला|बसला|उठला|पडला|धावला|हसला|रडला|बोलला)",
     "english": "Gender mismatch: 'ती' (feminine) with a masculine verb form",
     "marathi": "लिंग चुकीचे: 'ती' सोबत पुल्लिंग क्रियापद वापरले",
     "hint": "Use feminine verb form (e.g., गेली, आली, केली)",
     "replace": r"तो\1\2"},
    # Feminine verb form + masculine subject
    {"pattern": r"तो(\s+[^\n।॥]+\s+)(गेली|आली|केली|बसली|उठली|पडली|धावली|हसली|रडली|बोलली)",
     "english": "Gender mismatch: 'तो' (masculine) with a feminine verb form",
     "marathi": "लिंग चुकीचे: 'तो' सोबत स्त्रीलिंग क्रियापद वापरले",
     "hint": "Use masculine verb form (e.g., गेला, आला, केला)",
     "replace": r"ती\1\2"},
]

# ── Common Wrong Word Pairs (Confusable Words) ────────────────────────────────
COMMON_CONFUSABLES = [
    {"pattern": r"शेती\s+करतो\s+आम्ही", "hint": "आम्ही शेती करतो", "replace": "आम्ही शेती करतो",
     "english": "Unusual word order: subject should come before verb",
     "marathi": "मराठीत कर्ता आधी येतो (आम्ही शेती करतो)"},
    {"pattern": r"त्याचा(\s+)आई", "hint": "त्याची आई", "replace": r"त्याची\1आई",
     "english": "Incorrect prepositional gender (त्याची आई)",
     "marathi": "'आय' स्त्रीलिंगी असल्याने 'त्याची आई' लिहा"},
    {"pattern": r"तिची(\s+)मुलगा", "hint": "तिचा मुलगा", "replace": r"तिचा\1मुलगा",
     "english": "Incorrect prepositional gender (तिचा मुलगा)",
     "marathi": "'मुलगा' पुल्लिंगी असल्याने 'तिचा मुलगा' लिहा"},
]

# ── Orthography (Rhasva/Deergha/Anuswar) Errors ──────────────────────────────
ORTHOGRAPHY_ERRORS = [
    # Vowel Length (Deergha at end is standard for many Marathi words)
    {"pattern": r"नाहि", "hint": "नाही", "english": "Spelling: terminal 'i' should be long (deergha)", "marathi": "'नाही' असे लिहा (दीर्घ 'ही')"},
    {"pattern": r"आणी", "hint": "आणि", "english": "Spelling: 'आणि' takes short 'i' (rhasva)", "marathi": "'आणि' असे लिहा (ह्रस्व 'णि')"},
    {"pattern": r"परंतू", "hint": "परंतु", "english": "Spelling: 'परंतु' takes short 'u' (rhasva)", "marathi": "'परंतु' असे लिहा (ह्रस्व 'तु')"},
    {"pattern": r"माहीती", "hint": "माहिती", "english": "Spelling: 'माहिती' takes short second 'i'", "marathi": "'माहिती' असे लिहा (ह्रस्व 'हि')"},
    {"pattern": r"हळुहळु", "hint": "हळूहळू", "english": "Spelling error in 'hadvu-hadvu'", "marathi": "'हळूहळू' असे लिहा (दोन्ही कडे दीर्घ 'ऊ')"},
    {"pattern": r"महीना", "hint": "महिना", "english": "Spelling error in 'mahina'", "marathi": "'महिना' असे लिहा (ह्रस्व 'हि')"},
    {"pattern": r"पाणि", "hint": "पाणी", "english": "Spelling: 'water' ends in long 'i'", "marathi": "'पाणी' दीर्घ 'णी' असते"},
    {"pattern": r"कवि", "hint": "कवी", "english": "Spelling: 'poet' ends in long 'i' in standard Marathi", "marathi": "'कवी' दीर्घ 'वी' असते"},
    
    # Anuswar (Nasals) usage
    {"pattern": r"आमु", "hint": "आमूं", "english": "Missing nasal (anuswar) on terminal vowel", "marathi": "अनुस्वार हवा: 'आमूं' लिहा"},
    {"pattern": r"देउ", "hint": "देऊं", "english": "Missing nasal (anuswar) on terminal vowel", "marathi": "अनुस्वार हवा: 'देऊं' लिहा"},
    {"pattern": r"घेउ", "hint": "घेऊं", "english": "Missing nasal (anuswar) on terminal vowel", "marathi": "अनुस्वार हवा: 'घेऊं' लिहा"},
]

# ── Adjective Agreement Errors (A-ending Adjectives) ─────────────────────────
# Pattern: adjective + mismatching noun
ADJECTIVE_AGREEMENT_ERRORS = [
    # Masculine Adj + Feminine Noun
    {"pattern": r"चांगला(\s+)(मुलगी|आई|बहीण|शाळा|गाडी|सायकल|वही)",
     "hint": "चांगली", "replace": r"चांगली\1\2",
     "english": "Adjective mismatch: 'चांगला' (masculine) with feminine noun",
     "marathi": "विशेषण चुकीचे: स्त्रीलिंगी नामासाठी 'चांगली' वापरा"},
    # Feminine Adj + Masculine Noun
    {"pattern": r"चांगली(\s+)(मुलगा|भाऊ|बाप|शाळा|रस्ता|डब्बा|पेन|गव्हा|वाघ)",
     "hint": "चांगला", "replace": r"चांगला\1\2",
     "english": "Adjective mismatch: 'चांगली' (feminine) with masculine noun",
     "marathi": "विशेषण चुकीचे: पुल्लिंगी नामासाठी 'चांगला' वापरा"},
    # Plural Adj + Singular Noun
    {"pattern": r"चांगले(\s+)(मुलगा|मुलगी|पोरगा|पोरगी)",
     "hint": "चांगला/चांगली", "replace": r"चांगला\1\2",
     "english": "Adjective mismatch: plural form with singular noun",
     "marathi": "विशेषण चुकीचे: एकवचनी नामासाठी एकवचनी विशेषण वापरा"},
]

# ── Vibhakti (Case Endings) & Samanya Rupa Errors ─────────────────────────────
VIBHAKTI_ERRORS = [
    {"pattern": r"घरत", "hint": "घरात", "replace": "घरात",
     "english": "Incorrect inflection: 'घर' should become 'घरा' before suffix 'त'",
     "marathi": "सामान्यरूप चुकीचे: 'घर' चे 'घरा-' होऊन मग 'त' जोडा (घरात)"},
    {"pattern": r"शाळात", "hint": "शाळेत", "replace": "शाळेत",
     "english": "Incorrect inflection: 'शाळा' should become 'शाळे' before suffix 'त'",
     "marathi": "सामान्यरूप चुकीचे: 'शाळेत' असे लिहा"},
    {"pattern": r"मीला", "hint": "मला", "replace": "मला",
     "english": "Pronoun error: 'मी' becomes 'मला' with 'ला' suffix",
     "marathi": "'मीला' ऐवजी 'मला' वापरा"},
    {"pattern": r"मीचा", "hint": "माझा", "replace": "माझा",
     "english": "Pronoun error: Use 'माझा' instead of 'मीचा'",
     "marathi": "'मीचा' ऐवजी 'माझा' वापरा"},
]

# ── Pluralization (वचन) Errors ────────────────────────────────────────────────
PLURALIZATION_ERRORS = [
    {"pattern": r"अनेक(\s+)लोकं", "hint": "अनेक लोक", "replace": r"अनेक\1लोक", "english": "Incorrect pluralization. 'लोक' is already plural.", "marathi": "'अनेक लोक' लिहा. 'लोकं' हा शब्द व्याकरणात चुकीचा आहे."},
    {"pattern": r"सगळे(\s+)माणसं", "hint": "सगळी माणसं किंवा सगळे पुरुष", "replace": r"सगळी\1माणसं", "english": "Incorrect adjective-noun pluralization.", "marathi": "'सगळी माणसं' किंवा 'सगळे पुरुष' लिहा."},
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
        # self._check_danda(text, errors)  # Removed per user request
        self._check_double_spaces(text, errors)
        self._check_repeated_words(text, errors)
        self._check_sentence_length(text, errors)
        # self._check_missing_space_after_danda(text, errors) # Removed per user request
        self._check_repeated_punctuation(text, errors)
        self._check_digit_mixed_words(text, errors)
        self._check_leading_trailing_spaces(text, errors)
        self._check_gender_agreement(text, errors)
        self._check_adjective_agreement(text, errors)
        self._check_verb_subject_agreement(text, errors)
        self._check_confusables(text, errors)
        self._check_orthography(text, errors)
        self._check_vibhakti(text, errors)
        self._check_pluralization(text, errors)
        self._check_sov_structure(text, errors)
        self._check_punctuation(text, errors)

        return {
            "errors": errors,
            "errors_count": len(errors),
            "corrected_text": self._autocorrect(text, errors)
        }

    # ── Rule 1: Sentences should end with Period (.) ──────────────────────────
    # [DISABLED per user request — no longer enforcing period at end of sentence]

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
    # [DISABLED per user request — no longer enforcing period formatting]

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
            if e["replacements"] and e["replacements"][0] and e["ruleIssueType"] in ["spelling", "whitespace", "grammar"]:
                rep = e["replacements"][0]
                start = e["offset"]
                end = start + e["length"]
                corrected = corrected[:start] + rep + corrected[end:]

        # Finally apply safe global whitespace/punctuation fixes
        corrected = re.sub(r'  +', ' ', corrected)                 # double spaces
        corrected = re.sub(r'([!?।,])\1+', r'\1', corrected)       # repeated punct
        # (Missing Period logic removed per user request)

        return corrected.strip()

    # ── Universal Regex Helper for Devanagari ─────────────────────────────────
    def _apply_rule(self, rule: Dict[str, str], text: str, errors: List, issue_type: str) -> None:
        """Helper to apply regex rules using custom Devanagari word boundaries."""
        # Custom bounds: Start/Space/Punctuation ... pattern ... End/Space/Punctuation
        regex_str = r"(^|\s|[।॥.,!?])(" + rule["pattern"] + r")($|\s|[।॥.,!?])"
        for m in re.finditer(regex_str, text):
            offset = m.start(2)
            matched_text = m.group(2)
            length = len(matched_text)

            replacement = rule.get("hint", "")
            if "replace" in rule:
                # Use regex sub to preserve spaces and construct exact replacement
                replacement = re.sub(rule["pattern"], rule["replace"], matched_text)
            elif issue_type == "spelling":
                replacement = rule.get("hint", "")

            errors.append({
                "message": rule["marathi"],
                "english": rule["english"],
                "offset": offset,
                "length": length,
                "context": text[max(0, offset-10):min(len(text), offset+length+10)],
                "replacements": [replacement],
                "ruleIssueType": issue_type
            })

    # ── Rule 9: Gender Agreement ──────────────────────────────────────────────
    def _check_gender_agreement(self, text: str, errors: List) -> None:
        for rule in GENDER_MISMATCH_PAIRS:
            self._apply_rule(rule, text, errors, "grammar")

    # ── Rule 10: Verb-Subject Agreement ───────────────────────────────────────
    def _check_verb_subject_agreement(self, text: str, errors: List) -> None:
        for rule in VERB_SUBJECT_ERRORS:
            self._apply_rule(rule, text, errors, "grammar")

    # ── Rule 11: Confusable Words & Translitisisms ────────────────────────────
    def _check_confusables(self, text: str, errors: List) -> None:
        for rule in COMMON_CONFUSABLES:
            self._apply_rule(rule, text, errors, "grammar")

    # ── Rule 12: Orthography (Rhasva/Deergha) ─────────────────────────────────
    def _check_orthography(self, text: str, errors: List) -> None:
        for rule in ORTHOGRAPHY_ERRORS:
            self._apply_rule(rule, text, errors, "spelling")

    # ── Rule 13: Adjective Agreement ──────────────────────────────────────────
    def _check_adjective_agreement(self, text: str, errors: List) -> None:
        for rule in ADJECTIVE_AGREEMENT_ERRORS:
            self._apply_rule(rule, text, errors, "grammar")

    # ── Rule 14: Vibhakti / Samanya Rupa ──────────────────────────────────────
    def _check_vibhakti(self, text: str, errors: List) -> None:
        for rule in VIBHAKTI_ERRORS:
            self._apply_rule(rule, text, errors, "grammar")

    # ── Rule 15: Pluralization (vachan) ───────────────────────────────────────
    def _check_pluralization(self, text: str, errors: List) -> None:
        for rule in PLURALIZATION_ERRORS:
            self._apply_rule(rule, text, errors, "grammar")

    # ── Rule 16: SOV Structure (Basic) ────────────────────────────────────────
    def _check_sov_structure(self, text: str, errors: List) -> None:
        # Check if sentences end with characteristic Marathi verb markers
        # If a line seems like it has a verb in the middle followed by too many words
        # e.g., "Mi khato amba" (I eat mango)
        # Regex to detect Subject + Verb + Object instead of Subject + Object + Verb
        # This is a heuristic: Pronoun + Verb + Noun
        for m in re.finditer(r"\b(मी|तो|ती|ते|आम्ही|तुम्ही|आपण)\s+(खातो|पितो|करतो|आहे|गेलो|येतो)\s+([^\s।॥.!?]+)\b", text):
            errors.append({
                "message": "वाक्यरचना चुकीची: क्रियापद शेवटी असायला हवे (SOV structure)",
                "english": "Marathi word order: Verb should generally come at the end (SOV).",
                "offset": m.start(),
                "length": len(m.group(0)),
                "context": m.group(0),
                "replacements": [],
                "ruleIssueType": "grammar"
            })

    # ── Rule 17: Punctuation (Missing Full Stop, etc) ─────────────────────────
    def _check_punctuation(self, text: str, errors: List) -> None:
        # Check if sentence ends with punctuation
        sentences = re.split(r'[\u0964\u0965\n]', text)
        offset = 0
        for s in sentences:
            stripped = s.strip()
            if stripped and not stripped[-1] in ".!?,":
                # Check for missing full stop at end of line/sentence
                errors.append({
                    "message": "वाक्याच्या शेवटी पूर्णविराम (.) हवा",
                    "english": "Sentence should end with a period (.)",
                    "offset": offset + s.rfind(stripped[-1]),
                    "length": 1,
                    "context": stripped[-15:],
                    "replacements": ["."],
                    "ruleIssueType": "punctuation"
                })
            offset += len(s) + 1



# ── Singleton instance (no startup delay — no Java, no downloads) ─────────────
grammar_detector = MarathiGrammarDetector()
logger.info("Marathi Grammar Detector (pure-Python) initialized successfully.")
