# JellyParser — RU

[![Telegram](https://img.shields.io/badge/Telegram-@justidev-2CA5E0?logo=telegram&logoColor=white)](https://t.me/justidev)

**JellyParser** — модуль для [Heroku](https://github.com/coddrago/Heroku), который позволяет парсить существующие эмодзи-паки, находить в них стикеры/эмодзи с текстовыми полями (TextGroup/Shape Layers) и автоматически собирать их в новый пак с уникальным именем.

---

## Установка

```bash
.dlm https://raw.githubusercontent.com/justidev-heroku/justi-modules/main/modules/JellyParser.py
```

---

## Основные возможности

- **Анализ анимации (Lottie)**: Скачивает TGS файлы из указанного эмодзи-пака и анализирует их структуру на наличие групп `TextGroup` или текстовых Shape-слоев (например, `ty: 4`).
- **Сборка шаблонов**: Отбирает только те эмодзи, которые поддерживают кастомизацию текста, и пересобирает их в новый пак.
- **Уникальное имя**: Автоматически ищет первое незанятое имя вида `mainemoji_jellycolor{n}_by_justidev`, где `n` — порядковый номер пака.
- **Асинхронность**: Процесс загрузки, парсинга и повторной сборки выполняется полностью асинхронно в фоновом режиме.

---

## Команды

| Команда | Описание |
|---|---|
| `.jparse <ссылка>` | Парсинг эмодзи-пака (или ответом на сообщение со ссылкой) |

---

## Переключение языка

- [English docs](https://github.com/justidev-heroku/justi-modules/blob/main/Readme/JellyParser_en.md)

---

## Лицензия

MIT · [@justidev](https://t.me/justidev)
