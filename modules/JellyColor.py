# ╔══════════════════════════════════════════════════════════════════╗
# ║                        🎨 JellyColor v4.5.1                      ║
# ║           Перекраска стикеров/эмодзи + текстовые шаблоны         ║
# ║  v4.5.1: Минорное обновление: Убран пак «All in All»             ║
#            и фикс пака »Чёрные»                                    ║
# ╚══════════════════════════════════════════════════════════════════╝
#
# MIT License
#
# Copyright (c) 2026 justidev
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# meta developer: @justidev
# meta banner: https://raw.githubusercontent.com/justidev-heroku/justi-modules/refs/heads/main/assets/JellyColor.jpg
# requires: Pillow fonttools orjson
#
# modification: JellyColor manual scale adjustment and preview feature

__version__ = (4, 5, 1)

import asyncio
import glob
import gzip
import hashlib
import io
import json
import logging
import math
import os
import re
import time
import traceback
import urllib.request
import uuid
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageChops

from telethon.tl import functions, types
from telethon.tl.types import (
    DocumentAttributeSticker,
    DocumentAttributeCustomEmoji,
    DocumentAttributeImageSize,
    InputStickerSetShortName,
    InputStickerSetID,
    InputStickerSetEmpty,
    Message,
    MessageEntityCustomEmoji,
)
from telethon.errors import FloodWaitError

try:
    from fontTools.ttLib import TTFont
    from fontTools.pens.recordingPen import DecomposingRecordingPen
    HAS_FONTTOOLS = True
except ImportError:
    HAS_FONTTOOLS = False

from .. import loader, utils

logger = logging.getLogger("JellyColor")

try:
    import orjson
    HAS_ORJSON = True
except ImportError:
    HAS_ORJSON = False

_FONT_CACHE = {}


def _get_cached_font(font_path: str):
    ft = _FONT_CACHE.get(font_path)
    if ft is None:
        ft = TTFont(font_path)
        _FONT_CACHE[font_path] = ft
    return ft


def json_loads(data: bytes) -> dict:
    if HAS_ORJSON:
        return orjson.loads(data)
    return json.loads(data.decode("utf-8") if isinstance(data, bytes) else data)


def json_dumps(obj: dict, indent: bool = False) -> bytes:
    if HAS_ORJSON:
        if indent:
            return orjson.dumps(obj, option=orjson.OPT_INDENT_2)
        return orjson.dumps(obj)
    if indent:
        return json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
    return json.dumps(obj, separators=(",", ":")).encode("utf-8")


PRESET_COLORS: Dict[str, str] = {
    "🔴 Красный":    "#FF3B30",
    "🟠 Оранжевый":  "#FF9500",
    "🟡 Жёлтый":     "#FFCC00",
    "🟢 Зелёный":    "#34C759",
    "🔵 Синий":      "#007AFF",
    "🟣 Фиолетовый": "#AF52DE",
    "⚫️ Чёрный":     "#1C1C1E",
    "⚪️ Белый":      "#F2F2F7",
    "🩷 Розовый":    "#FF2D55",
    "🩵 Голубой":    "#5AC8FA",
    "🟤 Коричневый": "#A2845E",
    "🩶 Серый":      "#8E8E93",
}

PE = {
    "ok":      "5870633910337015697",
    "err":     "5870657884844462243",
    "brush":   "6050679691004612757",
    "pack":    "5778672437122045013",
    "palette": "5870676941614354370",
    "link":    "5769289093221454192",
    "stats":   "5870921681735781843",
    "clock":   "5983150113483134607",
    "sticker": "5886285355279193209",
    "write":   "5870753782874246579",
    "media":   "6035128606563241721",
    "eye":     "6037397706505195857",
    "trash":   "5870875489362513438",
    "export":  "5963103826075456248",
    "info":    "6028435952299413210",
    "back":    "5445362436418859744",
}

# ─── Gradient presets ────────────────────────────────────────────────────────
GRADIENT_PRESETS = [
    {"id":"sunset",    "name":"🌅 Закат",      "colors":["#FF416C","#FF4B2B"], "dir":"d"},
    {"id":"ocean",     "name":"🌊 Океан",      "colors":["#1A2980","#26D0CE"], "dir":"dr"},
    {"id":"aurora",    "name":"📣 Аврора",     "colors":["#00C9FF","#92FE9D"], "dir":"d"},
    {"id":"fire",      "name":"🔥 Огонь",      "colors":["#F12711","#F5AF19"], "dir":"v"},
    {"id":"sakura",    "name":"🌸 Сакура",     "colors":["#EC008C","#FC6767"], "dir":"d"},
    {"id":"galaxy",    "name":"🌌 Галактика",  "colors":["#3F5EFB","#FC466B"], "dir":"dr"},
    {"id":"forest",    "name":"🌿 Лес",        "colors":["#11998E","#38EF7D"], "dir":"v"},
    {"id":"neon",      "name":"⚡ Неон",       "colors":["#8A2387","#E94057","#F27121"], "dir":"h"},
    {"id":"gold",      "name":"👑 Золото",     "colors":["#BF953F","#FCF6BA","#B38728","#FBF5B7"], "dir":"d"},
    {"id":"candy",     "name":"🍭 Конфета",    "colors":["#EE9CA7","#FFDDE1"], "dir":"dr"},
    {"id":"cyberpunk", "name":"🔮 Киберпанк",  "colors":["#00F2FE","#4FACFE","#F35588"], "dir":"d"},
    {"id":"magma",     "name":"🌋 Магма",      "colors":["#000000","#7E0000","#FF3B00","#FFE600"], "dir":"v"},
]

TEMPLATE_SETS = [
    {"title": "🖤 Чёрные", "short_name": "mainemoji_jellycolor53_by_justidev"},
    {"title": "🖤 Чёрные 2", "short_name": "mainemoji_jellycolor5_by_justidev"},
    {"title": "🎨 Цветные", "short_name": "mainemoji_jellycolor4_by_justidev"},
    {"title": "🗂 Паспорт", "short_name": "mainemoji_jellycolor9_by_justidev"},
    {"title": "✨ Эксклюзивные", "short_name": "mainemoji_jellycolor10_by_justidev"},
    {"title": "✨ Эксклюзивные 2", "short_name": "mainemoji_jellycolor37_by_justidev"},
    {"title": "🍹 Секс на пляже", "short_name": "mainemoji_jellycolor51_by_justidev"},
]

TEMPLATE_PLACEHOLDER = "jelly"

SESSION_TTL = 600
CACHE_DIR = "/tmp/jelly_cache"
MAX_TGS_SIZE = 63 * 1024
RECOLOR_CONCURRENCY = 32

os.makedirs(CACHE_DIR, exist_ok=True)


def pe(emoji: str, eid: str) -> str:
    return '<tg-emoji emoji-id="' + eid + '">' + emoji + '</tg-emoji>'


def hex_to_rgb(hex_color: str):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(r: int, g: int, b: int) -> str:
    return "#{:02X}{:02X}{:02X}".format(r, g, b)





# ─── Image tinting ────────────────────────────────────────────────────────────

def tint_image(img: Image.Image, hex_color: str) -> Image.Image:
    r_target, g_target, b_target = hex_to_rgb(hex_color)
    img = img.convert("RGBA")
    r, g, b, ao = img.split()
    max_rg = ImageChops.lighter(r, g)
    val = ImageChops.lighter(max_rg, b)
    lut_r = [int(i * r_target / 255) for i in range(256)]
    lut_g = [int(i * g_target / 255) for i in range(256)]
    lut_b = [int(i * b_target / 255) for i in range(256)]
    rn = val.point(lut_r)
    gn = val.point(lut_g)
    bn = val.point(lut_b)
    return Image.merge("RGBA", (rn, gn, bn, ao))


def create_gradient_image(width: int, height: int, colors_hex: list, direction: str) -> Image.Image:
    n = len(colors_hex)
    rgbs = [hex_to_rgb(c) for c in colors_hex]

    if direction == "h":
        tw, th = 64, 1
        pixels = []
        for x in range(tw):
            t = x / (tw - 1)
            t = max(0.0, min(1.0, t))
            scaled = t * (n - 1)
            idx = min(int(scaled), n - 2)
            f = scaled - idx
            r1, g1, b1 = rgbs[idx]
            r2, g2, b2 = rgbs[idx + 1]
            r = int(r1 + (r2 - r1) * f)
            g = int(g1 + (g2 - g1) * f)
            b = int(b1 + (b2 - b1) * f)
            pixels.append((r, g, b))
        img = Image.new("RGB", (tw, th))
        img.putdata(pixels)
        return img.resize((width, height), Image.BILINEAR)

    elif direction == "v":
        tw, th = 1, 64
        pixels = []
        for y in range(th):
            t = y / (th - 1)
            t = max(0.0, min(1.0, t))
            scaled = t * (n - 1)
            idx = min(int(scaled), n - 2)
            f = scaled - idx
            r1, g1, b1 = rgbs[idx]
            r2, g2, b2 = rgbs[idx + 1]
            r = int(r1 + (r2 - r1) * f)
            g = int(g1 + (g2 - g1) * f)
            b = int(b1 + (b2 - b1) * f)
            pixels.append((r, g, b))
        img = Image.new("RGB", (tw, th))
        img.putdata(pixels)
        return img.resize((width, height), Image.BILINEAR)

    else:
        tw, th = 64, 64
        pixels = []
        for y in range(th):
            for x in range(tw):
                if direction in ("d", "dl"):
                    t = (x + y) / (tw + th - 2)
                elif direction == "dr":
                    t = ((tw - 1 - x) + y) / (tw + th - 2)
                else:
                    t = (x + y) / (tw + th - 2)
                
                t = max(0.0, min(1.0, t))
                scaled = t * (n - 1)
                idx = min(int(scaled), n - 2)
                f = scaled - idx
                r1, g1, b1 = rgbs[idx]
                r2, g2, b2 = rgbs[idx + 1]
                r = int(r1 + (r2 - r1) * f)
                g = int(g1 + (g2 - g1) * f)
                b = int(b1 + (b2 - b1) * f)
                pixels.append((r, g, b))
        img = Image.new("RGB", (tw, th))
        img.putdata(pixels)
        return img.resize((width, height), Image.BILINEAR)


def tint_image_gradient(img: Image.Image, colors_hex: list, direction: str) -> Image.Image:
    img = img.convert("RGBA")
    w, h = img.size
    r, g, b, ao = img.split()
    max_rg = ImageChops.lighter(r, g)
    val = ImageChops.lighter(max_rg, b)
    grad_img = create_gradient_image(w, h, colors_hex, direction)
    val_rgb = Image.merge("RGB", (val, val, val))
    tinted_rgb = ImageChops.multiply(grad_img, val_rgb)
    tr, tg, tb = tinted_rgb.split()
    return Image.merge("RGBA", (tr, tg, tb, ao))


# ─── Lottie gradient ──────────────────────────────────────────────────────────

def _sample_gradient(t: float, colors_hex: list) -> Tuple[float, float, float]:
    """Сэмплирует цвет градиента в позиции t ∈ [0, 1].
    t=0 → первый цвет (обычно тёмный), t=1 → последний (светлый).
    """
    n = len(colors_hex)
    if n == 1:
        r, g, b = hex_to_rgb(colors_hex[0])
        return r / 255, g / 255, b / 255
    t = max(0.0, min(1.0, t))
    scaled = t * (n - 1)
    i = min(int(scaled), n - 2)
    f = scaled - i
    r1, g1, b1 = hex_to_rgb(colors_hex[i])
    r2, g2, b2 = hex_to_rgb(colors_hex[i + 1])
    return (
        (r1 + (r2 - r1) * f) / 255,
        (g1 + (g2 - g1) * f) / 255,
        (b1 + (b2 - b1) * f) / 255,
    )


def _collect_lottie_brightnesses(lottie_json: dict) -> Tuple[float, float]:
    """Проходит весь Lottie JSON и собирает глобальный диапазон яркости всех цветов.
    Возвращает (b_min, b_max) для нормализации.
    """
    bs: List[float] = []

    def _rgb_brightness(rgb: list) -> Optional[float]:
        if len(rgb) >= 3 and isinstance(rgb[0], (int, float)):
            return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
        return None

    def _walk(obj):
        if isinstance(obj, dict):
            ty = obj.get("ty", "")
            if ty in ("fl", "st"):
                c = obj.get("c", {})
                if isinstance(c, dict):
                    k = c.get("k")
                    a = c.get("a", 0)
                    if a == 0 and isinstance(k, list):
                        bv = _rgb_brightness(k)
                        if bv is not None:
                            bs.append(bv)
                    elif a == 1 and isinstance(k, list):
                        for kf in k:
                            if isinstance(kf, dict):
                                s = kf.get("s")
                                bv = _rgb_brightness(s) if isinstance(s, list) else None
                                if bv is not None:
                                    bs.append(bv)
            elif ty in ("gf", "gs"):
                g = obj.get("g", {})
                if isinstance(g, dict):
                    p = int(g.get("p", 0))
                    kp = g.get("k", {})
                    if isinstance(kp, dict):
                        raw = kp.get("k")
                        if isinstance(raw, list) and raw and isinstance(raw[0], (int, float)):
                            i = 0
                            while i + 3 < p * 4 and i + 3 < len(raw):
                                bv = _rgb_brightness(raw[i + 1: i + 4])
                                if bv is not None:
                                    bs.append(bv)
                                i += 4
                        elif isinstance(raw, list):
                            for kf in raw:
                                if isinstance(kf, dict):
                                    s = kf.get("s")
                                    if isinstance(s, list) and s and isinstance(s[0], (int, float)):
                                        i = 0
                                        while i + 3 < p * 4 and i + 3 < len(s):
                                            bv = _rgb_brightness(s[i + 1: i + 4])
                                            if bv is not None:
                                                bs.append(bv)
                                            i += 4
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(lottie_json)
    if not bs:
        return 0.0, 1.0
    return min(bs), max(bs)


