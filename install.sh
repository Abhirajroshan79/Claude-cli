#!/bin/bash
echo "🚀 Installing Claude CLI..."
echo "================================"

if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python 3.8+"
    exit 1
fi

echo "📁 Creating directories..."
mkdir -p ~/.claude_sessions

echo "📦 Installing Python packages..."
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Installation complete!"
else
    echo "❌ Installation failed."
    echo "   pip install requests rich pyfiglet"
    exit 1
fi

if [ ! -f ~/.claude_sessions/account1.json ]; then
    echo "📝 Creating account template..."
    cat > ~/.claude_sessions/account1.json << 'TEMPLATE_EOF'
{
  "account_name": "your_email@gmail.com",
  "cookies": {
    "sessionKey": "YOUR_SESSION_KEY_HERE",
    "__cf_bm": "YOUR_CF_BM_HERE",
    "_cfuvid": "YOUR_CFUVID_HERE"
  }
}
TEMPLATE_EOF
    echo "⚠️ Update ~/.claude_sessions/account1.json with your cookies"
fi

echo ""
echo "✨ Claude CLI installed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Update cookies in ~/.claude_sessions/account1.json"
echo "2. Run: python cli.py"
echo "3. Press Ctrl+H for help"
