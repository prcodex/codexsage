#!/bin/bash
#
# SAGE Database Recreation Process
# Fetches 10-15 recent emails, enriches them, splits NewsBreif with links
# Use this anytime the database has problems
#

echo "🔄 SAGE DATABASE RECREATION PROCESS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cd /home/ubuntu/newspaper_project

# Set credentials
export GMAIL_USER="your_email@gmail.com"
export GMAIL_APP_PASSWORD="YOUR_GMAIL_APP_PASSWORD_HERE"
export ANTHROPIC_API_KEY="YOUR_ANTHROPIC_API_KEY_HERE"

echo "Step 1: Fetching 10 recent emails from Gmail..."
python3 /home/ubuntu/newspaper_project/fetch_and_split.py

echo ""
echo "Step 2: Restarting interface..."
pkill -f sage4_interface_fixed
nohup python3 sage4_interface_fixed.py > sage.log 2>&1 &

sleep 2

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ DATABASE RECREATED!"
echo ""
echo "🌐 View at: http://44.225.226.126:8540"
echo ""
echo "Fresh database with 10-15 recent emails, properly enriched and split!"
