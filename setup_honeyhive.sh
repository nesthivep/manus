#!/bin/bash

# Setup environment variables for HoneyHive
# Run this script with: source setup_honeyhive.sh

# Your OpenAI API key (if needed)
export OPENAI_API_KEY="your_openai_api_key_here"

# Your HoneyHive API key
export HONEYHIVE_API_KEY="your_honeyhive_api_key_here"

# Your HoneyHive project name
export HONEYHIVE_PROJECT="openmanus-trace"

# Optional: Your HoneyHive server URL (for self-hosted deployments)
# export HONEYHIVE_SERVER_URL="your_server_url_here"

echo "Environment variables for HoneyHive have been set."
echo "OPENAI_API_KEY: ${OPENAI_API_KEY:0:3}...${OPENAI_API_KEY: -3}"
echo "HONEYHIVE_API_KEY: ${HONEYHIVE_API_KEY:0:3}...${HONEYHIVE_API_KEY: -3}"
echo "HONEYHIVE_PROJECT: $HONEYHIVE_PROJECT"
if [ -n "$HONEYHIVE_SERVER_URL" ]; then
    echo "HONEYHIVE_SERVER_URL: $HONEYHIVE_SERVER_URL"
fi 