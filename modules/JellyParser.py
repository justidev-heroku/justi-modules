# ╔══════════════════════════════════════════════════════════════════╗
# ║                        🔮 JellyParser v0.2.8                     ║
# ║           Парсер эмодзи-паков на наличие текстовых групп         ║
# ║ v0.2.8: фикс белого фона + трёхэтапный контраст + доп. проверка  ║
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

import asyncio
import glob
import gzip
import io
import json
import logging
import os
import re
import time
import urllib.request
from telethon import functions, types
from telethon.tl.types import DocumentAttributeCustomEmoji, DocumentAttributeSticker, Message

from .. import loader, utils

try:
    import orjson
    HAS_ORJSON = True
except ImportError:
    HAS_ORJSON = False

try:
    from fontTools.ttLib import TTFont
    from fontTools.pens.recordingPen import DecomposingRecordingPen
    HAS_FONTTOOLS = True
except ImportError:
    HAS_FONTTOOLS = False

logger = logging.getLogger("JellyParser")

__version__ = (0, 2, 8)

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

CACHE_DIR = "/tmp/jelly_cache"
CONCURRENCY = 12
os.makedirs(CACHE_DIR, exist_ok=True)

TEMPLATE_PLACEHOLDER = "emc"
NEW_USERNAME = "JellyColor"

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
    "/usr/share/fonts/noto/NotoSans-Bold.ttf",
    "/usr/local/share/fonts/NotoSans-Bold.ttf",
]
_CACHED_FONT_PATH = "/tmp/jelly_color_comfortaa.ttf"
_FONT_CDN_URL = (
    "https://raw.githubusercontent.com/googlefonts/comfortaa/master/"
    "fonts/TTF/Comfortaa-Bold.ttf"
)


def pe(emoji: str, eid: str) -> str:
    return '<tg-emoji emoji-id="' + eid + '">' + emoji + '</tg-emoji>'


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


def _find_font():
    for p in _FONT_SEARCH:
        if os.path.exists(p): return p
    for p in glob.glob("/usr/share/fonts/**/*Bold*.ttf", recursive=True): return p
    found = glob.glob("/usr/share/fonts/**/*.ttf", recursive=True)
    return found[0] if found else None


def _ensure_font():
    log = logging.getLogger("JellyParser")
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


def _collect_path_verts(obj):
    verts = []
    def _walk(o):
        if isinstance(o, dict):
            if o.get("ty") == "sh":
                ks = o.get("ks", {})
                def _walk_ks(x):
                    if isinstance(x, dict):
                        if "v" in x and isinstance(x["v"], list):
                            for v in x["v"]:
                                if isinstance(v, (list, tuple)) and len(v) >= 2:
                                    verts.append((float(v[0]), float(v[1])))
                        for val in x.values():
                            _walk_ks(val)
                    elif isinstance(x, list):
                        for item in x:
                            _walk_ks(item)
                _walk_ks(ks)
            for val in o.values(): _walk(val)
        elif isinstance(o, list):
            for item in o: _walk(item)
    _walk(obj)
    return verts


def _verts_to_bounds(verts):
    if not verts: return None
    xs=[v[0] for v in verts]; ys=[v[1] for v in verts]
    return (min(xs), min(ys), max(xs), max(ys))


def _count_paths(obj):
    cnt = 0
    def _collect(o):
        nonlocal cnt
        if isinstance(o, dict):
            if o.get("ty") == "sh":
                cnt += 1
            for val in o.values(): _collect(val)
        elif isinstance(o, list):
            for item in o: _collect(item)
    _collect(obj)
    return cnt


def _has_fill(obj):
    found = False
    def _collect(o):
        nonlocal found
        if isinstance(o, dict):
            if o.get("ty") == "fl":
                found = True
                return
            for val in o.values(): _collect(val)
        elif isinstance(o, list):
            for item in o: _collect(item)
    _collect(obj)
    return found


