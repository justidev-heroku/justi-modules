# ╔══════════════════════════════════════════════════════════════════╗
# ║                        🔮 JellyParser v0.1.4                     ║
# ║           Парсер эмодзи-паков на наличие текстовых групп         ║
# ║        v0.1.4: поддержка Shape Layer USERNAME-плейсхолдера       ║
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
    from fontTools.ttLib import TTFont
    from fontTools.pens.recordingPen import DecomposingRecordingPen
    HAS_FONTTOOLS = True
except ImportError:
    HAS_FONTTOOLS = False

logger = logging.getLogger("JellyParser")

__version__ = (0, 1, 5)

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
    def _walk_layer(layer):
        yield layer
        if "shapes" in layer:
            for s in layer["shapes"]:
                yield from _walk_shape(s)
        if "it" in layer:
            for s in layer["it"]:
                yield from _walk_shape(s)

    def _walk_shape(shape):
        yield shape
        if "it" in shape:
            for s in shape["it"]:
                yield from _walk_shape(s)
        if "shapes" in shape:
            for s in shape["shapes"]:
                yield from _walk_shape(s)

    if "layers" in lottie:
        for l in lottie["layers"]:
            yield from _walk_layer(l)
            
    if "assets" in lottie:
        for a in lottie["assets"]:
            if "layers" in a:
                for l in a["layers"]:
                    yield from _walk_layer(l)


def _is_descendant(child, parent):
    found = False
    def _check(o):
        nonlocal found
        if found: return
        if isinstance(o, dict):
            if o is child:
                found = True
                return
            for val in o.values(): _check(val)
        elif isinstance(o, list):
            for item in o: _check(item)
    if "shapes" in parent:
        for s in parent["shapes"]: _check(s)
    if "it" in parent:
        for s in parent["it"]: _check(s)
    return found


def _has_keyword_child(obj):
    keywords = ["textgroup", "text", "letters", "emoji", "text shape", "emc", "logo"]
    found = False
    def _check(o):
        nonlocal found
        if found: return
        if isinstance(o, dict):
            nm = o.get("nm")
            if isinstance(nm, str) and nm:
                nm_lower = nm.lower()
                if "user" not in nm_lower and any(kw in nm_lower for kw in keywords):
                    found = True
                    return
            for val in o.values(): _check(val)
        elif isinstance(o, list):
            for item in o: _check(item)
    if isinstance(obj, dict):
        for val in obj.values(): _check(val)
    return found


def _is_keyword_match(el):
    keywords = ["textgroup", "text", "letters", "emoji", "text shape", "emc", "logo"]
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
        if ty == 4 or ty == "gr":
            if _is_keyword_match(el):
                if _count_paths(el) >= 1 and _has_fill(el):
                    named_targets.append(el)
                        
    if named_targets:
        final_targets = []
        for cand in named_targets:
            if any(_is_descendant(cand, t) for t in named_targets if t is not cand):
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
            if any(_is_descendant(cand, t) for t in fallback_targets if t is not cand):
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


def _replace_textgroup(lottie, new_shapes):
    targets = _find_text_targets(lottie)
    if not targets:
        return False
        
    def _hfl(items): return any(x.get("ty")=="fl" for x in items)
    
    def _islc(item):
        if item.get("ty")!="gr": return False
        return not _hfl(item.get("it",[])) and not any(x.get("ty")=="st" for x in item.get("it",[]))
        
    def _patch(lst):
        style = [x for x in lst if x.get("ty") not in ("sh", "el", "rc", "sr") and not _islc(x)]
        lst[:] = new_shapes + style

    for target in targets:
        if "it" in target:
            _patch(target.setdefault("it", []))
        elif "shapes" in target:
            _patch(target.setdefault("shapes", []))
        else:
            key = "shapes" if target.get("ty") == 4 else "it"
            _patch(target.setdefault(key, []))
            
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
        ns = _text_to_lottie_shapes(new_text, font_path, cx, cy, max(abs(y2 - y1), 5.), max_width=max(abs(x2 - x1), 5.))
        if ns and _replace_textgroup(lottie, ns):
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

        async def _check_doc(i, doc):
            mime = getattr(doc, "mime_type", "")
            if mime != "application/x-tgsticker":
                return None
            try:
                raw = await download_cached(self._client, doc)
                lottie_obj = json.loads(gzip.decompress(raw).decode("utf-8"))
                bounds = _get_textgroup_bounds(lottie_obj)
                if bounds:
                    return doc
            except Exception:
                pass
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
                lottie_obj = json.loads(gzip.decompress(raw).decode("utf-8"))
                modify_lottie(lottie_obj, "jelly")
                raw = gzip.compress(json.dumps(lottie_obj, separators=(",", ":")).encode("utf-8"), compresslevel=9)
            except Exception as e:
                logger.error(f"Failed to replace text with jelly for emoji {i}: {e}")
                
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
            await status_msg.edit(pe("❌", PE["err"]) + f" Не удалось создать набор: <code>{e}</code>")
