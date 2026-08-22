# 🤖 Claude CLI - Terminal AI Assistant

[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com/Abhirajroshan79/Claude-cli)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-yellow.svg)](https://www.python.org/)

A powerful, keyboard-only Claude CLI with persistent chat history, multiple account support, and file system access - all from your terminal!

---

## 📸 Preview

```

╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   ██████╗██╗      █████╗ ██╗   ██╗██████╗ ███████╗                ║
║   ██╔════╝██║     ██╔══██╗██║   ██║██╔══██╗██╔════╝                ║
║   ██║     ██║     ███████║██║   ██║██║  ██║█████╗                  ║
║   ██║     ██║     ██╔══██║██║   ██║██║  ██║██╔══╝                  ║
║   ╚██████╗███████╗██║  ██║╚██████╔╝██████╔╝███████╗                ║
║    ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝                ║
║                                                                   ║
║   🤖 AI Assistant                                                 ║
║   Your Terminal Claude                                            ║
╚═══════════════════════════════════════════════════════════════════╝

```

---

## ✨ Features

- 🎮 **Keyboard-Only Interface** - All commands via shortcuts (Ctrl+H for help)
- 🔐 **Multiple Account Support** - Switch between Claude accounts seamlessly
- 💾 **Persistent Chat History** - Never lose a conversation (SQLite database)
- 📁 **File System Access** - Browse, read, and edit files directly
- 🔄 **Auto-Resume** - Continue where you left off
- 🎨 **Beautiful UI** - Rich colors, tables, and formatting
- 📊 **Statistics** - Track your usage and conversations
- 💻 **Cross-Platform** - Works on Termux, Linux, macOS

---

## 🚀 Quick Install

```bash
git clone https://github.com/Abhirajroshan79/Claude-cli.git
cd Claude-cli
chmod +x install.sh
./install.sh
python cli.py
```

---

📋 Requirements

System Requirements

· Python 3.8 or higher
· Termux (Android) or Linux/macOS
· Internet connection

Python Dependencies

```
requests>=2.31.0
rich>=13.7.0
pyfiglet>=0.8.post1
```

---

🎯 Installation Guide

Step 1: Clone Repository

```bash
git clone https://github.com/Abhirajroshan79/Claude-cli.git
cd Claude-cli
```

Step 2: Make Installer Executable

```bash
chmod +x install.sh
```

Step 3: Run Installer

```bash
./install.sh
```

This will:

· Create necessary directories
· Install Python dependencies
· Create account template file

Step 4: Set Up Authentication

```bash
nano ~/.claude_sessions/account1.json
```

Add your cookies in this format:

```json
{
  "account_name": "your_email@gmail.com",
  "cookies": {
    "sessionKey": "sk-ant-sid02-...",
    "__cf_bm": "...",
    "_cfuvid": "...",
    "lastActiveOrg": "..."
  }
}
```

Step 5: Run Claude

```bash
python cli.py
```

---

🎮 Keyboard Shortcuts

Key Command Action
Ctrl+H /help Show help menu
Ctrl+N /new Start new conversation
Ctrl+S /switch Switch to next account
Ctrl+L /list List all accounts
Ctrl+E /history View conversation history
Ctrl+O /load Load conversation by ID
Ctrl+T /stats Show statistics
Ctrl+D /ls List directory contents
Ctrl+C /cd Change directory
Ctrl+P /pwd Show current directory
Ctrl+R /read Read a file
Ctrl+W /save Save conversation to file
Ctrl+X /exit Exit Claude CLI
Up/Down - Command history
Tab - Auto-complete

---

🔧 Multiple Accounts Setup

Add More Accounts

Create additional cookie files:

```bash
nano ~/.claude_sessions/account2.json
```

```json
{
  "account_name": "second_email@gmail.com",
  "cookies": {
    "sessionKey": "sk-ant-sid02-...",
    "__cf_bm": "...",
    "_cfuvid": "..."
  }
}
```

Switch Between Accounts

· Use /switch command
· Press Ctrl+S shortcut
· Type /list to see all accounts

Rate Limit Handling

When one account hits rate limit, simply:

1. Type /switch to change accounts
2. Or press Ctrl+S
3. Continue chatting immediately

---

📁 File Structure

```
~/.claude_sessions/
├── account1.json          # Account 1 cookies
├── account2.json          # Account 2 cookies
└── account3.json          # Account 3 cookies

~/.claude_history.db      # Chat history (SQLite)
~/.claude_agent_config.json  # Configuration file
~/.claude_cli_history     # Command history
~/.claude_prompt_history.txt  # Prompt history
```

Database Schema

```sql
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    title TEXT,
    created_at DATETIME,
    last_active DATETIME
);

CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT,
    role TEXT,
    content TEXT,
    timestamp DATETIME
);
```

---

🛠️ Available Commands

Command Description Example
/help Show help menu /help
/new Start new conversation /new
/switch Switch to next account /switch
/list List all accounts /list
/history View conversations /history
/load <id> Load conversation /load abc123
/stats Show statistics /stats
/clear Clear screen /clear
/ls List directory /ls /sdcard
/cd <path> Change directory /cd /sdcard/Download
/pwd Show current dir /pwd
/read <file> Read a file /read index.html
/cat <file> Read a file (alias) /cat main.py
/save <file> Save conversation /save chat.md
/version Show version /version
/exit Exit Claude /exit

---

📦 Dependencies

Python Packages

```bash
pip install requests rich pyfiglet
```

Termux Dependencies

```bash
pkg update && pkg upgrade
pkg install python python-pip sqlite
pip install requests rich pyfiglet
```

Linux/macOS Dependencies

```bash
pip3 install requests rich pyfiglet
```

---

🔐 Getting Your Cookies

Step-by-Step Guide

1. Open Claude in Browser
   · Go to https://claude.ai
   · Log in with your Google account
2. Open Developer Tools
   · Press F12 (Windows/Linux)
   · Press Cmd+Option+I (Mac)
3. Find Cookies
   · Go to Application tab (Chrome)
   · Go to Storage tab (Firefox)
   · Find Cookies → https://claude.ai
4. Copy Required Cookies
   · sessionKey - Required (starts with sk-ant-)
   · __cf_bm - Required
   · _cfuvid - Required
   · lastActiveOrg - Optional
5. Create JSON File

```bash
nano ~/.claude_sessions/account1.json
```

Paste this and fill in your values:

```json
{
  "account_name": "your_email@gmail.com",
  "cookies": {
    "sessionKey": "sk-ant-sid02-...",
    "__cf_bm": "...",
    "_cfuvid": "...",
    "lastActiveOrg": "4f183e6c-5d4a-4468-97bc-d1bb344023b6"
  }
}
```

---

🎯 Usage Examples

Start Claude

```bash
python cli.py
```

Send a Message

```
[your_email] ❯ Hello, who are you?
```

Create New Conversation

```
Press Ctrl+N
# OR
[your_email] ❯ /new
```

Load Previous Conversation

```
[your_email] ❯ /history
[your_email] ❯ /load abc123
```

Read a File

```
[your_email] ❯ /cd /sdcard/Download
[your_email] ❯ /read index.html
```

Save Conversation

```
[your_email] ❯ /save chat_export.md
```

---

🐛 Troubleshooting

*403 Forbidden Error*

· Cause: Cookies expired
· Solution: Refresh cookies from browser

*No Accounts Loaded*

· Cause: Missing account file
· Solution: Create ~/.claude_sessions/account1.json

*Rate Limit (429)*

· Cause: API rate limit reached
· Solution: Use /switch to change accounts

*405 Method Not Allowed*

· Cause: Wrong endpoint
· Solution: Update to latest version

*JSON Parse Error*

· Cause: Invalid JSON format
· Solution: Validate JSON at https://jsonlint.com

---

🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

---

📝 License

MIT License - See LICENSE file

---

⭐ Support

If you find this useful:

· ⭐ Star the repository on GitHub
· 🐛 Report issues
· 🔧 Submit pull requests

---

**Repository**

[Claude-cli](https://github.com/Abhirajroshan79/Claude-cli).

---

🙏 Credits

Built with ❤️ for the Claude Community

---

Made with ❤️ by Abhirajroshan79