def _get_all_elements(lottie):
    todo = []
    if "layers" in lottie:
        todo.extend(lottie["layers"])
    if "assets" in lottie:
        for a in lottie["assets"]:
            if "layers" in a:
                todo.extend(a["layers"])
    
    while todo:
        el = todo.pop()
        yield el
        sh = el.get("shapes")
        if sh:
            todo.extend(sh)
        it = el.get("it")
        if it:
            todo.extend(it)


def _is_descendant(child, parent):
    todo = []
    if "shapes" in parent:
        todo.extend(parent["shapes"])
    if "it" in parent:
        todo.extend(parent["it"])
        
    while todo:
        o = todo.pop()
        if o is child:
            return True
        sh = o.get("shapes")
        if sh:
            todo.extend(sh)
        it = o.get("it")
        if it:
            todo.extend(it)
    return False


def _has_keyword_child(obj):
    keywords = {"textgroup", "text", "letters", "emoji", "text shape", "emc", "logo"}
    todo = [obj]
    while todo:
        o = todo.pop()
        if isinstance(o, dict):
            nm = o.get("nm")
            if isinstance(nm, str) and nm:
                nm_lower = nm.lower()
                if "user" not in nm_lower and any(kw in nm_lower for kw in keywords):
                    return True
            for val in o.values():
                if isinstance(val, (dict, list)):
                    todo.append(val)
        elif isinstance(o, list):
            for item in o:
                if isinstance(item, (dict, list)):
                    todo.append(item)
    return False


def _is_keyword_match(el):
    keywords = {"textgroup", "text", "letters", "emoji", "text shape", "emc", "logo"}
    nm = el.get("nm")
    if isinstance(nm, str) and nm:
        nm_lower = nm.lower()
        if "user" not in nm_lower and any(kw in nm_lower for kw in keywords):
            return True
    return _has_keyword_child(el)


def _find_text_targets(lottie):
    elements = list(_get_all_elements(lottie))
    
    text_layers = [el for el in elements if el.get("ty") == 5]
    if text_layers:
        return text_layers

    named_targets = []
    for el in elements:
        ty = el.get("ty")
        # ty==4 is a top-level ShapeLayer — skip it as a direct target,
        # only target "gr" groups to avoid wiping the whole layer (body/outline etc.)
        if ty == "gr":
            if _is_keyword_match(el):
                if _count_paths(el) >= 1:
                    named_targets.append(el)
                        
    if named_targets:
        final_targets = []
        for cand in named_targets:
            if any(_is_descendant(t, cand) for t in named_targets if t is not cand):
                continue
            final_targets.append(cand)
        return final_targets

    fallback_targets = []
    for el in elements:
        ty = el.get("ty")
        if ty == "gr":
            nm = el.get("nm")
            nm_lower = (nm.lower() if isinstance(nm, str) else "")
            if "user" not in nm_lower:
                cnsh = _count_paths(el)
                if 2 <= cnsh <= 15 and _has_fill(el):
                    fallback_targets.append(el)
                    
    if fallback_targets:
        final_targets = []
        for cand in fallback_targets:
            if any(_is_descendant(t, cand) for t in fallback_targets if t is not cand):
                continue
            final_targets.append(cand)
        return final_targets

    return []


def _get_textgroup_bounds(lottie):
    targets = _find_text_targets(lottie)
    if targets:
        target = targets[0]
        if target.get("ty") == 5:
            pos = target.get("ks", {}).get("p", {}).get("k", [0, 0])
            cx, cy = (pos[0], pos[1]) if (isinstance(pos, list) and len(pos) >= 2) else (0.0, 0.0)
            font_size = 50.0
            max_width = 512.0
            return (cx - max_width / 2.0, cy - font_size / 2.0, cx + max_width / 2.0, cy + font_size / 2.0)
            
        verts = _collect_path_verts(target)
        if verts:
            return _verts_to_bounds(verts)
    return None


def _text_to_lottie_shapes(text, font_path, cx, cy, height, max_width=None):
    if not HAS_FONTTOOLS:
        logger.error("fontTools: package not found")
        return []
    ft=TTFont(font_path); gs=ft.getGlyphSet(); cm=ft.getBestCmap() or {}
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


