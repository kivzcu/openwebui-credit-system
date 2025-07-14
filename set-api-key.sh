#!/bin/bash

# Set the API key for extensions to match the server
API_KEY="vY97Yvh6qKywm8xE-ErTGfUofV0t1BiZ36wR3lLNHIY"

echo "Setting CREDITS_API_KEY environment variable..."
echo "export CREDITS_API_KEY=\"$API_KEY\"" >> ~/.bashrc

# Also set it for the current session
export CREDITS_API_KEY="$API_KEY"

echo "✅ API key set successfully!"
echo "Current API key: $CREDITS_API_KEY"
echo ""
echo "To make this permanent, add this line to your shell profile:"
echo "export CREDITS_API_KEY=\"$API_KEY\""
echo ""
echo "Or create a .env file in your OpenWebUI directory with:"
echo "CREDITS_API_KEY=$API_KEY"
