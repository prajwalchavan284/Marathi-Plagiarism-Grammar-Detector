import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from services.grammar import grammar_detector

text = "जो मुलगा अभ्यास करत नाही, तो नापास होईल."
result = grammar_detector.check_grammar(text)

print(f"Results for: '{text}'")
print(f"Error count: {result['errors_count']}")
for e in result['errors']:
    print(f"  - [{e['ruleIssueType']}] {e['message']} (English: {e['english']})")
    print(f"    Replacements: {e['replacements']}")
print(f"Corrected text: '{result['corrected_text']}'")
