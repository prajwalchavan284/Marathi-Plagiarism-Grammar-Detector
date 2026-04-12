import language_tool_python
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class MarathiGrammarDetector:
    def __init__(self):
        # Try Marathi first, then fall back to English if language pack not available
        for lang_code in ['mr', 'en-US']:
            try:
                self.tool = language_tool_python.LanguageTool(lang_code)
                logger.info(f"LanguageTool initialized with language: {lang_code}")
                self.lang = lang_code
                break
            except Exception as e:
                logger.warning(f"LanguageTool failed for '{lang_code}': {e}")
                self.tool = None
        if self.tool is None:
            logger.error("LanguageTool could not be initialized with any language.")

    def check_grammar(self, text: str) -> Dict[str, Any]:
        if not self.tool:
            return {"error": "Grammar checking tool not available."}
        
        if not text or not text.strip():
            return {"errors": [], "corrected_text": ""}

        try:
            matches = self.tool.check(text)
            
            # Format the matches for easy consumption by the frontend
            formatted_errors = []
            for match in matches:
                formatted_errors.append({
                    "message": match.message,
                    "offset": match.offset,
                    "length": match.errorLength,
                    "ruleIssueType": match.ruleIssueType,
                    "replacements": match.replacements[:5], # Provide top 5 replacements
                    "context": match.context
                })

            corrected_text = language_tool_python.utils.correct(text, matches)
            
            return {
                "errors": formatted_errors,
                "corrected_text": corrected_text,
                "errors_count": len(formatted_errors)
            }
        except Exception as e:
            logger.error(f"Error checking grammar: {e}")
            return {"error": f"Error during grammar check: {str(e)}"}

grammar_detector = MarathiGrammarDetector()
