# JellyColor — EN

[![Telegram](https://img.shields.io/badge/Telegram-@justidev-2CA5E0?logo=telegram&logoColor=white)](https://t.me/justidev)

![JellyColor Banner](https://raw.githubusercontent.com/justidev-heroku/justi-modules/refs/heads/main/assets/JellyColor.jpg)

**JellyColor** is a module for [Heroku](https://github.com/coddrago/Heroku) that allows you to recolor stickers and custom emojis into any solid color, and generate new text-based stickers/emojis from templates with custom font support.

Current version: **v4.6.0**.

---

## Installation

```bash
.dlm https://raw.githubusercontent.com/justidev-heroku/justi-modules/main/modules/JellyColor.py
```

---

## Features

- **High-Fidelity Recoloring**: Recolor static (WEBP) and animated (TGS) stickers/emojis into a single solid color while preserving shading, textures, highlights, and original depth (luminosity mapping). Correctly handles fills, strokes, and gradient-fill shapes.
- **Color History**: Recently used colors appear as a dedicated button row in the picker — repeat a color in one tap.
- **Auto Pack Naming**: A "🎲 Auto" button generates a valid short_name for you — no need to come up with one manually.
- **Fully Asynchronous**: Resource-heavy tasks (decompression, image processing, Lottie compression) run in background threads to keep the userbot interface non-blocking.
- **Scale Preview**: In the `.jt` wizard you can tune the text scale and send a preview of the first emojis to Saved Messages before generating.
- **Automatic Replacement (Fallback)**: If you attempt to create a stickerpack with a short_name you already own, the module offers to recreate the pack or append to the existing one.
- Interactive inline constructor `.jt` for generating stickers/emojis from text templates.
- Color choice: 12 premium presets or custom HEX entry.
- Support for uploading and managing custom fonts (`.ttf`, `.otf`) stored persistently.

---

## Commands

| Command | Description |
|---|---|
| `.j` | Recolor the sticker/emoji you replied to (inline color wizard) |
| `.jc <HEX>` | Quickly recolor and create a new sticker pack |
| `.jt` | Launch the inline wizard to create emojis from text templates |
| `.jaddfont <title>` | Add a custom font (replying to a `.ttf`/`.otf` file) |
| `.jdelfont <title>` | Delete a custom font |
| `.jfonts` | List installed custom fonts |
| `.jstats` | Statistics of creation operations |
| `.jdel <short_name>` | Delete a pack entry from statistics |
| `.jexport` | Export creation stats to JSON |

---

## Language switcher

- [Russian docs](https://github.com/justidev-heroku/justi-modules/blob/main/Readme/JellyColor_ru.md)

---

## License

MIT · [@justidev](https://t.me/justidev)
