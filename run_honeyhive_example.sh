#!/bin/bash

# Run the HoneyHive decorator example
echo "Running HoneyHive decorator example..."
python examples/honeyhive_decorator_example.py

# Check if the script ran successfully
if [ $? -eq 0 ]; then
    echo -e "\n✅ Example completed successfully!"
    echo "Check your HoneyHive dashboard to see the evaluation results."
else
    echo -e "\n❌ Example failed to run correctly."
    echo "Please check the error messages above."
fi 