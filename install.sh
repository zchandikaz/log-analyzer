#!/bin/bash

# Change this to the raw URL of log_analyzer.py in your GitHub repository
GITHUB_RAW_URL="https://raw.githubusercontent.com/zchandikaz/log-analyzer/master/log_analyzer.py"

# Check if we have sudo access
if sudo -n true 2>/dev/null; then
  # We have sudo access, install to /usr/local/bin
  echo "Installing to /usr/local/bin (requires sudo)..."

  # Download log_analyzer.py to /usr/local/bin
  sudo curl -L "$GITHUB_RAW_URL" -o /usr/local/bin/log_analyzer.py
  sudo chmod +x /usr/local/bin/log_analyzer.py

  # Create a wrapper script 'lgx'
  cat << 'EOF' | sudo tee /usr/local/bin/lgx > /dev/null
#!/bin/bash
python3 /usr/local/bin/log_analyzer.py "$@"
EOF
  sudo chmod +x /usr/local/bin/lgx

  echo "Installed 'lgx' command. You can now use 'lgx' to run log_analyzer.py."
else
  # No sudo access, ask to install in user directory
  read -p "No sudo access. Do you want to install in user directory? (y/n) " ans
  if [[ $ans == "y" ]]; then
    echo "Installing to $HOME/bin..."

    # Create bin directory if it doesn't exist
    mkdir -p "$HOME/bin"

    # Download log_analyzer.py to user's bin directory
    curl -L "$GITHUB_RAW_URL" -o "$HOME/bin/log_analyzer.py"
    chmod +x "$HOME/bin/log_analyzer.py"

    # Create a wrapper script 'lgx'
    cat << 'EOF' > "$HOME/bin/lgx"
#!/bin/bash
python3 "$HOME/bin/log_analyzer.py" "$@"
EOF
    chmod +x "$HOME/bin/lgx"

    echo "Installed 'lgx' command to $HOME/bin."
    echo "Make sure $HOME/bin is in your PATH. You may need to add the following to your .bashrc or .zshrc:"
    echo "export PATH=\"\$HOME/bin:\$PATH\""
  else
    echo "Installation cancelled"
    exit 1
  fi
fi
