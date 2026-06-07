# JellyParser — EN

[![Telegram](https://img.shields.io/badge/Telegram-@justidev-2CA5E0?logo=telegram&logoColor=white)](https://t.me/justidev)

**JellyParser** is a module for [Heroku](https://github.com/coddrago/Heroku) that lets you parse existing emoji packs, find emojis with text placeholders (TextGroup/Shape Layers), and automatically pack them into a new set under a unique name.

---

## Installation

```bash
.dlm https://raw.githubusercontent.com/justidev-heroku/justi-modules/main/modules/JellyParser.py
```

---

## Features

- **Lottie Structure Analysis**: Downloads TGS files from the specified emoji set and checks for `TextGroup` elements or shape layers representing text (e.g., `ty: 4`).
- **Template Collection**: Filters and gathers only the customizable text emojis, separating them from static/regular ones.
- **Unique Naming**: Automatically finds the first unused short name formatted as `mainemoji_jellycolor{n}_by_justidev`, where `n` is a sequential number.
- **Asynchronous Processing**: Downloading, parsing, and packing operations run asynchronously in background tasks.

---

## Commands

| Command | Description |
|---|---|
| `.jparse <link>` | Parse an emoji pack (or reply to a message containing a link) |

---

## Language switcher

- [Russian docs](https://github.com/justidev-heroku/justi-modules/blob/main/Readme/JellyParser_ru.md)

---

## License

MIT · [@justidev](https://t.me/justidev)
