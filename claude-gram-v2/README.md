# Claude-Gram v2

> [!NOTE]
> This project is a fork of the original [claude-gram by @ripcats](https://github.com/ripcats/ripcats-marketplace/tree/main/claude-gram), created and maintained by [@justidev](https://t.me/justidev).

**Claude-Gram v2** is a premium self-hosted Telegram channel bridge for [Claude Code](https://claude.ai/code) and Antigravity CLI (`agy`). It enables you to send and receive text, formatted code, files, logs, and photos directly from your AI agent. Running as an MCP (Model Context Protocol) server over stdio, it uses `aiogram 3` and includes advanced interactive management, multi-profile handling, and automatic daemon installation.

---

## 🌟 Key Features

* **Proportional Sprite Mascot** – A cute pixel-art sprite of **Claudgramik** (inspired by the official Anthropic mascot) welcomes you during setup.
* **Responsive ANSI Gradient Banners** – Beautiful startup graphics with horizontal terracotta-white-red color transitions that dynamically adapt to your terminal window size.
* **Interactive Cross-Platform Installer** (`install.sh` / `install.ps1`) – Configures dependencies (`playwright`, `curl_cffi`, system libraries) and registers background services under Linux (`systemd`), macOS (`launchd`), Windows (`Task Scheduler`/Startup), or generic `PM2`/`nohup`.
* **Automated Git Updates** – Periodically checks for new commits, resets code safely, sends a pretty Telegram notification with the changelog (list of new commits), and reboots.
* **Orphan Session Guard** – Robust `SIGTERM`/`SIGINT` wrapper interceptors and `control-group` service kills prevent background PTY processes from locking session files.
* **Multi-Profile Control** – Full Telegram command suite to list (`/accounts`), switch (`/switch_account`), log in (`/login`), backup (`/save_account`), or remove (`/delete_account`) credentials.
* **Model & Effort Switching** – Dynamically change models (`/model`) and reasoning effort levels (`/effort`) using native inline Telegram keyboards.
* **HTML Formatting** – Retains all Telegram typography (bold, italics, code blocks, quote blocks) and displays thinking processes beautifully.

---

## ⚙️ Requirements

* Python 3.10+
* `aiogram >= 3.28`, `orjson`, `curl_cffi`, `playwright`
* A Telegram bot token from [@BotFather](https://t.me/BotFather)

---

## 🚀 Installation

### 1. Automatic Install

Simply clone this directory and run the helper script:

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

The installer will guide you through entering your Telegram Bot Token and Owner Telegram ID, download python dependencies, and setup the background auto-starting service.

---

## 🤖 Bot Commands

| Command | Description |
|---|---|
| `/start` | Welcome message and initial authorization check. |
| `/accounts` | Display all saved profiles and the active account. |
| `/login <name>` | Start interactive OAuth login flow for a new profile. |
| `/save_account` | Backup the currently active profile credentials. |
| `/switch_account <name>` | Switch active email account profile and restart the bot. |
| `/delete_account <name>` | Permanently delete a profile credentials. |
| `/model` | Switch the Claude model (Sonnet, Opus, Haiku) using inline buttons. |
| `/effort` | Adjust the model's reasoning effort level (low, medium, high). |
| `/usage` | View detailed token limit statistics and billing state. |
| `/resume` | Select and resume any previous Claude Code session. |
| `/auto` | Toggle auto-permission confirmation. |
| `/close` | Terminate the active session, clear workspace logs, and close the thread. |

---

## 🛠️ Agent Tools (MCP server)

These tools are exposed to the Claude Code agent session:

| Tool | Description |
|---|---|
| `reply` | Send a text reply to Telegram chat (HTML formatted). |
| `reply_file` / `send_file_to_tg` | Send files, logs, photos or documents. |
| `reactions` | Add reactions (`👍`, `🔥`, `👀`, etc.) based on message mood. |
| `rename_thread` | Rename the current session topic (forum thread). |
| `edit_message` | Edit a previously sent text message. |
| `get_history` | Retrieve local logs of the active thread history. |

---

## 👤 Authors

* **Fork Author**: [@justidev](https://t.me/justidev)
* **Original Author**: [@ripcats](https://github.com/ripcats)

---

## 📄 License

This project is licensed under the MIT License.
