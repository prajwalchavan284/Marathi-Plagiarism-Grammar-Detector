import re
import unicodedata
import time
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set, Tuple

@dataclass
class GrammarError:
    """One detected grammar violation."""
    category:        str   # ORTHOGRAPHY / MORPHOLOGY / SYNTAX / LEXICAL / SURFACE
    sub_category:    str
    erroneous_token: str
    suggested_token: str
    character_offset: int
    token_length:    int
    severity:        str   # CRITICAL / WARNING / SUGGESTION
    explanation:     str



_DEV_RANGE = '\u0900-\u097F'


def _wb(word: str) -> str:
    """Devanagari-aware word boundary wrap."""
    return rf'(?<![{_DEV_RANGE}]){re.escape(word)}(?![{_DEV_RANGE}])'


def _add(errors: list, cat: str, sub: str, wrong: str, right: str,
         offset: int, sev: str, exp: str):
    errors.append(GrammarError(cat, sub, wrong, right, offset, len(wrong), sev, exp))


def _scan_pairs(text: str, pairs: dict, errors: list,
                cat: str, sub: str, sev: str, tmpl: str = "'{w}' → '{r}'"):
    for wrong, right in pairs.items():
        idx = 0
        while True:
            pos = text.find(wrong, idx)
            if pos == -1:
                break
            before = text[pos - 1] if pos > 0 else ' '
            after  = text[pos + len(wrong)] if pos + len(wrong) < len(text) else ' '
            if not re.match(f'[{_DEV_RANGE}]', before) and \
               not re.match(f'[{_DEV_RANGE}]', after):
                _add(errors, cat, sub, wrong, right, pos, sev,
                     tmpl.format(w=wrong, r=right))
            idx = pos + 1


def _scan_regex(text: str, rules: list, errors: list,
                cat: str, sub: str, sev: str):
    for pat, rep, exp in rules:
        for m in re.finditer(pat, text):
            _add(errors, cat, sub, m.group(), rep, m.start(), sev, exp)


