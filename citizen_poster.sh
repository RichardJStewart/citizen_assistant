#!/bin/bash

# === Configuration ===
INPUT_FILE="inputs.txt"                   # one message per line
URL="http://localhost:8000/chat"          # endpoint
INTERVAL=20                               # seconds between messages

# === Validation ===
if [ ! -f "$INPUT_FILE" ]; then
  echo "[ERROR] Input file not found: $INPUT_FILE" >&2
  exit 1
fi

echo "[INFO] Posting random messages to $URL every $INTERVAL seconds"
echo "Press Ctrl+C to stop."

# === Main Loop ===
while true; do
  # Pick a random non-empty line
  MESSAGE=$(grep -v '^[[:space:]]*$' "$INPUT_FILE" | shuf -n 1)

  if [ -z "$MESSAGE" ]; then
    echo "[WARN] No valid message found in $INPUT_FILE"
    sleep $INTERVAL
    continue
  fi

  # Escape double quotes in the message for safe JSON encoding
  SAFE_MSG=$(echo "$MESSAGE" | sed 's/"/\\"/g')

  # Build and send the JSON payload
  curl -s -X POST "$URL" \
    -H "Content-Type: application/json" \
    -d "{\"message\": \"$SAFE_MSG\"}" >/dev/null

  echo "$(date '+%Y-%m-%d %H:%M:%S') -> Sent: $MESSAGE"

  sleep $INTERVAL
done

