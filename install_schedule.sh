#!/bin/bash
# Installs a macOS LaunchAgent that runs run_sync.sh every 2 hours (and once at login).
# Usage:  bash install_schedule.sh
# The project folder is detected automatically, so nothing to edit.
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
LABEL="com.personal-dashboard.sync"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
INTERVAL_SECONDS=7200

chmod +x "$DIR/run_sync.sh"
mkdir -p "$HOME/Library/LaunchAgents" "$DIR/logs"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$DIR/run_sync.sh</string>
  </array>
  <key>StartInterval</key>
  <integer>$INTERVAL_SECONDS</integer>
  <key>RunAtLoad</key>
  <true/>
  <key>StandardOutPath</key>
  <string>$DIR/logs/launchd.out</string>
  <key>StandardErrorPath</key>
  <string>$DIR/logs/launchd.err</string>
</dict>
</plist>
EOF

# Reload if already installed, then load
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

echo "Installed. Sync runs now, then every $((INTERVAL_SECONDS / 3600)) hours."
echo "Project: $DIR"
echo "Log:     $DIR/logs/sync.log"