def _extract_styles(obj):
    styles = []
    seen = set()
    todo = [obj]
    while todo:
        o = todo.pop()
        if isinstance(o, dict):
            ty = o.get("ty")
            if ty in ("fl", "st", "gf", "gs"):
                ser = json.dumps(o, sort_keys=True)
                if ser not in seen:
                    seen.add(ser)
                    styles.append(o)
            for v in o.values():
                if isinstance(v, (dict, list)):
                    todo.append(v)
        elif isinstance(o, list):
            for item in o:
                if isinstance(item, (dict, list)):
                    todo.append(item)
    return styles


def _is_lottie_light(lottie, text_targets):
    """
    Определяет цвет текста: белый (False) или тёмный (True).

    Трёхэтапная логика:

    1. Смотрим fill-цвета ВНУТРИ текстовых таргетов.
       Если есть ЦВЕТНОЙ тёмный fill (lum < 0.4, не серый/чёрный) — это фоновая
       плашка тёмного цвета под текстом → белый текст (False).
       Серый/чёрный (max-min < 0.08) игнорируем — это текст предыдущей замены или outline.
       Белый (lum >= 0.95, серый) тоже игнорируем — это текст предыдущей замены.

    2. Собираем ВСЕ цвета эмодзи (fills + градиенты, вне таргетов).
       Если минимальная яркость < 0.35 — есть тёмные элементы → белый текст (False).
       Это ловит тёмные подиумы/фоны, нарисованные fills.

    3. Если min >= 0.35: смотрим медианную яркость (fills + градиенты).
       median >= 0.65 → фон светлый → тёмный текст (True).
       Иначе → белый текст (False).

    ИСПРАВЛЕНО в v0.2.7:
    - Правильный парсинг градиентов: g.k.k (вложенный объект) + g.p (кол-во стопов)
      Ранее g.k читался как список напрямую, но на деле это объект {k:[...], a:0},
      поэтому isinstance(g_k, list) возвращало False и градиенты игнорировались.
    - Градиенты (gf/gs) теперь включены в оба шага (min + median).
    - Убрана инверсия: fill внутри таргета = белый/серый → это старый текст, игнорируем.
    """
    def _lum(rgb):
        return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]

    def _is_gray(rgb):
        return max(rgb) - min(rgb) < 0.08

    def _parse_gradient_colors(o):
        """Правильный парсинг цветов из gf/gs объекта с учётом g.p и вложенного g.k.k"""
        g = o.get("g", {})
        p = g.get("p", 0) if isinstance(g, dict) else 0
        gk = g.get("k", {}) if isinstance(g, dict) else {}
        # g.k может быть объектом {k: [...], a: 0} или сразу списком
        if isinstance(gk, dict):
            gk = gk.get("k", [])
        if not isinstance(gk, list):
            return []
        colors = []
        if p > 0:
            # Берём только цветовые стопы: первые p*4 значений [pos, r, g, b, ...]
            color_data = gk[: p * 4]
            i = 0
            while i + 3 < len(color_data):
                r_, gg_, b_ = color_data[i + 1: i + 4]
                if all(isinstance(x, (int, float)) for x in (r_, gg_, b_)):
                    colors.append((float(r_), float(gg_), float(b_)))
                i += 4
        else:
            # Fallback без p: парсим пока позиция в [0..1]
            i = 0
            while i + 3 < len(gk):
                v4 = gk[i: i + 4]
                if all(isinstance(x, (int, float)) for x in v4):
                    pos = v4[0]
                    if 0.0 <= pos <= 1.0 and all(0.0 <= c <= 1.0 for c in v4[1:4]):
                        colors.append((float(v4[1]), float(v4[2]), float(v4[3])))
                        i += 4
                    else:
                        break
                else:
                    i += 1
        return colors

    # --- Шаг 1: цветной тёмный fill внутри текстового таргета ---
    target_fills = []

    def walk_target(o):
        if isinstance(o, dict):
            if o.get("ty") == "fl":
                ck = o.get("c", {}).get("k", [])
                if isinstance(ck, list) and len(ck) >= 3 and all(isinstance(x, (int, float)) for x in ck[:3]):
                    target_fills.append(tuple(float(x) for x in ck[:3]))
            for v in o.values():
                if isinstance(v, (dict, list)):
                    walk_target(v)
        elif isinstance(o, list):
            for item in o:
                walk_target(item)

    for t in text_targets:
        walk_target(t)

    # Игнорируем серые/белые fills внутри таргета — это текст от предыдущего парсинга
    colored_target_fills = [c for c in target_fills if not _is_gray(c) and _lum(c) < 0.95]
    if any(_lum(c) < 0.4 for c in colored_target_fills):
        return False  # цветной тёмный фон плашки → белый текст

    # --- Шаги 2 и 3: яркость всего эмодзи (вне таргетов), fills + градиенты ---
    text_target_ids = set(id(t) for t in text_targets)
    all_lums = []

    def walk(o, in_target=False):
        if isinstance(o, dict):
            if id(o) in text_target_ids:
                in_target = True
            if not in_target:
                ty = o.get("ty")
                if ty == "fl":
                    ck = o.get("c", {}).get("k", [])
                    if isinstance(ck, list) and len(ck) >= 3 and all(isinstance(x, (int, float)) for x in ck[:3]):
                        all_lums.append(_lum(tuple(float(x) for x in ck[:3])))
                elif ty in ("gf", "gs"):
                    for c in _parse_gradient_colors(o):
                        all_lums.append(_lum(c))
            for v in o.values():
                if isinstance(v, (dict, list)):
                    walk(v, in_target)
        elif isinstance(o, list):
            for item in o:
                walk(item, in_target)

    walk(lottie)

    if not all_lums:
        return False  # умолчание: белый текст

    min_lum = min(all_lums)
    # Шаг 2: есть тёмные элементы → белый текст
    if min_lum < 0.35:
        return False

    # Шаг 3: всё светлое — смотрим медиану
    lums = sorted(all_lums)
    median_lum = lums[len(lums) // 2]
    return median_lum >= 0.65

def _extract_gradient_colors(obj):
    g = obj.get("g", {})
    p = g.get("p", 0) if isinstance(g, dict) else 0
    gk = g.get("k", {}) if isinstance(g, dict) else {}
    if isinstance(gk, dict):
        gk = gk.get("k", [])
    if not isinstance(gk, list):
        return []
    colors = []
    if p > 0:
        color_data = gk[: p * 4]
        i = 0
        while i + 3 < len(color_data):
            r_, gg_, b_ = color_data[i + 1: i + 4]
            if all(isinstance(x, (int, float)) for x in (r_, gg_, b_)):
                colors.append((float(r_), float(gg_), float(b_)))
            i += 4
    else:
        i = 0
        while i + 3 < len(gk):
            v4 = gk[i: i + 4]
            if all(isinstance(x, (int, float)) for x in v4):
                pos = v4[0]
                if 0.0 <= pos <= 1.0 and all(0.0 <= c <= 1.0 for c in v4[1:4]):
                    colors.append((float(v4[1]), float(v4[2]), float(v4[3])))
                    i += 4
                else:
                    break
            else:
                i += 1
    return colors


def _has_white_overlapping_bg(lottie, targets, bounds):
    if not bounds:
        return False
    target_ids = set(id(t) for t in targets)
    
    def overlaps(sb, tb):
        if not sb or not tb: return False
        ix1 = max(sb[0], tb[0])
        iy1 = max(sb[1], tb[1])
        ix2 = min(sb[2], tb[2])
        iy2 = min(sb[3], tb[3])
        if ix1 < ix2 and iy1 < iy2:
            intersection_area = (ix2 - ix1) * (iy2 - iy1)
            target_area = (tb[2] - tb[0]) * (tb[3] - tb[1])
            if target_area <= 0:
                return False
            return (intersection_area / target_area) >= 0.15
        return False

    found_white = [False]

    def walk(obj, is_in_target=False):
        if found_white[0]:
            return
        if not isinstance(obj, (dict, list)):
            return
        if isinstance(obj, dict):
            if id(obj) in target_ids:
                is_in_target = True
            
            ty = obj.get("ty")
            nm = obj.get("nm")
            nm_lower = (nm.lower() if isinstance(nm, str) else "")
            
            if "user" in nm_lower:
                return
            
            if not is_in_target and (ty == "gr" or ty == 4):
                shapes = []
                fills = []
                def collect_sh_fl(o):
                    if isinstance(o, dict):
                        sub_nm = o.get("nm")
                        if isinstance(sub_nm, str) and "user" in sub_nm.lower():
                            return
                        t_ = o.get("ty")
                        if t_ == "sh":
                            shapes.append(o)
                        elif t_ in ("fl", "gf", "gs"):
                            fills.append(o)
                        for val in o.values():
                            if isinstance(val, (dict, list)):
                                collect_sh_fl(val)
                    elif isinstance(o, list):
                        for item in o:
                            collect_sh_fl(item)
                            
                collect_sh_fl(obj)
                
                if shapes and fills:
                    non_target_shapes = []
                    for sh in shapes:
                        is_target_sh = False
                        for t in targets:
                            if _is_descendant(sh, t) or sh is t:
                                is_target_sh = True
                                break
                        if not is_target_sh:
                            non_target_shapes.append(sh)
                            
                    if non_target_shapes:
                        verts = []
                        for sh in non_target_shapes:
                            verts.extend(_collect_path_verts(sh))
                        sb = _verts_to_bounds(verts)
                        if sb and overlaps(sb, bounds):
                            non_target_fills = []
                            for f in fills:
                                is_target_f = False
                                for t in targets:
                                    if _is_descendant(f, t) or f is t:
                                        is_target_f = True
                                        break
                                if not is_target_f:
                                    non_target_fills.append(f)
                                    
                            for fill in non_target_fills:
                                ity = fill.get("ty")
                                if ity == "fl":
                                    ck = fill.get("c", {}).get("k", [])
                                    if isinstance(ck, list) and len(ck) >= 3:
                                        if all(isinstance(x, (int, float)) for x in ck[:3]):
                                            r, g, b = ck[:3]
                                            lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
                                            if lum > 0.85:
                                                found_white[0] = True
                                                return
                                elif ity in ("gf", "gs"):
                                    gcs = _extract_gradient_colors(fill)
                                    if gcs:
                                        avg_lum = sum(0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2] for c in gcs) / len(gcs)
                                        if avg_lum > 0.85:
                                            found_white[0] = True
                                            return
                                            
            for v in obj.values():
                if isinstance(v, (dict, list)):
                    walk(v, is_in_target)
        elif isinstance(obj, list):
            for item in obj:
                walk(item, is_in_target)

    walk(lottie)
    return found_white[0]


