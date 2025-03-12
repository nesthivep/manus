#!/usr/bin/env python3

"""
Simple script to check if we can import the honeyhive module.
"""

import sys
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")

try:
    import honeyhive
    print(f"✅ Successfully imported honeyhive (version: {getattr(honeyhive, '__version__', 'unknown')})")
    
    # Check for specific modules
    try:
        from honeyhive import evaluator, aevaluator
        print(f"✅ Successfully imported evaluator and aevaluator")
    except ImportError as e:
        print(f"❌ Error importing evaluator and aevaluator: {e}")
    
    try:
        from honeyhive.async_api import evaluate as async_evaluate
        print(f"✅ Successfully imported async_evaluate")
    except ImportError as e:
        print(f"❌ Error importing async_evaluate: {e}")
        
except ImportError as e:
    print(f"❌ Failed to import honeyhive: {e}")
    
try:
    import openai
    print(f"✅ Successfully imported openai (version: {getattr(openai, '__version__', 'unknown')})")
except ImportError as e:
    print(f"❌ Failed to import openai: {e}") 