def apply_gradient_lottie(lottie_json: dict, gradient: dict) -> dict:
    """Умная перекраска TGS с градиентом.

    v3.1 — полностью переработан:
    Старый алгоритм (v3) заменял ВСЕ fl/st/gf/gs одним градиентным fill —
    это уничтожало внутреннюю структуру эмодзи (тени, блики, детали).

    Новый алгоритм — brightness remapping:
    1. Собирает все цвета по всему Lottie и находит глобальный диапазон яркости
    2. Для каждого цвета вычисляет его нормализованную яркость t ∈ [0, 1]
    3. Заменяет цвет на gradient.sample(t) — сэмпл градиента в этой позиции
    4. Тёмные детали → тёмный конец градиента; светлые → светлый конец
    5. Все внутренние соотношения яркостей (тени, блики) сохраняются
    6. Для gradient fills (gf/gs) — каждый стоп ремапируется отдельно
    7. Для анимированных keyframes — каждый кадр ремапируется (поддержка s-only формата)
    """
    colors_hex = gradient["colors"]
    b_min, b_max = _collect_lottie_brightnesses(lottie_json)
    b_range = b_max - b_min if b_max > b_min else 1.0

    def _t(rgb: list) -> float:
        """Нормализованная яркость цвета → позиция в градиенте [0, 1]."""
        if len(rgb) < 3 or not isinstance(rgb[0], (int, float)):
            return 0.5
        bv = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
        return (bv - b_min) / b_range

    def _remap(rgb: list) -> list:
        """Ремапирует [r,g,b,?] в цвет градиента по яркости. Alpha сохраняется."""
        nr, ng, nb = _sample_gradient(_t(rgb), colors_hex)
        alpha = rgb[3] if len(rgb) > 3 else 1.0
        return [nr, ng, nb, alpha]

    def _remap_grad_stops(raw: list, p: int) -> list:
        """Ремапирует цветовые стопы gradient fill/stroke по яркости.
        Alpha-стопы (после p*4) не трогаются.
        """
        color_len = p * 4
        if len(raw) < color_len:
            color_len = (len(raw) // 4) * 4
        new_raw = list(raw)
        i = 0
        while i + 3 < color_len:
            nr, ng, nb = _sample_gradient(_t(new_raw[i + 1: i + 4]), colors_hex)
            new_raw[i + 1] = nr
            new_raw[i + 2] = ng
            new_raw[i + 3] = nb
            i += 4
        return new_raw

    def _recolor_prop(prop: dict) -> None:
        """Ремапирует color-property {a, k} fl/st шейпа."""
        if not isinstance(prop, dict):
            return
        k = prop.get("k")
        if k is None:
            return
        if isinstance(k, list):
            if len(k) >= 3 and isinstance(k[0], (int, float)):
                prop["k"] = _remap(k)
            else:
                for kf in k:
                    if not isinstance(kf, dict):
                        continue
                    vs = kf.get("s")
                    if isinstance(vs, list) and len(vs) >= 3 and isinstance(vs[0], (int, float)):
                        kf["s"] = _remap(vs)
                    ve = kf.get("e")
                    if isinstance(ve, list) and len(ve) >= 3 and isinstance(ve[0], (int, float)):
                        kf["e"] = _remap(ve)

    def _recolor_grad_obj(g_obj: dict) -> None:
        """Ремапирует gradient-объект {p, k} gf/gs шейпа."""
        if not isinstance(g_obj, dict):
            return
        p = int(g_obj.get("p", 0))
        if p == 0:
            return
        k_prop = g_obj.get("k")
        if not isinstance(k_prop, dict):
            return
        raw = k_prop.get("k")
        if raw is None:
            return
        if isinstance(raw, list) and raw and isinstance(raw[0], (int, float)):
            k_prop["k"] = _remap_grad_stops(raw, p)
        elif isinstance(raw, list):
            for kf in raw:
                if not isinstance(kf, dict):
                    continue
                for field in ("s", "e"):
                    val = kf.get(field)
                    if isinstance(val, list) and val and isinstance(val[0], (int, float)):
                        kf[field] = _remap_grad_stops(val, p)

    def _walk(obj):
        if isinstance(obj, dict):
            ty = obj.get("ty", "")
            if ty in ("fl", "st"):
                _recolor_prop(obj.get("c", {}))
                return
            if ty in ("gf", "gs"):
                _recolor_grad_obj(obj.get("g"))
                return
            # Solid color layer
            sc = obj.get("sc")
            if isinstance(sc, str) and sc.startswith("#"):
                try:
                    sr, sg, sb = hex_to_rgb(sc)
                    nr, ng, nb = _sample_gradient(_t([sr / 255, sg / 255, sb / 255]), colors_hex)
                    obj["sc"] = rgb_to_hex(int(nr * 255), int(ng * 255), int(nb * 255))
                except Exception:
                    pass
            # Text layer
            t_obj = obj.get("t")
            if isinstance(t_obj, dict):
                d_obj = t_obj.get("d")
                if isinstance(d_obj, dict):
                    for kf in d_obj.get("k", []):
                        if isinstance(kf, dict):
                            s_obj = kf.get("s", {})
                            if isinstance(s_obj, dict):
                                for field in ("fc", "sc"):
                                    col = s_obj.get(field)
                                    if isinstance(col, list) and len(col) >= 3:
                                        nr, ng, nb = _sample_gradient(_t(col), colors_hex)
                                        alpha = col[3] if len(col) > 3 else 1.0
                                        s_obj[field] = [nr, ng, nb, alpha]
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(lottie_json)
    return lottie_json


# ─── Lottie tinting ───────────────────────────────────────────────────────────

def _recolor_rgb(val: list, nr: float, ng: float, nb: float) -> list:
    """Перекрашивает [r,g,b] или [r,g,b,a] через grayscale-умножение. Alpha сохраняется."""
    if len(val) < 3 or not isinstance(val[0], (int, float)):
        return val
    gray = 0.299 * val[0] + 0.587 * val[1] + 0.114 * val[2]
    alpha = val[3] if len(val) > 3 else 1.0
    return [nr * gray, ng * gray, nb * gray, alpha]


def _recolor_gradient_stops(raw: list, p: int, nr: float, ng: float, nb: float) -> list:
    """
    Перекрашивает массив Lottie gradient stops на месте (возвращает новый список).

    Формат Lottie градиента (НЕ просто [off,r,g,b,...]):
      Первые p*4 значений — цветовые стопы: [off, r, g, b,  off, r, g, b, ...]
      Следующие p*2 значений (если есть) — альфа-стопы: [off, a,  off, a, ...]

    Цветовые стопы перекрашиваются через grayscale-умножение.
    Альфа-стопы НЕ трогаются (они управляют прозрачностью отдельно).
    """
    color_len = p * 4
    if len(raw) < color_len:
        # Fallback: нестандартный формат — красим по 4 значения
        color_len = (len(raw) // 4) * 4

    new_raw = list(raw)
    i = 0
    while i + 3 < color_len:
        off = new_raw[i]
        gray = 0.299 * new_raw[i+1] + 0.587 * new_raw[i+2] + 0.114 * new_raw[i+3]
        new_raw[i+1] = nr * gray
        new_raw[i+2] = ng * gray
        new_raw[i+3] = nb * gray
        i += 4
    # Alpha-блок (индексы color_len..end) — не трогаем
    return new_raw


def tint_lottie(lottie_json: dict, hex_color: str) -> dict:
    """
    Полная перекраска TGS: fl, st, gf, gs (включая анимированные keyframes).

    v3 fixes:
      • Stroke (ty=st) — v2 вообще не красила
      • Gradient fill/stroke (gf/gs) — v2 не красила вообще
      • Animated fl/st: v2 патчила только s, v3 патчит s (+ e в старом формате)
      • Animated gf/gs: v2 не красила вовсе
      • Solid color layer (поле sc="#rrggbb") — v2 не трогала
      • Text layer (t.d.k[].s.fc / .sc) — v2 не трогала

    v3.1 fix (ГЛАВНЫЙ БАГ):
      Lottie формат After Effects 2022+ использует keyframes ТОЛЬКО с полем 's'.
      Поле 'e' (end value) отсутствует во всех современных TGS-файлах Telegram.
      v3 пыталась патчить 'e' которого нет → анимированные цвета не красились.
      v3.1: патчит 's' всегда; 'e' — только если присутствует (AE < 2022).
    """
    r, g, b = hex_to_rgb(hex_color)
    nr, ng, nb = r / 255, g / 255, b / 255

    def _recolor_prop(prop: dict) -> None:
        """Перекрашивает color-property {a, k} — плоский цвет (fl/st).

        Поддерживает оба формата Lottie:
          - Старый (AE < 2022): keyframes с полями s и e
          - Новый (AE >= 2022): keyframes только с полем s (без e)
            В новом формате «end value» следующего keyframe = s следующего kf.
        """
        if not isinstance(prop, dict):
            return
        k = prop.get("k")
        if k is None:
            return
        if isinstance(k, list):
            if len(k) >= 3 and isinstance(k[0], (int, float)):
                # Static [r,g,b] или [r,g,b,a]
                prop["k"] = _recolor_rgb(k, nr, ng, nb)
            else:
                # Animated keyframes — патчим s (и e если есть, старый формат)
                for kf in k:
                    if not isinstance(kf, dict):
                        continue
                    # 's' — значение в начале этого keyframe (есть всегда кроме последнего sentinel)
                    val_s = kf.get("s")
                    if isinstance(val_s, list) and len(val_s) >= 3 and isinstance(val_s[0], (int, float)):
                        kf["s"] = _recolor_rgb(val_s, nr, ng, nb)
                    # 'e' — только в старом формате Lottie (AE < 2022)
                    val_e = kf.get("e")
                    if isinstance(val_e, list) and len(val_e) >= 3 and isinstance(val_e[0], (int, float)):
                        kf["e"] = _recolor_rgb(val_e, nr, ng, nb)

    def _recolor_grad_obj(g_obj: dict) -> None:
        """
        Перекрашивает gradient-объект {p, k} из gf/gs.
        g_obj["p"] — количество цветовых стопов (нужно для разделения цвет/альфа).
        g_obj["k"] — property-объект {a, k: [...stops...]}.

        Поддерживает оба Lottie формата:
          - Старый: keyframes с s и e
          - Новый (AE >= 2022): keyframes только с s (нет поля e)
        """
        if not isinstance(g_obj, dict):
            return
        p = int(g_obj.get("p", 0))
        if p == 0:
            return
        k_prop = g_obj.get("k")
        if not isinstance(k_prop, dict):
            return
        raw = k_prop.get("k")
        if raw is None:
            return

        if isinstance(raw, list) and raw and isinstance(raw[0], (int, float)):
            # Static gradient stops
            k_prop["k"] = _recolor_gradient_stops(raw, p, nr, ng, nb)
        elif isinstance(raw, list):
            # Animated keyframes: патчим поля s и e (e только в старом формате)
            for kf in raw:
                if not isinstance(kf, dict):
                    continue
                for field in ("s", "e"):
                    val = kf.get(field)
                    if isinstance(val, list) and val and isinstance(val[0], (int, float)):
                        kf[field] = _recolor_gradient_stops(val, p, nr, ng, nb)

    def _walk(obj):
        if isinstance(obj, dict):
            ty = obj.get("ty", "")

            # Shape fill — плоский цвет
            if ty == "fl":
                _recolor_prop(obj.get("c", {}))
                return

            # Shape stroke — плоский цвет (v2 пропускала!)
            if ty == "st":
                _recolor_prop(obj.get("c", {}))
                return

            # Gradient fill (v2 пропускала; v3 учитывает g.p для альфа-стопов)
            if ty == "gf":
                _recolor_grad_obj(obj.get("g"))
                return

            # Gradient stroke (v2 пропускала)
            if ty == "gs":
                _recolor_grad_obj(obj.get("g"))
                return

            # Solid color layer: поле "sc" = "#rrggbb" (layer ty=1 в Lottie — число)
            sc_val = obj.get("sc")
            if isinstance(sc_val, str) and sc_val.startswith("#"):
                try:
                    sr, sg, sb = hex_to_rgb(sc_val)
                    gray = 0.299 * sr/255 + 0.587 * sg/255 + 0.114 * sb/255
                    obj["sc"] = rgb_to_hex(
                        int(nr * gray * 255),
                        int(ng * gray * 255),
                        int(nb * gray * 255),
                    )
                except Exception:
                    pass

            # Text layer: t.d.k[i].s.fc (fill color) и .sc (stroke color)
            t_obj = obj.get("t")
            if isinstance(t_obj, dict):
                d_obj = t_obj.get("d")
                if isinstance(d_obj, dict):
                    for kf in d_obj.get("k", []):
                        if isinstance(kf, dict):
                            s_obj = kf.get("s", {})
                            if isinstance(s_obj, dict):
                                for field in ("fc", "sc"):
                                    col = s_obj.get(field)
                                    if isinstance(col, list) and len(col) >= 3:
                                        gray = 0.299 * col[0] + 0.587 * col[1] + 0.114 * col[2]
                                        alpha = col[3] if len(col) > 3 else 1.0
                                        s_obj[field] = [nr*gray, ng*gray, nb*gray, alpha]

            # Рекурсия по остальным полям
            for v in obj.values():
                _walk(v)

        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(lottie_json)
    return lottie_json


def get_dominant_lottie_color(lottie_json: dict) -> Optional[str]:
    """Извлекает первый значимый цвет из Lottie JSON.
    v3: сначала ищет fill (fl), потом stroke (st), потом gradient-fill (gf).
    Fallback-цвет из stroke нужен для stroke-only иконок (повар, кофе и т.п.).
    """
    def _extract_static(c_prop) -> Optional[str]:
        if not isinstance(c_prop, dict):
            return None
        k = c_prop.get("k", [])
        if isinstance(k, list) and len(k) >= 3 and isinstance(k[0], (int, float)):
            return rgb_to_hex(int(k[0]*255), int(k[1]*255), int(k[2]*255))
        # animated — берём первый keyframe
        if isinstance(k, list):
            for kf in k:
                if isinstance(kf, dict):
                    s = kf.get("s")
                    if isinstance(s, list) and len(s) >= 3 and isinstance(s[0], (int, float)):
                        return rgb_to_hex(int(s[0]*255), int(s[1]*255), int(s[2]*255))
        return None

    candidates: list = []  # (priority, color)

    def _walk(obj):
        if isinstance(obj, dict):
            ty = obj.get("ty", "")
            if ty == "fl":
                c = _extract_static(obj.get("c", {}))
                if c:
                    candidates.append((0, c))
            elif ty == "st":
                c = _extract_static(obj.get("c", {}))
                if c:
                    candidates.append((1, c))
            elif ty == "gf":
                g = obj.get("g", {})
                k = g.get("k", {}) if isinstance(g, dict) else {}
                raw = k.get("k", []) if isinstance(k, dict) else []
                if isinstance(raw, list) and len(raw) >= 4 and isinstance(raw[0], (int, float)):
                    candidates.append((2, rgb_to_hex(int(raw[1]*255), int(raw[2]*255), int(raw[3]*255))))
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(lottie_json)
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]


# ─── Sticker cache ────────────────────────────────────────────────────────────

def _cache_key(doc) -> str:
    return os.path.join(CACHE_DIR, f"{doc.id}.bin")


async def download_cached(client, doc) -> bytes:
    path = _cache_key(doc)
    if os.path.exists(path):
        try:
            with open(path, "rb") as f:
                return f.read()
        except Exception as e:
            logger.warning(f"Failed to read cache file {path}: {e}", exc_info=True)
    data = await client.download_media(doc, bytes)
    try:
        with open(path, "wb") as f:
            f.write(data)
    except Exception as e:
        logger.warning(f"Failed to write cache file {path}: {e}", exc_info=True)
    return data


# ─── TGS size guard ───────────────────────────────────────────────────────────

def compress_tgs(lottie: dict) -> bytes:
    raw = json_dumps(lottie)
    compressed = gzip.compress(raw, compresslevel=6)
    if len(compressed) <= MAX_TGS_SIZE:
        return compressed

    def _strip_names(obj):
        if isinstance(obj, dict):
            obj.pop("nm", None)
            obj.pop("mn", None)
            for v in obj.values():
                _strip_names(v)
        elif isinstance(obj, list):
            for item in obj:
                _strip_names(item)
    _strip_names(lottie)
    raw = json_dumps(lottie)
    compressed = gzip.compress(raw, compresslevel=6)
    if len(compressed) <= MAX_TGS_SIZE:
        return compressed

    def _round_floats(obj, precision=2):
        if isinstance(obj, float):
            return round(obj, precision) if math.isfinite(obj) else obj
        elif isinstance(obj, dict):
            for k, v in list(obj.items()):
                obj[k] = _round_floats(v, precision)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                obj[i] = _round_floats(v, precision)
        return obj
    _round_floats(lottie, 2)
    raw = json_dumps(lottie)
    compressed = gzip.compress(raw, compresslevel=6)
    if len(compressed) <= MAX_TGS_SIZE:
        return compressed

    # Try higher compression level
    compressed = gzip.compress(raw, compresslevel=9)
    if len(compressed) <= MAX_TGS_SIZE:
        return compressed

    # Try precision=1
    _round_floats(lottie, 1)
    raw = json_dumps(lottie)
    compressed = gzip.compress(raw, compresslevel=9)
    if len(compressed) <= MAX_TGS_SIZE:
        return compressed

    # Try precision=0
    _round_floats(lottie, 0)
    raw = json_dumps(lottie)
    compressed = gzip.compress(raw, compresslevel=9)
    return compressed



# ─── fonttools helpers ────────────────────────────────────────────────────────

_FONT_SEARCH = [
    "/usr/share/fonts/truetype/comfortaa/Comfortaa-Bold.ttf",
    "/usr/share/fonts/truetype/roboto/Roboto-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    "/usr/share/fonts/noto/NotoSans-Bold.ttf",
    "/usr/local/share/fonts/NotoSans-Bold.ttf",
]
_CACHED_FONT_PATH = "/tmp/jelly_color_comfortaa.ttf"
_FONT_CDN_URL = (
    "https://raw.githubusercontent.com/googlefonts/comfortaa/master/"
    "fonts/TTF/Comfortaa-Bold.ttf"
)


def _find_font():
    for p in _FONT_SEARCH:
        if os.path.exists(p): return p
    for p in glob.glob("/usr/share/fonts/**/*Bold*.ttf", recursive=True): return p
    found = glob.glob("/usr/share/fonts/**/*.ttf", recursive=True)
    return found[0] if found else None


def _ensure_font():
    log = logging.getLogger("JellyColor")
    comfortaa_system_path = _FONT_SEARCH[0]
    if os.path.exists(comfortaa_system_path):
        return comfortaa_system_path
    if os.path.exists(_CACHED_FONT_PATH) and os.path.getsize(_CACHED_FONT_PATH) > 50000:
        return _CACHED_FONT_PATH
    log.info("_ensure_font: downloading from CDN...")
    try:
        urllib.request.urlretrieve(_FONT_CDN_URL, _CACHED_FONT_PATH)
        if os.path.exists(_CACHED_FONT_PATH) and os.path.getsize(_CACHED_FONT_PATH) > 50000:
            return _CACHED_FONT_PATH
    except Exception as e:
        log.error(f"_ensure_font: download failed: {e}")
    p = _find_font()
    if p: return p
    return None



def _collect_path_verts(obj, target=None):
    if target is None:
        target = obj
    verts = []
    
    def get_group_transform(grp):
        items = grp.get("it", grp.get("shapes", []))
        for item in items:
            if item.get("ty") == "tr":
                return item
        return {}

    def transform_point(x, y, tr):
        def get_val(prop, default):
            if not prop:
                return default
            k = prop.get("k", default)
            if isinstance(k, list) and k and isinstance(k[0], dict):
                val = k[0].get("s", default)
                if not isinstance(val, list):
                    val = [val]
                return val
            return k

        ak = get_val(tr.get("a"), [0, 0])
        ax = float(ak[0]) if isinstance(ak, list) and len(ak) >= 1 else 0.0
        ay = float(ak[1]) if isinstance(ak, list) and len(ak) >= 2 else 0.0
        
        sk = get_val(tr.get("s"), [100, 100])
        sx = float(sk[0]) if isinstance(sk, list) and len(sk) >= 1 else 100.0
        sy = float(sk[1]) if isinstance(sk, list) and len(sk) >= 2 else 100.0
        
        rk = get_val(tr.get("r"), 0.0)
        if isinstance(rk, list):
            rk = float(rk[0]) if rk else 0.0
        else:
            rk = float(rk)
            
        pk = get_val(tr.get("p"), [0, 0])
        px = float(pk[0]) if isinstance(pk, list) and len(pk) >= 1 else 0.0
        py = float(pk[1]) if isinstance(pk, list) and len(pk) >= 2 else 0.0
        
        x1 = x - ax
        y1 = y - ay
        
        x2 = x1 * (sx / 100.0)
        y2 = y1 * (sy / 100.0)
        
        if rk != 0.0:
            rad = math.radians(rk)
            cos_r = math.cos(rad)
            sin_r = math.sin(rad)
            x3 = x2 * cos_r - y2 * sin_r
            y3 = x2 * sin_r + y2 * cos_r
        else:
            x3, y3 = x2, y2
            
        x4 = x3 + px
        y4 = y3 + py
        return x4, y4

    def walk(o, tr_stack):
        if isinstance(o, dict):
            ty = o.get("ty")
            if ty == "gr":
                new_stack = list(tr_stack)
                if o is not target:
                    tr = get_group_transform(o)
                    if tr:
                        new_stack.append(tr)
                items = o.get("it", o.get("shapes", []))
                for item in items:
                    if item.get("ty") != "tr":
                        walk(item, new_stack)
            elif ty == "sh":
                ks = o.get("ks", {})
                k = ks.get("k", {})
                if isinstance(k, list) and k and isinstance(k[0], dict):
                    k = k[0].get("s", k[0])
                if isinstance(k, dict) and "v" in k:
                    for v in k["v"]:
                        tx, ty = float(v[0]), float(v[1])
                        for tr in reversed(tr_stack):
                            tx, ty = transform_point(tx, ty, tr)
                        verts.append((tx, ty))
            else:
                for val in o.values():
                    if isinstance(val, (dict, list)):
                        walk(val, tr_stack)
        elif isinstance(o, list):
            for item in o:
                walk(item, tr_stack)

    walk(obj, [])
    return verts


def _verts_to_bounds(verts):
    if not verts: return None
    xs=[v[0] for v in verts]; ys=[v[1] for v in verts]
    return (min(xs), min(ys), max(xs), max(ys))


def _get_textgroup_bounds(lottie):
    keywords = {"textgroup", "text", "letters", "emoji", "text shape", "emc", "logo", "label", "word", "txt", "title", "caption"}
    
    def matches(name):
        if not name or not isinstance(name, str):
            return False
        nm_lower = name.lower()
        return "user" not in nm_lower and any(kw in nm_lower for kw in keywords)

    elements = []
    todo = []
    if "layers" in lottie:
        todo.extend(lottie["layers"])
    if "assets" in lottie:
        for a in lottie["assets"]:
            if "layers" in a:
                todo.extend(a["layers"])
    
    while todo:
        el = todo.pop()
        elements.append(el)
        sh = el.get("shapes")
        if sh: todo.extend(sh)
        it = el.get("it")
        if it: todo.extend(it)

    # 1. Look for type 5 text layers
    text_layers = [el for el in elements if el.get("ty") == 5]
    if text_layers:
        target = text_layers[0]
        pos = target.get("ks", {}).get("p", {}).get("k", [0, 0])
        if isinstance(pos, list) and pos and isinstance(pos[0], dict):
            pos = pos[0].get("s", [0, 0])
        cx, cy = (pos[0], pos[1]) if (isinstance(pos, list) and len(pos) >= 2) else (0.0, 0.0)
        font_size = 50.0
        max_width = 512.0
        return (cx - max_width / 2.0, cy - font_size / 2.0, cx + max_width / 2.0, cy + font_size / 2.0)

    def is_descendant(child, parent):
        td = []
        if "shapes" in parent: td.extend(parent["shapes"])
        if "it" in parent: td.extend(parent["it"])
        while td:
            o = td.pop()
            if o is child: return True
            sh = o.get("shapes")
            if sh: td.extend(sh)
            it = o.get("it")
            if it: td.extend(it)
        return False

    # 2. Look for named targets matching keywords
    named_targets = []
    for el in elements:
        ty = el.get("ty")
        if ty == "gr" and matches(el.get("nm")):
            cnt = 0
            t_todo = [el]
            while t_todo:
                o = t_todo.pop()
                if isinstance(o, dict):
                    if o.get("ty") == "sh": cnt += 1
                    for v in o.values():
                        if isinstance(v, (dict, list)): t_todo.append(v)
                elif isinstance(o, list):
                    for item in o:
                        if isinstance(item, (dict, list)): t_todo.append(item)
            if cnt >= 1:
                named_targets.append(el)

    if named_targets:
        final_targets = []
        for cand in named_targets:
            if any(is_descendant(t, cand) for t in named_targets if t is not cand):
                continue
            final_targets.append(cand)
        if final_targets:
            verts = _collect_path_verts(final_targets[0])
            if verts:
                return _verts_to_bounds(verts)

    return None



def _text_to_lottie_shapes(text, font_path, cx, cy, height, max_width=None):
    if not HAS_FONTTOOLS:
        logger.error("fontTools: package not found")
        return []
    try:
        ft = _get_cached_font(font_path)
    except Exception as e:
        logger.error(f"fontTools: failed to load font {font_path}: {e}")
        return []
    gs=ft.getGlyphSet(); cm=ft.getBestCmap() or {}
    upm=ft["head"].unitsPerEm
    os2=ft.get("OS/2")
    cap_h=float(getattr(os2,"sCapHeight",0) or getattr(os2,"sTypoAscender",upm*0.72))
    if cap_h<=0: cap_h=upm*0.72
    sc=height/cap_h
    total_adv=0.0; glyph_list=[]
    for ch in text:
        gn=cm.get(ord(ch))
        if not gn or gn not in gs:
            fb={ord("'"): [0x2019,0x02BC], ord("–"): [0x002D], ord("—"): [0x002D]}
            for alt in fb.get(ord(ch),[]):
                gn=cm.get(alt)
                if gn and gn in gs: break
            else: gn=None
        adv=float(gs[gn].width) if gn and gn in gs else upm*0.35
        glyph_list.append((gn,adv)); total_adv+=adv
    if max_width and total_adv>0:
        sc=min(sc,(max_width/(total_adv*sc)*sc)*0.92)
    start_x=cx-total_adv*sc/2.0; base_y=cy+(cap_h/2.0)*sc
    shapes=[]; cur_x=start_x
    for gn,adv in glyph_list:
        if gn is None: cur_x+=adv*sc; continue
        pen=DecomposingRecordingPen(gs); gs[gn].draw(pen)
        vs_,ii_,oo_=[],[],[]
        def _close():
            if vs_:
                shapes.append({"ty":"sh","nm":"p","ks":{"a":0,"k":{"c":True,
                    "v":[list(v) for v in vs_],"i":[list(v) for v in ii_],"o":[list(v) for v in oo_]}}})
        for op,args in pen.value:
            if op=="moveTo":
                _close(); vs_.clear(); ii_.clear(); oo_.clear()
                fx,fy=args[0]; lx=fx*sc+cur_x; ly=base_y-fy*sc
                vs_.append([lx,ly]); ii_.append([0.,0.]); oo_.append([0.,0.])
            elif op=="lineTo":
                fx,fy=args[0]; lx=fx*sc+cur_x; ly=base_y-fy*sc
                vs_.append([lx,ly]); ii_.append([0.,0.]); oo_.append([0.,0.])
            elif op=="curveTo":
                (c1x,c1y),(c2x,c2y),(ex,ey)=args
                pvx,pvy=vs_[-1]
                oo_[-1]=[c1x*sc+cur_x-pvx,base_y-c1y*sc-pvy]
                nvx=ex*sc+cur_x; nvy=base_y-ey*sc
                vs_.append([nvx,nvy]); ii_.append([c2x*sc+cur_x-nvx,base_y-c2y*sc-nvy]); oo_.append([0.,0.])
            elif op=="qCurveTo":
                pts=list(args); p0x,p0y=vs_[-1]
                for qi in range(len(pts)-1):
                    qcx,qcy=pts[qi]
                    qex,qey=pts[qi+1] if qi==len(pts)-2 else ((pts[qi][0]+pts[qi+1][0])/2,(pts[qi][1]+pts[qi+1][1])/2)
                    qcs=(qcx*sc+cur_x,base_y-qcy*sc); qes=(qex*sc+cur_x,base_y-qey*sc)
                    c1s=(p0x+2/3*(qcs[0]-p0x),p0y+2/3*(qcs[1]-p0y))
                    c2s=(qes[0]+2/3*(qcs[0]-qes[0]),qes[1]+2/3*(qcs[1]-qes[1]))
                    oo_[-1]=[c1s[0]-p0x,c1s[1]-p0y]
                    vs_.append(list(qes)); ii_.append([c2s[0]-qes[0],c2s[1]-qes[1]]); oo_.append([0.,0.])
                    p0x,p0y=qes
            elif op in ("endPath","closePath"):
                _close(); vs_.clear(); ii_.clear(); oo_.clear()
        _close(); cur_x+=adv*sc
    return shapes



def _replace_textgroup(lottie, new_shapes):
    patched_any = False
    
    def _hfl(items): return any(x.get("ty")=="fl" for x in items)
    
    def _islc(item):
        if item.get("ty")!="gr": return False
        return not _hfl(item.get("it",[])) and not any(x.get("ty")=="st" for x in item.get("it",[]))
        
    def _patch(lst):
        nonlocal patched_any
        style=[x for x in lst if x.get("ty") not in ("sh","el","rc","sr") and not _islc(x)]
        lst[:]=new_shapes+style
        patched_any = True

    # 1. Try to find by explicit names: "TextGroup", "Text", "text" (excluding username)
    matched_named = []
    def walk_named(obj, path=()):
        if isinstance(obj, dict):
            nm = obj.get("nm", "")
            if isinstance(nm, str) and nm:
                nm_lower = nm.lower()
                # Exclude username groups
                if "user" not in nm_lower:
                    if obj.get("ty") == "gr" and ("textgroup" in nm_lower or nm_lower == "text"):
                        matched_named.append((obj, path))
            for k, v in obj.items():
                walk_named(v, path + (k,))
        elif isinstance(obj, list):
            for i, x in enumerate(obj):
                walk_named(x, path + (i,))

    walk_named(lottie)
    if matched_named:
        # Filter ancestors
        filtered = []
        for gr1, p1 in matched_named:
            is_ancestor = False
            for gr2, p2 in matched_named:
                if len(p1) < len(p2) and p2[:len(p1)] == p1:
                    is_ancestor = True
                    break
            if not is_ancestor:
                filtered.append(gr1)
        for gr in filtered:
            _patch(gr.setdefault("it", []))
            
    if patched_any:
        return True

    # 2. Try to find by shape layers containing "text" in name or type 5 layers
    def try_ll(layers):
        nonlocal patched_any
        for layer in layers:
            ty = layer.get("ty")
            if ty not in (4, 5): continue
            nm=layer.get("nm","")
            if not isinstance(nm, str): continue
            nm_lower = nm.lower()
            if "user" in nm_lower: continue
            
            if ty == 5:
                layer["ty"] = 4
                layer.pop("t", None)
                style = {
                    "ty": "fl",
                    "c": {"a": 0, "k": [1, 1, 1, 1]},
                    "o": {"a": 0, "k": 100},
                    "r": 1,
                    "nm": "Fill 1"
                }
                layer["shapes"] = new_shapes + [style]
                patched_any = True
                continue
                
            shapes=layer.get("shapes",[]); nm=layer.get("nm","")
            n=sum(1 for s in shapes if s.get("ty")=="sh")
            fl=any(s.get("ty")=="fl" for s in shapes)
            if ("text" in nm_lower and n>=2 and fl) or (n>=3 and fl):
                _patch(shapes)

    for ll in [lottie.get("layers",[])]+[a.get("layers",[]) for a in lottie.get("assets",[])]:  
        try_ll(ll)

    if patched_any:
        return True

    # 3. Fallback heuristic (only if name matching failed)
    def _cdsh(gr): return sum(1 for x in gr.get("it",[]) if x.get("ty")=="sh")
    def _cnsh(gr):
        n=0
        for x in gr.get("it",[]):
            n+=1 if x.get("ty")=="sh" else (_cnsh(x) if x.get("ty")=="gr" else 0)
        return n

    matched_heuristic = []
    def walk_heuristic(obj, path=()):
        if isinstance(obj, dict):
            nm = obj.get("nm", "")
            nm_lower = nm.lower() if isinstance(nm, str) else ""
            if "user" not in nm_lower:
                if obj.get("ty") == "gr" and _hfl(obj.get("it",[])):
                    # Text placeholders like "jelly" have between 3 and 12 shapes usually
                    # Complex drawings like a car outline have many more
                    num_shapes = _cnsh(obj)
                    if (_cdsh(obj)==0 or _cdsh(obj)>=3) and 3 <= num_shapes <= 12:
                        matched_heuristic.append((obj, path))
            for k, v in obj.items():
                walk_heuristic(v, path + (k,))
        elif isinstance(obj, list):
            for i, x in enumerate(obj):
                walk_heuristic(x, path + (i,))

    walk_heuristic(lottie)
    if matched_heuristic:
        filtered = []
        for gr1, p1 in matched_heuristic:
            is_ancestor = False
            for gr2, p2 in matched_heuristic:
                if len(p1) < len(p2) and p2[:len(p1)] == p1:
                    is_ancestor = True
                    break
            if not is_ancestor:
                filtered.append(gr1)
        for gr in filtered:
            _patch(gr.setdefault("it", []))

    return patched_any



def _find_username_bounds(lottie):
    def walk(obj):
        if isinstance(obj, dict):
            if (obj.get("ty") == "gr" or obj.get("ty") == 4 or obj.get("ty") == "4") and obj.get("nm") == "USERNAME":
                b = _verts_to_bounds(_collect_path_verts(obj))
                if b: return b, obj
            for v in obj.values():
                r = walk(v)
                if r: return r
        elif isinstance(obj, list):
            for item in obj:
                r = walk(item)
                if r: return r
        return None
    return walk(lottie)


def _replace_username(lottie, new_text, font_path, scale_factor: float = 1.0):
    replaced = False

    def walk(obj):
        nonlocal replaced
        if isinstance(obj, dict):
            if (obj.get("ty") == "gr" or obj.get("ty") == 4 or obj.get("ty") == "4") and obj.get("nm") == "USERNAME":
                b = _verts_to_bounds(_collect_path_verts(obj))
                if b:
                    x1, y1, x2, y2 = b
                    cx = (x1 + x2) / 2
                    cy = (y1 + y2) / 2
                    h = max(abs(y2 - y1), 1.0) * scale_factor
                    w = max(abs(x2 - x1), 1.0)
                    cx_clamped = max(30.0, min(482.0, cx))
                    canvas_max_width = 2.0 * min(cx_clamped - 30.0, 482.0 - cx_clamped)
                    allowed_w = max(w, min(canvas_max_width, w * 2.5)) * scale_factor
                    ns = _text_to_lottie_shapes(
                        new_text,
                        font_path,
                        cx,
                        cy,
                        h,
                        max_width=allowed_w,
                    )
                    if ns:
                        if "it" in obj:
                            items = obj.setdefault("it", [])
                        elif "shapes" in obj:
                            items = obj.setdefault("shapes", [])
                        else:
                            key = "shapes" if (obj.get("ty") == 4 or obj.get("ty") == "4") else "it"
                            items = obj.setdefault(key, [])

                        def _hfl(lst):
                            return any(x.get("ty") == "fl" for x in lst)
                        style = [
                            x for x in items
                            if x.get("ty") not in ("sh", "el", "rc", "sr")
                            and not (x.get("ty") == "gr" and not _hfl(x.get("it", x.get("shapes", []))))
                        ]
                        items[:] = ns + style
                        replaced = True
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(lottie)
    return replaced


OLD_USERNAME = "@emojicreationbot"
NEW_USERNAME = "JellyColor"


def _dominant_color_from_gradient(colors: list) -> str:
    if not colors:
        return "#000000"
    rs, gs, bs = [], [], []
    for c in colors:
        r, g, b = hex_to_rgb(c)
        rs.append(r); gs.append(g); bs.append(b)
    return rgb_to_hex(sum(rs)//len(rs), sum(gs)//len(gs), sum(bs)//len(bs))


def _apply_neon_style_to_items(items: list, stroke_hex: str) -> list:
    sr, sg, sb = hex_to_rgb(stroke_hex)
    snr, sng, snb = sr / 255, sg / 255, sb / 255
    
    # 80% white + 20% chosen color for a pastel neon core
    fnr = 0.8 + 0.2 * snr
    fng = 0.8 + 0.2 * sng
    fnb = 0.8 + 0.2 * snb
    
    fill_obj = None
    stroke_obj = None
    other_items = []
    
    for item in items:
        if not isinstance(item, dict):
            other_items.append(item)
            continue
        ty = item.get("ty")
        if ty == "fl":
            fill_obj = item
        elif ty == "st":
            stroke_obj = item
        else:
            other_items.append(item)
            
    if not fill_obj:
        fill_obj = {
            "ty": "fl",
            "nm": "NeonFill",
            "c": {"a": 0, "k": [fnr, fng, fnb, 1]},
            "o": {"a": 0, "k": 100}
        }
    else:
        c = fill_obj.setdefault("c", {})
        c["a"] = 0
        c["k"] = [fnr, fng, fnb, 1]
        
    if not stroke_obj:
        stroke_obj = {
            "ty": "st",
            "nm": "NeonStroke",
            "c": {"a": 0, "k": [snr, sng, snb, 1]},
            "o": {"a": 0, "k": 100},
            "w": {"a": 0, "k": 3.0},
            "lc": 1,
            "lj": 1
        }
    else:
        c = stroke_obj.setdefault("c", {})
        c["a"] = 0
        c["k"] = [snr, sng, snb, 1]
        w = stroke_obj.setdefault("w", {})
        w["a"] = 0
        w["k"] = 3.0
        stroke_obj["lc"] = 1
        stroke_obj["lj"] = 1
        
    shapes = [x for x in other_items if isinstance(x, dict) and x.get("ty") in ("sh", "el", "rc", "sr")]
    non_shapes = [x for x in other_items if x not in shapes]
    
    # Render stroke behind fill for clean neon look
    return shapes + [stroke_obj, fill_obj] + non_shapes


def _set_text_neon_style(lottie: dict, stroke_hex: str) -> None:
    def _is_text_group(obj):
        if not isinstance(obj, dict):
            return False
        if obj.get("ty") != "gr":
            return False
        nm = (obj.get("nm") or "").lower()
        return "textgroup" in nm or nm == "text"

    def _is_text_layer(obj):
        if not isinstance(obj, dict):
            return False
        if obj.get("ty") != 4:
            return False
        nm = (obj.get("nm") or "").lower()
        return "text" in nm and "user" not in nm

    def _walk(obj):
        if isinstance(obj, dict):
            if _is_text_group(obj):
                obj["it"] = _apply_neon_style_to_items(obj.get("it", []), stroke_hex)
            elif _is_text_layer(obj):
                obj["shapes"] = _apply_neon_style_to_items(obj.get("shapes", []), stroke_hex)
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for x in obj:
                _walk(x)

    _walk(lottie)


def _add_default_text_layer(lottie: dict):
    max_ind = 0
    layers = lottie.get("layers", [])
    for l in layers:
        ind = l.get("ind", 0)
        if isinstance(ind, int) and ind > max_ind:
            max_ind = ind
    
    new_layer = {
        "ty": 5,
        "nm": "Text 1",
        "sr": 1,
        "st": 0,
        "op": 9999,
        "ip": 0,
        "ind": max_ind + 1,
        "ks": {
            "a": {"a": 0, "k": [0, 0, 0]},
            "p": {"a": 0, "k": [256, 420, 0]},
            "s": {"a": 0, "k": [100, 100, 100]},
            "r": {"a": 0, "k": 0},
            "o": {"a": 0, "k": 100}
        },
        "t": {
            "d": {
                "k": [
                    {
                        "s": {
                            "s": 40,
                            "f": "Comfortaa-Bold",
                            "t": "placeholder",
                            "j": 2,
                            "tr": 0,
                            "lh": 48,
                            "ls": 0,
                            "fc": [1, 1, 1]
                        },
                        "t": 0
                    }
                ]
            }
        }
    }
    layers.append(new_layer)


def modify_lottie(lottie: dict, new_text: str, font_path: str = None, scale_factor: float = 1.0) -> bool:
    if not font_path:
        font_path=_ensure_font()
    if not font_path: return False
    changed=False
    
    # Check bounds. If not found, add default text layer!
    bounds=_get_textgroup_bounds(lottie)
    if not bounds:
        _add_default_text_layer(lottie)
        bounds=_get_textgroup_bounds(lottie)
        changed=True
        
    if bounds:
        x1,y1,x2,y2=bounds; cx=(x1+x2)/2; cy=(y1+y2)/2
        h = max(abs(y2-y1), 5.) * scale_factor
        w = max(abs(x2-x1), 5.)
        cx_clamped = max(30.0, min(482.0, cx))
        canvas_max_width = 2.0 * min(cx_clamped - 30.0, 482.0 - cx_clamped)
        allowed_w = max(w, min(canvas_max_width, w * 2.2)) * scale_factor
        ns=_text_to_lottie_shapes(new_text,font_path,cx,cy,h,max_width=allowed_w)
        if ns and _replace_textgroup(lottie,ns): changed=True
    if _find_username_bounds(lottie):
        if _replace_username(lottie,NEW_USERNAME,font_path,scale_factor): changed=True
    return changed


def replace_text_in_tgs(tgs_bytes: bytes, old_text: str, new_text: str, font_path: str = None) -> bytes:
    raw=gzip.decompress(tgs_bytes); lottie=json_loads(raw)
    modify_lottie(lottie, new_text, font_path)
    return compress_tgs(lottie)


# ─── Recolor helpers ──────────────────────────────────────────────────────────

def _recolor_document_sync(data: bytes, mime: str, hex_color: str, is_emoji: bool) -> io.BytesIO:
    if mime=="application/x-tgsticker":
        lottie=json_loads(gzip.decompress(data))
        buf=io.BytesIO(compress_tgs(tint_lottie(lottie,hex_color))); buf.name="sticker.tgs"
    else:
        sz=100 if is_emoji else 512
        img=Image.open(io.BytesIO(data)).convert("RGBA")
        if img.size != (sz, sz):
            img = img.resize((sz,sz),Image.LANCZOS)
        buf=io.BytesIO(); tint_image(img,hex_color).save(buf,format="WEBP",lossless=True)
        buf.seek(0); buf.name="sticker.webp"
    buf.seek(0)
    return buf


async def recolor_document(client, doc, hex_color: str, is_emoji: bool = False) -> io.BytesIO:
    data=await download_cached(client,doc)
    mime=getattr(doc,"mime_type","")
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _recolor_document_sync, data, mime, hex_color, is_emoji)


def _recolor_document_gradient_sync(data: bytes, mime: str, gradient: dict, is_emoji: bool) -> io.BytesIO:
    if mime=="application/x-tgsticker":
        lottie=json_loads(gzip.decompress(data))
        apply_gradient_lottie(lottie,gradient)
        buf=io.BytesIO(compress_tgs(lottie)); buf.name="sticker.tgs"
    else:
        sz=100 if is_emoji else 512
        img=Image.open(io.BytesIO(data)).convert("RGBA")
        if img.size != (sz, sz):
            img = img.resize((sz,sz),Image.LANCZOS)
        buf=io.BytesIO()
        tint_image_gradient(img, gradient["colors"], gradient.get("dir", "d")).save(buf,format="WEBP",lossless=True)
        buf.seek(0); buf.name="sticker.webp"
    buf.seek(0)
    return buf


async def recolor_document_gradient(client, doc, gradient: dict, is_emoji: bool = False) -> io.BytesIO:
    """Перекрашивает стикер с градиентом."""
    data=await download_cached(client,doc)
    mime=getattr(doc,"mime_type","")
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _recolor_document_gradient_sync, data, mime, gradient, is_emoji)