def _replace_textgroup(lottie, new_shapes, height=None):
    targets = _find_text_targets(lottie)
    if not targets:
        return False
        
    bounds = _get_textgroup_bounds(lottie)
    if bounds and _has_white_overlapping_bg(lottie, targets, bounds):
        fill_color = [0.05, 0.05, 0.05, 1]
    elif _is_lottie_light(lottie, targets):
        fill_color = [0.05, 0.05, 0.05, 1]
    else:
        fill_color = [1, 1, 1, 1]
        
    for target in targets:
        styles = [{
            "ty": "fl",
            "c": {"a": 0, "k": fill_color},
            "o": {"a": 0, "k": 100},
            "r": 1,
            "nm": "Fill 1"
        }]

        # target is always a "gr" group — preserve its transform "tr"
        original_tr = None
        for x in target.get("it", []):
            if x.get("ty") == "tr":
                original_tr = x
                break
        if not original_tr:
            original_tr = {
                "ty": "tr",
                "p": {"a": 0, "k": [0, 0]},
                "a": {"a": 0, "k": [0, 0]},
                "s": {"a": 0, "k": [100, 100]},
                "r": {"a": 0, "k": 0},
                "o": {"a": 0, "k": 100},
                "sk": {"a": 0, "k": 0},
                "sa": {"a": 0, "k": 0},
                "nm": "Transform"
            }
        target["it"] = new_shapes + styles + [original_tr]

    return True


