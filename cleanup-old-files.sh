#!/bin/bash
# Cleanup script: Move old state/log files to archive

cd /var/www/html/codelabhaven/projects/dryrun

echo "Moving old v2 and v3 files to archive..."

# Create archive if it doesn't exist
mkdir -p archive

# Move old state/log files
mv paper_state.json archive/ 2>/dev/null && echo "✓ Moved paper_state.json"
mv paper_trades.json archive/ 2>/dev/null && echo "✓ Moved paper_trades.json"
mv paper_log.txt archive/ 2>/dev/null && echo "✓ Moved paper_log.txt"
mv paper_state_v3.json archive/ 2>/dev/null && echo "✓ Moved paper_state_v3.json"
mv paper_state_v3.json.save archive/ 2>/dev/null && echo "✓ Moved paper_state_v3.json.save"
mv paper_trades_v3.json archive/ 2>/dev/null && echo "✓ Moved paper_trades_v3.json"
mv paper_log_v3.txt archive/ 2>/dev/null && echo "✓ Moved paper_log_v3.txt"

echo ""
echo "Remaining files in root:"
ls -1 *.json *.txt 2>/dev/null || echo "(none - all moved to archive)"

echo ""
echo "Active state file (should be the only one):"
ls -1 paper_trading_state.json 2>/dev/null && echo "✓ paper_trading_state.json (v4 - ACTIVE)" || echo "⚠ Missing paper_trading_state.json"

echo ""
echo "Done! Old files are in archive/"