class KB:

    # ── Noun Gender Sets ───────────────────────────────────────────────────────
    MASC_NOUNS: Set[str] = {
        'मुलगा', 'पोरगा', 'भाऊ', 'बाप', 'दादा', 'काका', 'मामा', 'आजोबा',
        'नवरा', 'भाऊजी', 'मित्र', 'शत्रू', 'राजा', 'देव', 'कुत्रा', 'घोडा',
        'उंट', 'बैल', 'वाघ', 'सिंह', 'कावळा', 'पोपट', 'साप', 'उंदीर', 'हत्ती',
        'नेता', 'कवी', 'लेखक', 'शिक्षक', 'विद्यार्थी', 'वकील', 'डॉक्टर',
        'पंतप्रधान', 'अध्यक्ष', 'सेवक', 'माणूस', 'मनुष्य',
        'रस्ता', 'पाऊस', 'वारा', 'दगड', 'पर्वत', 'सूर्य', 'चंद्र',
        'समुद्र', 'डोंगर', 'वृक्ष', 'आंबा', 'केळा', 'पेरू',
        'दिवस', 'महिना', 'वर्ष', 'रंग', 'डब्बा', 'पेन', 'रस्ता',
    }

    FEM_NOUNS: Set[str] = {
        'मुलगी', 'पोरगी', 'बहीण', 'आई', 'माय', 'ताई', 'काकी', 'मामी',
        'मावशी', 'आजी', 'मैत्रीण', 'राणी', 'देवी', 'बायको', 'वहिनी',
        'कुत्री', 'घोडी', 'गाय', 'म्हैस', 'मांजर',
        'नदी', 'विहीर', 'टेकडी', 'जमीन',
        'शाळा', 'इमारत', 'खुर्ची', 'वही', 'टोपी', 'साडी', 'चादर', 'सायकल',
        'गाडी', 'रेल्वे', 'बस', 'होडी', 'बोट',
        'भाषा', 'कविता', 'कथा', 'माहिती', 'खबर', 'बातमी',
        'रात्र', 'संध्याकाळ', 'सकाळ', 'वेळ',
    }

    NEUT_NOUNS: Set[str] = {
        'घर', 'पुस्तक', 'काम', 'पाणी', 'गाव', 'मन', 'गाणे', 'फूल',
        'झाड', 'दार', 'दुकान', 'विमान', 'स्वप्न', 'आकाश', 'मैदान',
        'जग', 'जंगल', 'शेत', 'खेळणे', 'भाषण', 'ज्ञान', 'सत्य',
        'फळ', 'जेवण', 'औषध', 'दूध', 'तेल', 'धान्य',
        'शहर', 'राज्य', 'राष्ट्र',
    }

    # ── Spelling / Shuddhalekhan ───────────────────────────────────────────────
    SPELLING: Dict[str, str] = {
        # Vowel-length
        'नाहि':       'नाही',
        'नाहीं':      'नाही',
        'खुप':        'खूप',
        'दुर':        'दूर',
        'मुल':        'मूल',
        'पानी':       'पाणी',
        'पाणि':       'पाणी',
        'कवि':        'कवी',
        'पुर्व':      'पूर्व',
        'सुर्य':      'सूर्य',
        'जिवन':       'जीवन',
        'हळुहळु':     'हळूहळू',
        'हळू हळू':    'हळूहळू',
        'महीना':      'महिना',
        'माहीती':     'माहिती',
        # Anusvara / nasalization
        'अन्त':       'अंत',
        'चिन्ता':     'चिंता',
        'पन्ख':       'पंख',
        'बन्ध':       'बंध',
        'पन्डित':     'पंडित',
        'मन्दिर':     'मंदिर',
        'सम्पूर्ण':   'संपूर्ण',
        'संपर्ण':     'संपूर्ण',
        # Double-letter / gemination
        'आहेे':       'आहे',
        'आहेत्':      'आहेत',
        'नाहीी':      'नाही',
        'झालेे':      'झाले',
        'प्रसिध्द':   'प्रसिद्ध',
        'सुध्दा':     'सुद्धा',
        'बुध्दी':     'बुद्धी',
        'विद्दार्थी': 'विद्यार्थी',
        # Morpheme / inflection
        'आणी':        'आणि',
        'आणिक':       'आणखी',
        'परंतू':      'परंतु',
        'परंतूही':    'परंतुही',
        'माहिति':     'माहिती',
        'म्हनाला':    'म्हणाला',
        'म्हनाली':    'म्हणाली',
        'म्हनाले':    'म्हणाले',
        'म्हनतो':     'म्हणतो',
        'म्हनते':     'म्हणते',
        'म्हनतात':    'म्हणतात',
        'म्हनून':     'म्हणून',
        'म्हनायला':   'म्हणायला',
        'पूत्र':      'पुत्र',
        # Colloquial contractions
        'दिलाय':      'दिला आहे',
        'केलाय':      'केला आहे',
        'आलाय':       'आला आहे',
        'गेलाय':      'गेला आहे',
        'हवाये':      'हवा आहे',
        'नकोये':      'नको आहे',
        # Confused pairs
        'भेटली':      'मिळाली',
        'भेटला':      'मिळाला',
        'बद्धल':      'बद्दल',
        'पेक्षां':    'पेक्षा',
        'मुळाने':     'मुळे',
        'मुळून':      'मुळे',
        'करूनी':      'करून',
        'जाऊनी':      'जाऊन',
        'येऊनी':      'येऊन',
        'तसेंच':      'तसेच',
        'मात्रं':     'मात्र',
        'जेणेकरुन':   'जेणेकरून',
        'कारणंकी':    'कारण की',
        'कारणकी':     'कारण की',
        'कारण की':    'कारण',
        'परंतु पण':   'परंतु',
        'म्हणून तर':  'म्हणून',
        # Formal pronoun forms (old) → modern
        'आपणास':     'आपल्याला',
        'तुम्हास':   'तुम्हाला',
        'त्यांस':    'त्यांना',
        'त्यास':     'त्याला',
        # Continuous tense errors — तो form
        'सांगतो आहे': 'सांगत आहे',
        'बघतो आहे':   'बघत आहे',
        'करतो आहे':   'करत आहे',
        'जातो आहे':   'जात आहे',
        'येतो आहे':   'येत आहे',
        'खातो आहे':   'खात आहे',
        'बोलतो आहे':  'बोलत आहे',
        'पाहतो आहे':  'पाहत आहे',
        'चालतो आहे':  'चालत आहे',
        'धावतो आहे':  'धावत आहे',
        'लिहितो आहे': 'लिहित आहे',
        'वाचतो आहे':  'वाचत आहे',
        'शिकतो आहे':  'शिकत आहे',
        # Continuous tense errors — ती form
        # NOTE: These are handled by _check_continuous regex rules.
        # Do NOT add them here as they conflict with the GNP pass.
        # Continuous (other)
        'जाती आहे':   'जात आहे',
        'येती आहे':   'येत आहे',
        'खाती आहे':   'खात आहे',
        # Future tense typos
        'येतेल':      'येईल',
        'जाईेल':      'जाईल',
        'होईेल':      'होईल',
        'करईल':       'करेल',
        'बघईल':       'बघेल',
        'होऊन जाईल': 'होईल',
        # Perfect tense errors
        'गेलेला आहे': 'गेला आहे',
        'केलेला आहे': 'केला आहे',
        'आलेला आहे':  'आला आहे',
        'केलेत':      'केले',
        'गेलेत':      'गेले',
        'आलेत':       'आले',
        # Negation spelling
        'करत नाहि':  'करत नाही',
        'जात नाहि':  'जात नाही',
        'येत नाहि':  'येत नाही',
        'बोलत नाहि': 'बोलत नाही',
        'सांगत नाहि':'सांगत नाही',
        # Complex tense combo
        'जातो होती':   'जात होते',
        'जाते होती':   'जात होते',
        'करतो होती':   'करत होते',
        'खेळतो होती':  'खेळत होते',
        'शाळा जातो होती': 'शाळेत जात होते',
        # Plural + wrong verb (spelling-level fix)
        'मुलं खेळत होता': 'मुले खेळत होती',
        'मुलं खेळत होते': 'मुले खेळत होती',
        # 1st person plural past
        'आम्ही खूप हसले': 'आम्ही खूप हसलो',
        'आम्ही हसले':     'आम्ही हसलो',
        # Possessive genitive
        'माझी मित्रला':  'माझ्या मित्राला',
        'माझी मित्राला': 'माझ्या मित्राला',
    }
    SPELLING = {k: v for k, v in SPELLING.items() if k != v}

    # ── Sandhi ────────────────────────────────────────────────────────────────
    SANDHI: Dict[str, str] = {
        'सूर्य उदय':   'सूर्योदय',
        'सुर्य उदय':   'सूर्योदय',
        'देव अलय':     'देवालय',
        'देव आलय':     'देवालय',
        'महा उत्सव':   'महोत्सव',
        'विद्या अर्थी':'विद्यार्थी',
        'ग्राम उदय':   'ग्रामोदय',
    }

    # ── Vibhakti Case-Marker Rules ─────────────────────────────────────────────
    VIBHAKTI: List[Tuple[str, str, str]] = [
        # Locative misuse
        (_wb('शाळेला'),    'शाळेत',      'Locative: शाळेत (not शाळेला)'),
        (_wb('बाजाराला'),  'बाजारात',    'Locative: बाजारात (not बाजाराला)'),
        (_wb('घराला'),     'घरात',       'Locative: घरात (not घराला)'),
        (_wb('गावाला'),    'गावात',      'Locative: गावात (not गावाला)'),
        (_wb('खोलीला'),    'खोलीत',      'Locative: खोलीत'),
        (_wb('ऑफिसला'),   'ऑफिसमध्ये',  'Locative: ऑफिसमध्ये (not ऑफिसला)'),
        (_wb('मुंबईमधे'),  'मुंबईत',     'Locative: मुंबईत preferred'),
        (_wb('शहरामधे'),   'शहरात',      'Locative: शहरात preferred'),
        # Incorrect inflection forms
        (_wb('घरत'),       'घरात',       'घर → सामान्यरूप घरा- → घरात'),
        (_wb('शाळात'),     'शाळेत',      'शाळा → सामान्यरूप शाळे- → शाळेत'),
        # Pronoun vibhakti
        (_wb('मीला'),      'मला',        'Dwiteeyaa of मी → मला'),
        (_wb('मीचा'),      'माझा',       'Possessive of मी → माझा'),
        (_wb('तूला'),      'तुला',       'Dwiteeyaa of तू → तुला'),
        (_wb('तूचा'),      'तुझा',       'Possessive: तुझा'),
        (_wb('तूची'),      'तुझी',       'Possessive: तुझी'),
        (_wb('तूचे'),      'तुझे',       'Possessive: तुझे'),
        (_wb('ह्याला'),    'याला',       'Modern standard: याला'),
        (_wb('ह्याचा'),    'याचा',       'Modern standard: याचा'),
        (_wb('ह्यांना'),   'यांना',      'Modern standard: यांना'),
        (_wb('आम्हीला'),   'आम्हाला',    'आम्हाला (not आम्हीला)'),
        (_wb('तुम्हीला'),  'तुम्हाला',   'तुम्हाला (not तुम्हीला)'),
        (_wb('त्यांला'),   'त्यांना',    'Dative plural: त्यांना'),
        # Redundant stacking (from reference code 2)
        (_wb('भावालाने'),  'भावाने',     'Redundant vibhakti stacking'),
        (_wb('गावाकडेला'), 'गावाकडे',    'Redundant: remove ला after कडे'),
        (r'(?<![^\s\u0900-\u097F])वर\s+ला(?=[\s\u0964.,!?]|$)', 'वर',
         'Redundant: ला is not needed after वर'),
        (r'(?<![^\s\u0900-\u097F])खाली\s+ला(?=[\s\u0964.,!?]|$)', 'खाली',
         'Redundant: ला is not needed after खाली'),
        (r'(?<![^\s\u0900-\u097F])साठी\s+ला(?=[\s\u0964.,!?]|$)', 'साठी',
         'Redundant: ला is not needed after साठी'),
        (r'(?<![^\s\u0900-\u097F])कडे\s+ला(?=[\s\u0964.,!?]|$)', 'कडे',
         'Redundant: ला is not needed after कडे'),
        (r'(?<![^\s\u0900-\u097F])कडून\s+ने(?=[\s\u0964.,!?]|$)', 'कडून',
         'Redundant: ने is not needed after कडून'),
        (r'(?<![^\s\u0900-\u097F])मध्ये\s+त(?=[\s\u0964.,!?]|$)', 'मध्ये',
         'Redundant: त is not needed after मध्ये'),
        (r'(?<![^\s\u0900-\u097F])त\s+मधे(?=[\s\u0964.,!?]|$)', 'त',
         'Redundant: Use त OR मधे for locative, not both'),
        (r'(?<![^\s\u0900-\u097F])ला\s+ने(?=[\s\u0964.,!?]|$)', 'ला किंवा ने',
         'Redundant stacking of ला and ने'),
        (r'(?<![^\s\u0900-\u097F])ने\s+ला(?=[\s\u0964.,!?]|$)', 'ने किंवा ला',
         'Redundant stacking of ने and ला'),
        # त्याला ने → त्याने
        (_wb('त्याला ने'), 'त्याने', 'त्याला + ने → merge to त्याने'),
        (_wb('तिला ने'),   'तिने',   'तिला + ने → merge to तिने'),
    ]

    # ── GNP Agreement Rules ────────────────────────────────────────────────────
    GNP: List[Dict[str, str]] = [
        # ── मी (1st Sing.) ──
        {'s':'मी',    'w':'गेला',    'c':'गेलो',    'e':'मी + past masc. → गेलो'},
        {'s':'मी',    'w':'गेली',    'c':'गेलो',    'e':'मी + past → गेलो (masc.)'},
        {'s':'मी',    'w':'बोलला',   'c':'बोललो',   'e':'मी बोललो (1st masc.)'},
        {'s':'मी',    'w':'बोलली',   'c':'बोललो',   'e':'मी बोललो'},
        {'s':'मी',    'w':'केला',    'c':'केले',    'e':'Ergativity: मी केले'},
        {'s':'मी',    'w':'दिला',    'c':'दिले',    'e':'Ergativity: मी दिले'},
        {'s':'मी',    'w':'घेला',    'c':'घेतले',   'e':'Ergativity: मी घेतले'},
        {'s':'मी',    'w':'खाला',    'c':'खाल्ले',  'e':'Ergativity: मी खाल्ले'},
        {'s':'मी',    'w':'आणला',    'c':'आणले',    'e':'Ergativity: मी आणले'},
        {'s':'मी',    'w':'केलास',   'c':'केले',    'e':'1st Pers.: मी केले'},
        {'s':'मी',    'w':'जाईल',    'c':'जाईन',    'e':'Future 1st Sing.: मी जाईन'},
        {'s':'मी',    'w':'येईल',    'c':'येईन',    'e':'Future 1st Sing.: मी येईन'},
        {'s':'मी',    'w':'करेल',    'c':'करेन',    'e':'Future 1st Sing.: मी करेन'},
        {'s':'मी',    'w':'सांगेल',  'c':'सांगेन',  'e':'Future 1st Sing.: मी सांगेन'},
        {'s':'मी',    'w':'बघेल',    'c':'बघेन',    'e':'Future 1st Sing.: मी बघेन'},
        {'s':'मी',    'w':'आहोत',    'c':'आहे',     'e':'1st Sing. aux: मी आहे'},
        {'s':'मी',    'w':'आहात',    'c':'आहे',     'e':'1st Sing. aux: मी आहे'},
        {'s':'मी',    'w':'आहेत',    'c':'आहे',     'e':'1st Sing. aux: मी आहे'},
        {'s':'मी',    'w':'होता',    'c':'होतो',    'e':'मी + past aux masc.: होतो'},
        {'s':'मी',    'w':'करतात',   'c':'करतो',    'e':'मी + करतात → करतो/करते'},
        # ── आम्ही (1st Pl.) ──
        {'s':'आम्ही', 'w':'गेला',    'c':'गेलो',    'e':'आम्ही + past → गेलो'},
        {'s':'आम्ही', 'w':'गेली',    'c':'गेलो',    'e':'आम्ही + past → गेलो'},
        {'s':'आम्ही', 'w':'गेले',    'c':'गेलो',    'e':'आम्ही + past → गेलो'},
        {'s':'आम्ही', 'w':'आहे',     'c':'आहोत',    'e':'आम्ही + aux → आहोत'},
        {'s':'आम्ही', 'w':'आहात',    'c':'आहोत',    'e':'आम्ही + aux → आहोत'},
        {'s':'आम्ही', 'w':'आहेत',    'c':'आहोत',    'e':'आम्ही + aux → आहोत'},
        # ── तू (2nd Sing.) ──
        {'s':'तू',    'w':'गेला',    'c':'गेलास',   'e':'तू + past masc. → गेलास'},
        {'s':'तू',    'w':'गेली',    'c':'गेलीस',   'e':'तू + past fem. → गेलीस'},
        {'s':'तू',    'w':'केला',    'c':'केलास',   'e':'तू + past trans. → केलास'},
        {'s':'तू',    'w':'आहे',     'c':'आहेस',    'e':'2nd Sing.: तू आहेस'},
        {'s':'तू',    'w':'आहोत',    'c':'आहेस',    'e':'2nd Sing.: तू आहेस'},
        {'s':'तू',    'w':'आहात',    'c':'आहेस',    'e':'2nd Sing.: तू आहेस'},
        {'s':'तू',    'w':'आहेत',    'c':'आहेस',    'e':'2nd Sing.: तू आहेस'},
        {'s':'तू',    'w':'करतो',    'c':'करतोस',   'e':'2nd Sing.: तू करतोस'},
        # ── तुम्ही (2nd Pl. Honorific) ──
        {'s':'तुम्ही','w':'आहे',     'c':'आहात',    'e':'Honorific: तुम्ही आहात'},
        {'s':'तुम्ही','w':'आहोत',    'c':'आहात',    'e':'Honorific: तुम्ही आहात'},
        {'s':'तुम्ही','w':'आहेत',    'c':'आहात',    'e':'Honorific: तुम्ही आहात'},
        {'s':'तुम्ही','w':'गेला',    'c':'गेलात',   'e':'Honorific past: तुम्ही गेलात'},
        {'s':'तुम्ही','w':'गेली',    'c':'गेलात',   'e':'Honorific past: तुम्ही गेलात'},
        {'s':'तुम्ही','w':'गेले',    'c':'गेलात',   'e':'Honorific past: तुम्ही गेलात'},
        {'s':'तुम्ही','w':'केला',    'c':'केलात',   'e':'Honorific past: तुम्ही केलात'},
        {'s':'तुम्ही','w':'केले',    'c':'केलात',   'e':'Honorific past: तुम्ही केलात'},
        {'s':'तुम्ही','w':'करतो',    'c':'करता',    'e':'Honorific present: तुम्ही करता'},
        {'s':'तुम्ही','w':'जातो',    'c':'जाता',    'e':'Honorific present: तुम्ही जाता'},
        {'s':'तुम्ही','w':'येतो',    'c':'येता',    'e':'Honorific present: तुम्ही येता'},
        {'s':'तुम्ही','w':'बोलतो',   'c':'बोलता',   'e':'Honorific present: तुम्ही बोलता'},
        {'s':'तुम्ही','w':'होता',    'c':'होतात',   'e':'Honorific past: तुम्ही होतात'},
        # ── तो (3rd Sing. Masc.) ──
        {'s':'तो',    'w':'गेली',    'c':'गेला',    'e':'तो + fem. past → गेला'},
        {'s':'तो',    'w':'गेले',    'c':'गेला',    'e':'तो + pl/neu past → गेला'},
        {'s':'तो',    'w':'आहेत',    'c':'आहे',     'e':'3rd Sing.: तो आहे'},
        {'s':'तो',    'w':'आहोत',    'c':'आहे',     'e':'3rd Sing.: तो आहे'},
        {'s':'तो',    'w':'होती',    'c':'होता',    'e':'तो + होती → होता'},
        {'s':'तो',    'w':'करते',    'c':'करतो',    'e':'तो + करते → करतो'},
        {'s':'तो',    'w':'जाते',    'c':'जातो',    'e':'तो + जाते → जातो'},
        {'s':'तो',    'w':'येते',    'c':'येतो',    'e':'तो + येते → येतो'},
        {'s':'तो',    'w':'बोलते',   'c':'बोलतो',   'e':'तो + बोलते → बोलतो'},
        {'s':'तो',    'w':'गाते',    'c':'गातो',    'e':'तो + गाते → गातो'},
        {'s':'तो',    'w':'हसते',    'c':'हसतो',    'e':'तो + हसते → हसतो'},
        {'s':'तो',    'w':'रडते',    'c':'रडतो',    'e':'तो + रडते → रडतो'},
        # ── ती (3rd Sing. Fem.) ──
        {'s':'ती',    'w':'गेला',    'c':'गेली',    'e':'ती + masc. past → गेली'},
        {'s':'ती',    'w':'गेले',    'c':'गेली',    'e':'ती + neut. past → गेली'},
        {'s':'ती',    'w':'आहेत',    'c':'आहे',     'e':'3rd Sing. Fem.: ती आहे'},
        {'s':'ती',    'w':'होता',    'c':'होती',    'e':'ती + होता → होती'},
        {'s':'ती',    'w':'गातो',    'c':'गाते',    'e':'ती + गातो → गाते'},
        {'s':'ती',    'w':'करतो',    'c':'करते',    'e':'ती + करतो → करते'},
        {'s':'ती',    'w':'जातो',    'c':'जाते',    'e':'ती + जातो → जाते'},
        {'s':'ती',    'w':'येतो',    'c':'येते',    'e':'ती + येतो → येते'},
        {'s':'ती',    'w':'बोलतो',   'c':'बोलते',   'e':'ती + बोलतो → बोलते'},
        {'s':'ती',    'w':'हसतो',    'c':'हसते',    'e':'ती + हसतो → हसते'},
        {'s':'ती',    'w':'रडतो',    'c':'रडते',    'e':'ती + रडतो → रडते'},
        # ── ते (3rd Pl. / Honorific) ──
        {'s':'ते',    'w':'गेला',    'c':'गेले',    'e':'3rd Pl. past: ते गेले'},
        {'s':'ते',    'w':'गेली',    'c':'गेले',    'e':'3rd Pl. past: ते गेले'},
        {'s':'ते',    'w':'आहे',     'c':'आहेत',    'e':'3rd Pl. aux: ते आहेत'},
        {'s':'ते',    'w':'आहोत',    'c':'आहेत',    'e':'3rd Pl.: ते आहेत'},
        {'s':'ते',    'w':'आहात',    'c':'आहेत',    'e':'3rd Pl.: ते आहेत'},
        {'s':'ते',    'w':'होता',    'c':'होते',    'e':'ते + होता → होते'},
        # ── त्या (3rd Pl. Fem.) ──
        {'s':'त्या',  'w':'गेला',    'c':'गेल्या',  'e':'3rd Pl. Fem. past: त्या गेल्या'},
        {'s':'त्या',  'w':'गेले',    'c':'गेल्या',  'e':'3rd Pl. Fem. past: त्या गेल्या'},
        {'s':'त्या',  'w':'आहे',     'c':'आहेत',    'e':'3rd Pl. Fem.: त्या आहेत'},
        # ── अनेकवचन subjects ──
        {'s':'मुलं',  'w':'आहे',     'c':'आहेत',    'e':'Plural: मुलं आहेत'},
        {'s':'मुलं',  'w':'होता',    'c':'होते',    'e':'मुलं होते (neut. pl.)'},
        {'s':'मुलं',  'w':'होती',    'c':'होते',    'e':'मुलं होते'},
        {'s':'लोक',   'w':'आहे',     'c':'आहेत',    'e':'लोक → आहेत'},
        {'s':'लोकं',  'w':'आहे',     'c':'आहेत',    'e':'लोकं → आहेत'},
    ]
    GNP = [r for r in GNP if r['w'] != r['c']]

    # ── Demonstrative Gender Rules ─────────────────────────────────────────────
    # (wrong_dem, correct_dem, noun_set_key, explanation)
    DEMONSTRATIVE: List[Tuple[str, str, str, str]] = [
        ('हा',  'ही',  'FEM',  '"हा" + fem. noun → ही'),
        ('हा',  'हे',  'NEUT', '"हा" + neut. noun → हे'),
        ('ही',  'हा',  'MASC', '"ही" + masc. noun → हा'),
        ('ही',  'हे',  'NEUT', '"ही" + neut. noun → हे'),
        ('हे',  'हा',  'MASC', '"हे" + masc. noun → हा'),
        ('हे',  'ही',  'FEM',  '"हे" + fem. noun → ही'),
        ('तो',  'ती',  'FEM',  '"तो" + fem. noun → ती'),
        ('तो',  'ते',  'NEUT', '"तो" + neut. noun → ते'),
        ('ती',  'तो',  'MASC', '"ती" + masc. noun → तो'),
        ('ती',  'ते',  'NEUT', '"ती" + neut. noun → ते'),
    ]

    # ── Relative Pronoun Gender Rules ──────────────────────────────────────────
    # (wrong_rel, correct_rel, noun_set_key, explanation)
    RELATIVE_PRONOUN: List[Tuple[str, str, str, str]] = [
        ('जी',  'जो',  'MASC', '"जी" (fem.) + masc. noun → जो'),
        ('जो',  'जी',  'FEM',  '"जो" (masc.) + fem. noun → जी'),
        ('जे',  'जो',  'MASC', '"जे" (pl./neut.) + masc. sing. noun → जो'),
        ('जे',  'जी',  'FEM',  '"जे" (pl.) + fem. sing. noun → जी'),
    ]

    # ── Adjective Gender Agreement ─────────────────────────────────────────────
    ADJECTIVE_MAP: Dict[str, Dict[str, str]] = {
        'चांगला': {'FEM': 'चांगली', 'NEUT': 'चांगले'},
        'चांगली': {'MASC': 'चांगला', 'NEUT': 'चांगले'},
        'चांगले': {'MASC': 'चांगला', 'FEM': 'चांगली'},
        'मोठा':   {'FEM': 'मोठी',   'NEUT': 'मोठे'},
        'मोठी':   {'MASC': 'मोठा',  'NEUT': 'मोठे'},
        'मोठे':   {'MASC': 'मोठा',  'FEM': 'मोठी'},
        'छोटा':   {'FEM': 'छोटी',   'NEUT': 'छोटे'},
        'छोटी':   {'MASC': 'छोटा',  'NEUT': 'छोटे'},
        'जुना':   {'FEM': 'जुनी',   'NEUT': 'जुने'},
        'जुनी':   {'MASC': 'जुना',  'NEUT': 'जुने'},
        'नवा':    {'FEM': 'नवी',    'NEUT': 'नवे'},
        'नवी':    {'MASC': 'नवा',   'NEUT': 'नवे'},
        'काळा':   {'FEM': 'काळी',   'NEUT': 'काळे'},
        'पांढरा': {'FEM': 'पांढरी', 'NEUT': 'पांढरे'},
        'निळा':   {'FEM': 'निळी',   'NEUT': 'निळे'},
        # invariants — kept empty so check skips them
        'लाल': {}, 'उंच': {}, 'हुशार': {}, 'गरीब': {}, 'श्रीमंत': {},
        'नवीन': {}, 'जड': {}, 'हलका': {},
    }

    # ── Possessive Gender Agreement ────────────────────────────────────────────
    POSSESSIVES: Dict[str, Dict[str, str]] = {
        'त्याचा': {'FEM': 'त्याची',  'NEUT': 'त्याचे'},
        'त्याची': {'MASC': 'त्याचा', 'NEUT': 'त्याचे'},
        'त्याचे': {'MASC': 'त्याचा', 'FEM': 'त्याची'},
        'तिचा':   {'FEM': 'तिची',    'NEUT': 'तिचे'},
        'तिची':   {'MASC': 'तिचा',   'NEUT': 'तिचे'},
        'तिचे':   {'MASC': 'तिचा',   'FEM': 'तिची'},
        'माझा':   {'FEM': 'माझी',    'NEUT': 'माझे'},
        'माझी':   {'MASC': 'माझा',   'NEUT': 'माझे'},
        'माझे':   {'MASC': 'माझा',   'FEM': 'माझी'},
        'तुझा':   {'FEM': 'तुझी',    'NEUT': 'तुझे'},
        'तुझी':   {'MASC': 'तुझा',   'NEUT': 'तुझे'},
        'तुझे':   {'MASC': 'तुझा',   'FEM': 'तुझी'},
        'आमचा':   {'FEM': 'आमची',    'NEUT': 'आमचे'},
        'आमची':   {'MASC': 'आमचा',   'NEUT': 'आमचे'},
        'आमचे':   {'MASC': 'आमचा',   'FEM': 'आमची'},
        'तुमचा':  {'FEM': 'तुमची',   'NEUT': 'तुमचे'},
        'तुमची':  {'MASC': 'तुमचा',  'NEUT': 'तुमचे'},
        'तुमचे':  {'MASC': 'तुमचा',  'FEM': 'तुमची'},
    }

    POSS_FEM:  Set[str] = {'आई','बहीण','मुलगी','पोरगी','ताई','काकी','मामी','मावशी',
                            'आजी','मैत्रीण','राणी','देवी','गाडी','शाळा','खुर्ची',
                            'वही','भाषा','कविता','बातमी','बायको','वहिनी'}
    POSS_MASC: Set[str] = {'मुलगा','पोरगा','भाऊ','बाप','दादा','काका','आजोबा',
                            'मित्र','कुत्रा','घोडा','राजा','देव','शिक्षक','नवरा'}
    POSS_NEUT: Set[str] = {'घर','पुस्तक','काम','मन','गाणे','फूल','झाड','दुकान',
                            'स्वप्न','आकाश','जग','शेत','जेवण'}

    # ── Continuous Tense Regex Rules ───────────────────────────────────────────
    CONTINUOUS: List[Tuple[str, str, str]] = [
        (_wb('जाती आहे'),  'जात आहे',  'Continuous (f): जात आहे'),
        (_wb('येती आहे'),  'येत आहे',  'Continuous (f): येत आहे'),
        (_wb('खाती आहे'),  'खात आहे',  'Continuous (f): खात आहे'),
        (_wb('पितो आहे'),  'पीत आहे',  'Continuous: पीत आहे'),
        (_wb('पिते आहे'),  'पीत आहे',  'Continuous: पीत आहे'),
    ]

    # ── Auxiliary Agreement ────────────────────────────────────────────────────
    AUX: List[Tuple[str, str, str]] = [
        (_wb('मी आहोत'),    'मी आहे',      '1st Sing.: मी आहे'),
        (_wb('मी आहात'),    'मी आहे',      '1st Sing.: मी आहे'),
        (_wb('मी आहेत'),    'मी आहे',      '1st Sing.: मी आहे'),
        (_wb('तू आहे'),     'तू आहेस',     '2nd Sing.: तू आहेस'),
        (_wb('तू आहोत'),    'तू आहेस',     '2nd Sing.: तू आहेस'),
        (_wb('तू आहात'),    'तू आहेस',     '2nd Sing.: तू आहेस'),
        (_wb('तो आहेत'),    'तो आहे',      '3rd Sing. Masc.: तो आहे'),
        (_wb('ती आहेत'),    'ती आहे',      '3rd Sing. Fem.: ती आहे'),
        (_wb('आम्ही आहे'),  'आम्ही आहोत', '1st Pl.: आम्ही आहोत'),
        (_wb('आम्ही आहात'), 'आम्ही आहोत', '1st Pl.: आम्ही आहोत'),
        (_wb('आम्ही आहेत'), 'आम्ही आहोत', '1st Pl.: आम्ही आहोत'),
        (_wb('तुम्ही आहे'), 'तुम्ही आहात','2nd Pl. Hon.: तुम्ही आहात'),
        (_wb('तुम्ही आहोत'),'तुम्ही आहात','2nd Pl. Hon.: तुम्ही आहात'),
        (_wb('तुम्ही आहेत'),'तुम्ही आहात','2nd Pl. Hon.: तुम्ही आहात'),
        (_wb('ते आहे'),     'ते आहेत',    '3rd Pl.: ते आहेत'),
        (_wb('ते आहोत'),    'ते आहेत',    '3rd Pl.: ते आहेत'),
        (_wb('ते आहात'),    'ते आहेत',    '3rd Pl.: ते आहेत'),
        (_wb('त्या आहे'),   'त्या आहेत',  '3rd Pl. Fem.: त्या आहेत'),
    ]

    # ── Negation Rules ─────────────────────────────────────────────────────────
    NEGATION: List[Tuple[str, str, str]] = [
        (_wb('नाहि'),       'नाही',     'Spelling of negation: नाही'),
        (_wb('नाही होता'),  'नव्हता',   'Past neg. Masc.: नव्हता'),
        (_wb('नाही होती'),  'नव्हती',   'Past neg. Fem.: नव्हती'),
        (_wb('नाही होते'),  'नव्हते',   'Past neg. Pl.: नव्हते'),
        (_wb('नाही होतो'),  'नव्हतो',   'Past neg. 1st Pers.: नव्हतो'),
        (_wb('नाही आहे'),   'नाही',     'Redundant: नाही + आहे → नाही'),
        (_wb('नको नाही'),   'नको',      'Redundant double negation'),
        # नाही should come AFTER verb stem, not before verb
        (r'(?<![{_DEV_RANGE}])नाही\s+(करतो|करते|जातो|जाते|येतो|येते|आहे|होतो|बोलतो|सांगतो)(?![{_DEV_RANGE}])',
         'verb + नाही',
         'नाही क्रियापदानंतर येते — नाही should come AFTER the verb stem (e.g. करत नाही)'),
    ]

    # ── Word-Order / SOV Rules ─────────────────────────────────────────────────
    SOV_RULES: List[Tuple[str, str, str]] = [
        # Verb at sentence start
        (r'(?:^|\u0964\s*)(आहे|होते|होता|होती|होतो|केले|केली|केला|गेला|गेली|गेले'
         r'|करतो|करते|करतात|जातो|जाते|जातात|येतो|येते|येतात'
         r'|बोलतो|बोलते|सांगतो|सांगते)\b',
         '[क्रियापद शेवटी हवे]',
         'मराठीत क्रियापद शेवटी येते (SOV order) — Verb should be at end of clause'),
        # तुम्ही + non-honorific verb
        (r'\bतुम्ही\s+[\u0900-\u097F]+\s+(करतो|जातो|येतो|बोलतो)\b',
         'करता / जाता / येता / बोलता',
         'तुम्ही सोबत आदरार्थी रूप वापरा: करता/जाता/येता/बोलता'),
    ]

    # ── Dialect Normalization ──────────────────────────────────────────────────
    DIALECT: Dict[str, str] = {
        'कायला':  'का',      'कोन्या': 'कोणत्या',
        'कुठं':   'कोठे',   'कवा':    'केव्हा',
        'पन':     'पण',      'एवाढं':  'एवढे',
        'कसला':   'कोणता',  'त्ये':   'ते',
        'तवा':    'तेव्हा',  'काहून':  'का',
        'म्हनून': 'म्हणून',
    }
    DIALECT = {k: v for k, v in DIALECT.items() if k != v}

    # ── Complex Clause Pairs ───────────────────────────────────────────────────
    CLAUSE_PAIRS: List[Tuple[str, str, str]] = [
        # Longer openers before shorter (avoids जरी being caught by जर rule)
        ('जोपर्यंत', 'तोपर्यंत', 'Durative "जोपर्यंत" needs "तोपर्यंत"'),
        ('जेव्हा',   'तेव्हा',   'Temporal "जेव्हा" needs "तेव्हा"'),
        ('जितका',    'तितका',    'Comparative "जितका" needs "तितका"'),
        ('जेथे',     'तेथे',     'Locative "जेथे" needs "तेथे"'),
        ('जरी',      'तरी',      'Concessive "जरी" needs "तरी"'),
        ('जर',       'तर',       'Conditional "जर" needs "तर"'),
        ('जे',       'ते',       'Relative "जे" needs "ते"'),
    ]

    # ── Question Words ─────────────────────────────────────────────────────────
    QUESTION_WORDS: Set[str] = {
        'कोण', 'काय', 'कुठे', 'कोठे', 'केव्हा', 'कधी', 'किती',
        'कसा', 'कशी', 'कसे', 'कोणता', 'कोणती', 'कोणते',
        'कुठून', 'का', 'कशासाठी',
    }

    # ── Severity Weights ───────────────────────────────────────────────────────
    WEIGHTS: Dict[str, float] = {
        'SYNTAX': 15.0, 'MORPHOLOGY': 10.0, 'ORTHOGRAPHY': 5.0,
        'LEXICAL': 4.0, 'SURFACE': 1.5, 'SUGGESTION': 0.5,
    }