def _find_username_bounds(lottie):
    def walk(obj):
        if isinstance(obj, dict):
            if (obj.get("ty") == "gr" or obj.get("ty") == 4 or obj.get("ty") == "4") and obj.get("nm") == "USERNAME":
                b = _verts_to_bounds(_collect_path_verts(obj))
                if b:
                    return b, obj
            for v in obj.values():
                r = walk(v)
                if r:
                    return r
        elif isinstance(obj, list):
            for item in obj:
                r = walk(item)
                if r:
                    return r
        return None
    return walk(lottie)


def _replace_username(lottie, new_text, font_path):
    replaced = False

    def walk(obj):
        nonlocal replaced
        if isinstance(obj, dict):
            if (obj.get("ty") == "gr" or obj.get("ty") == 4 or obj.get("ty") == "4") and obj.get("nm") == "USERNAME":
                b = _verts_to_bounds(_collect_path_verts(obj))
                if b:
                    x1, y1, x2, y2 = b
                    ns = _text_to_lottie_shapes(
                        new_text,
                        font_path,
                        (x1 + x2) / 2,
                        (y1 + y2) / 2,
                        max(abs(y2 - y1), 1.0),
                        max_width=max(abs(x2 - x1), 1.0),
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
                            if x.get("ty") not in ("sh", "el", "rc", "sr", "st", "gs")
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


def _optimize_lottie_floats(o):
    if isinstance(o, float):
        return round(o, 3)
    elif isinstance(o, dict):
        return {k: _optimize_lottie_floats(v) for k, v in o.items()}
    elif isinstance(o, list):
        return [_optimize_lottie_floats(x) for x in o]
    return o


def modify_lottie(lottie: dict, new_text: str, font_path: str = None) -> bool:
    if not font_path:
        font_path = _ensure_font()
    if not font_path:
        return False
    changed = False
    bounds = _get_textgroup_bounds(lottie)
    if bounds:
        x1, y1, x2, y2 = bounds
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        height = max(abs(y2 - y1), 5.)
        ns = _text_to_lottie_shapes(new_text, font_path, cx, cy, height, max_width=max(abs(x2 - x1), 5.))
        if ns and _replace_textgroup(lottie, ns, height):
            changed = True
    if _find_username_bounds(lottie):
        if _replace_username(lottie, NEW_USERNAME, font_path):
            changed = True
    return changed


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
                    fs = await client(functions.messages.GetStickerSetRequest(
                        stickerset=types.InputStickerSetShortName(short_name=sn), hash=0
                    ))
                    old_docs = fs.documents
                    
                    for sticker in stickers:
                        await client(functions.stickers.AddStickerToSetRequest(
                            stickerset=types.InputStickerSetShortName(short_name=sn),
                            sticker=sticker
                        ))
                    
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


@loader.tds
class JellyParserMod(loader.Module):
    """Парсер эмодзи-паков на наличие текстовых слоев и создание нового пака.
    MIT License | Copyright (c) 2026 justidev"""

    strings = {"name": "JellyParser"}

    def __init__(self):
        self._semaphore = None

    def _sem(self):
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(CONCURRENCY)
        return self._semaphore

    async def _parallel(self, docs, fn, label, message):
        log = logger
        results = []
        lock = asyncio.Lock()
        progress = [0]
        sem = self._sem()
        last_edit = [0.0]

        async def _update_progress(p, n):
            now = asyncio.get_event_loop().time()
            if now - last_edit[0] < 2.0:
                return
            last_edit[0] = now
            bar_len = 20
            filled = int(p / n * bar_len)
            bar = "█" * filled + "░" * (bar_len - filled)
            try:
                await message.edit((
                    pe("⏰", PE["clock"]) + f" <b>{label}...</b>\n\n"
                    f"<code>[{bar}]</code> {int(p / n * 100)}%\n"
                    f"<b>{p}/{n}</b>"
                ))
            except Exception:
                pass

        async def _run(i, doc):
            retries = 3
            item = None
            for attempt in range(retries):
                try:
                    async with sem:
                        item = await fn(i, doc)
                    break
                except Exception as e:
                    err = str(e)
                    if "FloodWait" in err or "flood" in err.lower():
                        wait = 5 * (attempt + 1)
                        log.warning(f"_parallel FloodWait item {i}, sleeping {wait}s")
                        await asyncio.sleep(wait)
                    elif attempt < retries - 1:
                        log.warning(f"_parallel item {i} attempt {attempt + 1} failed: {e}")
                        await asyncio.sleep(1)
                    else:
                        log.error(f"_parallel item {i} failed after {retries} attempts: {e}")
            async with lock:
                if item is not None:
                    results.append((i, item))
                progress[0] += 1
                p = progress[0]
            n = len(docs)
            if n > 1:
                await _update_progress(p, n)

        await asyncio.gather(*[_run(i, d) for i, d in enumerate(docs)])
        results.sort(key=lambda x: x[0])
        return [x for _, x in results]

    @loader.command()
    async def jparse(self, message: Message):
        """Парсинг эмодзи-пака на наличие текстовых слоев и создание нового пака.
        Использование: .jparse <ссылка> (или ответом на сообщение с ссылкой)"""
        args = utils.get_args_raw(message).strip()
        if not args:
            reply = await message.get_reply_message()
            if reply and reply.text:
                args = reply.text.strip()
        
        if not args:
            await utils.answer(message, pe("ℹ️", PE["info"]) + " Укажите ссылку на эмодзи-пак: <code>.jparse https://t.me/addemoji/name</code>")
            return

        match = re.search(r"(?:addemoji/|set=|addstickers/)([a-zA-Z0-9_]+)", args)
        if not match:
            await utils.answer(message, pe("❌", PE["err"]) + " Некорректная ссылка на эмодзи/стикер пак.")
            return
        
        pack_short = match.group(1)
        status_msg = await utils.answer(message, pe("⏰", PE["clock"]) + f" Получаем информацию о паке <code>{pack_short}</code>...")
        
        try:
            fs = await self._client(functions.messages.GetStickerSetRequest(
                stickerset=types.InputStickerSetShortName(short_name=pack_short), hash=0
            ))
        except Exception as e:
            await status_msg.edit(pe("❌", PE["err"]) + f" Не удалось получить пак: <code>{e}</code>")
            return

        docs = list(fs.documents)
        if not docs:
            await status_msg.edit(pe("❌", PE["err"]) + " Пак пуст.")
            return

        set_is_emoji = bool(getattr(fs.set, "emojis", False))
        if not set_is_emoji:
            try:
                set_is_emoji = bool(getattr(fs.set, "flags", 0) & (1 << 5))
            except Exception:
                set_is_emoji = False
        
        if not set_is_emoji:
            await status_msg.edit(pe("❌", PE["err"]) + " Это не эмодзи-пак (только эмодзи-паки поддерживаются для парсинга).")
            return

        await status_msg.edit(pe("⏰", PE["clock"]) + f" Скачиваем и парсим {len(docs)} эмодзи...")

        debug_logs = []

        async def _check_doc(i, doc):
            mime = getattr(doc, "mime_type", "")
            if mime != "application/x-tgsticker":
                return None
            try:
                raw = await download_cached(self._client, doc)
                decompressed = gzip.decompress(raw)
                lottie_obj = orjson.loads(decompressed) if HAS_ORJSON else json.loads(decompressed.decode("utf-8"))
                bounds = _get_textgroup_bounds(lottie_obj)
                
                targets = _find_text_targets(lottie_obj)
                target_info = f"Target types: {[t.get('ty') for t in targets]}" if targets else "None"
                debug_logs.append(f"Doc {i} ({getattr(doc, 'id', 'unknown')}): bounds={bounds}, targets={target_info}")
                
                if bounds:
                    return doc
            except Exception as e:
                debug_logs.append(f"Doc {i} check failed: {e}")
            return None

        filtered_docs = await self._parallel(docs, _check_doc, "Парсинг эмодзи", status_msg)
        filtered_docs = [d for d in filtered_docs if d is not None]

        if not filtered_docs:
            await status_msg.edit(pe("❌", PE["err"]) + " В паке не найдено эмодзи с текстовыми группами (textGroup).")
            return

        await status_msg.edit(pe("⏰", PE["clock"]) + f" Найдено <b>{len(filtered_docs)}</b> текстовых эмодзи. Создаём пак...")

        # Find first free mainemoji_jellycolor{n}_by_justidev
        n = 1
        while True:
            target_short = f"mainemoji_jellycolor{n}_by_justidev"
            try:
                await self._client(functions.messages.GetStickerSetRequest(
                    stickerset=types.InputStickerSetShortName(short_name=target_short), hash=0
                ))
                n += 1
            except Exception as e:
                if "STICKERSET_INVALID" in str(e) or "invalid" in str(e).lower():
                    break
                else:
                    break

        me = await self._client.get_me()
        mee = await self._client.get_input_entity("me")

        async def _upload_doc(i, doc):
            raw = await download_cached(self._client, doc)
            
            # Decompress, modify text placeholder to "jelly", compress back
            try:
                decompressed = gzip.decompress(raw)
                lottie_obj = orjson.loads(decompressed) if HAS_ORJSON else json.loads(decompressed.decode("utf-8"))
                orig_size = len(decompressed)
                res = modify_lottie(lottie_obj, "jelly")
                lottie_obj = _optimize_lottie_floats(lottie_obj)
                
                serialized = orjson.dumps(lottie_obj) if HAS_ORJSON else json.dumps(lottie_obj, separators=(",", ":")).encode("utf-8")
                raw = gzip.compress(serialized, compresslevel=9)
                debug_logs.append(f"Doc {i} ({getattr(doc, 'id', 'unknown')}): modify_lottie={res}, orig_size={orig_size}, new_size={len(serialized)}, compressed_size={len(raw)}")
            except Exception as e:
                logger.error(f"Failed to replace text with jelly for emoji {i}: {e}")
                debug_logs.append(f"Doc {i} modify failed: {e}")
                
            buf = io.BytesIO(raw)
            buf.name = "sticker.tgs"
            buf.seek(0)
            
            alt = "✨"
            for a in getattr(doc, "attributes", []):
                if isinstance(a, (DocumentAttributeCustomEmoji, DocumentAttributeSticker)):
                    alt = getattr(a, "alt", None) or "✨"
                    break
            
            up = await self._client.upload_file(buf, file_name=buf.name)
            return await _upload_item(self._client, mee, up, "application/x-tgsticker", alt, True)

        await status_msg.edit(pe("⏰", PE["clock"]) + f" Загружаем {len(filtered_docs)} эмодзи в новый пак...")
        uploaded_items = await self._parallel(filtered_docs, _upload_doc, "Загрузка медиа", status_msg)
        
        if not uploaded_items:
            await status_msg.edit(pe("❌", PE["err"]) + " Не удалось загрузить ни одного эмодзи.")
            return

        try:
            title = f"JellyColor Templates {n}"
            final_name, err = await _safe_create_set(self._client, me.id, title, target_short, uploaded_items, True)
            if err:
                raise ValueError(err)
            
            link = f"https://t.me/addemoji/{final_name}"
            await status_msg.edit(
                pe("✅", PE["ok"]) + f" <b>Пак успешно создан!</b>\n\n"
                + pe("📦", PE["pack"]) + f" Всего добавлено: <b>{len(uploaded_items)}</b> шт.\n"
                + pe("🔗", PE["link"]) + f" <a href=\"{link}\">{link}</a>",
                parse_mode="HTML"
            )
        except Exception as e:
            debug_path = "/root/jelly_debug.log"
            try:
                with open(debug_path, "w", encoding="utf-8") as df:
                    df.write("\n".join(debug_logs))
                log_info = f"\n\n📝 Лог отладки сохранен в: <code>{debug_path}</code>"
            except Exception:
                log_info = ""
            await status_msg.edit(pe("❌", PE["err"]) + f" Не удалось создать набор: <code>{e}</code>{log_info}")