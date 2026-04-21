import sys
import os

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

try:
    from services.grammar import grammar_detector
    
    test_text = "मी गेल़ा. तो गेली. ती गेला. हे मुलगा आहे. तो शाळा जातो होती."
    print(f"Testing text: {test_text}")
    print("-" * 50)
    
    result = grammar_detector.check_grammar(test_text)
    
    print(f"Grammar Score: {result['grammar_score']}")
    print(f"Errors Found: {result['errors_count']}")
    print("-" * 50)
    for err in result['errors']:
        print(f"[{err['severity']}] {err['message']} (at {err['offset']})")
        print(f"   Suggestion: {err['replacements'][0]}")
    
    print("-" * 50)
    print(f"Corrected Text: {result['corrected_text']}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
