#!/bin/bash
#
# SAGE System Installation Script
#

echo "🚀 Installing SAGE System"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Create directories
echo "📁 Creating directories..."
mkdir -p /home/ubuntu/logs
mkdir -p /home/ubuntu/newspaper_project

# Copy files
echo "📋 Copying system files..."
cp -r ../src/* /home/ubuntu/newspaper_project/
cp -r ../config/* /home/ubuntu/newspaper_project/

# Set permissions
echo "🔐 Setting permissions..."
chmod +x /home/ubuntu/newspaper_project/scripts/*.sh

echo ""
echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "1. Copy config/env.example to .env"
echo "2. Edit .env with your credentials"
echo "3. Run: source .env"
echo "4. Run: ./src/scripts/recreate_database.sh"
echo "5. Start services (see deployment/DEPLOYMENT.md)"