def validate_short_name(name: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9_]{1,64}",name))


async def _upload_item(client, me_entity, uploaded, mime: str, emoji_str: str, is_emoji: bool):
    if is_emoji:
        attr=types.DocumentAttributeCustomEmoji(alt=emoji_str,stickerset=types.InputStickerSetEmpty(),free=False,text_color=False)
    else:
        attr=types.DocumentAttributeSticker(alt=emoji_str,stickerset=types.InputStickerSetEmpty())
    is_tgs=mime=="application/x-tgsticker"
    mt="application/x-tgsticker" if is_tgs else "image/webp"
    fn="sticker.tgs" if is_tgs else "sticker.webp"
    if is_tgs or is_emoji:
        extra_attrs=[]
    else:
        extra_attrs=[types.DocumentAttributeImageSize(w=512,h=512)]
    media=types.InputMediaUploadedDocument(
        file=uploaded,mime_type=mt,
        attributes=[types.DocumentAttributeFilename(file_name=fn),attr]+extra_attrs,
    )
    r=await client(functions.messages.UploadMediaRequest(peer=me_entity,media=media))
    d=r.document
    return types.InputStickerSetItem(
        document=types.InputDocument(id=d.id,access_hash=d.access_hash,file_reference=d.file_reference),
        emoji=emoji_str,
    )


