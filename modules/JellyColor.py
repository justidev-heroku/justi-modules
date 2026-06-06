# ╔══════════════════════════════════════════════════════════════════╗
# ║                        🎨 JellyColor v3.8.1                     ║
# ║           Перекраска стикеров/эмодзи + текстовые шаблоны         ║
# ║  v3.8.1: контрастный текст, фикс 100x100 emoji, фикс съезда слоёв  ║
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
# requires: Pillow fonttools

__version__ = (3, 8, 3)

import asyncio
from lottie.objects import Animation, Group, ShapeLayer, TextLayer, Path, Bezier, Fill, Color, TransformShape, BoundingBox, FillRule
from lottie import NVector
import glob
import gzip
import io
import json
import math
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image

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

from .. import loader, utils


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
    {"title": "♣️ BLACK HOLE",  "short_name": "main_by_emojicreationbot"},
    {"title": "🎨 COLOR",       "short_name": "testmain1_by_justidev"},
    {"title": "🌀 ALL IN ALL",  "short_name": "SpizdiAllEmojis"},
]

TEMPLATE_PLACEHOLDER = "emc"

SESSION_TTL = 600
CACHE_DIR = "/tmp/jelly_cache"
MAX_TGS_SIZE = 63 * 1024
RECOLOR_CONCURRENCY = 12

os.makedirs(CACHE_DIR, exist_ok=True)


def pe(emoji: str, eid: str) -> str:
    return '<tg-emoji emoji-id="' + eid + '">' + emoji + '</tg-emoji>'


def hex_to_rgb(hex_color: str):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(r: int, g: int, b: int) -> str:
    return "#{:02X}{:02X}{:02X}".format(r, g, b)


def _luminance(hex_color: str) -> float:
    """Вычисляет относительную яркость цвета (0=чёрный, 1=белый)."""
    r, g, b = hex_to_rgb(hex_color)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255


def _contrast_text_color(hex_color: str) -> str:
    """Возвращает '#FFFFFF' для тёмных фонов, '#000000' для светлых."""
    return "#FFFFFF" if _luminance(hex_color) < 0.5 else "#000000"


