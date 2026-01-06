#!/bin/bash
set -e

MAX_ITERATIONS=${1:-10}
SCRIPT_DIR="$(cd "$(dirname \
  "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Starting Ralph"

for i in $(seq 1 $MAX_ITERATIONS); do
echo "═══ Iteration $i ═══"
  
  # Pipe the prompt.md content directly into claude with dangerous mode enabled
  OUTPUT=$(cat "$SCRIPT_DIR/prompt.md" \
    | claude --dangerously-skip-permissions 2>&1 \
    | tee /dev/stderr) || true
  
  # Check for the completion tag (case-insensitive just in case)
  if echo "$OUTPUT" | grep -qi "<promise>COMPLETE</promise>"; then
    echo "✅ Done!"
    exit 0
  fi
done

echo "⚠️ Max iterations reached"
exit 1
