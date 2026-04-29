# CodexCLI — EN

[![Telegram](https://img.shields.io/badge/Telegram-@justidev-2CA5E0?logo=telegram&logoColor=white)](https://t.me/justidev)

![CodexCLI Banner](https://raw.githubusercontent.com/sepiol026-wq/GoyModules/refs/heads/main/assets/CodexCLI.png)

**CodexCLI** is a [Heroku](https://github.com/coddrago/Heroku) module that brings OpenAI Codex CLI directly into Telegram.

Current branch target: **v1.4.0**.

---

## Installation

```bash
.dlm https://raw.githubusercontent.com/justidev-heroku/justi-modules/main/modules/CodexCLI.py
```

or:

```bash
.addrepo https://github.com/justidev-heroku/justi-modules/modules
```

---

## Key Features

- Codex CLI in Telegram (`.cdx` + slash aliases like `/status` via `.cdx /status`)
- Streaming execution status with redesigned UI
- `reasoning_mode` support: `low | medium | high | xhigh`
- Image generation via `.cimg` (`gpt-image-1` / `gpt-image-2`)
- Inline `.cimg` controls: regenerate, model menu, full prompt export

---

## Commands

| Command | Description |
|---|---|
| `.cdx <prompt>` | Send a Codex request |
| `.cdxpatch <edit>` | Patch/extend previous request |
| `.cdxstop` | Stop active request |
| `.cdxclear` | Clear chat memory |
| `.cdxreset` | Full memory reset |
| `.cdxmodel [name]` | Show/change Codex model |
| `.cdxprompt <text>` | Set system prompt |
| `.cimg <prompt>` | Generate an image |

---

## `.cimg` UI (v1.4.0)

After generation, inline controls are available:

- `🔄 Regenerate`
- `🎛 Select model` → submenu with `1️⃣ gpt-image-1` and `2️⃣ gpt-image-2`
- `◀️ Back` (return from model submenu)
- `📄 Show prompt` (shown only when prompt length is over 512 chars)

Long prompt behavior:

- caption shows the first 512 characters;
- full prompt can be sent as `.txt` via `Show prompt`.

Model selected from inline buttons is also persisted into `cfg image_model`.

---

## Authentication

| Command | Description |
|---|---|
| `.cdxauth status` | Check auth status |
| `.cdxauth auth` | Device login via ChatGPT |
| `.cdxauth apikey <key>` | Save API key |
| `.cdxauth codex` | Bind codex-login using API key |
| `.cdxauth clear` | Clear auth artifacts |

---

## Config (important)

| Parameter | Description |
|---|---|
| `codex_model` | Codex model (e.g. `gpt-5.3-codex`) |
| `reasoning_mode` | Reasoning mode: `low/medium/high/xhigh` |
| `image_model` | Default model for `.cimg` |
| `approval_mode` | Approval behavior (`default/plan/auto-edit/yolo`) |
| `openai_api_key` | API key |
| `openai_base_url` | Base URL for OpenAI-compatible API |

---

## Language Switch

- [Русская документация](https://github.com/justidev-heroku/justi-modules/blob/main/Readme/CodexCLI_ru.md)

---

## License

MIT · [@justidev](https://t.me/justidev)