# ══════════════════════════════════════════════════════════════════════════════
# GRAMMAR ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class MarathiGrammarEngine:
    """Full offline rule-based Marathi grammar engine — 23+ rule categories."""

    def __init__(self):
        self.kb = KB()
        self._noun_sets: Dict[str, Set[str]] = {
            'MASC': self.kb.MASC_NOUNS,
            'FEM':  self.kb.FEM_NOUNS,
            'NEUT': self.kb.NEUT_NOUNS,
        }

    def _normalize(self, text: str) -> str:
        return unicodedata.normalize('NFC', text).strip()

    def _sentences(self, text: str) -> List[Tuple[str, int]]:
        result = []
        for m in re.finditer(r'[^\u0964\u0965.!?\n]+[\u0964\u0965.!?\n]?', text):
            s = m.group().strip()
            if s:
                result.append((s, m.start()))
        return result or [(text, 0)]

    # ── Pass 1: Spelling ──────────────────────────────────────────────────────
    def _check_spelling(self, text: str, errors: list):
        _scan_pairs(text, self.kb.SPELLING, errors,
                    'ORTHOGRAPHY', 'SPELLING', 'WARNING', "Spelling: '{w}' → '{r}'")

    # ── Pass 2: Sandhi ────────────────────────────────────────────────────────
    def _check_sandhi(self, text: str, errors: list):
        _scan_pairs(text, self.kb.SANDHI, errors,
                    'ORTHOGRAPHY', 'SANDHI', 'WARNING',
                    "Sandhi: '{w}' → '{r}'")

    # ── Pass 3: Vibhakti ──────────────────────────────────────────────────────
    def _check_vibhakti(self, text: str, errors: list):
        _scan_regex(text, self.kb.VIBHAKTI, errors,
                    'MORPHOLOGY', 'VIBHAKTI', 'CRITICAL')

    # ── Pass 4: GNP Agreement ────────────────────────────────────────────────
    def _check_gnp(self, text: str, errors: list):
        for rule in self.kb.GNP:
            sm = re.search(_wb(rule['s']), text)
            vm = re.search(_wb(rule['w']), text)
            if sm and vm:
                _add(errors, 'SYNTAX', 'GNP_AGREEMENT',
                     rule['w'], rule['c'], vm.start(), 'CRITICAL',
                     f"GNP: {rule['e']}")

    # ── Pass 5: Demonstrative Gender ─────────────────────────────────────────
    def _check_demonstrative(self, text: str, errors: list):
        for dem, correct, ns_key, exp in self.kb.DEMONSTRATIVE:
            for noun in self._noun_sets[ns_key]:
                pat = (rf'(?<![{_DEV_RANGE}]){re.escape(dem)}'
                       rf'\s+(?:\S+\s+)?{re.escape(noun)}(?![{_DEV_RANGE}])')
                for m in re.finditer(pat, text):
                    if m.group().split()[0] == dem:
                        _add(errors, 'SYNTAX', 'DEMONSTRATIVE_GENDER',
                             dem, correct, m.start(), 'CRITICAL',
                             f'{exp} (before "{noun}")')

    # ── Pass 6: Relative Pronoun Gender ──────────────────────────────────────
    def _check_relative_pronoun(self, text: str, errors: list):
        for rel, correct, ns_key, exp in self.kb.RELATIVE_PRONOUN:
            for noun in self._noun_sets[ns_key]:
                pat = (rf'(?<![{_DEV_RANGE}]){re.escape(rel)}'
                       rf'\s+(?:\S+\s+)?{re.escape(noun)}(?![{_DEV_RANGE}])')
                for m in re.finditer(pat, text):
                    if m.group().split()[0] == rel:
                        _add(errors, 'SYNTAX', 'RELATIVE_PRONOUN_GENDER',
                             rel, correct, m.start(), 'CRITICAL',
                             f'{exp} (before "{noun}")')

    # ── Pass 7: Adjective Gender ──────────────────────────────────────────────
    def _check_adjective_gender(self, text: str, errors: list):
        for adj, corrections in self.kb.ADJECTIVE_MAP.items():
            if not corrections:
                continue
            for ns_key, correct_adj in corrections.items():
                for noun in self._noun_sets[ns_key]:
                    pat = (rf'(?<![{_DEV_RANGE}]){re.escape(adj)}'
                           rf'\s+(?:\S+\s+)?{re.escape(noun)}(?![{_DEV_RANGE}])')
                    for m in re.finditer(pat, text):
                        if m.group().split()[0] == adj:
                            _add(errors, 'SYNTAX', 'ADJECTIVE_GENDER',
                                 adj, correct_adj, m.start(), 'CRITICAL',
                                 f'Adjective "{adj}" + "{noun}" ({ns_key}) → "{correct_adj}"')

    # ── Pass 8: Possessive Gender ─────────────────────────────────────────────
    def _check_possessive_gender(self, text: str, errors: list):
        poss_sets = {'FEM': self.kb.POSS_FEM, 'MASC': self.kb.POSS_MASC,
                     'NEUT': self.kb.POSS_NEUT}
        for poss, corrections in self.kb.POSSESSIVES.items():
            for ns_key, correct_poss in corrections.items():
                for noun in poss_sets[ns_key]:
                    pat = (rf'(?<![{_DEV_RANGE}]){re.escape(poss)}'
                           rf'\s+(?:\S+\s+)?{re.escape(noun)}(?![{_DEV_RANGE}])')
                    for m in re.finditer(pat, text):
                        if m.group().split()[0] == poss:
                            _add(errors, 'SYNTAX', 'POSSESSIVE_GENDER',
                                 poss, correct_poss, m.start(), 'CRITICAL',
                                 f'Possessive: "{poss}" + "{noun}" ({ns_key}) → "{correct_poss}"')

    # ── Pass 9: Continuous Tense ──────────────────────────────────────────────
    def _check_continuous(self, text: str, errors: list):
        _scan_regex(text, self.kb.CONTINUOUS, errors,
                    'SYNTAX', 'CONTINUOUS_TENSE', 'CRITICAL')

    # ── Pass 10: Auxiliary ────────────────────────────────────────────────────
    def _check_aux(self, text: str, errors: list):
        _scan_regex(text, self.kb.AUX, errors, 'SYNTAX', 'AUXILIARY', 'CRITICAL')

    # ── Pass 11: Negation ─────────────────────────────────────────────────────
    def _check_negation(self, text: str, errors: list):
        _scan_regex(text, self.kb.NEGATION, errors,
                    'MORPHOLOGY', 'NEGATION', 'WARNING')

    # ── Pass 12: Vibhakti Stacking via GNP (already in VIBHAKTI list) ────────

    # ── Pass 13: Word Order / SOV ─────────────────────────────────────────────
    def _check_sov(self, text: str, errors: list):
        for pat, rep, exp in self.kb.SOV_RULES:
            for m in re.finditer(pat, text, re.MULTILINE):
                _add(errors, 'SYNTAX', 'WORD_ORDER', m.group(), rep,
                     m.start(), 'WARNING', exp)

    # ── Pass 14: Dialect ──────────────────────────────────────────────────────
    def _check_dialect(self, text: str, errors: list):
        _scan_pairs(text, self.kb.DIALECT, errors,
                    'LEXICAL', 'DIALECT', 'SUGGESTION',
                    "Non-standard: '{w}' → '{r}'")

    # ── Pass 15: Complex Clause Pairing ──────────────────────────────────────
    def _check_clause_pairing(self, text: str, errors: list):
        for sent, base in self._sentences(text):
            for opener, closer, exp in self.kb.CLAUSE_PAIRS:
                # Use word-boundary aware search to avoid matching inside longer words
                # e.g. "जे" should NOT match inside "पाहिजे"
                opener_pat = _wb(opener)
                closer_pat = _wb(closer)
                opener_m = re.search(opener_pat, sent)
                if opener_m and not re.search(closer_pat, sent):
                    _add(errors, 'SYNTAX', 'CLAUSE_PAIRING',
                         opener, closer, base + opener_m.start(), 'WARNING', exp)

    # ── Pass 16: Repetition ───────────────────────────────────────────────────
    def _check_repetition(self, text: str, errors: list):
        for m in re.finditer(
            rf'(?<![{_DEV_RANGE}])([{_DEV_RANGE}]+)\s+\1(?![{_DEV_RANGE}])', text
        ):
            word = m.group(1)
            _add(errors, 'ORTHOGRAPHY', 'REPETITION',
                 m.group(), word, m.start(), 'WARNING',
                 f'Repeated word: "{word}" appears twice consecutively')

    # ── Pass 17: Question Punctuation ─────────────────────────────────────────
    def _check_question_punctuation(self, text: str, errors: list):
        for sent, base in self._sentences(text):
            s = sent.rstrip()
            if s and s[-1] in '.।':
                words = set(re.findall(rf'[{_DEV_RANGE}]+', sent))
                if words & self.kb.QUESTION_WORDS:
                    _add(errors, 'ORTHOGRAPHY', 'PUNCTUATION',
                         s[-1], '?', base + len(s) - 1, 'WARNING',
                         'Question sentence should end with ? not "' + s[-1] + '"')

    # ── Pass 18: Surface Checks ───────────────────────────────────────────────
    def _check_surface(self, text: str, errors: list):
        # Double spaces
        for m in re.finditer(r'  +', text):
            _add(errors, 'SURFACE', 'DOUBLE_SPACE',
                 m.group(), ' ', m.start(), 'SUGGESTION',
                 'Extra whitespace between words')
        # Repeated punctuation (!!, ??, ।।)
        for m in re.finditer(r'([!?,।])\1+', text):
            _add(errors, 'SURFACE', 'REPEATED_PUNCT',
                 m.group(), m.group(1), m.start(), 'WARNING',
                 f'Punctuation "{m.group(1)}" repeated unnecessarily')
        # English digits inside Devanagari words
        for m in re.finditer(
            rf'[{_DEV_RANGE}]+[0-9]+[{_DEV_RANGE}]*|[0-9]+[{_DEV_RANGE}]+', text
        ):
            _add(errors, 'SURFACE', 'DIGIT_IN_DEVANAGARI',
                 m.group(), '', m.start(), 'WARNING',
                 'English digits mixed with Devanagari characters')

    # ── Pass 19: Sentence Length ──────────────────────────────────────────────
    def _check_sentence_length(self, text: str, errors: list):
        for sent, base in self._sentences(text):
            words = sent.strip().split()
            if len(words) > 40:
                _add(errors, 'SURFACE', 'SENTENCE_TOO_LONG',
                     sent[:40] + '…', '[split sentence]', base, 'SUGGESTION',
                     f'Sentence is very long ({len(words)} words). Consider splitting.')


    # ── Auto-Correct (Hard Repair) ────────────────────────────────────────────
    def hard_repair(self, text: str) -> str:
        work = self._normalize(text)

        # 1. Spelling — longest first to avoid partial-match conflicts
        for w, r in sorted(self.kb.SPELLING.items(), key=lambda x: -len(x[0])):
            work = re.sub(_wb(w), r, work)

        # 2. Sandhi
        for w, r in self.kb.SANDHI.items():
            work = re.sub(re.escape(w), r, work)

        # 3. Vibhakti direct patterns
        vibhakti_direct = [
            (r'शाळेला\b',    'शाळेत'),
            (r'बाजाराला\b',  'बाजारात'),
            (r'ऑफिसला\b',   'ऑफिसमध्ये'),
            (r'घराला\b',     'घरात'),
            (r'\bत्याचा\s+(आई|बहीण|मुलगी|ताई)\b', r'त्याची \1'),
            (r'\bतिची\s+(मुलगा|भाऊ|बाप|दादा|काका)\b', r'तिचा \1'),
            (r'\bत्याला\s+ने\b', 'त्याने'),
            (r'\bतिला\s+ने\b',   'तिने'),
            (r'\bवर\s+ला\b',     'वर'),
            (r'\bखाली\s+ला\b',   'खाली'),
            (r'\bसाठी\s+ला\b',   'साठी'),
            (r'\bकडे\s+ला\b',    'कडे'),
            (r'\bकडून\s+ने\b',   'कडून'),
            (r'\bमध्ये\s+त\b',   'मध्ये'),
            (r'\bमीला\b',        'मला'),
            (r'\bमीचा\b',        'माझा'),
            (r'\bतूला\b',        'तुला'),
            (r'\bतूचा\b',        'तुझा'),
        ]
        for pat, repl in vibhakti_direct:
            work = re.sub(pat, repl, work, flags=re.UNICODE)

        # 4. Auxiliary
        for pat, rep, _ in self.kb.AUX:
            work = re.sub(pat, rep, work)

        # 5. Clause-scoped verb agreement (cross-sentence safe — bounded by [^\n।.!?])
        verb_clause = [
            (r'\bमी\b([^\n\u0964.!?]*?)\bआहेत\b',   r'मी\1आहे'),
            (r'\bमी\b([^\n\u0964.!?]*?)\bआहोत\b',   r'मी\1आहे'),
            (r'\bमी\b([^\n\u0964.!?]*?)\bगेला\b',   r'मी\1गेलो'),
            (r'\bमी\b([^\n\u0964.!?]*?)\bजाईल\b',   r'मी\1जाईन'),
            (r'\bमी\b([^\n\u0964.!?]*?)\bकरेल\b',   r'मी\1करेन'),
            (r'\bमी\b([^\n\u0964.!?]*?)\bयेईल\b',   r'मी\1येईन'),
            (r'\bमी\b([^\n\u0964.!?]*?)\bहोता\b',   r'मी\1होतो'),
            (r'\bती\b([^\n\u0964.!?]*?)\bगेला\b',   r'ती\1गेली'),
            (r'\bती\b([^\n\u0964.!?]*?)\bकरतो\b',   r'ती\1करते'),
            (r'\bती\b([^\n\u0964.!?]*?)\bजातो\b',   r'ती\1जाते'),
            (r'\bती\b([^\n\u0964.!?]*?)\bहोता\b',   r'ती\1होती'),
            (r'\bती\b([^\n\u0964.!?]*?)\bआहेत\b',   r'ती\1आहे'),
            (r'\bतो\b([^\n\u0964.!?]*?)\bगेली\b',   r'तो\1गेला'),
            (r'\bतो\b([^\n\u0964.!?]*?)\bकरते\b',   r'तो\1करतो'),
            (r'\bतो\b([^\n\u0964.!?]*?)\bजाते\b',   r'तो\1जातो'),
            (r'\bतो\b([^\n\u0964.!?]*?)\bहोती\b',   r'तो\1होता'),
            (r'\bतो\b([^\n\u0964.!?]*?)\bआहेत\b',   r'तो\1आहे'),
            (r'\bते\b([^\n\u0964.!?]*?)\bआहे\b',    r'ते\1आहेत'),
            (r'\bते\b([^\n\u0964.!?]*?)\bगेला\b',   r'ते\1गेले'),
            (r'\bते\b([^\n\u0964.!?]*?)\bहोता\b',   r'ते\1होते'),
            (r'\bत्या\b([^\n\u0964.!?]*?)\bगेला\b', r'त्या\1गेल्या'),
            (r'\bत्या\b([^\n\u0964.!?]*?)\bआहे\b',  r'त्या\1आहेत'),
            (r'\bतुम्ही\b([^\n\u0964.!?]*?)\bगेला\b', r'तुम्ही\1गेलात'),
            (r'\bतुम्ही\b([^\n\u0964.!?]*?)\bगेली\b', r'तुम्ही\1गेलात'),
            (r'\bतुम्ही\b([^\n\u0964.!?]*?)\bआहे\b',  r'तुम्ही\1आहात'),
            (r'\bतुम्ही\b([^\n\u0964.!?]*?)\bकरतो\b', r'तुम्ही\1करता'),
            (r'\bतुम्ही\b([^\n\u0964.!?]*?)\bहोता\b', r'तुम्ही\1होतात'),
            (r'\b(आम्ही|आपण)\b([^\n\u0964.!?]*?)\bआहे\b', r'\1\2आहोत'),
            (r'\bआम्ही\b([^\n\u0964.!?]*?)\bगेला\b', r'आम्ही\1गेलो'),
            (r'\bतू\b([^\n\u0964.!?]*?)\bगेला\b',   r'तू\1गेलास'),
            (r'\bतू\b([^\n\u0964.!?]*?)\bगेली\b',   r'तू\1गेलीस'),
            (r'\bतू\b([^\n\u0964.!?]*?)\bकरतो\b',   r'तू\1करतोस'),
            (r'\bमुलं\b([^\n\u0964.!?]*?)\bहोता\b', r'मुलं\1होते'),
        ]
        for pat, repl in verb_clause:
            work = re.sub(pat, repl, work, flags=re.UNICODE)

        # 6. GNP simple-case fixes
        for rule in self.kb.GNP:
            if re.search(_wb(rule['s']), work):
                work = re.sub(_wb(rule['w']), rule['c'], work)

        # 7. Demonstrative gender
        for dem, correct, ns_key, _ in self.kb.DEMONSTRATIVE:
            for noun in self._noun_sets[ns_key]:
                pat = (rf'(?<![{_DEV_RANGE}]){re.escape(dem)}'
                       rf'(\s+(?:\S+\s+)?{re.escape(noun)})(?![{_DEV_RANGE}])')
                work = re.sub(pat, correct + r'\1', work)

        # 8. Adjective gender
        for adj, corrections in self.kb.ADJECTIVE_MAP.items():
            for ns_key, correct_adj in corrections.items():
                for noun in self._noun_sets[ns_key]:
                    pat = (rf'(?<![{_DEV_RANGE}]){re.escape(adj)}'
                           rf'(\s+(?:\S+\s+)?{re.escape(noun)})(?![{_DEV_RANGE}])')
                    work = re.sub(pat, correct_adj + r'\1', work)

        # 9. Possessive gender
        poss_sets = {'FEM': self.kb.POSS_FEM, 'MASC': self.kb.POSS_MASC,
                     'NEUT': self.kb.POSS_NEUT}
        for poss, corrections in self.kb.POSSESSIVES.items():
            for ns_key, correct_poss in corrections.items():
                for noun in poss_sets[ns_key]:
                    pat = (rf'(?<![{_DEV_RANGE}]){re.escape(poss)}'
                           rf'(\s+(?:\S+\s+)?{re.escape(noun)})(?![{_DEV_RANGE}])')
                    work = re.sub(pat, correct_poss + r'\1', work)

        # 10. Relative pronoun gender
        for rel, correct, ns_key, _ in self.kb.RELATIVE_PRONOUN:
            for noun in self._noun_sets[ns_key]:
                pat = (rf'(?<![{_DEV_RANGE}]){re.escape(rel)}'
                       rf'(\s+(?:\S+\s+)?{re.escape(noun)})(?![{_DEV_RANGE}])')
                work = re.sub(pat, correct + r'\1', work)

        # 11. Repetition removal
        work = re.sub(
            rf'(?<![{_DEV_RANGE}])([{_DEV_RANGE}]+)\s+\1(?![{_DEV_RANGE}])',
            r'\1', work)

        # 12. Surface cleanup
        work = re.sub(r'  +', ' ', work)
        work = re.sub(r'([!?,।])\1+', r'\1', work)

        return work.strip()

    def analyze(self, text: str) -> Dict[str, Any]:
        if not text or not text.strip():
            return {'errors': [], 'errors_count': 0,
                    'corrected_text': '', 'grammar_score': 100, 'metrics': {}}

        start_ts = time.perf_counter()
        normalized = self._normalize(text)
        all_errors: List[GrammarError] = []

        self._check_spelling(normalized, all_errors)
        self._check_sandhi(normalized, all_errors)
        self._check_vibhakti(normalized, all_errors)
        self._check_gnp(normalized, all_errors)
        self._check_continuous(normalized, all_errors)
        self._check_aux(normalized, all_errors)
        self._check_negation(normalized, all_errors)
        self._check_sov(normalized, all_errors)
        self._check_dialect(normalized, all_errors)
        self._check_demonstrative(normalized, all_errors)
        self._check_relative_pronoun(normalized, all_errors)
        self._check_adjective_gender(normalized, all_errors)
        self._check_possessive_gender(normalized, all_errors)
        self._check_clause_pairing(normalized, all_errors)
        self._check_repetition(normalized, all_errors)
        self._check_question_punctuation(normalized, all_errors)
        self._check_surface(normalized, all_errors)
        self._check_sentence_length(normalized, all_errors)

        # Deduplicate by offset
        seen: Set[int] = set()
        unique: List[GrammarError] = []
        for err in sorted(all_errors, key=lambda e: e.character_offset):
            if err.character_offset not in seen:
                unique.append(err)
                seen.add(err.character_offset)

        # Score
        score = 100.0
        for err in unique:
            w = self.kb.WEIGHTS.get(err.category, 5.0)
            if err.severity == 'SUGGESTION':
                w *= 0.2
            elif err.severity == 'WARNING':
                w *= 0.5
            score -= w
        score = max(0.0, round(score, 2))

        corrected = self.hard_repair(text)
        tokens = normalized.split()
        word_count = len(tokens)
        unique_words = len(set(tokens))
        ttr = round(unique_words / max(1, word_count), 4)
        proc_ms = round((time.perf_counter() - start_ts) * 1000, 3)

        return {
            'errors': [{
                'message':       e.explanation,
                'english':       f'{e.category} → {e.sub_category}',
                'offset':        e.character_offset,
                'length':        e.token_length,
                'replacements':  [e.suggested_token],
                'ruleIssueType': 'grammar',
                'severity':      e.severity,
            } for e in unique],
            'errors_count':   len(unique),
            'corrected_text': corrected,
            'grammar_score':  score,
            'metrics': {
                'word_count':       word_count,
                'unique_words':     unique_words,
                'type_token_ratio': ttr,
                'reading_level':    'Professional' if ttr > 0.6 else 'Standard',
                'processing_ms':    proc_ms,
            }
        }


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC INTERFACE
# ══════════════════════════════════════════════════════════════════════════════

class MarathiGrammarDetector:
    """Drop-in singleton — sync + async check_grammar methods."""

    def __init__(self):
        self._engine = MarathiGrammarEngine()

    def check_grammar(self, text: str) -> Dict[str, Any]:
        return self._engine.analyze(text)

    async def check_grammar_async(self, text: str) -> Dict[str, Any]:
        return self._engine.analyze(text)


grammar_detector = MarathiGrammarDetector()
