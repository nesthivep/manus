#!/bin/bash
#
# Script to run the OpenManus evaluation tests
#

# Print header
echo "===================================="
echo "  OpenManus Evaluation Test Runner"
echo "===================================="
echo ""

# Check Python availability
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not found in PATH"
    exit 1
fi

# Check if virtual environment exists
if [ -d "venv" ] || [ -d ".venv" ]; then
    # Activate virtual environment
    if [ -d "venv" ]; then
        echo "Activating virtual environment (venv)..."
        source venv/bin/activate
    else
        echo "Activating virtual environment (.venv)..."
        source .venv/bin/activate
    fi
else
    echo "No virtual environment found. Running with system Python."
fi

# Check for HoneyHive API key
if [ -z "$HH_API_KEY" ]; then
    echo "Warning: HH_API_KEY not set in environment."
    echo "Setting a default API key for testing purposes only."
    export HH_API_KEY="dXV3cXpoZmFwb3NsY3N4N3lidmE2aQ=="
fi

echo "Starting evaluation tests..."
echo ""

# Run tests
python3 test_evaluation.py

# Check result
if [ $? -eq 0 ]; then
    echo ""
    echo "Tests completed successfully!"
    
    # Check if results file exists
    if [ -f "evaluation_test_results.json" ]; then
        echo "Results saved to: evaluation_test_results.json"
    fi
else
    echo ""
    echo "Tests failed with errors. Check the logs for details."
    exit 1
fi

echo ""
echo "===================================="
echo "  Evaluation Tests Complete"
echo "===================================="

# Deactivate virtual environment if it was activated
if [ -n "$VIRTUAL_ENV" ]; then
    deactivate
fi

exit 0 