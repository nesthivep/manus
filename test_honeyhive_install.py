#!/usr/bin/env python3

"""
Test script to verify HoneyHive is properly installed.
"""

import sys
import importlib.util

def check_package(package_name):
    """Check if a package is installed and print its version."""
    try:
        spec = importlib.util.find_spec(package_name)
        if spec is None:
            print(f"❌ {package_name} is NOT installed")
            return False
        
        module = importlib.import_module(package_name)
        version = getattr(module, "__version__", "unknown version")
        print(f"✅ {package_name} is installed (version: {version})")
        
        # Check for specific modules in honeyhive
        if package_name == "honeyhive":
            try:
                from honeyhive import evaluator, aevaluator, trace, atrace
                print(f"  ✅ Basic decorators (evaluator, aevaluator, trace, atrace) are available")
            except ImportError as e:
                print(f"  ❌ Error importing basic decorators: {e}")
            
            try:
                from honeyhive.async_api import evaluate as async_evaluate
                print(f"  ✅ async_api.evaluate is available")
            except ImportError as e:
                print(f"  ❌ Error importing async_api.evaluate: {e}")
        
        return True
    except Exception as e:
        print(f"❌ Error checking {package_name}: {e}")
        return False

def check_environment():
    """Check if required environment variables are set."""
    import os
    
    env_vars = {
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY"),
        "HONEYHIVE_API_KEY": os.environ.get("HONEYHIVE_API_KEY"),
        "HONEYHIVE_PROJECT": os.environ.get("HONEYHIVE_PROJECT"),
        "HONEYHIVE_SERVER_URL": os.environ.get("HONEYHIVE_SERVER_URL")
    }
    
    print("\nEnvironment Variables:")
    for var, value in env_vars.items():
        if value:
            # Show first 3 and last 3 characters for API keys
            if "API_KEY" in var and len(value) > 6:
                masked_value = f"{value[:3]}...{value[-3:]}"
                print(f"✅ {var} is set ({masked_value})")
            else:
                print(f"✅ {var} is set ({value})")
        else:
            if var == "HONEYHIVE_SERVER_URL":
                print(f"ℹ️ {var} is not set (optional)")
            else:
                print(f"❌ {var} is not set")

def main():
    """Main function to check HoneyHive installation."""
    print("Checking HoneyHive Installation\n")
    
    print("Python Version:", sys.version)
    print("\nRequired Packages:")
    
    honeyhive_installed = check_package("honeyhive")
    check_package("openai")
    
    check_environment()
    
    print("\nSummary:")
    if honeyhive_installed:
        print("✅ HoneyHive appears to be properly installed.")
        print("  To use it, make sure you have set the required environment variables.")
    else:
        print("❌ HoneyHive is not properly installed.")
        print("  Please install it with: pip install honeyhive")

if __name__ == "__main__":
    main() 