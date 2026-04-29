# CodexCLI — RU

[![Telegram](https://img.shields.io/badge/Telegram-@justidev-2CA5E0?logo=telegram&logoColor=white)](https://t.me/justidev)

![CodexCLI Banner](https://raw.githubusercontent.com/sepiol026-wq/GoyModules/refs/heads/main/assets/CodexCLI.png)

**CodexCLI** — модуль для [Heroku](https://github.com/coddrago/Heroku), который интегрирует OpenAI Codex CLI прямо в Telegram.

Актуальная ветка: **v1.4.0**.

---

## Установка

```bash
.dlm https://raw.githubusercontent.com/justidev-heroku/justi-modules/main/modules/CodexCLI.py
```

или:

```bash
.addrepo https://github.com/justidev-heroku/justi-modules/modules
```

---

## Основные возможности

- Codex CLI внутри Telegram (`.cdx` + slash-алиасы вроде `/status` через `.cdx /status`)
- Streaming-статус выполнения с обновлённым UI
- Поддержка `reasoning_mode`: `low | medium | high | xhigh`
- Генерация изображений через `.cimg` (`gpt-image-1` / `gpt-image-2`)
- Inline-контролы для `.cimg`: перегенерация, меню выбора модели, показ полного промпта

---

## Команды

| Команда | Описание |
|---|---|
| `.cdx <запрос>` | Отправить запрос в Codex |
| `.cdxpatch <правка>` | Дополнить/исправить предыдущий запрос |
| `.cdxstop` | Остановить активный запрос |
| `.cdxclear` | Очистить память текущего чата |
| `.cdxreset` | Полная очистка памяти |
| `.cdxmodel [name]` | Показать/сменить модель Codex |
| `.cdxprompt <text>` | Установить системный промпт |
| `.cimg <prompt>` | Сгенерировать изображение |

---

## `.cimg` UI (v1.4.0)

После генерации доступны inline-кнопки:

- `🔄 Перегенерировать`
- `🎛 Выбрать модель` → подменю с `1️⃣ gpt-image-1` и `2️⃣ gpt-image-2`
- `◀️ Назад` (возврат из меню выбора модели)
- `📄 Показать промпт` (если промпт длиннее 512 символов)

Поведение длинного промпта:

- в подписи показываются первые 512 символов;
- полный промпт отправляется `.txt` по кнопке `Показать промпт`.

Выбор модели в кнопках сохраняется в `cfg image_model` как новый дефолт.

---

## Авторизация

| Команда | Описание |
|---|---|
| `.cdxauth status` | Проверить статус авторизации |
| `.cdxauth auth` | Device login через ChatGPT |
| `.cdxauth apikey <key>` | Сохранить API ключ |
| `.cdxauth codex` | Привязать codex-login через API key |
| `.cdxauth clear` | Очистить auth-данные |

---

## Конфигурация (ключевое)

| Параметр | Описание |
|---|---|
| `codex_model` | Модель Codex (например `gpt-5.3-codex`) |
| `reasoning_mode` | Режим reasoning: `low/medium/high/xhigh` |
| `image_model` | Дефолт-модель для `.cimg` |
| `approval_mode` | Режим подтверждений (`default/plan/auto-edit/yolo`) |
| `openai_api_key` | API key |
| `openai_base_url` | Базовый URL OpenAI-совместимого API |

---

## Переключение языка

- [English docs](https://github.com/justidev-heroku/justi-modules/blob/main/Readme/CodexCLI_en.md)

---

## Лицензия

MIT · [@justidev](https://t.me/justidev)