def _get_partition_short_name(short_name: str, n: int) -> str:
    if n <= 1:
        return short_name
    if "_by_" in short_name.lower():
        parts = short_name.rsplit("_by_", 1)
        return f"{parts[0]}_v{n}_by_{parts[1]}"
    return f"{short_name}_v{n}"


def _get_bot_suffix(me):
    """Возвращает безопасный суффикс для short_name пака (username или числовой id)."""
    if me.username and re.fullmatch(r'[a-zA-Z0-9_]+', me.username):
        return me.username
    return str(me.id)


async def _safe_create_set(client, uid, title, short_name, stickers, is_emoji, exists_mode="recreate"):
    limit = 180 if is_emoji else 120
    chunks = [stickers[i:i + limit] for i in range(0, len(stickers), limit)]
    created_names = []

    for idx, chunk in enumerate(chunks):
        n = idx + 1
        curr_short = _get_partition_short_name(short_name, n)
        curr_title = title if n == 1 else f"{title} v{n}"
        
        try:
            await client(functions.stickers.CreateStickerSetRequest(
                user_id=uid, title=curr_title, short_name=curr_short, stickers=chunk, emojis=is_emoji,
            ))
            created_names.append(curr_short)
        except Exception as e:
            err_msg = str(e).lower()
            if "already exists" in err_msg or "already_exists" in err_msg or "short_name_occupied" in err_msg:
                if exists_mode == "recreate":
                    try:
                        await client(functions.stickers.DeleteStickerSetRequest(
                            stickerset=types.InputStickerSetShortName(short_name=curr_short)
                        ))
                        await asyncio.sleep(0.5)
                        await client(functions.stickers.CreateStickerSetRequest(
                            user_id=uid, title=curr_title, short_name=curr_short, stickers=chunk, emojis=is_emoji,
                        ))
                        created_names.append(curr_short)
                    except Exception as del_err:
                        logger.exception(f"Failed to recreate stickerpack via delete {curr_short}")
                        return None, f"Не удалось перезаписать пак {curr_short}: {del_err}"
                else:
                    try:
                        add_sem = asyncio.Semaphore(10)
                        async def _add_one(sticker):
                            async with add_sem:
                                await client(functions.stickers.AddStickerToSetRequest(
                                    stickerset=types.InputStickerSetShortName(short_name=curr_short),
                                    sticker=sticker
                                ))
                        await asyncio.gather(*[_add_one(s) for s in chunk])
                        created_names.append(curr_short)
                    except Exception as add_err:
                        logger.exception(f"Failed to append stickers to existing stickerpack {curr_short}")
                        return None, f"Не удалось добавить стикеры в пак {curr_short}: {add_err}"
            else:
                logger.exception(f"CreateStickerSetRequest failed for {curr_short}")
                return None, str(e)
                
    return created_names, None


# ─── Module ───────────────────────────────────────────────────────────────────

