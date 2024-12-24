#!/bin/bash
set -e

# Function to validate configuration file
validate_config() {
    if [ ! -f "$CONFIG_PATH" ]; then
        echo "Error: Configuration file not found at $CONFIG_PATH"
        exit 1
    fi

    # Validate YAML syntax
    python -c "import yaml; yaml.safe_load(open('$CONFIG_PATH'))" || {
        echo "Error: Invalid YAML syntax in configuration file"
        exit 1
    }
}

# Function to setup logging directory
setup_logging() {
    mkdir -p /logs
    chmod 755 /logs
    
    # Create log file if it doesn't exist
    touch /logs/media_cleanup.log
    chmod 644 /logs/media_cleanup.log
}

# Function to check required environment variables
check_environment() {
    if [ -z "$CONFIG_PATH" ]; then
        echo "Error: CONFIG_PATH environment variable not set"
        exit 1
    fi
}

# Main execution
main() {
    echo "Starting Media Cleanup Service..."
    
    # Perform initial checks
    check_environment
    validate_config
    setup_logging
    
    # Run the Python script
    echo "Running media cleanup script with config from $CONFIG_PATH"
    python /app/media_cleanup.py "$CONFIG_PATH"
}

# Execute main function
main "$@"