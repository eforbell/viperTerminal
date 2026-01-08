#!/bin/bash
set -e

MAX_ITERATIONS=${1:-10}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "🚀 Starting Ralph - Feature 3: Data Reliability & Chart Improvements"
echo "📁 Project: $PROJECT_DIR"
echo "📋 Max iterations: $MAX_ITERATIONS"
echo ""

cd "$PROJECT_DIR"

for i in $(seq 1 $MAX_ITERATIONS); do
  echo "═══════════════════════════════════════"
  echo "═══ Iteration $i of $MAX_ITERATIONS ═══"
  echo "═══════════════════════════════════════"
  
  # Pipe the prompt.md content directly into claude with dangerous mode enabled
  OUTPUT=$(cat "$SCRIPT_DIR/prompt.md" \
    | claude --model sonnet --dangerously-skip-permissions 2>&1 \
    | tee /dev/stderr) || true
  
  # Check for rate limit
  if echo "$OUTPUT" | grep -qi "You've hit your limit\|rate limit\|resets.*America"; then
    echo ""
    echo "⚠️  Rate limit hit. Stopping Ralph."
    echo "💤 Resume later when limit resets."
    #exit 2
  fi
  
  # Check for the completion tag (case-insensitive just in case)
  if echo "$OUTPUT" | grep -qi "<promise>COMPLETE</promise>"; then
    echo ""
    echo "✅ All stories complete!"
    exit 0
  fi
  
  echo ""
  echo "⏳ Story completed. Continuing to next..."
  echo ""
done

echo "⚠️ Max iterations ($MAX_ITERATIONS) reached"
exit 1
