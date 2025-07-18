# PowerShell Installation Script for Log Analyzer on Windows
# Similar to install.sh but adapted for Windows environment

# Change this to the raw URL of log_analyzer.py in your GitHub repository
$GITHUB_RAW_URL = "https://raw.githubusercontent.com/zchandikaz/log-analyzer/main/log_analyzer.py"

# Function to check if running as administrator
function Test-Admin {
    $currentUser = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $currentUser.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Function to add a directory to the PATH environment variable
function Add-ToPath {
    param (
        [string]$Directory
    )
    
    $currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
    if ($currentPath -notlike "*$Directory*") {
        [Environment]::SetEnvironmentVariable("PATH", "$currentPath;$Directory", "User")
        Write-Host "Added $Directory to your PATH environment variable."
        Write-Host "You may need to restart your terminal for the changes to take effect."
    }
}

# Check if running as administrator
if (Test-Admin) {
    # We have admin access, install to Program Files
    Write-Host "Installing to C:\Program Files\log-analyzer (requires administrator privileges)..."
    
    # Create directory if it doesn't exist
    $installDir = "C:\Program Files\log-analyzer"
    if (-not (Test-Path -Path $installDir)) {
        New-Item -ItemType Directory -Path $installDir | Out-Null
    }
    
    # Download log_analyzer.py
    Invoke-WebRequest -Uri $GITHUB_RAW_URL -OutFile "$installDir\log_analyzer.py"
    
    # Create a batch file wrapper 'lgx.bat'
    @"
@echo off
python "%ProgramFiles%\log-analyzer\log_analyzer.py" %*
"@ | Out-File -FilePath "$installDir\lgx.bat" -Encoding ascii
    
    # Add to system PATH if not already there
    $systemPath = [Environment]::GetEnvironmentVariable("PATH", "Machine")
    if ($systemPath -notlike "*$installDir*") {
        [Environment]::SetEnvironmentVariable("PATH", "$systemPath;$installDir", "Machine")
        Write-Host "Added $installDir to system PATH."
    }
    
    Write-Host "Installed 'lgx' command. You can now use 'lgx' to run log_analyzer.py."
}
else {
    # No admin access, ask to install in user directory
    $response = Read-Host "No administrator privileges. Do you want to install in user directory? (y/n)"
    if ($response -eq "y") {
        Write-Host "Installing to $env:USERPROFILE\log-analyzer..."
        
        # Create directory if it doesn't exist
        $installDir = "$env:USERPROFILE\log-analyzer"
        if (-not (Test-Path -Path $installDir)) {
            New-Item -ItemType Directory -Path $installDir | Out-Null
        }
        
        # Download log_analyzer.py
        Invoke-WebRequest -Uri $GITHUB_RAW_URL -OutFile "$installDir\log_analyzer.py"
        
        # Create a batch file wrapper 'lgx.bat'
        @"
@echo off
python "%USERPROFILE%\log-analyzer\log_analyzer.py" %*
"@ | Out-File -FilePath "$installDir\lgx.bat" -Encoding ascii
        
        # Add to user PATH
        Add-ToPath -Directory $installDir
        
        Write-Host "Installed 'lgx' command to $installDir."
        Write-Host "Make sure Python is installed and available in your PATH."
    }
    else {
        Write-Host "Installation cancelled"
        exit 1
    }
}

Write-Host "Installation completed successfully."