@loader.tds
class JellyColorMod(loader.Module):
    """🎨 JellyColor: Перекраска стикеров и создание текстовых эмодзи-паков.
    Поддерживает градиенты, пользовательские шрифты, изменение масштаба и отмену генерации."""

    strings = {"name": "JellyColor"}

    def __init__(self):
        self._sessions:     Dict[int,Dict[str,Any]] = {}
        self._tsessions:    Dict[int,Dict[str,Any]] = {}
        self._semaphore = None

    def _sem(self):
        if self._semaphore is None:
            self._semaphore=asyncio.Semaphore(RECOLOR_CONCURRENCY)
        return self._semaphore

    def _expire(self):
        now=time.time()
        for store in (self._sessions,self._tsessions):
            for k in [k for k,v in store.items() if now-v.get("ts",now)>SESSION_TTL]:
                store.pop(k,None)

    def _color_history(self) -> List[str]:
        seen=[]; out=[]
        for e in reversed(self.db.get("JellyColor","stats",[])):
            c=e.get("color","")
            if c and c!="text" and c not in seen:
                seen.append(c); out.append(c)
            if len(out)>=5: break
        return out

    async def _report_error(self, e: Exception, ptype: str, pname: str):
        logger.exception("JellyColor error occurred")
        try:
            cid = self.db.get("heroku.forums", "channel_id", None)
            if not cid:
                return
            logchat_id = int(f"-100{cid}")
            forums_cache = self.db.get("heroku.forums", "forums_cache", {})
            topic_id = forums_cache.get("heroku-userbot", {}).get("Logs")
            tb_str = traceback.format_exc()
            msg_text = (
                f"❌ <b>JellyColor Error</b>\n\n"
                f"<b>Type:</b> {ptype}\n"
                f"<b>Short Name:</b> <code>{pname}</code>\n"
                f"<b>Error:</b> <code>{str(e)}</code>\n\n"
                f"<b>Traceback:</b>\n"
                f"<pre><code class=\"language-python\">{tb_str[:3000]}</code></pre>"
            )
            debug_files = glob.glob("/tmp/jelly_debug_last.*")
            if debug_files:
                await self._client.send_file(
                    logchat_id,
                    debug_files[0],
                    caption=msg_text,
                    reply_to=topic_id
                )
            else:
                await self._client.send_message(
                    logchat_id,
                    msg_text,
                    reply_to=topic_id
                )
        except Exception as ex:
            logger.error(f"Failed to report error to logchat: {ex}", exc_info=True)

    async def _resolve_target(self, reply):
        td=tt=ts=None
        if reply.sticker:
            for a in reply.sticker.attributes:
                if isinstance(a,DocumentAttributeSticker):
                    ss=a.stickerset
                    if isinstance(ss,(InputStickerSetShortName,InputStickerSetID)):
                        td,tt,ts=reply.sticker,"sticker",ss; break
        if not td:
            for ent in (reply.entities or []):
                if isinstance(ent,MessageEntityCustomEmoji):
                    docs=await self._client(functions.messages.GetCustomEmojiDocumentsRequest(document_id=[ent.document_id]))
                    if not docs: continue
                    doc=docs[0]
                    for a in doc.attributes:
                        if isinstance(a,(DocumentAttributeCustomEmoji,DocumentAttributeSticker)):
                            ss=getattr(a,"stickerset",None)
                            if ss and not isinstance(ss,InputStickerSetEmpty):
                                td,tt,ts=doc,"emoji",ss; break
                    if td: break
        return td,tt,ts

    async def _parallel(self, docs, fn, label, call, reply_markup=None):
        """Запускает fn(i,doc)->item|None параллельно с прогрессом.

        Fixes:
        - call.edit дросселируется: не чаще раза в 2с, только из одной корутины
        - ошибки логируются, не глотаются молча
        - прогресс обновляется строго под lock
        - FloodWaitError обрабатывается явно
        """
        log = logger
        results=[]; lock=asyncio.Lock(); progress=[0]; sem=self._sem()
        last_edit=[0.0]  # время последнего edit, общее для всех корутин

        async def _update_progress(p, n):
            now=asyncio.get_event_loop().time()
            if now - last_edit[0] < 2.0:
                return
            last_edit[0]=now
            bar_len=20; filled=int(p/n*bar_len)
            bar="█"*filled+"░"*(bar_len-filled)
            try:
                await call.edit(
                    text=(
                        pe("⏰",PE["clock"])+f" <b>{label}...</b>\n\n"
                        f"<code>[{bar}]</code> {int(p/n*100)}%\n"
                        f"<b>{p}/{n}</b>"
                    ),
                    reply_markup=reply_markup
                )
            except Exception:
                pass

        async def _run(i,doc):
            retries=3
            item=None
            for attempt in range(retries):
                try:
                    async with sem:
                        item=await fn(i,doc)
                    break
                except FloodWaitError as e:
                    wait = getattr(e, "seconds", None) or 5 * (attempt + 1)
                    log.warning(f"_parallel FloodWait item {i}, sleeping {wait}s")
                    await asyncio.sleep(wait)
                except Exception as e:
                    if attempt<retries-1:
                        log.warning(f"_parallel item {i} attempt {attempt+1} failed: {e}")
                        await asyncio.sleep(1)
                    else:
                        log.error(f"_parallel item {i} failed after {retries} attempts: {e}")
            async with lock:
                if item is not None:
                    results.append((i,item))
                progress[0]+=1
                p=progress[0]
            n=len(docs)
            if n>1:
                await _update_progress(p, n)

        await asyncio.gather(*[_run(i,d) for i,d in enumerate(docs)])
        results.sort(key=lambda x:x[0])
        return [x for _,x in results]

    # ─── Shared color/gradient UI helpers ────────────────────────────────────

    @staticmethod
    def _patch_allow(rows, uid):
        """Inject always_allow=[uid] into every callback button to prevent
        Heroku's 'argument of type bool is not iterable' crash."""
        for row in rows:
            for btn in row:
                if "callback" in btn and "always_allow" not in btn:
                    btn["always_allow"] = [uid]
        return rows

    def _gradient_menu_text(self) -> str:
        user_gradients = self.db.get("JellyColor", "user_gradients", [])
        all_grads = GRADIENT_PRESETS + user_gradients
        lines = [pe("🎨", PE["stats"]) + " <b>Выберите градиент</b>\n"]
        for g in all_grads:
            lines.append(f"{g['name']}  <code>{'  '.join(g['colors'])}</code>")
        return "\n".join(lines)

    def _gradient_menu_markup(self, grad_cb, uid, back_cb):
        user_gradients = self.db.get("JellyColor", "user_gradients", [])
        all_grads = GRADIENT_PRESETS + user_gradients
        rows = []; row = []
        for g in all_grads:
            row.append({"text": g["name"], "icon_custom_emoji_id": PE["stats"],
                        "callback": grad_cb, "args": (uid, g["id"])})
            if len(row) == 2:
                rows.append(row); row = []
        if row:
            rows.append(row)
        rows.append([{"text": "◁ Назад", "icon_custom_emoji_id": PE["palette"],
                      "callback": back_cb, "args": (uid,)}])
        return rows

    def _color_rows_with_gradient(self, uid, col_cb, hex_cb, grad_open_cb, no_color_cb=None, custom_grad_cb=None):
        """Генерирует строки кнопок выбора цвета: пресеты 2-в-ряд + HEX + градиент + без перекраски + свой градиент."""
        rows = []; row = []
        for label, hv in PRESET_COLORS.items():
            row.append({"text": label, "callback": col_cb, "args": (uid, hv)})
            if len(row) == 2:
                rows.append(row); row = []
        if row:
            rows.append(row)
        rows.append([{"text": "✏️ Свой HEX", "icon_custom_emoji_id": PE["palette"],
                      "input": "Введите HEX, например #FF3B30", "handler": hex_cb, "args": (uid,)}])
        grad_row = [{"text": "🎨 Градиент", "icon_custom_emoji_id": PE["stats"],
                     "callback": grad_open_cb, "args": (uid,)}]
        if custom_grad_cb:
            grad_row.append({"text": "✏️ Свой градиент", "icon_custom_emoji_id": PE["palette"],
                             "input": "Введите HEX через запятую, например #FF0000,#00FF00,#0000FF",
                             "handler": custom_grad_cb, "args": (uid,)})
        rows.append(grad_row)
        if no_color_cb:
            rows.append([{"text": "◻️ Без перекраски", "icon_custom_emoji_id": PE["eye"],
                          "callback": no_color_cb, "args": (uid,)}])
        return rows

    # ─── .j ───────────────────────────────────────────────────────────────────

    @loader.command()
    async def j(self, message: Message):
        """Ответьте на стикер/эмодзи — перекраска с выбором цвета"""
        self._expire()
        reply=await message.get_reply_message()
        if not reply: await utils.answer(message,pe("❌",PE["err"])+" Ответьте на стикер или эмодзи."); return
        td,tt,ts=await self._resolve_target(reply)
        if not td: await utils.answer(message,pe("❌",PE["err"])+" Стикер/эмодзи не найден."); return
        try: full_set=await self._client(functions.messages.GetStickerSetRequest(stickerset=ts,hash=0))
        except Exception as e:
            logger.exception("GetStickerSetRequest failed in .j command")
            await utils.answer(message,pe("❌",PE["err"])+" "+str(e)); return
        uid=message.sender_id; pc=len(full_set.documents)
        self._sessions[uid]={"ts":time.time(),"type":tt,"doc":td,"set_id":ts,
            "set_short":getattr(full_set.set,"short_name",""),"full_set":full_set,"pack_count":pc,
            "scope":None,"color":None,"gradient":None,"pack_name":None,
            "step":"scope" if pc>1 else "color"}
        await message.delete()
        await self.inline.form(text=self._j_text(uid),reply_markup=self._j_markup(uid),message=message,always_allow=[uid])

    def _j_text(self,uid):
        s=self._sessions[uid]; step=s["step"]
        if step=="scope": return pe("🖤",PE["brush"])+f" <b>Что перекрасить?</b>\n\nПак <code>{s['set_short']}</code> — <b>{s['pack_count']}</b> шт."
        if step=="color":
            hist=self._color_history()
            hs=("\n"+pe("⏰",PE["clock"])+" Последние: "+"  ".join(f"<code>{c}</code>" for c in hist)) if hist else ""
            sc="один" if s["scope"]=="one" else f"весь пак ({s['pack_count']})"
            return pe("🖋",PE["palette"])+f" <b>Цвет</b> — {sc}{hs}"
        if step=="gradient_menu": return self._gradient_menu_text()
        if step=="title":
            g=s.get("gradient")
            label=g["name"] if g else f"<code>{s['color'] or 'без перекраски'}</code>"
            return pe("🏷",PE["sticker"])+f" <b>Название пака</b>\n\nЦвет: {label}\n\n<i>Введите отображаемое название (любые символы)</i>"
        if step=="name":
            return pe("🏷",PE["sticker"])+f" <b>short_name пака</b>\n\nНазвание: <b>{s.get('pack_title','')}</b>\n\n<i>Введите short_name — только a-z, 0-9, _</i>"
        if step=="exists_choice":
            return pe("⚠️",PE["info"])+f" <b>Пак уже существует!</b>\n\nПак <code>{s['pack_name']}</code> уже создан на вашем аккаунте. Выберите действие:"
        if step=="processing":
            return pe("⏰",PE["clock"])+" <b>Перекрашиваю...</b>\n\nПожалуйста, подождите. Создаю копию векторных стикеров с новыми цветами."
        return pe("⏰",PE["clock"])+" <b>Перекрашиваю...</b>"

    def _j_markup(self,uid):
        return self._patch_allow(self.__j_markup_inner(uid), uid)

    def __j_markup_inner(self,uid):
        s=self._sessions[uid]; step=s["step"]
        pc = s.get("pack_count", 1)
        if step=="scope": return [[
            {"text":"Один","icon_custom_emoji_id":PE["sticker"],"emoji_id":PE["sticker"],"style":"primary","callback":self._j_s1,"args":(uid,)},
            {"text":"Весь пак","icon_custom_emoji_id":PE["pack"],"emoji_id":PE["pack"],"style":"success","callback":self._j_sa,"args":(uid,)},
        ]]
        if step in ("color","gradient_menu"):
            if step=="gradient_menu":
                rows = self._gradient_menu_markup(self._j_grad,uid,self._j_back_col)
                for r in rows:
                    for btn in r:
                        btn["emoji_id"] = btn.get("icon_custom_emoji_id")
                        btn["style"] = "primary"
                return rows
            rows = self._color_rows_with_gradient(uid,self._j_col,self._j_hex,self._j_open_grad,
                                                  no_color_cb=self._j_no_color,
                                                  custom_grad_cb=self._j_custom_grad)
            for r in rows:
                for btn in r:
                    btn["emoji_id"] = btn.get("icon_custom_emoji_id")
                    if "HEX" in btn["text"] or "Градиент" in btn["text"]:
                        btn["style"] = "primary"
                    elif "Без перекраски" in btn["text"]:
                        btn["style"] = "primary"
            if pc > 1:
                rows.append([{"text": "⬅️ Назад", "icon_custom_emoji_id": PE["back"],"emoji_id":PE["back"],"style":"danger","callback":self._j_back,"args":(uid,)}])
            return rows
        if step=="title": return [
            [{"text":"Ввести название","icon_custom_emoji_id":PE["sticker"],"emoji_id":PE["sticker"],"style":"primary","input":"Например: My Cool Pack","handler":self._j_title,"args":(uid,)}],
            [{"text":"⬅️ Назад","icon_custom_emoji_id":PE["back"],"emoji_id":PE["back"],"style":"danger","callback":self._j_back,"args":(uid,)}]
        ]
        if step=="name": return [
            [{"text":"Ввести short_name","icon_custom_emoji_id":PE["palette"],"emoji_id":PE["palette"],"style":"primary","input":"a-z, 0-9, _ (без _by_username)","handler":self._j_name,"args":(uid,)}],
            [{"text":"⬅️ Назад","icon_custom_emoji_id":PE["back"],"emoji_id":PE["back"],"style":"danger","callback":self._j_back,"args":(uid,)}]
        ]
        if step=="exists_choice":
            return [
                [
                    {"text": "Пересоздать (очистить пак)", "icon_custom_emoji_id": PE["trash"],"emoji_id":PE["trash"],"style":"danger","callback":self._j_handle_exists_choice,"args":(uid,"recreate")},
                ],
                [
                    {"text": "Добавить (сохранить старые)", "icon_custom_emoji_id": PE["pack"],"emoji_id":PE["pack"],"style":"success","callback":self._j_handle_exists_choice,"args":(uid,"add")},
                ],
                [
                    {"text": "⬅️ Назад", "icon_custom_emoji_id": PE["back"],"emoji_id":PE["back"],"style":"primary","callback":self._j_back,"args":(uid,)},
                ]
            ]
        if step=="processing":
            return [
                [{"text": "🛑 Остановить создание", "icon_custom_emoji_id": PE["err"],"emoji_id":PE["err"],"style":"danger","callback":self._j_cancel_generation,"args":(uid,)}]
            ]
        return []

    async def _j_back(self, call, uid):
        s = self._sessions.get(uid)
        if not s: await call.answer("Сессия устарела.", show_alert=True); return
        step = s["step"]
        pc = s.get("pack_count", 1)
        if step == "color":
            if pc > 1:
                s["step"] = "scope"
            else:
                await call.answer("Назад вернуться нельзя (первый шаг).", show_alert=True)
                return
        elif step == "gradient_menu":
            s["step"] = "color"
        elif step == "title":
            s["step"] = "color"
        elif step == "name":
            s["step"] = "title"
        elif step == "exists_choice":
            s["step"] = "name"
        await call.edit(text=self._j_text(uid), reply_markup=self._j_markup(uid))

    async def _j_cancel_generation(self, call, uid):
        s = self._sessions.get(uid)
        if not s: await call.answer("Сессия устарела.", show_alert=True); return
        task = s.get("run_task")
        if task and not task.done():
            task.cancel()
        s["step"] = "title"
        await call.answer("🛑 Создание пака остановлено", show_alert=True)
        await call.edit(text=self._j_text(uid), reply_markup=self._j_markup(uid))

    async def _j_s1(self,call,uid):
        s=self._sessions.get(uid)
        if not s: await call.answer("Сессия устарела.",show_alert=True); return
        s["scope"]="one"; s["step"]="color"
        await call.edit(text=self._j_text(uid),reply_markup=self._j_markup(uid))

    async def _j_sa(self,call,uid):
        s=self._sessions.get(uid)
        if not s: await call.answer("Сессия устарела.",show_alert=True); return
        s["scope"]="all"; s["step"]="color"
        await call.edit(text=self._j_text(uid),reply_markup=self._j_markup(uid))

    async def _j_col(self,call,uid,hex_color):
        s=self._sessions.get(uid)
        if not s: await call.answer("Сессия устарела.",show_alert=True); return
        s["color"]=hex_color; s["gradient"]=None; s["step"]="title"
        await call.edit(text=self._j_text(uid),reply_markup=self._j_markup(uid))

    async def _j_hex(self,call,value,uid):
        s=self._sessions.get(uid)
        if not s: await call.answer("Сессия устарела.",show_alert=True); return
        c=value.strip()
        if not c.startswith("#"): c="#"+c
        if not re.fullmatch(r"#[0-9a-fA-F]{6}",c): await call.answer("Неверный HEX.",show_alert=True); return
        s["color"]=c.upper(); s["gradient"]=None; s["step"]="title"
        await call.edit(text=self._j_text(uid),reply_markup=self._j_markup(uid))

    async def _j_open_grad(self,call,uid):
        s=self._sessions.get(uid)
        if not s: await call.answer("Сессия устарела.",show_alert=True); return
        s["step"]="gradient_menu"
        await call.edit(text=self._j_text(uid),reply_markup=self._j_markup(uid))

    async def _j_grad(self,call,uid,grad_id):
        s=self._sessions.get(uid)
        if not s: await call.answer("Сессия устарела.",show_alert=True); return
        user_gradients = self.db.get("JellyColor", "user_gradients", [])
        g=next((x for x in GRADIENT_PRESETS + user_gradients if x["id"]==grad_id),None)
        if not g: return
        s["gradient"]=g; s["color"]="grad:"+g["name"]; s["step"]="title"
        await call.edit(text=self._j_text(uid),reply_markup=self._j_markup(uid))

    async def _j_back_col(self,call,uid):
        s=self._sessions.get(uid)
        if not s: await call.answer("Сессия устарела.",show_alert=True); return
        s["step"]="color"
        await call.edit(text=self._j_text(uid),reply_markup=self._j_markup(uid))

    async def _j_no_color(self,call,uid):
        s=self._sessions.get(uid)
        if not s: await call.answer("Сессия устарела.",show_alert=True); return
        s["color"]=None; s["gradient"]=None; s["step"]="title"
        await call.edit(text=self._j_text(uid),reply_markup=self._j_markup(uid))

    async def _j_custom_grad(self,call,value,uid):
        s=self._sessions.get(uid)
        if not s: await call.answer("Сессия устарела.",show_alert=True); return
        parts=[p.strip() for p in value.split(",")]
        colors=[]
        for p in parts:
            c=p if p.startswith("#") else "#"+p
            if re.fullmatch(r"#[0-9a-fA-F]{6}",c): colors.append(c.upper())
        if len(colors)<2:
            await call.answer("Нужно минимум 2 HEX через запятую, например #FF0000,#0000FF",show_alert=True); return
        g={"id":"custom","name":"✏️ Свой","colors":colors,"dir":"d"}
        s["gradient"]=g; s["color"]="grad:✏️ Свой"; s["step"]="title"
        await call.edit(text=self._j_text(uid),reply_markup=self._j_markup(uid))

    async def _j_title(self,call,value,uid):
        s=self._sessions.get(uid)
        if not s: await call.answer("Сессия устарела.",show_alert=True); return
        title=value.strip()
        if not title: await call.answer("Название не может быть пустым.",show_alert=True); return
        s["pack_title"]=title; s["step"]="name"
        await call.edit(text=self._j_text(uid),reply_markup=self._j_markup(uid))

    async def _j_name(self,call,value,uid):
        s=self._sessions.get(uid)
        if not s: await call.answer("Сессия устарела.",show_alert=True); return
        if s.get("step")=="processing": await call.answer("Уже идёт.",show_alert=True); return
        c=value.strip().lower()
        if not validate_short_name(c): await call.answer("Только a-z,0-9,_",show_alert=True); return
        me=await self._client.get_me()
        pname=c+"_by_"+_get_bot_suffix(me)
        s["pack_name"]=pname
        
        # Check if pack already exists
        exists = False
        try:
            await self._client(functions.messages.GetStickerSetRequest(
                stickerset=types.InputStickerSetShortName(short_name=pname), hash=0
            ))
            exists = True
        except Exception:
            pass
            
        if exists:
            s["step"]="exists_choice"
            await call.edit(text=self._j_text(uid), reply_markup=self._j_markup(uid))
        else:
            s["step"]="processing"
            s["exists_mode"]="recreate"
            await call.edit(text=self._j_text(uid), reply_markup=self._j_markup(uid))
            s["run_task"] = asyncio.ensure_future(self._j_run(call,uid))

    async def _j_handle_exists_choice(self, call, uid, choice):
        s=self._sessions.get(uid)
        if not s: await call.answer("Сессия устарела.",show_alert=True); return
        if choice == "cancel":
            s["step"]="name"
            await call.edit(text=self._j_text(uid), reply_markup=self._j_markup(uid))
            return
        s["exists_mode"] = choice
        s["step"]="processing"
        await call.edit(text=self._j_text(uid), reply_markup=self._j_markup(uid))
        s["run_task"] = asyncio.ensure_future(self._j_run(call, uid))

    async def _j_run(self,call,uid):
        s=self._sessions.get(uid)
        if not s: return
        try:
            color=s["color"]; pname=s["pack_name"]; ptype=s["type"]
            gradient=s.get("gradient")  # None если обычный цвет
            docs=[s["doc"]] if (s["scope"]=="one" or s["pack_count"]==1) else list(s["full_set"].documents)
            me=await self._client.get_me(); mee=await self._client.get_input_entity("me")
            async def _fn(i,doc):
                _is_emoji=(ptype=="emoji")
                orig_mime=getattr(doc,"mime_type","image/webp")
                mime="application/x-tgsticker" if orig_mime=="application/x-tgsticker" else "image/webp"
                if gradient:
                    buf=await recolor_document_gradient(self._client,doc,gradient,is_emoji=_is_emoji)
                elif color:
                    buf=await recolor_document(self._client,doc,color,is_emoji=_is_emoji)
                else:
                    # Без перекраски — только ресайз для статичных
                    data=await download_cached(self._client,doc)
                    if orig_mime=="application/x-tgsticker":
                        buf=io.BytesIO(data); buf.name="sticker.tgs"
                    else:
                        sz=100 if _is_emoji else 512
                        img=Image.open(io.BytesIO(data)).convert("RGBA")
                        if img.size != (sz, sz):
                            img = img.resize((sz,sz),Image.LANCZOS)
                        buf=io.BytesIO(); img.save(buf,format="WEBP",lossless=True)
                        buf.seek(0); buf.name="sticker.webp"
                    buf.seek(0)
                
                # Save a copy to /tmp for debugging
                try:
                    for fpath in glob.glob("/tmp/jelly_debug_last.*"):
                        os.remove(fpath)
                    ext = "tgs" if buf.name.endswith(".tgs") else "webp"
                    with open(f"/tmp/jelly_debug_last.{ext}", "wb") as f:
                        f.write(buf.getvalue())
                    buf.seek(0)
                except Exception:
                    pass

                es="🎨"
                for a in doc.attributes:
                    if isinstance(a,(DocumentAttributeCustomEmoji,DocumentAttributeSticker)):
                        es=getattr(a,"alt",None) or "🎨"; break
                up=await self._client.upload_file(buf,file_name=buf.name)
                return await _upload_item(self._client,mee,up,mime,es,ptype=="emoji")
            ordered=await self._parallel(docs,_fn,"Перекраска",call,reply_markup=self._j_markup(uid))
            if not ordered: raise ValueError("Нет стикеров")
            clabel=gradient["name"] if gradient else (color or "без перекраски")
            title=s.get("pack_title") or "JellyColor "+clabel
            fn,err=await _safe_create_set(self._client,me.id,title,pname,ordered,ptype=="emoji",exists_mode=s.get("exists_mode","recreate"))
            if err: raise ValueError(err)
            
            links = ["https://t.me/" + ("addemoji/" if ptype=="emoji" else "addstickers/") + name for name in fn]
            main_link = links[0]
            links_text = "\n".join([f"• <a href=\"{l}\">{l}</a>" for l in links])
            
            stats=self.db.get("JellyColor","stats",[])
            clabel=gradient["name"] if gradient else (color or "без перекраски")
            for name, link in zip(fn, links):
                stats.append({"name":name,"link":link,"color":clabel,"count":len(ordered),"type":ptype,"ts":int(time.time())})
            self.db.set("JellyColor","stats",stats)
            tl="Стикерпак" if ptype=="sticker" else "Эмодзи-пак"
            tag=f"<code>{clabel}</code>"
            await call.edit(
                text=(pe("✅",PE["ok"])+" <b>Готово!</b>\n\n"
                      +pe("🖤",PE["brush"])+f" {tl} → {tag}\n"
                      +pe("📦",PE["pack"])+f" <b>{len(ordered)}</b> шт.\n\n"
                      +pe("🔗",PE["link"])+f" <b>Ссылки на паки:</b>\n{links_text}"),
                reply_markup=[[{"text":"Открыть","icon_custom_emoji_id":PE["link"],"emoji_id":PE["link"],"style":"success","url":main_link}]],
            )
            self._sessions.pop(uid,None)
        except asyncio.CancelledError:
            logger.info(".j final pack generation was cancelled.")
            raise
        except Exception as e:
            await call.edit(text=pe("❌",PE["err"])+" <code>"+str(e)+"</code>")
            await self._report_error(e, ptype, pname)
            self._sessions.pop(uid,None)

    # ─── .jc ────────────────────────────────────────────────────────────

    @loader.command()
    async def jc(self, message: Message):
        """Быстрая перекраска с созданием пака из 1 эмодзи: .jc #HEX (ответьте на эмодзи/стикер)"""
        reply=await message.get_reply_message()
        args=utils.get_args_raw(message).strip()
        if not reply or not args:
            await utils.answer(message,pe("ℹ️",PE["info"])+" Ответьте на эмодзи и напишите <code>.jc #FF3B30</code>"); return
        hc=args if args.startswith("#") else "#"+args
        if not re.fullmatch(r"#[0-9a-fA-F]{6}",hc): await utils.answer(message,pe("❌",PE["err"])+" Неверный HEX"); return
        td,tt,_=await self._resolve_target(reply)
        if not td: await utils.answer(message,pe("❌",PE["err"])+" Эмодзи/стикер не найден."); return
        msg=await utils.answer(message,pe("⏰",PE["clock"])+" Создаю...")
        try:
            is_emoji=(tt=="emoji")
            buf=await recolor_document(self._client,td,hc,is_emoji=is_emoji)
            
            # Save a copy to /tmp for debugging
            try:
                for fpath in glob.glob("/tmp/jelly_debug_last.*"):
                    os.remove(fpath)
                ext = "tgs" if buf.name.endswith(".tgs") else "webp"
                with open(f"/tmp/jelly_debug_last.{ext}", "wb") as f:
                    f.write(buf.getvalue())
                buf.seek(0)
            except Exception:
                pass

            me=await self._client.get_me(); mee=await self._client.get_input_entity("me")
            orig_mime=getattr(td,"mime_type","image/webp")
            mime="application/x-tgsticker" if orig_mime=="application/x-tgsticker" else "image/webp"
            es="🎨"
            for a in td.attributes:
                if isinstance(a,(DocumentAttributeCustomEmoji,DocumentAttributeSticker)):
                    es=getattr(a,"alt",None) or "🎨"; break
            uploaded=await self._client.upload_file(buf,file_name=buf.name)
            is_emoji=(tt=="emoji")
            item=await _upload_item(self._client,mee,uploaded,mime,es,is_emoji)
            sn="jc"+hc[1:].lower()+"_by_"+_get_bot_suffix(me)
            final_name,err=await _safe_create_set(self._client,me.id,"JellyColor "+hc,sn,[item],is_emoji)
            if err: raise ValueError(err)
            final_name_str = final_name[0] if isinstance(final_name, list) else final_name
            link="https://t.me/"+("addemoji/" if is_emoji else "addstickers/")+final_name_str
            await msg.edit(pe("✅",PE["ok"])+f" Готово!\n\n"+pe("🔗",PE["link"])+f" <a href=\"{link}\">{link}</a>")
        except Exception as e:
            await msg.edit(pe("❌",PE["err"])+" <code>"+str(e)+"</code>")
            await self._report_error(e, tt, sn)


    # ─── .jt — текстовые шаблоны ────────────────────────────────────────────────

    @loader.command()
    async def jt(self, message: Message):
        """Создать эмодзи-пак из шаблона с вашим текстом + выбор цвета"""
        self._expire()
        uid=message.sender_id
        self._tsessions[uid]={"ts":time.time(),"step":"template","template":None,"text":None,
                               "color":None,"pack_name":None,"preview_msg":None, "scale_factor": 0.8}
        await message.delete()
        await self.inline.form(text=self._jt_text(uid),reply_markup=self._jt_markup(uid),message=message,always_allow=[uid])
    def _jt_text(self, uid):
        s=self._tsessions[uid]; step=s["step"]
        if step=="template": return pe("🖤",PE["brush"])+" <b>Выберите шаблон</b>\n\nТекст <code>"+TEMPLATE_PLACEHOLDER+"</code> будет заменён на ваш."
        if step=="text": return pe("✍️",PE["write"])+f" <b>Введите текст</b>\n\nШаблон: <b>{s['template']['title']}</b>\n2-4 символа — оптимально."
        if step=="font": return pe("✍️",PE["write"])+f" <b>Выберите шрифт</b>\n\nТекст: <code>{s['text']}</code>"
        if step=="preview":
            return (pe("🔎",PE["eye"])+f" <b>Предпросмотр масштаба</b>\n\n"
                    f"Текст: <code>{s['text']}</code>\n"
                    f"Шрифт: <b>{s.get('font_title', 'Comfortaa')}</b>\n"
                    f"Текущий масштаб: <b>{s.get('scale_factor', 0.8):.2f}x</b> ({int(round(s.get('scale_factor', 0.8) * 100))}%)\n\n"
                    f"Первые 5 эмодзи отправлены в ваше <b>Избранное</b> (Saved Messages) для предпросмотра.\n"
                    f"Вы можете настроить масштаб кнопками ниже.")
        if step=="preview_gen":
            return pe("⏰",PE["clock"])+f" <b>Генерирую предпросмотр...</b>\n\nСоздаю первые 5 эмодзи с масштабом <b>{s.get('scale_factor', 0.8):.2f}x</b> и отправляю в Избранное."
        if step=="color":
            hist=self._color_history()
            hs=("\n"+pe("⏰",PE["clock"])+" Последние: "+"  ".join(f"<code>{c}</code>" for c in hist)) if hist else ""
            return pe("🎨",PE["palette"])+f" <b>Цвет эмодзи</b>\n\nТекст: <code>{s['text']}</code>{hs}"
        if step=="title": return pe("🏷",PE["sticker"])+f" <b>Название пака</b>\n\nТекст: <code>{s['text']}</code>" + (f"  Цвет: <code>{s['color']}</code>" if s.get('color') else "  (без перекраски)") + "\n\n<i>Введите отображаемое название (любые символы)</i>"
        if step=="name": return pe("🏷",PE["sticker"])+f" <b>short_name пака</b>\n\nНазвание: <b>{s.get('pack_title','')}</b>\n\n<i>Введите short_name — только a-z, 0-9, _</i>"
        if step=="exists_choice":
            return pe("⚠️",PE["info"])+f" <b>Пак уже существует!</b>\n\nПак <code>{s['pack_name']}</code> уже создан на вашем аккаунте. Выберите действие:"
        if step=="processing":
            return pe("⏰",PE["clock"])+f" <b>Создаю пак...</b>\n\nПожалуйста, подождите. Идет генерация эмодзи/стикеров."
        return pe("⏰",PE["clock"])+" <b>Создаём...</b>"

    def _jt_markup(self,uid):
        return self._patch_allow(self.__jt_markup_inner(uid), uid)

    def __jt_markup_inner(self,uid):
        s=self._tsessions[uid]; step=s["step"]
        if step=="template": return [[{"text":t["title"],"icon_custom_emoji_id":PE["sticker"],"emoji_id":PE["sticker"],
            "style":"primary","callback":self._jt_tmpl,"args":(uid,i)}] for i,t in enumerate(TEMPLATE_SETS)]
        if step=="text": return [
            [{"text":"Ввести текст","icon_custom_emoji_id":PE["palette"],"emoji_id":PE["palette"],"style":"primary",
              "input":"Текст (вместо "+TEMPLATE_PLACEHOLDER+")","handler":self._jt_text_in,"args":(uid,)}],
            [{"text":"⬅️ Назад","icon_custom_emoji_id":PE["back"],"emoji_id":PE["back"],"style":"danger","callback":self._jt_back,"args":(uid,)}]
        ]
        if step=="font":
            user_fonts = self.db.get("JellyColor", "user_fonts", [])
            buttons = [[{"text": "Comfortaa (По умолчанию)", "icon_custom_emoji_id": PE["sticker"],"emoji_id":PE["sticker"], "style": "primary", "callback": self._jt_font_sel, "args": (uid, "default")}]]
            for f in user_fonts:
                buttons.append([{"text": f["title"], "icon_custom_emoji_id": PE["sticker"],"emoji_id":PE["sticker"], "style": "primary", "callback": self._jt_font_sel, "args": (uid, f["title"])}])
            buttons.append([{"text":"⬅️ Назад","icon_custom_emoji_id":PE["back"],"emoji_id":PE["back"], "style": "danger", "callback":self._jt_back,"args":(uid,)}])
            return buttons
        if step=="preview":
            me_id = s.get("me_id") or uid
            saved_messages_link = f"tg://openmessage?user_id={me_id}"
            return [
                [
                    {"text": "🔎 Мельче (-10%)", "callback": self._jt_scale_change, "args": (uid, -0.1), "style": "primary"},
                    {"text": "🔍 Крупнее (+10%)", "callback": self._jt_scale_change, "args": (uid, 0.1), "style": "primary"},
                ],
                [
                    {"text": "📝 Свой масштаб (%)", "input": "Введите масштаб в % (например, 80 или 120)", "handler": self._jt_custom_scale_in, "args": (uid,), "style": "primary"},
                ],
                [
                    {"text": "✅ Применить", "icon_custom_emoji_id": PE["ok"],"emoji_id":PE["ok"], "style": "success", "callback": self._jt_confirm, "args": (uid,)},
                    {"text": "✏️ Изменить текст", "icon_custom_emoji_id": PE["brush"],"emoji_id":PE["brush"], "style": "primary", "callback": self._jt_retry, "args": (uid,)},
                ],
                [
                    {"text": "💬 Перейти в Избранное", "icon_custom_emoji_id": PE["link"],"emoji_id":PE["link"], "style": "success", "url": saved_messages_link}
                ],
                [
                    {"text":"⬅️ Назад","icon_custom_emoji_id":PE["back"],"emoji_id":PE["back"], "style": "danger", "callback":self._jt_back,"args":(uid,)}
                ]
            ]
        if step=="preview_gen":
            return [
                [{"text": "🛑 Остановить генерацию", "icon_custom_emoji_id": PE["err"],"emoji_id":PE["err"], "style": "danger", "callback": self._jt_cancel_generation, "args": (uid, "preview")}]
            ]
        if step=="color":
            rows=self._color_rows_with_gradient(uid,self._jt_col,self._jt_hex,self._jt_open_grad,
                                                 no_color_cb=self._jt_no_color,
                                                 custom_grad_cb=self._jt_custom_grad)
            for r in rows:
                for btn in r:
                    btn["emoji_id"] = btn.get("icon_custom_emoji_id")
                    if "HEX" in btn["text"] or "Градиент" in btn["text"]:
                        btn["style"] = "primary"
                    elif "Без перекраски" in btn["text"]:
                        btn["style"] = "primary"
            rows.append([{"text": "⬅️ Назад", "icon_custom_emoji_id": PE["back"],"emoji_id":PE["back"], "style": "danger", "callback": self._jt_back, "args": (uid,)}])
            return rows
        if step=="gradient_menu":
            rows = self._gradient_menu_markup(self._jt_grad,uid,self._jt_back_col)
            for r in rows:
                for btn in r:
                    btn["emoji_id"] = btn.get("icon_custom_emoji_id")
                    btn["style"] = "primary"
            return rows
        if step=="title": return [
            [{"text":"Ввести название","icon_custom_emoji_id":PE["sticker"],"emoji_id":PE["sticker"], "style": "primary", "input":"Например: My Cool Pack","handler":self._jt_title,"args":(uid,)}],
            [{"text":"⬅️ Назад","icon_custom_emoji_id":PE["back"],"emoji_id":PE["back"], "style": "danger", "callback":self._jt_back,"args":(uid,)}]
        ]
        if step=="name": return [
            [{"text":"Ввести short_name","icon_custom_emoji_id":PE["palette"],"emoji_id":PE["palette"], "style": "primary", "input":"a-z, 0-9, _ (без _by_username)","handler":self._jt_name,"args":(uid,)}],
            [{"text":"⬅️ Назад","icon_custom_emoji_id":PE["back"],"emoji_id":PE["back"], "style": "danger", "callback":self._jt_back,"args":(uid,)}]
        ]
        if step=="exists_choice":
            return [
                [
                    {"text": "Пересоздать (очистить пак)", "icon_custom_emoji_id": PE["trash"],"emoji_id":PE["trash"], "style": "danger", "callback": self._jt_handle_exists_choice, "args": (uid, "recreate")},
                ],
                [
                    {"text": "Добавить (сохранить старые)", "icon_custom_emoji_id": PE["pack"],"emoji_id":PE["pack"], "style": "success", "callback": self._jt_handle_exists_choice, "args": (uid, "add")},
                ],
                [
                    {"text": "⬅️ Назад", "icon_custom_emoji_id": PE["back"],"emoji_id":PE["back"], "style": "primary", "callback": self._jt_back, "args": (uid,)},
                ]
            ]
        if step=="processing":
            return [
                [{"text": "🛑 Остановить создание", "icon_custom_emoji_id": PE["err"],"emoji_id":PE["err"], "style": "danger", "callback": self._jt_cancel_generation, "args": (uid, "run")}]
            ]
        return []

    async def _jt_back(self, call, uid):
        s = self._tsessions.get(uid)
        if not s: await call.answer("Сессия устарела.", show_alert=True); return
        step = s["step"]
        if step == "text":
            s["step"] = "template"
        elif step == "font":
            s["step"] = "text"
        elif step == "preview":
            s["step"] = "font"
        elif step == "color":
            s["step"] = "preview"
        elif step == "gradient_menu":
            s["step"] = "color"
        elif step == "title":
            s["step"] = "color"
        elif step == "name":
            s["step"] = "title"
        elif step == "exists_choice":
            s["step"] = "name"
        await call.edit(text=self._jt_text(uid), reply_markup=self._jt_markup(uid))

    async def _jt_cancel_generation(self, call, uid, task_type):
        s = self._tsessions.get(uid)
        if not s: await call.answer("Сессия устарела.", show_alert=True); return
        if task_type == "preview":
            task = s.get("preview_task")
            if task and not task.done():
                task.cancel()
            s["preview_running"] = False
            s["step"] = "font"
            await call.answer("🛑 Генерация предпросмотра остановлена", show_alert=True)
        elif task_type == "run":
            task = s.get("run_task")
            if task and not task.done():
                task.cancel()
            s["step"] = "title"
            await call.answer("🛑 Генерация пака остановлена", show_alert=True)
        await call.edit(text=self._jt_text(uid), reply_markup=self._jt_markup(uid))

    async def _jt_custom_scale_in(self, call, value, uid):
        s = self._tsessions.get(uid)
        if not s: await call.answer("Сессия устарела.", show_alert=True); return
        if s.get("preview_running"):
            await call.answer("⏳ Генерируется предыдущий предпросмотр, подождите...", show_alert=True)
            return
        val_str = value.strip().replace("%", "")
        try:
            val_pct = float(val_str)
            if val_pct < 10 or val_pct > 300:
                await call.answer("Масштаб должен быть от 10% до 300%", show_alert=True)
                return
            s["scale_factor"] = round(val_pct / 100.0, 2)
        except ValueError:
            await call.answer("Введите корректное число (например, 80 или 120)", show_alert=True)
            return
        s["step"] = "preview_gen"
        await call.edit(text=self._jt_text(uid), reply_markup=self._jt_markup(uid))
        s["preview_task"] = asyncio.ensure_future(self._jt_generate_and_send_preview(uid, call))

    async def _jt_tmpl(self,call,uid,idx):
        s=self._tsessions.get(uid)
        if not s: await call.answer("Сессия устарела.",show_alert=True); return
        s["template"]=TEMPLATE_SETS[idx]; s["step"]="text"
        await call.edit(text=self._jt_text(uid),reply_markup=self._jt_markup(uid))

    async def _jt_text_in(self,call,value,uid):
        s=self._tsessions.get(uid)
        if not s: await call.answer("Сессия устарела.",show_alert=True); return
        c=value.strip()
        if not c: await call.answer("Пустой текст.",show_alert=True); return
        if len(c)>12: await call.answer("Макс 12 символов.",show_alert=True); return
        s["text"]=c; s["step"]="font"
        await call.edit(text=self._jt_text(uid),reply_markup=self._jt_markup(uid))

    async def _jt_font_sel(self, call, uid, font_title):
        s = self._tsessions.get(uid)
        if not s: await call.answer("Сессия устарела.", show_alert=True); return
        if s.get("preview_running"):
            await call.answer("⏳ Генерируется предыдущий предпросмотр, подождите...", show_alert=True)
            return
        if font_title == "default":
            s["font_path"] = None
            s["font_title"] = "Comfortaa"
        else:
            user_fonts = self.db.get("JellyColor", "user_fonts", [])
            found = next((f for f in user_fonts if f["title"] == font_title), None)
            if found:
                s["font_path"] = found["path"]
                s["font_title"] = found["title"]
            else:
                s["font_path"] = None
                s["font_title"] = "Comfortaa"
        s["step"] = "preview_gen"
        await call.edit(text=self._jt_text(uid), reply_markup=self._jt_markup(uid))
        s["preview_task"] = asyncio.ensure_future(self._jt_generate_and_send_preview(uid, call))

    async def _jt_scale_change(self, call, uid, delta):
        s = self._tsessions.get(uid)
        if not s: await call.answer("Сессия устарела.", show_alert=True); return
        if s.get("preview_running"):
            await call.answer("⏳ Генерируется предыдущий предпросмотр, подождите...", show_alert=True)
            return
        s["scale_factor"] = round(max(0.1, min(3.0, s.get("scale_factor", 0.8) + delta)), 1)
        s["step"] = "preview_gen"
        await call.edit(text=self._jt_text(uid), reply_markup=self._jt_markup(uid))
        s["preview_task"] = asyncio.ensure_future(self._jt_generate_and_send_preview(uid, call))

    async def _jt_generate_and_send_preview(self, uid, call):
        s = self._tsessions.get(uid)
        if not s: return
        s["preview_running"] = True
        if "scale_factor" not in s:
            s["scale_factor"] = 0.8
        tmpl = s["template"]
        txt = s["text"]
        font_path = s.get("font_path")
        if not font_path:
            font_path = _ensure_font()
        try:
            try:
                fs = await self._client(functions.messages.GetStickerSetRequest(
                    stickerset=types.InputStickerSetShortName(short_name=tmpl["short_name"]), hash=0
                ))
                docs = list(fs.documents)[:5]
            except Exception as e:
                await call.edit(text=pe("❌",PE["err"])+f" Ошибка шаблона: <code>{e}</code>")
                return
            
            me = await self._client.get_me()
            s["me_id"] = me.id
            
            try:
                await self._client.send_message(
                    "me", 
                    f"<b>🎨 JellyColor: Предпросмотр</b>\n"
                    f"Шаблон: <code>{tmpl['title']}</code>\n"
                    f"Текст: <code>{txt}</code>\n"
                    f"Масштаб: <code>{s['scale_factor']:.2f}x</code>"
                )
            except Exception:
                pass

            loop = asyncio.get_event_loop()
            for doc in docs:
                try:
                    raw = await download_cached(self._client, doc)
                    mime = getattr(doc, "mime_type", "")
                    if mime == "application/x-tgsticker":
                        def _process_tgs():
                            lottie_obj = json_loads(gzip.decompress(raw))
                            modify_lottie(lottie_obj, txt, font_path, scale_factor=s["scale_factor"])
                            return compress_tgs(lottie_obj)
                        patched = await loop.run_in_executor(None, _process_tgs)
                        buf = io.BytesIO(patched)
                        buf.name = "preview_sticker.tgs"
                    else:
                        def _process_img():
                            img = Image.open(io.BytesIO(raw)).convert("RGBA").resize((100,100), Image.LANCZOS)
                            buf = io.BytesIO()
                            img.save(buf, format="WEBP", lossless=True)
                            buf.seek(0)
                            return buf.getvalue()
                        img_data = await loop.run_in_executor(None, _process_img)
                        buf = io.BytesIO(img_data)
                        buf.name = "preview_sticker.webp"
                    up = await self._client.upload_file(buf, file_name=buf.name)
                    await self._client.send_file("me", up, force_document=False)
                except Exception as e:
                    logger.exception("Failed to send preview item")
        except asyncio.CancelledError:
            logger.info("Preview generation task was cancelled.")
            raise
        finally:
            s["preview_running"] = False
            is_cancelled = False
            try:
                t = asyncio.current_task()
                if t and t.cancelled():
                    is_cancelled = True
            except Exception:
                pass
            
            if not is_cancelled:
                if uid in self._tsessions and self._tsessions[uid] is s:
                    s["step"] = "preview"
                    await call.edit(text=self._jt_text(uid), reply_markup=self._jt_markup(uid))
                    try:
                        await call.answer("💬 Первые 5 эмодзи отправлены в Избранное (Saved Messages) для предпросмотра!", show_alert=True)
                    except Exception:
                        pass

    async def _jt_confirm(self,call,uid):
        s=self._tsessions.get(uid)
        if not s: await call.answer("Сессия устарела.",show_alert=True); return
        if s.get("preview_running"):
            await call.answer("⏳ Подождите окончания генерации предпросмотра.", show_alert=True)
            return
        s["step"]="color"
        await call.edit(text=self._jt_text(uid),reply_markup=self._jt_markup(uid))

    async def _jt_retry(self,call,uid):
        s=self._tsessions.get(uid)
        if not s: await call.answer("Сессия устарела.",show_alert=True); return
        if s.get("preview_running"):
            await call.answer("⏳ Подождите окончания генерации предпросмотра.", show_alert=True)
            return
        s["step"]="text"; s["text"]=None
        await call.edit(text=self._jt_text(uid),reply_markup=self._jt_markup(uid))

    async def _jt_col(self,call,uid,hc):
        s=self._tsessions.get(uid)
        if not s: await call.answer("Сессия устарела.",show_alert=True); return
        s["color"]=hc; s["gradient"]=None; s["step"]="title"
        await call.edit(text=self._jt_text(uid),reply_markup=self._jt_markup(uid))

    async def _jt_hex(self,call,value,uid):
        s=self._tsessions.get(uid)
        if not s: await call.answer("Сессия устарела.",show_alert=True); return
        c=value.strip()
        if not c.startswith("#"): c="#"+c
        if not re.fullmatch(r"#[0-9a-fA-F]{6}",c): await call.answer("Неверный HEX.",show_alert=True); return
        s["color"]=c.upper(); s["gradient"]=None; s["step"]="title"
        await call.edit(text=self._jt_text(uid),reply_markup=self._jt_markup(uid))

    async def _jt_open_grad(self,call,uid):
        s=self._tsessions.get(uid)
        if not s: await call.answer("Сессия устарела.",show_alert=True); return
        s["step"]="gradient_menu"
        await call.edit(text=self._jt_text(uid),reply_markup=self._jt_markup(uid))

    async def _jt_grad(self,call,uid,grad_id):
        s=self._tsessions.get(uid)
        if not s: await call.answer("Сессия устарела.",show_alert=True); return
        user_gradients = self.db.get("JellyColor", "user_gradients", [])
        g=next((x for x in GRADIENT_PRESETS + user_gradients if x["id"]==grad_id),None)
        if not g: return
        s["gradient"]=g; s["color"]="grad:"+g["name"]; s["step"]="title"
        await call.edit(text=self._jt_text(uid),reply_markup=self._jt_markup(uid))

    async def _jt_back_col(self,call,uid):
        s=self._tsessions.get(uid)
        if not s: await call.answer("Сессия устарела.",show_alert=True); return
        s["step"]="color"
        await call.edit(text=self._jt_text(uid),reply_markup=self._jt_markup(uid))

    async def _jt_no_color(self,call,uid):
        s=self._tsessions.get(uid)
        if not s: await call.answer("Сессия устарела.",show_alert=True); return
        s["color"]=None; s["gradient"]=None; s["step"]="title"
        await call.edit(text=self._jt_text(uid),reply_markup=self._jt_markup(uid))

    async def _jt_custom_grad(self,call,value,uid):
        s=self._tsessions.get(uid)
        if not s: await call.answer("Сессия устарела.",show_alert=True); return
        parts=[p.strip() for p in value.split(",")]
        colors=[]
        for p in parts:
            c=p if p.startswith("#") else "#"+p
            if re.fullmatch(r"#[0-9a-fA-F]{6}",c): colors.append(c.upper())
        if len(colors)<2:
            await call.answer("Нужно минимум 2 HEX через запятую, например #FF0000,#0000FF",show_alert=True); return
        g={"id":"custom","name":"✏️ Свой","colors":colors,"dir":"d"}
        s["gradient"]=g; s["color"]="grad:✏️ Свой"; s["step"]="title"
        await call.edit(text=self._jt_text(uid),reply_markup=self._jt_markup(uid))


    async def _jt_title(self,call,value,uid):
        s=self._tsessions.get(uid)
        if not s: await call.answer("Сессия устарела.",show_alert=True); return
        title=value.strip()
        if not title: await call.answer("Название не может быть пустым.",show_alert=True); return
        s["pack_title"]=title; s["step"]="name"
        await call.edit(text=self._jt_text(uid),reply_markup=self._jt_markup(uid))

    async def _jt_name(self,call,value,uid):
        s=self._tsessions.get(uid)
        if not s: await call.answer("Сессия устарела.",show_alert=True); return
        c=value.strip().lower()
        if not validate_short_name(c): await call.answer("Только a-z,0-9,_",show_alert=True); return
        me=await self._client.get_me()
        pname=c+"_by_"+_get_bot_suffix(me)
        s["pack_name"]=pname
        
        # Check if pack already exists
        exists = False
        try:
            await self._client(functions.messages.GetStickerSetRequest(
                stickerset=types.InputStickerSetShortName(short_name=pname), hash=0
            ))
            exists = True
        except Exception:
            pass
            
        if exists:
            s["step"]="exists_choice"
            await call.edit(text=self._jt_text(uid), reply_markup=self._jt_markup(uid))
        else:
            s["step"]="processing"
            s["exists_mode"]="recreate"
            await call.edit(text=self._jt_text(uid), reply_markup=self._jt_markup(uid))
            s["run_task"] = asyncio.ensure_future(self._jt_run(call,uid))

    async def _jt_handle_exists_choice(self, call, uid, choice):
        s=self._tsessions.get(uid)
        if not s: await call.answer("Сессия устарела.",show_alert=True); return
        if choice == "cancel":
            s["step"]="name"
            await call.edit(text=self._jt_text(uid), reply_markup=self._jt_markup(uid))
            return
        s["exists_mode"] = choice
        s["step"]="processing"
        await call.edit(text=self._jt_text(uid), reply_markup=self._jt_markup(uid))
        s["run_task"] = asyncio.ensure_future(self._jt_run(call, uid))

    async def _jt_run(self,call,uid):
        s=self._tsessions.get(uid)
        if not s: return
        try:
            tmpl,txt,pname,color=s["template"],s["text"],s["pack_name"],s.get("color")
            gradient=s.get("gradient")
            try:
                fs=await self._client(functions.messages.GetStickerSetRequest(
                    stickerset=types.InputStickerSetShortName(short_name=tmpl["short_name"]),hash=0))
            except Exception as e:
                await call.edit(text=pe("❌",PE["err"])+" Шаблон: <code>"+str(e)+"</code>")
                self._tsessions.pop(uid,None); return
            docs=list(fs.documents)
            me=await self._client.get_me(); mee=await self._client.get_input_entity("me")
            async def _fn(i,doc):
                raw=await download_cached(self._client,doc)
                mime=getattr(doc,"mime_type","")
                loop = asyncio.get_event_loop()
                if mime=="application/x-tgsticker":
                    def _process_tgs():
                        lottie_obj = json_loads(gzip.decompress(raw))
                        modify_lottie(lottie_obj, txt, s.get("font_path"), scale_factor=s.get("scale_factor", 1.0))
                        if gradient:
                            apply_gradient_lottie(lottie_obj, gradient)
                            outline_color = _dominant_color_from_gradient(gradient["colors"])
                        elif color:
                            tint_lottie(lottie_obj, color)
                            outline_color = color
                        else:
                            outline_color = None
                            
                        if outline_color:
                            _set_text_neon_style(lottie_obj, outline_color)
                        return compress_tgs(lottie_obj)
                    patched = await loop.run_in_executor(None, _process_tgs)
                    buf=io.BytesIO(patched); buf.name="sticker.tgs"
                else:
                    def _process_img():
                        img=Image.open(io.BytesIO(raw)).convert("RGBA").resize((100,100),Image.LANCZOS)
                        if gradient:
                            img=tint_image_gradient(img, gradient["colors"], gradient.get("dir", "d"))
                        elif color and not color.startswith("grad:"):
                            img=tint_image(img,color)
                        buf=io.BytesIO()
                        img.save(buf,format="WEBP",lossless=True)
                        buf.seek(0)
                        return buf.getvalue()
                    img_data = await loop.run_in_executor(None, _process_img)
                    buf=io.BytesIO(img_data); buf.name="sticker.webp"
                    mime="image/webp"

                es="✨"
                for a in doc.attributes:
                    if isinstance(a,(DocumentAttributeCustomEmoji,DocumentAttributeSticker)):
                        es=getattr(a,"alt",None) or "✨"; break
                up=await self._client.upload_file(buf,file_name=buf.name)
                return await _upload_item(self._client,mee,up,mime,es,True)
            ordered=await self._parallel(docs,_fn,"Создаём",call,reply_markup=self._jt_markup(uid))
            if not ordered:
                await call.edit(text=pe("❌",PE["err"])+" Ни один эмодзи не обработан.", reply_markup=self._jt_markup(uid))
                self._tsessions.pop(uid,None); return
            color_label=gradient["name"] if gradient else (color or "без перекраски")
            pack_title=s.get("pack_title") or txt+" Emoji Pack"
            fn,err=await _safe_create_set(self._client,me.id,pack_title,pname,ordered,True,exists_mode=s.get("exists_mode","recreate"))
            if err: raise ValueError(err)
            
            links = ["https://t.me/addemoji/" + name for name in fn]
            main_link = links[0]
            links_text = "\n".join([f"• <a href=\"{l}\">{l}</a>" for l in links])
            
            stats=self.db.get("JellyColor","stats",[])
            for name, link in zip(fn, links):
                stats.append({"name":name,"link":link,"color":color or "text","count":len(ordered),"type":"emoji","ts":int(time.time())})
            self.db.set("JellyColor","stats",stats)
            await call.edit(
                text=(pe("✅",PE["ok"])+" <b>Готово!</b>\n\n"
                      +pe("✍️",PE["write"])+f" Текст: <code>{txt}</code>\n"
                      +pe("🎨",PE["palette"])+f" Цвет: <code>{color_label}</code>\n"
                      +pe("📦",PE["pack"])+f" <b>{len(ordered)}</b> шт.\n\n"
                      +pe("🔗",PE["link"])+f" <b>Ссылки на паки:</b>\n{links_text}"),
                reply_markup=[[{"text":"Открыть","icon_custom_emoji_id":PE["link"],"emoji_id":PE["link"],"style":"success","url":main_link}]],
            )
            self._tsessions.pop(uid,None)
        except asyncio.CancelledError:
            logger.info(".jt final pack generation was cancelled.")
            raise
        except Exception as e:
            await call.edit(text=pe("❌",PE["err"])+" <code>"+str(e)+"</code>")
            await self._report_error(e, "emoji", pname)
            self._tsessions.pop(uid,None)

    # ─── Fonts commands ───────────────────────────────────────────────────────

    @loader.command()
    async def jaddfont(self, message: Message):
        """Добавить свой шрифт (.ttf или .otf). Ответьте на файл шрифта: .jaddfont <название>"""
        args = utils.get_args_raw(message).strip()
        if not args:
            await utils.answer(message, pe("ℹ️", PE["info"]) + " Укажите название шрифта: <code>.jaddfont <название></code>")
            return
        
        reply = await message.get_reply_message()
        if not reply or not reply.media or not reply.document:
            await utils.answer(message, pe("❌", PE["err"]) + " Ответьте на файл шрифта (.ttf или .otf)")
            return
        
        doc = reply.document
        filename = getattr(doc.attributes[0], "file_name", "") if doc.attributes else ""
        if not filename:
            filename = "font.ttf"
        
        ext = os.path.splitext(filename)[1].lower()
        if ext not in [".ttf", ".otf"]:
            await utils.answer(message, pe("❌", PE["err"]) + " Поддерживаются только файлы .ttf и .otf")
            return
        
        # Ensure directory exists
        os.makedirs("/root/jelly_fonts", exist_ok=True)
        
        # We can use MD5 hash of title for filename to avoid collisions and invalid chars
        safe_title = "".join([c for c in args if c.isalnum() or c in (" ", "_", "-")]).strip()
        if not safe_title:
            await utils.answer(message, pe("❌", PE["err"]) + " Недопустимое название шрифта.")
            return

        h = hashlib.md5(safe_title.encode("utf-8")).hexdigest()
        dest_filename = f"{h}{ext}"
        dest_path = os.path.join("/root/jelly_fonts", dest_filename)
        
        # Check if font with same title already exists
        user_fonts = self.db.get("JellyColor", "user_fonts", [])
        if any(f["title"].lower() == safe_title.lower() for f in user_fonts):
            await utils.answer(message, pe("❌", PE["err"]) + f" Шрифт с названием <b>{safe_title}</b> уже существует.")
            return
            
        await utils.answer(message, pe("⏰", PE["clock"]) + " Скачиваю шрифт...")
        try:
            await self._client.download_media(doc, dest_path)
        except Exception as e:
            logger.exception("Failed to download font in .jaddfont command")
            await utils.answer(message, pe("❌", PE["err"]) + f" Не удалось скачать шрифт: <code>{e}</code>")
            return
            
        user_fonts.append({
            "title": safe_title,
            "path": dest_path,
            "filename": dest_filename
        })
        self.db.set("JellyColor", "user_fonts", user_fonts)
        await utils.answer(message, pe("✅", PE["ok"]) + f" Шрифт <b>{safe_title}</b> успешно добавлен!")

    @loader.command()
    async def jdelfont(self, message: Message):
        """Удалить шрифт: .jdelfont <название>"""
        args = utils.get_args_raw(message).strip()
        if not args:
            await utils.answer(message, pe("ℹ️", PE["info"]) + " Укажите название шрифта: <code>.jdelfont <название></code>")
            return
        
        user_fonts = self.db.get("JellyColor", "user_fonts", [])
        found = next((f for f in user_fonts if f["title"].lower() == args.lower()), None)
        if not found:
            await utils.answer(message, pe("❌", PE["err"]) + f" Шрифт <b>{args}</b> не найден.")
            return
        
        user_fonts.remove(found)
        self.db.set("JellyColor", "user_fonts", user_fonts)
        
        if os.path.exists(found["path"]):
            try:
                os.remove(found["path"])
            except Exception as e:
                logger.warning(f"Failed to delete font file {found['path']}: {e}", exc_info=True)
                
        await utils.answer(message, pe("✅", PE["ok"]) + f" Шрифт <b>{found['title']}</b> удален.")

    @loader.command()
    async def jfonts(self, message: Message):
        """Список установленных шрифтов"""
        user_fonts = self.db.get("JellyColor", "user_fonts", [])
        if not user_fonts:
            await utils.answer(message, pe("ℹ️", PE["info"]) + " Нет пользовательских шрифтов. Будет использоваться системный Comfortaa.")
            return
        
        lines = [pe("🔤", PE["brush"]) + " <b>Пользовательские шрифты:</b>\n"]
        for i, f in enumerate(user_fonts, 1):
            lines.append(f"<b>{i}.</b> {f['title']} (<code>{os.path.basename(f['path'])}</code>)")
        await utils.answer(message, "\n".join(lines), parse_mode="HTML")

    # ─── .jstats ──────────────────────────────────────────────────────────────

    @loader.command()
    async def jstats(self, message: Message):
        """Статистика операций"""
        stats=self.db.get("JellyColor","stats",[])
        if not stats: await utils.answer(message,pe("📊",PE["stats"])+" Пусто."); return
        total_s=sum(e.get("count",0) for e in stats)
        chist={}
        for e in stats:
            c=e.get("color","")
            if c and c!="text": chist[c]=chist.get(c,0)+1
        top=[f"<code>{c}</code>×{n}" for c,n in sorted(chist.items(),key=lambda x:-x[1])[:3]]
        lines=[
            pe("📊",PE["stats"])+" <b>JellyColor</b>\n",
            pe("📦",PE["pack"])+f" Операций: <b>{len(stats)}</b> | Стикеров: <b>{total_s}</b>",
            pe("🎨",PE["palette"])+" Топ цвета: "+("  ".join(top) or "—"),
            "\n<b>Последние 15:</b>",
        ]
        for i,e in enumerate(reversed(stats[-15:]),1):
            c=e.get("color","?"); t=e.get("type","emoji")
            cs="текст" if c=="text" else f"<code>{c}</code>"
            ti=pe("🏷",PE["sticker"]) if t=="sticker" else pe("✅",PE["ok"])
            lines.append(f"\n<b>{i}.</b> {ti} <code>{e['name']}</code>\n   {pe(chr(0x1f58c),PE['brush'])} {cs} | {pe(chr(0x1f4e6),PE['pack'])} <b>{e['count']}</b>\n   <a href=\"{e['link']}\">{e['link']}</a>")
        await utils.answer(message,"\n".join(lines),parse_mode="HTML")

    # ─── .jdel ────────────────────────────────────────────────────────────────

    @loader.command()
    async def jdel(self, message: Message):
        """Удалить запись из статистики: .jdel short_name"""
        args=utils.get_args_raw(message).strip()
        if not args: await utils.answer(message,pe("ℹ️",PE["info"])+" <code>.jdel short_name</code>"); return
        stats=self.db.get("JellyColor","stats",[])
        new=[e for e in stats if e.get("name")!=args]
        if len(new)==len(stats): await utils.answer(message,pe("❌",PE["err"])+f" <code>{args}</code> не найден."); return
        self.db.set("JellyColor","stats",new)
        await utils.answer(message,pe("✅",PE["ok"])+f" Удалено: <code>{args}</code>")

    # ─── .jexport ─────────────────────────────────────────────────────────────

    @loader.command()
    async def jexport(self, message: Message):
        """Экспорт статистики в JSON"""
        stats=self.db.get("JellyColor","stats",[])
        if not stats: await utils.answer(message,pe("ℹ️",PE["info"])+" Пустая статистика."); return
        buf=io.BytesIO(json_dumps(stats, indent=True)); buf.name="jelly_stats.json"; buf.seek(0)
        await self._client.send_file(message.chat_id,buf,
            caption=pe("📤",PE["export"])+f" Экспорт — <b>{len(stats)}</b> записей",parse_mode="HTML")
        await message.delete()

    @loader.command()
    async def jaddgrad(self, message: Message):
        """Добавить свой градиент: .jaddgrad <название> <HEX,HEX,...> [h/v/d/dr]"""
        args = utils.get_args_raw(message).strip()
        if not args:
            await utils.answer(message, pe("ℹ️", PE["info"]) + " Использование: <code>.jaddgrad <название> <HEX,HEX,...> [направление]</code>\nПример: <code>.jaddgrad Мой #FF0000,#0000FF d</code>")
            return
            
        parts = args.split(maxsplit=2)
        if len(parts) < 2:
            await utils.answer(message, pe("❌", PE["err"]) + " Укажите название и цвета (HEX через запятую)")
            return
            
        name = parts[0]
        colors_str = parts[1]
        direction = parts[2].lower() if len(parts) > 2 else "d"
        if direction not in ("h", "v", "d", "dr"):
            direction = "d"
            
        color_parts = [c.strip() for c in colors_str.split(",")]
        colors = []
        for p in color_parts:
            c = p if p.startswith("#") else "#" + p
            if re.fullmatch(r"#[0-9a-fA-F]{6}", c):
                colors.append(c.upper())
                
        if len(colors) < 2:
            await utils.answer(message, pe("❌", PE["err"]) + " Нужно указать минимум 2 корректных HEX-цвета через запятую")
            return
            
        user_gradients = self.db.get("JellyColor", "user_gradients", [])
        if any(g["name"].lower().replace("✨ ", "") == name.lower() for g in user_gradients):
            await utils.answer(message, pe("❌", PE["err"]) + f" Градиент с названием <b>{name}</b> уже существует.")
            return
            
        g_id = "user_" + uuid.uuid4().hex[:8]
        new_g = {
            "id": g_id,
            "name": "✨ " + name,
            "colors": colors,
            "dir": direction
        }
        user_gradients.append(new_g)
        self.db.set("JellyColor", "user_gradients", user_gradients)
        await utils.answer(message, pe("✅", PE["ok"]) + f" Градиент <b>{name}</b> успешно добавлен!")

    @loader.command()
    async def jdelgrad(self, message: Message):
        """Удалить свой градиент: .jdelgrad <название>"""
        name = utils.get_args_raw(message).strip()
        if not name:
            await utils.answer(message, pe("ℹ️", PE["info"]) + " Укажите название градиента для удаления: <code>.jdelgrad <название></code>")
            return
            
        user_gradients = self.db.get("JellyColor", "user_gradients", [])
        new_list = [g for g in user_gradients if g["name"].lower().replace("✨ ", "") != name.lower()]
        if len(new_list) == len(user_gradients):
            await utils.answer(message, pe("❌", PE["err"]) + f" Пользовательский градиент <b>{name}</b> не найден.")
            return
            
        self.db.set("JellyColor", "user_gradients", new_list)
        await utils.answer(message, pe("✅", PE["ok"]) + f" Градиент <b>{name}</b> удален.")

    @loader.command()
    async def jgrads(self, message: Message):
        """Список доступных градиентов"""
        user_gradients = self.db.get("JellyColor", "user_gradients", [])
        lines = [pe("🎨", PE["stats"]) + " <b>Системные градиенты:</b>\n"]
        for g in GRADIENT_PRESETS:
            lines.append(f"• {g['name']} (<code>{g['dir']}</code>): <code>{','.join(g['colors'])}</code>")
            
        if user_gradients:
            lines.append("\n<b>✨ Пользовательские градиенты:</b>\n")
            for g in user_gradients:
                clean_name = g['name'].replace("✨ ", "")
                lines.append(f"• {clean_name} (<code>{g['dir']}</code>): <code>{','.join(g['colors'])}</code>")
                
        await utils.answer(message, "\n".join(lines), parse_mode="HTML")

    # ─── .jdump ───────────────────────────────────────────────────────────────

    @loader.command()
    async def jdump(self, message: Message):
        """Ответьте на эмодзи — дамп TGS + JSON"""
        reply=await message.get_reply_message()
        if not reply: await utils.answer(message,pe("❌",PE["err"])+" Ответьте на эмодзи."); return
        eid=None
        for ent in (reply.entities or []):
            if isinstance(ent,MessageEntityCustomEmoji): eid=ent.document_id; break
        if eid is None: await utils.answer(message,pe("❌",PE["err"])+" Премиум эмодзи не найдено."); return
        msg=await utils.answer(message,pe("⏰",PE["clock"])+" Дамплю...")
        docs=await self._client(functions.messages.GetCustomEmojiDocumentsRequest(document_id=[eid]))
        if not docs: await msg.edit(pe("❌",PE["err"])+" Нет документа."); return
        doc=docs[0]; raw=await download_cached(self._client,doc)
        mime=getattr(doc,"mime_type","")
        lines=[f"id: {eid}",f"mime: {mime}",f"size: {len(raw)} bytes"]
        if mime=="application/x-tgsticker":
            try:
                lottie=json_loads(gzip.decompress(raw))
                lines+=[f"w={lottie.get('w')} h={lottie.get('h')} fr={lottie.get('fr')} v={lottie.get('v')}",
                        f"layers: {len(lottie.get('layers',[]))}",
                        f"assets: {len(lottie.get('assets',[]))}",
                        f"text_bounds: {_get_textgroup_bounds(lottie)}",
                        f"dominant_color: {get_dominant_lottie_color(lottie)}",
                        "\n--- FULL JSON ---",
                        json_dumps(lottie, indent=True).decode("utf-8")]
            except Exception as e:
                logger.exception("Failed to decompress and parse Lottie in .jdump command")
                lines.append(f"ERROR: {e}")
        bd=io.BytesIO("\n".join(lines).encode()); bd.name=f"dump_{eid}.txt"; bd.seek(0)
        br=io.BytesIO(raw); br.name=f"raw_{eid}.tgs"; br.seek(0)
        # Отправляем файлы по отдельности — SendMultiMediaRequest падает на таких документах
        await self._client.send_file(message.chat_id,bd,caption=f"📄 Dump <code>{eid}</code>",parse_mode="HTML")
        await self._client.send_file(message.chat_id,br)
        await msg.delete()

