#!/bin/bash

# Enable strict error handling
set -e  # Exit script on any error
set -o pipefail  # Catch errors in pipelines

# Function to run a script and log its execution
run_script() {
    script_name=$1
    echo "Running $script_name..."
    start_time=$(date +%s)
    
    python3 "$script_name"
    exit_code=$?
    
    end_time=$(date +%s)
    duration=$((end_time - start_time))

    if [ $exit_code -eq 0 ]; then
        echo "$script_name completed successfully in $duration seconds."
    else
        echo "Error: $script_name failed with exit code $exit_code."
        exit $exit_code
    fi
}

# Run scripts sequentially with logging
run_script "availability.py"
run_script "cost.py"
run_script "latency.py"
run_script "sensitivity.py"

echo "All scripts executed successfully!"