#!/usr/bin/env bash
# Check for geno-iso inbox notifications and display them.
# Called from SessionStart hook in geno-tools.

INBOX="${HOME}/.geno/iso/inbox.jsonl"

if [ ! -s "$INBOX" ]; then
    exit 0
fi

COUNT=$(wc -l < "$INBOX" | tr -d ' ')
echo "geno-iso: ${COUNT} notification(s)"

while IFS= read -r line; do
    TYPE=$(echo "$line" | python3 -c "import sys,json; print(json.loads(sys.stdin.read()).get('type','?'))" 2>/dev/null || echo "?")
    SUMMARY=$(echo "$line" | python3 -c "import sys,json; print(json.loads(sys.stdin.read()).get('summary',''))" 2>/dev/null || echo "")
    if [ -n "$SUMMARY" ]; then
        echo "  [${TYPE}] ${SUMMARY}"
    fi
done < "$INBOX"

# Archive after display
ARCHIVE="${HOME}/.geno/iso/inbox.$(date +%Y%m%d%H%M%S).jsonl"
mv "$INBOX" "$ARCHIVE"
