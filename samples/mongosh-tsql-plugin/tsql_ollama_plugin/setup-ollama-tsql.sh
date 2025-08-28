#!/bin/bash

echo "Setting up Local Ollama-Powered Amazon DocumentDB TSQL Plugin for mongosh..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required for Amazon DocumentDB compatibility checking"
    exit 1
fi

# Prompt for Amazon DocumentDB compatibility tool location
echo ""
echo "This plugin requires the Amazon DocumentDB compatibility tool (compat.py)"
echo "Download from: https://github.com/awslabs/amazon-documentdb-tools/blob/master/compat-tool/compat.py"
echo ""
read -p "Enter the full path to compat.py: " COMPAT_PATH

if [ ! -f "$COMPAT_PATH" ]; then
    echo "> Error: compat.py not found at $COMPAT_PATH"
    echo "> Please verify the location of compat.py and re-run"
    exit 1
fi

# Install Ollama if needed
if ! command -v ollama &> /dev/null; then
    echo "> Installing Ollama..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install ollama
        else
            curl -fsSL https://ollama.com/install.sh | sh
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        curl -fsSL https://ollama.com/install.sh | sh
    else
        echo ">> Please install Ollama manually from https://ollama.com"
        exit 1
    fi
fi

# Start Ollama
if ! pgrep -x "ollama" > /dev/null; then
    echo "> Starting Ollama..."
    nohup ollama serve > /dev/null 2>&1 &
    sleep 3
fi

# Install recommended model
echo "> Installing CodeLlama 7B (~3.8GB)..."
ollama pull codellama:7b

# Install plugin
echo "> Installing plugin..."
if [ ! -d "$HOME/.mongosh" ]; then
    mkdir -p ~/.mongosh
    echo ">> Created ~/.mongosh directory"
fi

if [ -f "$HOME/.mongosh/tsql-ollama-plugin.js" ]; then
    echo ">> Plugin already exists, updating..."
fi

cp tsql-ollama-plugin.js ~/.mongosh/tsql-ollama-plugin.js

# Generate DocumentDB constraints file
echo "> Generating Amazon DocumentDB compatibility file..."
python3 -c "
import re
import json

with open('$COMPAT_PATH', 'r') as f:
    content = f.read()

# Extract the load_keywords function content
keywords_match = re.search(r'def load_keywords\(\):\s*\n\s*thisKeywords = \{(.*?)\}', content, re.DOTALL)
if not keywords_match:
    print('Could not find keywords in compat.py')
    exit(1)

keywords_content = keywords_match.group(1)

# Find operators that have '5.0':'No' (unsupported in DocumentDB 5.0)
unsupported = []
for line in keywords_content.split('\n'):
    if '\"5.0\":\"No\"' in line:
        # Extract the operator name from the beginning of the line
        operator_match = re.search(r'\"(\\\$[^\"]+)\"', line)
        if operator_match:
            unsupported.append(operator_match.group(1))

# Save to JSON file
with open('$HOME/.mongosh/documentdb-constraints.json', 'w') as f:
    json.dump({'unsupported_operators': unsupported}, f, indent=2)

print(f'Found {len(unsupported)} unsupported operators for DocumentDB 5.0')
"

echo "> Plugin and compatibility constraints generated successfully"

# Add plugin reference
echo "load('$HOME/.mongosh/tsql-ollama-plugin.js');" > ~/.mongoshrc.js
echo "> Updated .mongoshrc.js"

echo ""
echo "Local Ollama-Powered Amazon DocumentDB TSQL Plugin for mongosh installation complete!"
echo ""
echo "Next steps:"
echo "1. Use in mongosh: tsql('SELECT * FROM users')"