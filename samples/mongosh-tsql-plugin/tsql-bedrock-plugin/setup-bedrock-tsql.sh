#!/bin/bash

echo "Setting up Amazon Bedrock-powered Amazon DocumentDB TSQL Plugin for mongosh..."

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI is required for Amazon Bedrock integration"
    echo "Install from: https://aws.amazon.com/cli/"
    exit 1
fi

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

# Install plugin
echo "> Installing plugin..."
if [ ! -d "$HOME/.mongosh" ]; then
    mkdir -p ~/.mongosh
    echo ">> Created ~/.mongosh directory"
fi

if [ -f "$HOME/.mongosh/tsql-bedrock-plugin.js" ]; then
    echo ">> Plugin already exists, updating..."
fi

cp tsql-bedrock-plugin.js ~/.mongosh/

# Generate DocumentDB compatibility file
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
        operator_match = re.search(r'\"(\\\$[^\"]+)\"', line)
        if operator_match:
            unsupported.append(operator_match.group(1))

with open('$HOME/.mongosh/documentdb-constraints.json', 'w') as f:
    json.dump({'unsupported_operators': unsupported}, f, indent=2)
"

echo "> Plugin and compatibility file generated successfully"

# Add plugin reference
echo "load('$HOME/.mongosh/tsql-bedrock-plugin.js');" > ~/.mongoshrc.js
echo "> Updated .mongoshrc.js"

echo ""
echo "Amazon DocumentDB TSQL Plugin for mongosh installation complete!"
echo ""
echo "Next steps:"
echo "1. Configure AWS credentials: aws configure"
echo "2. Ensure Bedrock access and enable Claude 3 Haiku model (anthropic.claude-3-haiku-20240307-v1:0)"
echo "3. Use in mongosh: tsql('SELECT * FROM users')"