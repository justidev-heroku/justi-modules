# Claude-Gram v2 — EN

[![Telegram](https://img.shields.io/badge/Telegram-@justidev-2CA5E0?logo=telegram&logoColor=white)](https://t.me/justidev)

![Claude-Gram v2 Banner](https://raw.githubusercontent.com/justidev-heroku/justi-modules/main/assets/claude_gram_v2.jpg)

**Claude-Gram v2** is a premium self-hosted Telegram channel bridge for [Claude Code](https://claude.ai/code) and Antigravity CLI (`agy`). It enables you to send and receive text, formatted code, files, logs, and photos directly from your AI agent context.

> [!NOTE]
> This project is a fork of the original [claude-gram by @ripcats](https://github.com/ripcats/ripcats-marketplace/tree/main/claude-gram).

Current version: **v2.0.0**.

---

## Installation

### 1. Clone the repository
Clone the modules repository and navigate to the project directory:
```bash
git clone https://github.com/justidev-heroku/justi-modules.git
cd justi-modules/claude-gram-v2
```

### 2. Run the installer
The helper script will automatically verify Python, install all required dependencies (including `aiogram`, `playwright`, `curl_cffi`), and set up the background daemon auto-start.

#### Linux / macOS:
```bash
chmod +x install.sh
./install.sh
```

#### Windows (Run PowerShell as Admin):
```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
.\install.ps1
```

---

## Key Features

- **Claudgramik Mascot** – A cute pixel-art mascot welcomes you during setup.
- **Gradient Banners** – Beautiful startup graphics that dynamically adapt to your terminal width.
- **Auto-updates from Git** – The bot checks for updates every 15 minutes, automatically pulls them, and sends a changelog directly to Telegram.
- **Anti-hang Protection** – Built-in signal handling stops background PTY tasks clean, preventing crashes during service reboots.
- **Multi-account Manager** – Easily log in, backup, and switch between profile credentials straight from the chat.
- **Model & Effort Selectors** – Switch models (Sonnet/Opus/Haiku) and reasoning depths (Effort) using quick Telegram buttons.
- **HTML Message Rendering** – Keeps all native Telegram formatting (bold, italics, quotes, and code blocks) intact.


---

## Bot Commands

| Command | Description |
|---|---|
| `/start` | Welcome message and initial owner authorization check |
| `/accounts` | Display all saved profiles and the active account |
| `/login <name>` | Start interactive OAuth login flow for a new profile |
| `/save_account` | Backup the currently active profile credentials |
| `/switch_account <name>` | Switch active email account profile and restart the bot |
| `/delete_account <name>` | Permanently delete a profile credentials from the server |
| `/model` | Switch the Claude model (Sonnet, Opus, Haiku) using inline buttons |
| `/effort` | Adjust the model's reasoning effort level (low, medium, high) |
| `/usage` | View detailed token limit statistics and billing state |
| `/resume` | Select and resume any previous Claude Code session |
| `/auto` | Toggle auto-permission confirmation |
| `/close` | Terminate the active session, clear workspace logs, and close the thread |

---

## Agent Tools (MCP server)

| Tool | Description |
|---|---|
| `reply` | Send a text reply to Telegram chat (HTML formatted) |
| `reply_file` | Send files, logs, photos or documents |
| `reactions` | Add reactions (`👍`, `🔥`, `👀`, etc.) based on message mood |
| `rename_thread` | Rename the current session topic (forum thread) |
| `edit_message` | Edit a previously sent text message |
| `get_history` | Retrieve local logs of the active thread history |

---

## Configuration (access.json)

| Parameter | Description |
|---|---|
| `allowFrom` | List of allowed Telegram IDs |
| `ackReaction` | Default emoji reaction to incoming user messages |
| `tz` | Timezone for forum threads (e.g. `Europe/Moscow`) |
| `threads` | Toggle forum thread mode (`true`/`false`) |

---

## Language Switching

- [Russian docs](README.md)

---

## License

MIT · [@justidev](https://t.me/justidev)
