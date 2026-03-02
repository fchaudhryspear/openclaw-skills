#!/bin/bash

# Get current day of the week
DAY=$(date +%A)

# Subject with day
SUBJECT="Daily Peptide Summary - $DAY"

# Get peptides for today using jq
PEPTIDES=$(jq -r ".[\"$DAY\"] | to_entries | map(\"- \(.key): \(.value)\") | join(\"\n\")" ~/.openclaw/workspace/peptides.json)

# If no peptides, set a default message
if [ -z "$PEPTIDES" ]; then
  PEPTIDES="No peptides scheduled for today."
fi

# Format body
BODY="Today's Peptides:\n\n$PEPTIDES"

# Send email using osascript
osascript <<EOF
tell application "Mail"
  set theMessage to make new outgoing message with properties {subject:"$SUBJECT", content:"$BODY", visible:false}
  tell theMessage
    make new to recipient at end of to recipients with properties {address:"faisal@credologi.com"}
  end tell
  send theMessage
end tell
EOF