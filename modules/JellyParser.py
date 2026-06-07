# ╔══════════════════════════════════════════════════════════════════╗
# ║                        🔮 JellyParser v0.1.0                     ║
# ║           Парсер эмодзи-паков на наличие текстовых групп         ║
# ║                  v0.1.0 beta: первый релиз                       ║
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
# requires: Pillow

import asyncio
import gzip
import io
import json
import logging
import os
import re
import time
from telethon import functions, types
from telethon.tl.types import DocumentAttributeCustomEmoji, DocumentAttributeSticker, Message

from .. import loader, utils

logger = logging.getLogger("JellyParser")

__version__ = (0, 1, 0)

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


def _get_textgroup_bounds(lottie):
    def find_named(obj):
        if isinstance(obj, dict):
            if obj.get("ty")=="gr" and obj.get("nm")=="TextGroup":
                b=_verts_to_bounds(_collect_path_verts(obj))
                if b: return b
            for v in obj.values():
                r=find_named(v)
                if r: return r
        elif isinstance(obj, list):
            for item in obj:
                r=find_named(item)
                if r: return r
        return None
    b=find_named(lottie)
    if b: return b

    def find_text_layer(layers):
        for layer in layers:
            if layer.get("ty")!=4: continue
            nm=layer.get("nm",""); shapes=layer.get("shapes",[])
            n_sh=sum(1 for s in shapes if s.get("ty")=="sh")
            has_fl=any(s.get("ty")=="fl" for s in shapes)
            if ("text" in nm.lower() or "Text" in nm) and n_sh>=2 and has_fl:
                b=_verts_to_bounds(_collect_path_verts({"shapes":shapes}))
                if b: return b
        return None

    all_ll=[lottie.get("layers",[])]+[a.get("layers",[]) for a in lottie.get("assets",[])]
    for ll in all_ll:
        b=find_text_layer(ll)
        if b: return b

    def _gfl(gr): return any(x.get("ty")=="fl" for x in gr.get("it",[]))
    def _cdsh(gr): return sum(1 for x in gr.get("it",[]) if x.get("ty")=="sh")
    def _cnsh(gr):
        n=0
        for x in gr.get("it",[]):
            n+=1 if x.get("ty")=="sh" else (_cnsh(x) if x.get("ty")=="gr" else 0)
        return n

    matched = []
    def walk(obj, path=()):
        if isinstance(obj, dict):
            if obj.get("ty")=="gr" and _gfl(obj) and (_cdsh(obj)==0 or _cdsh(obj)>=3) and _cnsh(obj)>=3:
                matched.append((obj, path))
            for k, v in obj.items():
                walk(v, path + (k,))
        elif isinstance(obj, list):
            for i, x in enumerate(obj):
                walk(x, path + (i,))

    walk(lottie)

    filtered_matched = []
    for gr1, p1 in matched:
        is_ancestor = False
        for gr2, p2 in matched:
            if len(p1) < len(p2) and p2[:len(p1)] == p1:
                is_ancestor = True
                break
        if not is_ancestor:
            filtered_matched.append(gr1)

    for gr in filtered_matched:
        verts = _collect_path_verts(gr)
        if verts:
            xs=[v[0] for v in verts]; ys=[v[1] for v in verts]
            w=max(xs)-min(xs); h=max(ys)-min(ys)+1e-9
            if w>h*1.3 or w>0:
                b = _verts_to_bounds(verts)
                if b: return b

    return None


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
                # Set exists, increment and check again
                n += 1
            except Exception as e:
                if "STICKERSET_INVALID" in str(e) or "invalid" in str(e).lower():
                    break
                else:
                    # Treat other exceptions as free just in case
                    break

        me = await self._client.get_me()
        mee = await self._client.get_input_entity("me")

        async def _upload_doc(i, doc):
            raw = await download_cached(self._client, doc)
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
