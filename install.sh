#!/bin/bash

# Change this to the raw URL of log_analyzer.py in your GitHub repository
GITHUB_RAW_URL="https://github.com/zchandikaz/log-analyzer/raw/refs/heads/master/log_analyzer.py"

# Download log_analyzer.py to /usr/local/bin (requires sudo)
sudo curl -L "$GITHUB_RAW_URL" -o /usr/local/bin/log_analyzer.py
sudo chmod +x /usr/local/bin/log_analyzer.py

# Create a wrapper script 'lgx'
echo '#!/bin/bash
python3 /usr/local/bin/log_analyzer.py "$@"' | sudo tee /usr/local/bin/lgx > /dev/null

sudo chmod +x /usr/local/bin/lgx

echo "Installed 'lgx' command. You can now use 'lgx' to run log_analyzer.py."