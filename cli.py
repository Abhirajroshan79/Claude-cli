#!/usr/bin/env python3
"""
Claude CLI - Terminal AI Assistant
Keyboard-only interface with persistent chat history
"""

import json
import os
import sys
import sqlite3
import time
import requests
from datetime import datetime
import threading
import readline

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown
from rich.text import Text
from rich.syntax import Syntax
from rich import box
import pyfiglet

CONSOLE = Console()
DB_PATH = os.path.expanduser("~/.claude_history.db")
SESSIONS_DIR = os.path.expanduser("~/.claude_sessions")
VERSION = "2.0.0"

COLORS = {
    'primary': 'cyan',
    'success': 'green',
    'error': 'red',
    'warning': 'yellow',
    'info': 'magenta',
    'claude': '#d97757',
    'directory': 'bright_blue',
    'file': 'bright_green',
    'shortcut': 'bright_yellow',
}

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            title TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_active DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT,
            role TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(conversation_id) REFERENCES conversations(id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS session_state (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

class SessionManager:
    def __init__(self):
        self.current_conv = None
        self._load_session()
    
    def _load_session(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT value FROM session_state WHERE key = 'current_conv'")
            row = c.fetchone()
            if row:
                self.current_conv = row[0]
            conn.close()
        except:
            pass
    
    def save_session(self, conv_id):
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute(
                "INSERT OR REPLACE INTO session_state (key, value) VALUES (?, ?)",
                ('current_conv', conv_id)
            )
            conn.commit()
            conn.close()
        except:
            pass
    
    def clear_session(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("DELETE FROM session_state WHERE key = 'current_conv'")
            conn.commit()
            conn.close()
            self.current_conv = None
        except:
            pass

class CookieManager:
    def __init__(self):
        self.accounts = []
        self.current = 0
        self._load_cookies()
    
    def _load_cookies(self):
        if not os.path.exists(SESSIONS_DIR):
            os.makedirs(SESSIONS_DIR)
            return
        
        for fname in os.listdir(SESSIONS_DIR):
            if fname.endswith('.json'):
                path = os.path.join(SESSIONS_DIR, fname)
                try:
                    with open(path, 'r') as f:
                        data = json.load(f)
                    
                    name = data.get('account_name', fname[:-5])
                    cookies = data.get('cookies', {})
                    if not cookies:
                        continue
                    
                    session = requests.Session()
                    session.cookies.update(cookies)
                    session.headers.update({
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Accept': 'application/json, text/plain, */*',
                        'Content-Type': 'application/json',
                        'Origin': 'https://claude.ai',
                        'Referer': 'https://claude.ai/chat',
                    })
                    
                    self.accounts.append({
                        'name': name,
                        'cookies': cookies,
                        'session': session
                    })
                    
                except Exception as e:
                    continue
        
        if not self.accounts:
            CONSOLE.print(f"[{COLORS['error']}]❌ No valid accounts loaded![/]")
            CONSOLE.print(f"[yellow]Add cookies to: {SESSIONS_DIR}/account1.json[/]")
            sys.exit(1)
    
    def get_current(self):
        if self.accounts:
            return self.accounts[self.current]
        return None
    
    def switch(self):
        if len(self.accounts) > 1:
            self.current = (self.current + 1) % len(self.accounts)
            return True
        return False
    
    def list_accounts(self):
        return [acc['name'] for acc in self.accounts]

class ClaudeClient:
    def __init__(self, cookie_manager):
        self.cookie_mgr = cookie_manager
        self.account = cookie_manager.get_current()
        self.session = self.account['session'] if self.account else None
        self.org_id = None
        self.current_conv = None
    
    def get_org_id(self):
        if self.org_id:
            return self.org_id
        
        if self.session:
            for cookie in self.session.cookies:
                if 'lastActiveOrg' in cookie.name:
                    self.org_id = cookie.value
                    return self.org_id
        
        try:
            resp = self.session.get('https://claude.ai/api/organizations', timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0:
                    self.org_id = data[0].get('uuid')
                    if self.org_id:
                        return self.org_id
        except:
            pass
        
        self.org_id = "4f183e6c-5d4a-4468-97bc-d1bb344023b6"
        return self.org_id
    
    def create_conversation(self, title=None):
        org_id = self.get_org_id()
        url = f'https://claude.ai/api/organizations/{org_id}/chat_conversations'
        
        if not title:
            title = f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        payload = {"name": title}
        resp = self.session.post(url, json=payload, timeout=10)
        
        if resp.status_code in [200, 201]:
            data = resp.json()
            conv_id = data.get('uuid')
            if conv_id:
                return conv_id
        
        raise Exception(f"Could not create conversation: {resp.status_code}")
    
    def send_message(self, message, conversation_id=None, progress_callback=None):
        if not self.session:
            raise Exception("No active session")
        
        try:
            org_id = self.get_org_id()
            
            if not conversation_id:
                conversation_id = self.create_conversation()
            
            self.current_conv = conversation_id
            
            url = f'https://claude.ai/api/organizations/{org_id}/chat_conversations/{conversation_id}/completion'
            
            payload = {
                "prompt": message,
                "attachments": [],
                "files": []
            }
            
            if progress_callback:
                progress_callback("sending")
            
            resp = self.session.post(url, json=payload, timeout=60)
            
            if resp.status_code == 200:
                response_text = resp.text
                reply = ""
                
                for line in response_text.split('\n'):
                    if line.startswith('data: '):
                        try:
                            data = json.loads(line[6:])
                            if data.get('type') == 'completion':
                                completion = data.get('completion', '')
                                if completion:
                                    reply += completion
                                    if progress_callback:
                                        progress_callback("streaming", reply)
                        except:
                            continue
                
                if not reply:
                    try:
                        data = resp.json()
                        reply = data.get('completion', data.get('text', str(data)))
                    except:
                        reply = "Could not parse response"
                
                if not reply or reply == "":
                    reply = "(empty response)"
                
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                
                c.execute("SELECT id FROM conversations WHERE id = ?", (conversation_id,))
                if not c.fetchone():
                    c.execute(
                        "INSERT INTO conversations (id, title, last_active) VALUES (?, ?, ?)",
                        (conversation_id, f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}", datetime.now().isoformat())
                    )
                else:
                    c.execute(
                        "UPDATE conversations SET last_active = ? WHERE id = ?",
                        (datetime.now().isoformat(), conversation_id)
                    )
                
                c.execute(
                    "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
                    (conversation_id, 'user', message)
                )
                c.execute(
                    "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
                    (conversation_id, 'assistant', reply)
                )
                conn.commit()
                conn.close()
                
                if progress_callback:
                    progress_callback("done", reply)
                
                return reply, conversation_id
            else:
                raise Exception(f"Failed: {resp.status_code}")
                
        except Exception as e:
            if progress_callback:
                progress_callback("error", str(e))
            raise Exception(f"Error: {e}")

class FileManager:
    @staticmethod
    def list_directory(path=None):
        if not path:
            path = os.getcwd()
        
        try:
            items = os.listdir(path)
            directories = []
            files = []
            
            for item in items:
                if item.startswith('.'):
                    continue
                full_path = os.path.join(path, item)
                if os.path.isdir(full_path):
                    directories.append(item + '/')
                else:
                    files.append(item)
            
            directories.sort()
            files.sort()
            
            table = Table(title=f"📂 Directory: {path}", box=box.ROUNDED, border_style=COLORS['directory'])
            table.add_column("Name", style=COLORS['directory'])
            table.add_column("Size", style=COLORS['secondary'])
            
            for d in directories:
                table.add_row(f"[bold {COLORS['directory']}]{d}[/]", "DIR")
            
            for f in files:
                size = os.path.getsize(os.path.join(path, f))
                size_str = f"{size} B"
                if size > 1024:
                    size_str = f"{size/1024:.1f} KB"
                if size > 1024*1024:
                    size_str = f"{size/(1024*1024):.1f} MB"
                table.add_row(f, size_str)
            
            CONSOLE.print(table)
            
        except Exception as e:
            CONSOLE.print(f"[{COLORS['error']}]❌ Error: {e}[/]")
    
    @staticmethod
    def read_file(path):
        try:
            if not os.path.exists(path):
                CONSOLE.print(f"[{COLORS['error']}]❌ File not found: {path}[/]")
                return
            
            if os.path.isdir(path):
                CONSOLE.print(f"[{COLORS['warning']}]⚠️  {path} is a directory[/]")
                return
            
            try:
                with open(path, 'r') as f:
                    content = f.read()
                
                ext = os.path.splitext(path)[1].lower()
                lang_map = {
                    '.py': 'python', '.js': 'javascript', '.html': 'html',
                    '.css': 'css', '.json': 'json', '.sh': 'bash',
                    '.txt': 'text', '.md': 'markdown', '.yml': 'yaml',
                    '.yaml': 'yaml', '.xml': 'xml'
                }
                lang = lang_map.get(ext, 'text')
                
                if len(content) > 5000:
                    CONSOLE.print(f"[{COLORS['warning']}]⚠️  File is large. Showing first 5000 chars...[/]")
                    content = content[:5000] + "...\n\n[truncated]"
                
                CONSOLE.print(Panel(
                    Syntax(content, lang, theme="monokai", line_numbers=True),
                    title=f"📄 {os.path.basename(path)}",
                    border_style=COLORS['file']
                ))
                
            except UnicodeDecodeError:
                CONSOLE.print(f"[{COLORS['warning']}]⚠️  {path} appears to be a binary file[/]")
                
        except Exception as e:
            CONSOLE.print(f"[{COLORS['error']}]❌ Error reading file: {e}[/]")
    
    @staticmethod
    def change_directory(path):
        try:
            os.chdir(path)
            return True
        except Exception as e:
            CONSOLE.print(f"[{COLORS['error']}]❌ Error: {e}[/]")
            return False
    
    @staticmethod
    def save_conversation(conv_id, filename):
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute(
                "SELECT role, content, timestamp FROM messages WHERE conversation_id = ? ORDER BY timestamp",
                (conv_id,)
            )
            rows = c.fetchall()
            conn.close()
            
            if not rows:
                CONSOLE.print(f"[{COLORS['warning']}]⚠️  No messages in this conversation[/]")
                return
            
            with open(filename, 'w') as f:
                f.write(f"# Claude Conversation\n")
                f.write(f"# ID: {conv_id}\n")
                f.write(f"# Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                for row in rows:
                    role = "You" if row['role'] == 'user' else "Claude"
                    f.write(f"## {role} ({row['timestamp']})\n\n")
                    f.write(row['content'])
                    f.write("\n\n---\n\n")
            
            CONSOLE.print(f"[{COLORS['success']}]✅ Conversation saved to: {filename}[/]")
            
        except Exception as e:
            CONSOLE.print(f"[{COLORS['error']}]❌ Error saving: {e}[/]")

class ClaudeUI:
    def __init__(self):
        self.cookie_mgr = CookieManager()
        self.client = ClaudeClient(self.cookie_mgr)
        self.session_mgr = SessionManager()
        self.file_mgr = FileManager()
        self.current_conv = self.session_mgr.current_conv
        self.client.current_conv = self.current_conv
        self.running = True
        
        readline.parse_and_bind('tab: complete')
        readline.parse_and_bind('set editing-mode emacs')
        
        self.histfile = os.path.expanduser("~/.claude_cli_history")
        try:
            readline.read_history_file(self.histfile)
        except FileNotFoundError:
            pass
        
        self.show_banner()
    
    def show_banner(self):
        os.system('clear')
        banner = pyfiglet.figlet_format("Claude CLI", font="slant")
        CONSOLE.print(Panel(
            Text(banner, style=f"bold {COLORS['claude']}"),
            title=f"🤖 v{VERSION}",
            subtitle="Keyboard-Only Interface",
            border_style=COLORS['primary'],
            width=80,
            box=box.DOUBLE
        ))
        
        shortcuts_table = Table(title="⌨️ Keyboard Shortcuts", box=box.ROUNDED, border_style=COLORS['shortcut'])
        shortcuts_table.add_column("Key", style=COLORS['shortcut'], no_wrap=True)
        shortcuts_table.add_column("Command", style=COLORS['info'])
        shortcuts_table.add_column("Action", style=COLORS['secondary'])
        
        shortcuts = [
            ("Ctrl+H", "/help", "Show help"),
            ("Ctrl+N", "/new", "New conversation"),
            ("Ctrl+S", "/switch", "Switch account"),
            ("Ctrl+L", "/list", "List accounts"),
            ("Ctrl+E", "/history", "View history"),
            ("Ctrl+O", "/load", "Load conversation"),
            ("Ctrl+T", "/stats", "Show stats"),
            ("Ctrl+D", "/ls", "List directory"),
            ("Ctrl+C", "/cd", "Change directory"),
            ("Ctrl+P", "/pwd", "Show current dir"),
            ("Ctrl+R", "/read", "Read file"),
            ("Ctrl+W", "/save", "Save conversation"),
            ("Ctrl+X", "/exit", "Exit"),
            ("Up/Down", "", "Command history"),
            ("Tab", "", "Auto-complete"),
        ]
        
        for key, cmd, action in shortcuts:
            shortcuts_table.add_row(key, cmd, action)
        
        CONSOLE.print(Panel(
            shortcuts_table,
            title="⌨️ Keyboard Shortcuts",
            border_style=COLORS['primary'],
            box=box.DOUBLE
        ))
        
        CONSOLE.print(f"\n[bold green]✅ Active Account:[/] {self.cookie_mgr.get_current()['name']}")
        CONSOLE.print(f"[dim]📁 Available: {', '.join(self.cookie_mgr.list_accounts())}[/]")
        if self.current_conv:
            CONSOLE.print(f"[dim]🔄 Resumed: {self.current_conv[:8]}...[/]")
        CONSOLE.print()
    
    def show_help(self):
        help_table = Table(title="📖 Claude CLI Help", box=box.ROUNDED, border_style=COLORS['primary'])
        help_table.add_column("Command", style=COLORS['claude'], no_wrap=True)
        help_table.add_column("Description", style=COLORS['info'])
        help_table.add_column("Shortcut", style=COLORS['shortcut'])
        
        commands = [
            ("/help", "Show this help", "Ctrl+H"),
            ("/new", "Start new conversation", "Ctrl+N"),
            ("/switch", "Switch to next account", "Ctrl+S"),
            ("/list", "List all accounts", "Ctrl+L"),
            ("/history", "View conversations", "Ctrl+E"),
            ("/load <id>", "Load conversation by ID", "Ctrl+O"),
            ("/stats", "Show statistics", "Ctrl+T"),
            ("/clear", "Clear screen", "Ctrl+U"),
            ("/exit", "Exit Claude CLI", "Ctrl+X"),
            ("/ls", "List directory contents", "Ctrl+D"),
            ("/cd", "Change directory", "Ctrl+C"),
            ("/pwd", "Show current directory", "Ctrl+P"),
            ("/read", "Read a file", "Ctrl+R"),
            ("/save", "Save conversation to file", "Ctrl+W"),
        ]
        
        for cmd, desc, shortcut in commands:
            help_table.add_row(cmd, desc, shortcut)
        
        CONSOLE.print(Panel(
            help_table,
            title="📖 Claude CLI Help",
            border_style=COLORS['primary'],
            box=box.DOUBLE
        ))
    
    def show_stats(self):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("SELECT COUNT(*) FROM conversations")
        conv_count = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM messages")
        msg_count = c.fetchone()[0]
        
        c.execute("SELECT role, COUNT(*) FROM messages GROUP BY role")
        roles = c.fetchall()
        
        c.execute("SELECT id, title, last_active FROM conversations ORDER BY last_active DESC LIMIT 1")
        last = c.fetchone()
        
        conn.close()
        
        stats_table = Table(title="📊 Statistics", box=box.ROUNDED, border_style=COLORS['success'])
        stats_table.add_column("Metric", style=COLORS['primary'])
        stats_table.add_column("Value", style=COLORS['info'])
        
        stats_table.add_row("Total Conversations", str(conv_count))
        stats_table.add_row("Total Messages", str(msg_count))
        for role, count in roles:
            emoji = "👤" if role == "user" else "🤖"
            stats_table.add_row(f"{emoji} {role.capitalize()}", str(count))
        
        if last:
            stats_table.add_row("Last Active", f"{last[0][:8]}... - {last[1][:20]}...")
        
        CONSOLE.print(stats_table)
    
    def show_history(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT id, title, created_at, last_active FROM conversations ORDER BY last_active DESC LIMIT 20")
        rows = c.fetchall()
        conn.close()
        
        if not rows:
            CONSOLE.print(f"[{COLORS['warning']}]📭 No conversations yet.[/]")
            return
        
        history_table = Table(title="📜 Recent Conversations", box=box.ROUNDED, border_style=COLORS['primary'])
        history_table.add_column("ID", style=COLORS['claude'], no_wrap=True)
        history_table.add_column("Title", style=COLORS['info'])
        history_table.add_column("Created", style=COLORS['secondary'])
        history_table.add_column("Active", style=COLORS['secondary'])
        
        for row in rows:
            conv_id = row['id'][:8] + "..."
            title = row['title'][:30] + "..." if len(row['title']) > 30 else row['title']
            history_table.add_row(conv_id, title, row['created_at'][:16], row['last_active'][:16])
        
        CONSOLE.print(history_table)
        CONSOLE.print(f"[{COLORS['info']}]💡 Use /load <full_id> to load a conversation[/]")
    
    def show_conversation(self, conv_id):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute(
            "SELECT role, content, timestamp FROM messages WHERE conversation_id = ? ORDER BY timestamp",
            (conv_id,)
        )
        rows = c.fetchall()
        conn.close()
        
        if not rows:
            CONSOLE.print(f"[{COLORS['warning']}]📭 No messages in this conversation.[/]")
            return
        
        CONSOLE.print(f"\n[bold {COLORS['primary']}]📖 Conversation {conv_id[:8]}...[/]\n")
        
        for row in rows:
            if row['role'] == 'user':
                CONSOLE.print(f"[bold {COLORS['claude']}]👤 You:[/] {row['content']}")
            else:
                CONSOLE.print(f"[bold {COLORS['success']}]🤖 Claude:[/] {row['content']}")
            CONSOLE.print(f"[dim]🕐 {row['timestamp']}[/]\n")
    
    def send_with_progress(self, message, conv_id):
        done = threading.Event()
        response = [None]
        error = [None]
        
        def progress_callback(status, data=None):
            if status == "sending":
                CONSOLE.print("[bold cyan]⏳ Sending to Claude...[/]", end="\r")
            elif status == "streaming":
                CONSOLE.print(f"[dim]📝 Generating: {data[:50]}...[/]", end="\r")
            elif status == "done":
                CONSOLE.print("[bold green]✅ Done![/]")
                response[0] = data
                done.set()
            elif status == "error":
                error[0] = data
                done.set()
        
        def send_thread():
            try:
                reply, new_conv = self.client.send_message(message, conv_id, progress_callback)
                if not response[0]:
                    response[0] = reply
                    self.current_conv = new_conv
                    self.session_mgr.save_session(new_conv)
                    done.set()
            except Exception as e:
                error[0] = str(e)
                done.set()
        
        thread = threading.Thread(target=send_thread)
        thread.daemon = True
        thread.start()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task("[cyan]Thinking...", total=None)
            while not done.is_set():
                time.sleep(0.1)
                progress.update(task, advance=1)
        
        if error[0]:
            raise Exception(error[0])
        
        return response[0], self.client.current_conv or self.current_conv
    
    def process_command(self, command):
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ''
        
        if cmd == '/help':
            self.show_help()
        elif cmd == '/new':
            self.current_conv = None
            self.client.current_conv = None
            self.session_mgr.clear_session()
            CONSOLE.print("[bold green]✅ New conversation ready![/]")
        elif cmd == '/switch':
            if self.cookie_mgr.switch():
                self.client = ClaudeClient(self.cookie_mgr)
                self.current_conv = None
                self.session_mgr.clear_session()
                CONSOLE.print(f"[bold green]✅ Switched to:[/] {self.cookie_mgr.get_current()['name']}")
            else:
                CONSOLE.print(f"[{COLORS['warning']}]⚠️ Only one account available[/]")
        elif cmd == '/list':
            accounts = self.cookie_mgr.list_accounts()
            CONSOLE.print(f"[bold]📁 Accounts:[/] {', '.join(accounts)}")
        elif cmd == '/history':
            self.show_history()
        elif cmd == '/load':
            if arg:
                self.current_conv = arg
                self.client.current_conv = arg
                self.session_mgr.save_session(arg)
                self.show_conversation(arg)
            else:
                CONSOLE.print(f"[{COLORS['warning']}]⚠️ Usage: /load <conversation_id>[/]")
        elif cmd == '/stats':
            self.show_stats()
        elif cmd == '/clear':
            os.system('clear')
            self.show_banner()
        elif cmd == '/ls':
            self.file_mgr.list_directory(arg if arg else None)
        elif cmd == '/cd':
            if arg:
                if self.file_mgr.change_directory(arg):
                    CONSOLE.print(f"[{COLORS['success']}]✅ Changed to: {os.getcwd()}[/]")
            else:
                self.file_mgr.change_directory(os.path.expanduser("~"))
        elif cmd == '/pwd':
            CONSOLE.print(f"[bold]📍 Current Directory:[/] {os.getcwd()}")
        elif cmd == '/read' or cmd == '/cat':
            if arg:
                self.file_mgr.read_file(arg)
            else:
                CONSOLE.print(f"[{COLORS['warning']}]⚠️ Usage: {cmd} <filename>[/]")
        elif cmd == '/save':
            if arg:
                conv_id = self.current_conv or self.client.current_conv
                if conv_id:
                    self.file_mgr.save_conversation(conv_id, arg)
                else:
                    CONSOLE.print(f"[{COLORS['warning']}]⚠️ No active conversation[/]")
            else:
                CONSOLE.print(f"[{COLORS['warning']}]⚠️ Usage: /save <filename>[/]")
        elif cmd == '/version':
            CONSOLE.print(f"[bold]Claude CLI v{VERSION}[/]")
        elif cmd == '/exit':
            self.running = False
        else:
            CONSOLE.print(f"[{COLORS['error']}]❌ Unknown command. Type /help for available commands.[/]")
    
    def run(self):
        while self.running:
            try:
                dir_name = os.getcwd().split('/')[-1] if os.getcwd() != '/' else '/'
                prompt = f"[{COLORS['claude']}]{self.cookie_mgr.get_current()['name'][:15]}[/] [dim]{dir_name}[/] ❯ "
                
                user_input = input(prompt)
                
                readline.add_history(user_input)
                readline.write_history_file(self.histfile)
                
            except KeyboardInterrupt:
                print("\n[Use Ctrl+D to exit]")
                continue
            except EOFError:
                break
            
            if not user_input.strip():
                continue
            
            if user_input.startswith('/'):
                self.process_command(user_input)
                continue
            
            try:
                print("⏳ Sending...", end="")
                reply, conv_id = self.send_with_progress(user_input, self.current_conv or self.client.current_conv)
                self.current_conv = conv_id
                self.client.current_conv = conv_id
                self.session_mgr.save_session(conv_id)
                
                print("\r" + " " * 80 + "\r", end="")
                
                CONSOLE.print()
                CONSOLE.print(Panel(
                    Markdown(reply) if len(reply) < 1000 else reply,
                    title="🤖 Claude",
                    border_style=COLORS['success'],
                    box=box.ROUNDED,
                ))
                CONSOLE.print()
                
            except Exception as e:
                print("\r" + " " * 80 + "\r", end="")
                CONSOLE.print(f"[{COLORS['error']}]❌ Error: {e}[/]")
                if "429" in str(e):
                    CONSOLE.print(f"[{COLORS['warning']}]💡 Try /switch to change accounts[/]")
        
        CONSOLE.print("[bold yellow]👋 Goodbye![/]")

def main():
    try:
        ui = ClaudeUI()
        ui.run()
    except KeyboardInterrupt:
        CONSOLE.print("\n[yellow]👋 Goodbye![/]")
    except Exception as e:
        CONSOLE.print(f"[red]❌ Fatal Error: {e}[/]")
        sys.exit(1)

if __name__ == "__main__":
    main()
