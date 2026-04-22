# CodexCLI — EN

[![Telegram](https://img.shields.io/badge/Telegram-@justidev-2CA5E0?logo=telegram&logoColor=white)](https://t.me/justidev)

![CodexCLI Banner](https://raw.githubusercontent.com/sepiol026-wq/GoyModules/refs/heads/main/assets/CodexCLI.png)

**CodexCLI** is a module for [Heroku](https://github.com/coddrago/Heroku) that integrates OpenAI Codex CLI directly into Telegram. Supports ChatGPT OAuth, real-time response streaming and Telegram action execution via AI.  
**Forked of [QwenCLI](https://github.com/sepiol026-wq/GoyModules/blob/main/QwenCLI.py)**

---

## Module installation

```
.dlm https://raw.githubusercontent.com/justidev-heroku/justi-modules/main/modules/CodexCLI.py
```

or via repository:

```
.addrepo https://github.com/justidev-heroku/justi-modules/modules
```

---

## Requirements

- [Heroku](https://github.com/coddrago/Heroku)
- OpenAI API key / ChatGPT account
- `codex` CLI installed on the host

> If `codex CLI` is not installed on the host — use `.cdxinstall` to automatically set up a local Runtime.

---

## Runtime installation

| Command | Description |
|---------|-------------|
| `.cdxinstall` | Automatically install local Codex CLI Runtime |

---

## Authentication

| Command | Description |
|---------|-------------|
| `.cdxauth status` | Show current auth status |
| `.cdxauth auth` | Sign in via ChatGPT OAuth (device flow) |
| `.cdxauth easy` | Auto login with API key fallback |
| `.cdxauth apikey <key>` | Set OpenAI API key |
| `.cdxauth clear` | Reset all auth data |

---

## Commands

| Command | Description |
|---------|-------------|
| `.cdx <prompt>` | Send a request to Codex |
| `.cdxpatch <edit>` | Clarify or extend the previous request |
| `.cdxstop` | Stop the current request |
| `.cdxclear` | Clear dialog history in the chat |
| `.cdxmodel [model]` | Show or change the model |
| `.cdxprompt <text>` | Set a system prompt |

---

## Configuration

| Parameter | Description |
|-----------|-------------|
| `codex_model` | Model (e.g. `gpt-5.3-codex`, `gpt-5.4`) |
| `approval_mode` | Approval mode: `yolo`, `plan`, `auto-edit`, `default` |
| `system_instruction` | Default system prompt |
| `openai_base_url` | Custom API endpoint (leave empty for ChatGPT OAuth) |

---

## Switch language

- [Русская документация](codexcli_ru.md)

---

## License

MIT · [@justidev](https://t.me/justidev)