def _dominant_color_from_gradient(colors: list) -> str:
    """Средний цвет градиента для определения контраста."""
    if not colors:
        return "#000000"
    rs, gs, bs = [], [], []
    for c in colors:
        r, g, b = hex_to_rgb(c)
        rs.append(r); gs.append(g); bs.append(b)
    return rgb_to_hex(sum(rs)//len(rs), sum(gs)//len(gs), sum(bs)//len(bs))


# ─── Image tinting ────────────────────────────────────────────────────────────

def tint_image(img: Image.Image, hex_color: str) -> Image.Image:
    from PIL import ImageChops
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
    tw, th = 64, 64
    img = Image.new("RGB", (tw, th))
    pixels = []
    n = len(colors_hex)
    rgbs = [hex_to_rgb(c) for c in colors_hex]
    
    for y in range(th):
        for x in range(tw):
            if direction == "h":
                t = x / (tw - 1)
            elif direction == "v":
                t = y / (th - 1)
            elif direction in ("d", "dl"):
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
            
    img.putdata(pixels)
    return img.resize((width, height), Image.BILINEAR)


def tint_image_gradient(img: Image.Image, colors_hex: list, direction: str) -> Image.Image:
    from PIL import ImageChops
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
        except Exception:
            pass
    data = await client.download_media(doc, bytes)
    try:
        with open(path, "wb") as f:
            f.write(data)
    except Exception:
        pass
    return data


# ─── TGS size guard ───────────────────────────────────────────────────────────

def compress_tgs(lottie: dict) -> bytes:
    raw = json.dumps(lottie, separators=(",", ":")).encode("utf-8")
    compressed = gzip.compress(raw, compresslevel=9)
    if len(compressed) > MAX_TGS_SIZE:
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
        raw = json.dumps(lottie, separators=(",", ":")).encode("utf-8")
        compressed = gzip.compress(raw, compresslevel=9)

    if len(compressed) > MAX_TGS_SIZE:
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
        raw = json.dumps(lottie, separators=(",", ":")).encode("utf-8")
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
    import logging; log = logging.getLogger("JellyColor")
    comfortaa_system_path = _FONT_SEARCH[0]
    if os.path.exists(comfortaa_system_path):
        return comfortaa_system_path
    if os.path.exists(_CACHED_FONT_PATH) and os.path.getsize(_CACHED_FONT_PATH) > 50000:
        return _CACHED_FONT_PATH
    log.info("_ensure_font: downloading from CDN...")
    try:
        import urllib.request
        urllib.request.urlretrieve(_FONT_CDN_URL, _CACHED_FONT_PATH)
        if os.path.exists(_CACHED_FONT_PATH) and os.path.getsize(_CACHED_FONT_PATH) > 50000:
            return _CACHED_FONT_PATH
    except Exception as e:
        log.error(f"_ensure_font: download failed: {e}")
    p = _find_font()
    if p: return p
    return None



def _collect_path_verts(obj):
    verts = []
    def _walk(o):
        if isinstance(o, dict):
            if o.get("ty") == "sh":
                k = o.get("ks", {}).get("k", {})
                if isinstance(k, list) and k and isinstance(k[0], dict):
                    k = k[0].get("s", k[0])
                if isinstance(k, dict):
                    for v in k.get("v", []):
                        if isinstance(v, (list, tuple)) and len(v) >= 2:
                            verts.append((float(v[0]), float(v[1])))
            for val in o.values(): _walk(val)
        elif isinstance(o, list):
            for item in o: _walk(item)
    _walk(obj)
    return verts


def should_ignore(item):
    name = (getattr(item, "name", "") or "").lower()
    if any(x in name for x in ("matte", "mask", "clip", "hidden")):
        return True
    if getattr(item, "hidden", False):
        return True
    if hasattr(item, "matte_mode") and item.matte_mode is not None:
        val = item.matte_mode
        if hasattr(val, "value"):
            val = val.value
        if val != 0:
            return True
    if hasattr(item, "matte_target") and item.matte_target:
        return True
    return False

def get_all_elements(comp):
    """Recursively yield all layers, assets, and shape groups/elements in an Animation/Composition."""
    for layer in comp.layers:
        if should_ignore(layer):
            continue
        yield layer
        if hasattr(layer, "shapes"):
            for shape in layer.shapes:
                yield from _walk_shape(shape)
    if hasattr(comp, "assets"):
        for asset in comp.assets:
            if hasattr(asset, "layers"):
                for layer in asset.layers:
                    if should_ignore(layer):
                        continue
                    yield layer
                    if hasattr(layer, "shapes"):
                        for shape in layer.shapes:
                            yield from _walk_shape(shape)

def _walk_shape(shape):
    if should_ignore(shape):
        return
    yield shape
    if hasattr(shape, "shapes"):
        for sub in shape.shapes:
            yield from _walk_shape(sub)

def find_text_target(animation: Animation):
    # Priority 1: Live TextLayer
    for el in get_all_elements(animation):
        if isinstance(el, TextLayer):
            return el

    # Priority 2: Keyword match (excluding username)
    keywords = ["textgroup", "text", "letters", "emoji", "text shape", "emc", "logo"]
    for el in get_all_elements(animation):
        if hasattr(el, "name") and el.name:
            name_lower = el.name.lower()
            if "user" not in name_lower and any(kw in name_lower for kw in keywords):
                if isinstance(el, (Group, ShapeLayer)):
                    return el

    # Priority 3: Fallback structure
    for el in get_all_elements(animation):
        if isinstance(el, (Group, ShapeLayer)):
            if hasattr(el, "name") and el.name and "user" in el.name.lower():
                continue
            shapes = el.shapes if hasattr(el, "shapes") else []
            paths = [s for s in shapes if isinstance(s, Path)]
            has_fill = any(isinstance(s, Fill) for s in shapes)
            if 2 <= len(paths) <= 15 and has_fill:
                return el

    return None

def _get_textgroup_bounds(lottie: Any):
    is_dict = isinstance(lottie, dict)
    animation = Animation.load(lottie) if is_dict else lottie
    
    target = find_text_target(animation)
    if not target:
        return None
        
    if isinstance(target, TextLayer):
        pos = target.transform.position.value
        cx, cy = (pos[0], pos[1]) if (hasattr(pos, "__len__") and len(pos) >= 2) else (0.0, 0.0)
        doc = None
        if target.data and target.data.data and target.data.data.keyframes:
            doc = target.data.data.keyframes[0].start
        font_size = doc.font_size if doc else 50.0
        max_width = 512.0
        if doc and doc.wrap_size and doc.wrap_size[0] > 0:
            max_width = doc.wrap_size[0]
        elif target.composition and target.composition.width:
            max_width = target.composition.width
        return (cx - max_width / 2.0, cy - font_size / 2.0, cx + max_width / 2.0, cy + font_size / 2.0)

    # Path-only bounds calculation to exclude background graphics/boxes
    paths = []
    def collect_paths(item):
        if should_ignore(item):
            return
        if isinstance(item, Path):
            paths.append(item)
        elif hasattr(item, "shapes"):
            for s in item.shapes:
                collect_paths(s)
    collect_paths(target)

    bb = BoundingBox()
    for p in paths:
        if p.shape and p.shape.value:
            bb.expand(p.bounding_box(0))
    if not bb.isnull():
        return (bb.x1, bb.y1, bb.x2, bb.y2)
    return None

def _text_to_lottie_shapes(text, font_path, cx, cy, height, max_width=None):
    try:
        from fontTools.ttLib import TTFont
        from fontTools.pens.recordingPen import DecomposingRecordingPen
    except ImportError as e:
        import logging; logging.getLogger("JellyColor").error(f"fontTools: {e}")
        return None

    ft = TTFont(font_path)
    gs = ft.getGlyphSet()
    cm = ft.getBestCmap() or {}
    upm = ft["head"].unitsPerEm
    os2 = ft.get("OS/2")
    cap_h = float(getattr(os2, "sCapHeight", 0) or getattr(os2, "sTypoAscender", upm * 0.72))
    if cap_h <= 0:
        cap_h = upm * 0.72

    sc = height / cap_h
    total_adv = 0.0
    glyph_list = []

    for ch in text:
        gn = cm.get(ord(ch))
        if not gn or gn not in gs:
            fb = {ord("'"): [0x2019, 0x02BC], ord("–"): [0x002D], ord("—"): [0x002D]}
            for alt in fb.get(ord(ch), []):
                gn = cm.get(alt)
                if gn and gn in gs:
                    break
            else:
                gn = None
        adv = float(gs[gn].width) if gn and gn in gs else upm * 0.35
        glyph_list.append((gn, adv))
        total_adv += adv

    scale_y = sc * 100.0
    if max_width and (total_adv * sc) > max_width:
        scale_x = (max_width / total_adv) * 100.0
    else:
        scale_x = sc * 100.0

    parent_group = Group()
    parent_group.name = "JellyText_Container"

    # Insert a local Fill before letters get prepended with EvenOdd rule to prevent "white circle of death"
    fill_obj = Fill()
    fill_obj.name = "Fill"
    fill_obj.fill_rule = FillRule.EvenOdd
    fill_obj.color.value = Color(1.0, 1.0, 1.0)
    parent_group.shapes.insert(0, fill_obj)

    start_x = -total_adv / 2.0
    cur_x = 0.0

    for char_idx, (gn, adv) in enumerate(glyph_list):
        if gn is None:
            cur_x += adv
            continue

        char_group = Group()
        char_group.name = f"Char_{char_idx}"

        pen = DecomposingRecordingPen(gs)
        gs[gn].draw(pen)

        current_bezier = None

        def commit_path():
            if current_bezier and len(current_bezier.vertices) > 0:
                p_obj = Path()
                p_obj.name = "p"
                p_obj.shape.value = current_bezier
                char_group.shapes.insert(0, p_obj)

        for op, args in pen.value:
            if op == "moveTo":
                commit_path()
                current_bezier = Bezier()
                current_bezier.closed = True
                fx, fy = args[0]
                current_bezier.add_point(
                    NVector(fx, cap_h / 2.0 - fy),
                    NVector(0.0, 0.0),
                    NVector(0.0, 0.0)
                )
            elif op == "lineTo":
                if current_bezier is None:
                    current_bezier = Bezier()
                    current_bezier.closed = True
                fx, fy = args[0]
                current_bezier.add_point(
                    NVector(fx, cap_h / 2.0 - fy),
                    NVector(0.0, 0.0),
                    NVector(0.0, 0.0)
                )
            elif op == "curveTo":
                if current_bezier is None:
                    current_bezier = Bezier()
                    current_bezier.closed = True
                (c1x, c1y), (c2x, c2y), (ex, ey) = args
                pv = current_bezier.vertices[-1]
                c1_lottie = NVector(c1x, cap_h / 2.0 - c1y)
                current_bezier.out_tangents[-1] = c1_lottie - pv

                ev_lottie = NVector(ex, cap_h / 2.0 - ey)
                c2_lottie = NVector(c2x, cap_h / 2.0 - c2y)
                current_bezier.add_point(
                    ev_lottie,
                    c2_lottie - ev_lottie,
                    NVector(0.0, 0.0)
                )
            elif op == "qCurveTo":
                if current_bezier is None:
                    current_bezier = Bezier()
                    current_bezier.closed = True
                pts = list(args)
                p0 = current_bezier.vertices[-1]

                for qi in range(len(pts) - 1):
                    qcx, qcy = pts[qi]
                    qex, qey = pts[qi + 1] if qi == len(pts) - 2 else ((pts[qi][0] + pts[qi + 1][0]) / 2, (pts[qi][1] + pts[qi + 1][1]) / 2)

                    qcs = NVector(qcx, cap_h / 2.0 - qcy)
                    qes = NVector(qex, cap_h / 2.0 - qey)

                    c1s = p0 + (qcs - p0) * (2.0 / 3.0)
                    c2s = qes + (qcs - qes) * (2.0 / 3.0)

                    current_bezier.out_tangents[-1] = c1s - p0
                    current_bezier.add_point(
                        qes,
                        c2s - qes,
                        NVector(0.0, 0.0)
                    )
                    p0 = qes
            elif op in ("endPath", "closePath"):
                if current_bezier:
                    current_bezier.closed = True
                    commit_path()
                    current_bezier = None

        commit_path()

        char_group.transform.position.value = NVector(start_x + cur_x, 0.0)
        parent_group.shapes.insert(0, char_group)

        cur_x += adv

    parent_group.transform.position.value = NVector(cx, cy)
    parent_group.transform.scale.value = NVector(scale_x, scale_y)
    
    return parent_group

def _replace_textgroup(animation, new_group):
    target = find_text_target(animation)
    if not target:
        return False

    if isinstance(target, TextLayer):
        comp = target.composition
        if not comp:
            return False
        new_layer = ShapeLayer()
        new_layer.name = target.name or "Text Shape"
        new_layer.in_point = target.in_point
        new_layer.out_point = target.out_point
        new_layer.parent_index = target.parent_index
        if target.transform:
            new_layer.transform = target.transform.clone()
        new_layer.shapes = [new_group]
        try:
            idx = comp.layers.index(target)
            comp.layers.insert(idx, new_layer)
            comp.layers.remove(target)
        except ValueError:
            comp.add_layer(new_layer)
        return True

    if isinstance(target, ShapeLayer):
        target.shapes = [new_group]
        return True

    # Complete isolation: target's shapes are replaced by container + original transform
    original_tr = next((s for s in target.shapes if isinstance(s, TransformShape)), None)
    if not original_tr:
        original_tr = TransformShape()
    target.shapes = [new_group, original_tr]
    return True

def _find_username_bounds(animation):
    def walk(item):
        if isinstance(item, Group) and getattr(item, "name", "") == "USERNAME":
            verts = []
            def walk_sub(si):
                if isinstance(si, Path) and si.shape and si.shape.value:
                    verts.extend(si.shape.value.vertices)
                elif hasattr(si, "shapes"):
                    for s in si.shapes:
                        walk_sub(s)
            walk_sub(item)
            if verts:
                xs = [v[0] for v in verts]
                ys = [v[1] for v in verts]
                return (min(xs), min(ys), max(xs), max(ys)), item
        if hasattr(item, "shapes"):
            for s in item.shapes:
                r = walk(s)
                if r: return r
        if hasattr(item, "layers"):
            for l in item.layers:
                r = walk(l)
                if r: return r
        return None

    for l in animation.layers:
        r = walk(l)
        if r: return r
    for asset in animation.assets:
        if hasattr(asset, "layers"):
            for l in asset.layers:
                r = walk(l)
                if r: return r
    return None

def _replace_username(animation, new_text, font_path):
    res = _find_username_bounds(animation)
    if not res:
        return False
    bounds, grp = res
    x1, y1, x2, y2 = bounds
    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    height = max(abs(y2 - y1), 1.0)
    max_width = max(abs(x2 - x1), 1.0)

    new_group = _text_to_lottie_shapes(new_text, font_path, cx, cy, height, max_width)
    if not new_group:
        return False

    old_shapes = grp.shapes
    preserved = []
    for s in old_shapes:
        if isinstance(s, TransformShape):
            preserved.append(s)
        elif not isinstance(s, (Path, Group)):
            preserved.append(s)

    grp.shapes = [new_group] + preserved
    return True

OLD_USERNAME = "@emojicreationbot"
NEW_USERNAME = "@freecreateemoji"

def _set_text_fill_color(lottie: Any, hex_color: str) -> None:
    """Устанавливает цвет fill текстовых групп на hex_color."""
    is_dict = isinstance(lottie, dict)
    animation = Animation.load(lottie) if is_dict else lottie

    r, g, b = hex_to_rgb(hex_color)
    nr, ng, nb = r / 255.0, g / 255.0, b / 255.0
    color_obj = Color(nr, ng, nb)

    def walk(item):
        if isinstance(item, Fill):
            item.color.value = color_obj
        elif hasattr(item, "shapes"):
            for s in item.shapes:
                walk(s)
        elif hasattr(item, "layers"):
            for l in item.layers:
                walk(l)

    walk(animation)

    if is_dict:
        lottie.clear()
        lottie.update(animation.to_dict())

def modify_lottie(lottie: dict, new_text: str, font_path: str = None) -> bool:
    if not font_path:
        font_path = _ensure_font()
    if not font_path:
        return False

    animation = Animation.load(lottie)
    changed = False

    bounds = _get_textgroup_bounds(animation)
    if bounds:
        x1, y1, x2, y2 = bounds
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        height = max(abs(y2 - y1), 5.0)
        max_width = max(abs(x2 - x1), 5.0)

        new_group = _text_to_lottie_shapes(new_text, font_path, cx, cy, height, max_width)
        if new_group:
            # Apply slight skew for car templates if requested
            is_car_template = any(
                hasattr(l, "name") and l.name and any(x in l.name.lower() for x in ("fara", "kapot", "resh_lines"))
                for l in animation.layers
            )
            if is_car_template:
                new_group.transform.skew.value = -10.0
                
            if _replace_textgroup(animation, new_group):
                changed = True

    if _find_username_bounds(animation):
        if _replace_username(animation, NEW_USERNAME, font_path):
            changed = True

    if changed:
        lottie.clear()
        lottie.update(animation.to_dict())

    return changed

def replace_text_in_tgs(tgs_bytes: bytes, old_text: str, new_text: str, font_path: str = None) -> bytes:
    raw = gzip.decompress(tgs_bytes)
    lottie = json.loads(raw.decode("utf-8"))
    modify_lottie(lottie, new_text, font_path)
    return compress_tgs(lottie)
# ─── Recolor helpers ──────────────────────────────────────────────────────────

def _recolor_document_sync(data: bytes, mime: str, hex_color: str, is_emoji: bool) -> io.BytesIO:
    if mime=="application/x-tgsticker":
        lottie=json.loads(gzip.decompress(data))
        buf=io.BytesIO(compress_tgs(tint_lottie(lottie,hex_color))); buf.name="sticker.tgs"
    else:
        sz=100 if is_emoji else 512
        img=Image.open(io.BytesIO(data)).convert("RGBA").resize((sz,sz),Image.LANCZOS)
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
        lottie=json.loads(gzip.decompress(data))
        apply_gradient_lottie(lottie,gradient)
        buf=io.BytesIO(compress_tgs(lottie)); buf.name="sticker.tgs"
    else:
        sz=100 if is_emoji else 512
        img=Image.open(io.BytesIO(data)).convert("RGBA").resize((sz,sz),Image.LANCZOS)
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


async def _safe_create_set(client, uid, title, short_name, stickers, is_emoji, retries=3):
    for i in range(retries):
        sn=short_name if i==0 else f"{short_name}_v{i+1}"
        try:
            await client(functions.stickers.CreateStickerSetRequest(
                user_id=uid,title=title,short_name=sn,stickers=stickers,emojis=is_emoji,
            ))
            return sn,None
        except Exception as e:
            if "already exists" in str(e).lower() or "already_exists" in str(e).lower():
                try:
                    # Fetch current stickers in the set
                    fs = await client(functions.messages.GetStickerSetRequest(
                        stickerset=types.InputStickerSetShortName(short_name=sn), hash=0
                    ))
                    old_docs = fs.documents
                    
                    # Add new stickers
                    for sticker in stickers:
                        await client(functions.stickers.AddStickerToSetRequest(
                            stickerset=types.InputStickerSetShortName(short_name=sn),
                            sticker=sticker
                        ))
                    
                    # Delete old stickers
                    for doc in old_docs:
                        await client(functions.stickers.RemoveStickerFromSetRequest(
                            sticker=types.InputDocument(id=doc.id, access_hash=doc.access_hash, file_reference=doc.file_reference)
                        ))
                    return sn,None
                except Exception as add_err:
                    if i < retries - 1:
                        continue
                    return None,str(add_err)
            if "SHORT_NAME_OCCUPIED" in str(e) or "STICKERSET_INVALID" in str(e): continue
            return None,str(e)
    return None,"SHORT_NAME_OCCUPIED"


# ─── Module ───────────────────────────────────────────────────────────────────

@loader.tds
class JellyColorMod(loader.Module):
    """Перекраска + текстовые шаблоны с поддержкой пользовательских шрифтов.
    Ускорена генерация паков эмодзи и добавлено управление шрифтами (.jaddfont, .jdelfont, .jfonts).
    Команды: .j .jc .jt .tstats .jdel .jexport .jdump .jaddfont .jdelfont .jfonts"""

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
        import logging
        import traceback
        logger = logging.getLogger("JellyColor")
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
            import glob
            debug_files = glob.glob("/tmp/jelly_debug_last.*")
            if debug_files:
                await self._client.send_file(
                    logchat_id,
                    debug_files[0],
                    caption=msg_text,
                    message_thread_id=topic_id
                )
            else:
                await self._client.send_message(
                    logchat_id,
                    msg_text,
                    message_thread_id=topic_id
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

    async def _parallel(self, docs, fn, label, call):
        """Запускает fn(i,doc)->item|None параллельно с прогрессом.

        Fixes:
        - call.edit дросселируется: не чаще раза в 2с, только из одной корутины
        - ошибки логируются, не глотаются молча
        - прогресс обновляется строго под lock
        - FloodWaitError обрабатывается явно
        """
        import logging
        log = logging.getLogger("JellyColor")
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
                await call.edit(text=(
                    pe("⏰",PE["clock"])+f" <b>{label}...</b>\n\n"
                    f"<code>[{bar}]</code> {int(p/n*100)}%\n"
                    f"<b>{p}/{n}</b>"
                ))
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
                except Exception as e:
                    err=str(e)
                    if "FloodWait" in err or "flood" in err.lower():
                        wait=5*(attempt+1)
                        log.warning(f"_parallel FloodWait item {i}, sleeping {wait}s")
                        await asyncio.sleep(wait)
                    elif attempt<retries-1:
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
        except Exception as e: await utils.answer(message,pe("❌",PE["err"])+" "+str(e)); return
        uid=message.sender_id; pc=len(full_set.documents)
        self._sessions[uid]={"ts":time.time(),"type":tt,"doc":td,"set_id":ts,
            "set_short":getattr(full_set.set,"short_name",""),"full_set":full_set,"pack_count":pc,
            "scope":None,"color":None,"gradient":None,"pack_name":None,
            "step":"scope" if pc>1 else "color"}
        await message.delete()
        await self.inline.form(text=self._j_text(uid),reply_markup=self._j_markup(uid),message=message)

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
        return pe("⏰",PE["clock"])+" <b>Перекрашиваю...</b>"

    def _j_markup(self,uid):
        s=self._sessions[uid]; step=s["step"]
        if step=="scope": return [[
            {"text":"Один","icon_custom_emoji_id":PE["sticker"],"callback":self._j_s1,"args":(uid,)},
            {"text":"Весь пак","icon_custom_emoji_id":PE["pack"],"callback":self._j_sa,"args":(uid,)},
        ]]
        if step in ("color","gradient_menu"):
            if step=="gradient_menu":
                return self._gradient_menu_markup(self._j_grad,uid,self._j_back_col)
            return self._color_rows_with_gradient(uid,self._j_col,self._j_hex,self._j_open_grad,
                                                  no_color_cb=self._j_no_color,
                                                  custom_grad_cb=self._j_custom_grad)
        if step=="title": return [[{"text":"Ввести название","icon_custom_emoji_id":PE["sticker"],
                                    "input":"Например: My Cool Pack","handler":self._j_title,"args":(uid,)}]]
        if step=="name": return [[{"text":"Ввести short_name","icon_custom_emoji_id":PE["palette"],
                                   "input":"a-z, 0-9, _ (без _by_username)","handler":self._j_name,"args":(uid,)}]]
        return []

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
        s["pack_name"]=c+"_by_"+(me.username or "userbot")
        s["step"]="processing"
        await call.edit(text=self._j_text(uid))
        asyncio.ensure_future(self._j_run(call,uid))

    async def _j_run(self,call,uid):
        s=self._sessions[uid]
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
                    img=Image.open(io.BytesIO(data)).convert("RGBA").resize((sz,sz),Image.LANCZOS)
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
        ordered=await self._parallel(docs,_fn,"Перекраска",call)
        try:
            if not ordered: raise ValueError("Нет стикеров")
            clabel=gradient["name"] if gradient else (color or "без перекраски")
            title=s.get("pack_title") or "JellyColor "+clabel
            fn,err=await _safe_create_set(self._client,me.id,title,pname,ordered,ptype=="emoji")
            if err: raise ValueError(err)
            link="https://t.me/"+("addemoji/" if ptype=="emoji" else "addstickers/")+fn
        except Exception as e:
            await call.edit(text=pe("❌",PE["err"])+" <code>"+str(e)+"</code>")
            await self._report_error(e, ptype, pname)
            self._sessions.pop(uid,None); return
        stats=self.db.get("JellyColor","stats",[])
        clabel=gradient["name"] if gradient else (color or "без перекраски")
        stats.append({"name":fn,"link":link,"color":clabel,"count":len(ordered),"type":ptype,"ts":int(time.time())})
        self.db.set("JellyColor","stats",stats)
        tl="Стикерпак" if ptype=="sticker" else "Эмодзи-пак"
        tag=f"<code>{clabel}</code>"
        await call.edit(
            text=(pe("✅",PE["ok"])+" <b>Готово!</b>\n\n"
                  +pe("🖤",PE["brush"])+f" {tl} → {tag}\n"
                  +pe("📦",PE["pack"])+f" <b>{len(ordered)}</b> шт.\n\n"
                  +pe("🔗",PE["link"])+f" <a href=\"{link}\">{link}</a>"),
            reply_markup=[[{"text":"Открыть","icon_custom_emoji_id":PE["link"],"url":link}]],
        )
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
            sn="jc"+hc[1:].lower()+"_by_"+(me.username or "userbot")
            final_name,err=await _safe_create_set(self._client,me.id,"JellyColor "+hc,sn,[item],is_emoji)
            if err: raise ValueError(err)
            link="https://t.me/"+("addemoji/" if is_emoji else "addstickers/")+final_name
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
                               "color":None,"pack_name":None,"preview_msg":None,"is_emoji":True}
        await message.delete()
        await self.inline.form(text=self._jt_text(uid),reply_markup=self._jt_markup(uid),message=message)
    def _jt_text(self, uid):
        s=self._tsessions[uid]; step=s["step"]
        if step=="template": return pe("🖤",PE["brush"])+" <b>Выберите шаблон</b>\n\nТекст <code>"+TEMPLATE_PLACEHOLDER+"</code> будет заменён на ваш."
        if step=="text": return pe("✍️",PE["write"])+f" <b>Введите текст</b>\n\nШаблон: <b>{s['template']['title']}</b>\n2-4 символа — оптимально."
        if step=="font": return pe("✍️",PE["write"])+f" <b>Выберите шрифт</b>\n\nТекст: <code>{s['text']}</code>"
        if step=="preview": return pe("👁",PE["eye"])+f" <b>Предпросмотр</b>\n\nТекст: <code>{s['text']}</code> (Шрифт: <b>{s.get('font_title','Comfortaa')}</b>)\nСмотрите на тестовый эмодзи выше."
        if step=="pack_type": return pe("📦",PE["pack"])+f" <b>Тип стикер-пака</b>\n\nТекст: <code>{s['text']}</code>\n\nВыберите тип создаваемого пака:\n• <b>Custom Emoji</b> (отображаются в тексте, чатах, нужен Premium)\n• <b>Обычные стикеры</b> (отображаются в панели стикеров, размер 512x512)"
        if step=="color":
            hist=self._color_history()
            hs=("\n"+pe("⏰",PE["clock"])+" Последние: "+"  ".join(f"<code>{c}</code>" for c in hist)) if hist else ""
            return pe("🎨",PE["palette"])+f" <b>Цвет элементов</b>\n\nТекст: <code>{s['text']}</code>{hs}"
        if step=="title":
            pack_t = "эмодзи" if s.get("is_emoji", True) else "стикеров"
            return pe("🏷",PE["sticker"])+f" <b>Название пака {pack_t}</b>\n\nТекст: <code>{s['text']}</code>" + (f"  Цвет: <code>{s['color']}</code>" if s.get('color') else "  (без перекраски)") + "\n\n<i>Введите отображаемое название (любые символы)</i>"
        if step=="name": return pe("🏷",PE["sticker"])+f" <b>short_name пака</b>\n\nНазвание: <b>{s.get('pack_title','')}</b>\n\n<i>Введите short_name — только a-z, 0-9, _</i>"
        return pe("⏰",PE["clock"])+" <b>Создаём...</b>"

    def _jt_markup(self,uid):
        s=self._tsessions[uid]; step=s["step"]
        if step=="template": return [[{"text":t["title"],"icon_custom_emoji_id":PE["sticker"],
            "callback":self._jt_tmpl,"args":(uid,i)}] for i,t in enumerate(TEMPLATE_SETS)]
        if step=="text": return [[{"text":"Ввести текст","icon_custom_emoji_id":PE["palette"],
            "input":"Текст (вместо "+TEMPLATE_PLACEHOLDER+")","handler":self._jt_text_in,"args":(uid,)}]]
        if step=="font":
            user_fonts = self.db.get("JellyColor", "user_fonts", [])
            buttons = [[{"text": "Comfortaa (По умолчанию)", "icon_custom_emoji_id": PE["sticker"], "callback": self._jt_font_sel, "args": (uid, "default")}]]
            for f in user_fonts:
                buttons.append([{"text": f["title"], "icon_custom_emoji_id": PE["sticker"], "callback": self._jt_font_sel, "args": (uid, f["title"])}])
            return buttons
        if step=="preview": return [[
            {"text":"✅ Хорошо","icon_custom_emoji_id":PE["ok"],"callback":self._jt_confirm,"args":(uid,)},
            {"text":"✏️ Изменить","icon_custom_emoji_id":PE["palette"],"callback":self._jt_retry,"args":(uid,)},
        ]]
        if step=="pack_type": return [[
            {"text":"✨ Custom Emoji","icon_custom_emoji_id":PE["sticker"],"callback":self._jt_type_sel,"args":(uid,True)},
            {"text":"🖼 Обычные стикеры","icon_custom_emoji_id":PE["sticker"],"callback":self._jt_type_sel,"args":(uid,False)}
        ]]
        if step=="color":
            rows=self._color_rows_with_gradient(uid,self._jt_col,self._jt_hex,self._jt_open_grad,
                                                 no_color_cb=self._jt_no_color,
                                                 custom_grad_cb=self._jt_custom_grad)
            return rows
        if step=="gradient_menu":
            return self._gradient_menu_markup(self._jt_grad,uid,self._jt_back_col)
        if step=="title": return [[{"text":"Ввести название","icon_custom_emoji_id":PE["sticker"],
            "input":"Например: My Cool Pack","handler":self._jt_title,"args":(uid,)}]]
        if step=="name": return [[{"text":"Ввести short_name","icon_custom_emoji_id":PE["palette"],
            "input":"a-z, 0-9, _ (без _by_username)","handler":self._jt_name,"args":(uid,)}]]
        return []

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
        s["step"] = "preview"
        await call.edit(text=self._jt_text(uid), reply_markup=self._jt_markup(uid))
        asyncio.ensure_future(self._jt_preview(call, uid))

    async def _jt_preview(self,call,uid):
        s=self._tsessions.get(uid)
        if not s: return
        try:
            fs=await self._client(functions.messages.GetStickerSetRequest(
                stickerset=types.InputStickerSetShortName(short_name=s["template"]["short_name"]),hash=0))
            doc=fs.documents[0]
            raw=await download_cached(self._client,doc)
            mime=getattr(doc,"mime_type","")
            if mime=="application/x-tgsticker":
                loop = asyncio.get_event_loop()
                pat = await loop.run_in_executor(None, replace_text_in_tgs, raw, TEMPLATE_PLACEHOLDER, s["text"], s.get("font_path"))
                buf=io.BytesIO(pat); buf.name="preview.tgs"
            else:
                buf=io.BytesIO(raw); buf.name="preview.webp"
            buf.seek(0)
            
            chat_target = getattr(call, "chat_id", None) or uid
            try:
                chat_target = await self._client.get_input_entity(chat_target)
            except Exception:
                pass

            s["preview_msg"]=await self._client.send_file(
                chat_target,buf,caption=pe("👁",PE["eye"])+" <b>Preview: "+s["text"]+"</b>",parse_mode="HTML")
        except Exception as e:
            import logging
            logging.getLogger("JellyColor").error(f"Error in preview: {e}", exc_info=True)

    async def _jt_confirm(self,call,uid):
        s=self._tsessions.get(uid)
        if not s: await call.answer("Сессия устарела.",show_alert=True); return
        if s.get("preview_msg"):
            try: await s["preview_msg"].delete()
            except Exception: pass
        s["step"]="pack_type"
        await call.edit(text=self._jt_text(uid),reply_markup=self._jt_markup(uid))

    async def _jt_type_sel(self,call,uid,is_emoji):
        s=self._tsessions.get(uid)
        if not s: await call.answer("Сессия устарела.",show_alert=True); return
        s["is_emoji"]=is_emoji
        s["step"]="color"
        await call.edit(text=self._jt_text(uid),reply_markup=self._jt_markup(uid))

    async def _jt_retry(self,call,uid):
        s=self._tsessions.get(uid)
        if not s: await call.answer("Сессия устарела.",show_alert=True); return
        if s.get("preview_msg"):
            try: await s["preview_msg"].delete()
            except Exception: pass
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
        s["pack_name"]=c+"_by_"+(me.username or "userbot"); s["step"]="processing"
        await call.edit(text=self._jt_text(uid))
        asyncio.ensure_future(self._jt_run(call,uid))

    async def _jt_run(self,call,uid):
        s=self._tsessions[uid]
        tmpl,txt,pname,color=s["template"],s["text"],s["pack_name"],s.get("color")
        gradient=s.get("gradient")
        is_emoji=s.get("is_emoji", True)
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
                    lottie_obj = json.loads(gzip.decompress(raw).decode("utf-8"))
                    modify_lottie(lottie_obj, txt, s.get("font_path"))
                    if gradient:
                        apply_gradient_lottie(lottie_obj, gradient)
                        tc=_contrast_text_color(_dominant_color_from_gradient(gradient["colors"]))
                    elif color:
                        tint_lottie(lottie_obj, color)
                        tc=_contrast_text_color(color)
                    else:
                        tc=None
                    if tc:
                        _set_text_fill_color(lottie_obj, tc)
                    return compress_tgs(lottie_obj)
                patched = await loop.run_in_executor(None, _process_tgs)
                buf=io.BytesIO(patched); buf.name="sticker.tgs"
            else:
                def _process_img():
                    sz = 100 if is_emoji else 512
                    img=Image.open(io.BytesIO(raw)).convert("RGBA").resize((sz,sz),Image.LANCZOS)
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
            return await _upload_item(self._client,mee,up,mime,es,is_emoji)
        ordered=await self._parallel(docs,_fn,"Создаём",call)
        if not ordered:
            await call.edit(text=pe("❌",PE["err"])+" Ни один эмодзи не обработан.")
            self._tsessions.pop(uid,None); return
        color_label=gradient["name"] if gradient else (color or "без перекраски")
        try:
            pack_title=s.get("pack_title") or (txt+" Emoji Pack" if is_emoji else txt+" Sticker Pack")
            fn,err=await _safe_create_set(self._client,me.id,pack_title,pname,ordered,is_emoji)
            if err: raise ValueError(err)
            link="https://t.me/"+("addemoji/" if is_emoji else "addstickers/")+fn
        except Exception as e:
            await call.edit(text=pe("❌",PE["err"])+" <code>"+str(e)+"</code>")
            await self._report_error(e, "emoji" if is_emoji else "sticker", pname)
            self._tsessions.pop(uid,None); return
        stats=self.db.get("JellyColor","stats",[])
        stats.append({"name":fn,"link":link,"color":color or "text","count":len(ordered),"type":"emoji" if is_emoji else "sticker","ts":int(time.time())})
        self.db.set("JellyColor","stats",stats)
        await call.edit(
            text=(pe("✅",PE["ok"])+" <b>Готово!</b>\n\n"
                  +pe("✍️",PE["write"])+f" Текст: <code>{txt}</code>\n"
                  +pe("🎨",PE["palette"])+f" Цвет: <code>{color_label}</code>\n"
                  +pe("📦",PE["pack"])+f" <b>{len(ordered)}</b> шт.\n\n"
                  +pe("🔗",PE["link"])+f" <a href=\"{link}\">{link}</a>"),
            reply_markup=[[{"text":"Открыть","icon_custom_emoji_id":PE["link"],"url":link}]],
        )
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

        import hashlib
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
            except Exception:
                pass
                
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

    # ─── .tstats ──────────────────────────────────────────────────────────────

    @loader.command()
    async def tstats(self, message: Message):
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
        buf=io.BytesIO(json.dumps(stats,ensure_ascii=False,indent=2).encode()); buf.name="jelly_stats.json"; buf.seek(0)
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
            
        import uuid
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
                lottie=json.loads(gzip.decompress(raw))
                lines+=[f"w={lottie.get('w')} h={lottie.get('h')} fr={lottie.get('fr')} v={lottie.get('v')}",
                        f"layers: {len(lottie.get('layers',[]))}",
                        f"assets: {len(lottie.get('assets',[]))}",
                        f"text_bounds: {_get_textgroup_bounds(lottie)}",
                        f"dominant_color: {get_dominant_lottie_color(lottie)}",
                        "\n--- FULL JSON ---",
                        json.dumps(lottie,indent=2,ensure_ascii=False)]
            except Exception as e: lines.append(f"ERROR: {e}")
        bd=io.BytesIO("\n".join(lines).encode()); bd.name=f"dump_{eid}.txt"; bd.seek(0)
        br=io.BytesIO(raw); br.name=f"raw_{eid}.tgs"; br.seek(0)
        # Отправляем файлы по отдельности — SendMultiMediaRequest падает на таких документах
        await self._client.send_file(message.chat_id,bd,caption=f"📄 Dump <code>{eid}</code>",parse_mode="HTML")
        await self._client.send_file(message.chat_id,br)
        await msg.delete()