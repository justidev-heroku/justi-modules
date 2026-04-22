# CodexCLI — RU

[![Telegram](https://img.shields.io/badge/Telegram-@justidev-2CA5E0?logo=telegram&logoColor=white)](https://t.me/justidev)

![CodexCLI Banner](https://raw.githubusercontent.com/sepiol026-wq/GoyModules/refs/heads/main/assets/CodexCLI.png)

**CodexCLI** — модуль для [Heroku](https://github.com/coddrago/Heroku), интегрирующий OpenAI Codex CLI прямо в Telegram. Поддерживает авторизацию через ChatGPT OAuth, стриминг ответов в реальном времени и выполнение Telegram-действий.  
**Forked of [QwenCLI](https://github.com/sepiol026-wq/GoyModules/blob/main/QwenCLI.py)**

---

## Установка модуля

```
.dlm https://raw.githubusercontent.com/justidev-heroku/justi-modules/main/modules/CodexCLI.py
```

или через репозиторий:

```
.addrepo https://github.com/justidev-heroku/justi-modules/modules
```

---

## Требования

- [Heroku](https://github.com/coddrago/Heroku)
- OpenAI API ключ / ChatGPT аккаунт
- Установленный `codex` CLI на хосте

> Если `codex CLI` не установлен на хосте — используй `.cdxinstall` для автоматической установки локального Runtime.

---

## Установка Runtime

| Команда | Описание |
|---------|----------|
| `.cdxinstall` | Автоматически установить локальный Runtime Codex CLI |

---

## Авторизация

| Команда | Описание |
|---------|----------|
| `.cdxauth status` | Показать текущий статус авторизации |
| `.cdxauth auth` | Войти через ChatGPT OAuth (device flow) |
| `.cdxauth easy` | Автоматический вход с fallback на API key |
| `.cdxauth apikey <key>` | Задать OpenAI API ключ |
| `.cdxauth clear` | Сбросить все данные авторизации |

---

## Основные команды

| Команда | Описание |
|---------|----------|
| `.cdx <запрос>` | Отправить запрос в Codex |
| `.cdxpatch <правка>` | Уточнить или дополнить предыдущий запрос |
| `.cdxstop` | Остановить текущий запрос |
| `.cdxclear` | Очистить историю диалога в чате |
| `.cdxmodel [модель]` | Показать или сменить модель |
| `.cdxprompt <текст>` | Установить системный промпт |

---

## Конфигурация

| Параметр | Описание |
|----------|----------|
| `codex_model` | Модель (например `gpt-5.3-codex`, `gpt-5.4`) |
| `approval_mode` | Режим подтверждений: `yolo`, `plan`, `auto-edit`, `default` |
| `system_instruction` | Системный промпт по умолчанию |
| `openai_base_url` | Кастомный API endpoint (оставь пустым при ChatGPT OAuth) |

---

## Переключение языка

- [English docs](codexcli_en.md)

---

## Лицензия

MIT · [@justidev](https://t.me/justidev)
