# JellyColor — EN

[![Telegram](https://img.shields.io/badge/Telegram-@justidev-2CA5E0?logo=telegram&logoColor=white)](https://t.me/justidev)

**JellyColor** is a module for [Heroku](https://github.com/coddrago/Heroku) that allows you to recolor stickers and custom emojis, apply color gradients, and generate new text-based stickers/emojis from templates with custom font support.

Current version: **v3.7.0**.

---

## Installation

```bash
.dlm https://raw.githubusercontent.com/justidev-heroku/justi-modules/main/modules/JellyColor.py
```

---

## Features

- **High-Fidelity Gradient Overlays**: Apply gradients to static WebP images/stickers using HSV Value-luminosity mapping. This fully preserves shading, textures, and original highlights while preventing color fading on vibrant elements (like red or blue).
- **Custom Gradients**: Add and save custom multi-color gradients to the database, specifying their layout direction (horizontal, vertical, diagonal). Custom gradients are automatically integrated into the inline menus.
- **Fully Asynchronous**: Resource-heavy tasks (decompression, image processing, Lottie compression) run in background threads to keep the userbot interface non-blocking.
- **Direct Chat Preview**: Template previews are sent directly to the active chat instead of Saved Messages, and deleted automatically once confirmed.
- **Automatic Replacement (Fallback)**: If you attempt to create a stickerpack with a short_name you already own, the module automatically replaces old stickers with the new ones.
- Recolor static (WEBP) and animated (TGS) stickers/emojis into single solid colors or gradients.
- Interactive inline constructor `.jt` for generating stickers/emojis from text templates.
- Color choice: 12 premium presets, custom HEX entry, or gradient configurations.
- Support for uploading and managing custom fonts (`.ttf`, `.otf`) stored persistently.

---

## Commands

| Command | Description |
|---|---|
| `.j <HEX or gradient>` | Recolor the sticker you replied to |
| `.jc <HEX or gradient>` | Recolor and create a new sticker pack |
| `.jt` | Launch the inline wizard to create emojis from text templates |
| `.jaddfont <title>` | Add a custom font (replying to a `.ttf`/`.otf` file) |
| `.jdelfont <title>` | Delete a custom font |
| `.jfonts` | List installed custom fonts |
| `.jaddgrad <name> <HEX,HEX,...> [h/v/d/dr]` | Save a custom color gradient |
| `.jdelgrad <name>` | Delete a custom color gradient |
| `.jgrads` | List all available system and custom gradients |
| `.jstats` | Statistics of creation operations |
| `.jdel <short_name>` | Delete a pack entry from statistics |
| `.jexport` | Export creation stats to JSON |

---

## Language switcher

- [Russian docs](https://github.com/justidev-heroku/justi-modules/blob/main/Readme/JellyColor_ru.md)

---

## License

MIT · [@justidev](https://t.me/justidev)
