#!/bin/bash
# Removes the scheduled sync. Usage:  bash uninstall_schedule.sh
LABEL="com.personal-dashboard.sync"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
rm -f "$PLIST"
echo "Schedule removed."
