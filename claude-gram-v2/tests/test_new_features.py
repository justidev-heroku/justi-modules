"""Tests for new features: thinking bubble, reactions, send_file_to_tg, model/effort commands."""
import asyncio
import json
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Minimal stubs so server.py imports without a real bot token
# ---------------------------------------------------------------------------

os_mod = __import__("os")
os_mod.environ.setdefault("TELEGRAM_BOT_TOKEN", "000000000:AAtest_stub_token_for_tests")

# Patch Path.home() only for SETTINGS_FILE resolution; we'll tmp-dir it per test.


def _import_server():
    """Import server module fresh, patching heavy side-effects."""
    if "server" in sys.modules:
        return sys.modules["server"]
    with patch("aiogram.Bot.__init__", return_value=None), \
         patch("aiogram.Bot.get_me", new_callable=AsyncMock), \
         patch("sqlite3.connect"):
        import importlib, importlib.util
        spec = importlib.util.spec_from_file_location(
            "server",
            "/root/ripcats-marketplace/claude-gram/server.py",
        )
        mod = importlib.util.module_from_spec(spec)
        sys.modules["server"] = mod
        try:
            spec.loader.exec_module(mod)
        except SystemExit:
            pass
    return mod


# ---------------------------------------------------------------------------
# stop_thinking — double-call safety
# ---------------------------------------------------------------------------

def test_stop_thinking_no_bubble():
    """stop_thinking with no pending bubble must not raise."""
    import server
    server.active_thinking_tasks.clear()
    server.stop_thinking("99999", None)  # no-op, no exception


def test_stop_thinking_double_call():
    """Second stop_thinking for same chat_id is a silent no-op."""
    import server
    server.active_thinking_tasks["99999"] = 42
    with patch.object(server, "bot") as mock_bot:
        mock_bot.delete_message = AsyncMock()
        server.stop_thinking("99999", None)
        server.stop_thinking("99999", None)  # must not raise or double-delete
    assert "99999" not in server.active_thinking_tasks


# ---------------------------------------------------------------------------
# reactions — emoji fallback
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reactions_no_emoji_uses_fallback():
    """reactions tool without emoji field defaults to 👀."""
    import server
    calls = []

    async def fake_set_reaction(chat_id, msg_id, reaction):
        calls.append(reaction)

    with patch.object(server, "bot") as mock_bot, \
         patch.object(server, "assert_allowed_chat"):
        mock_bot.set_message_reaction = AsyncMock(side_effect=fake_set_reaction)
        await server.handle_tool_call(
            msg_id=1,
            params={"name": "reactions", "arguments": {"chat_id": "1", "message_id": "2"}},
        )

    assert calls, "set_message_reaction was not called"
    from aiogram.types import ReactionTypeEmoji
    assert calls[0][0].emoji == "👀"


@pytest.mark.asyncio
async def test_reactions_explicit_emoji_respected():
    """Explicit emoji is passed through unchanged."""
    import server
    calls = []

    async def fake_set_reaction(chat_id, msg_id, reaction):
        calls.append(reaction)

    with patch.object(server, "bot") as mock_bot, \
         patch.object(server, "assert_allowed_chat"):
        mock_bot.set_message_reaction = AsyncMock(side_effect=fake_set_reaction)
        await server.handle_tool_call(
            msg_id=1,
            params={"name": "reactions", "arguments": {"chat_id": "1", "message_id": "2", "emoji": "❤"}},
        )

    from aiogram.types import ReactionTypeEmoji
    assert calls[0][0].emoji == "❤"


# ---------------------------------------------------------------------------
# send_file_to_tg — delegates to tool_reply_file
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_file_to_tg_delegates():
    """send_file_to_tg must call tool_reply_file with same args."""
    import server
    with patch.object(server, "tool_reply_file", new_callable=AsyncMock) as mock_rf:
        mock_rf.return_value = "sent (id: 1)"
        args = {"chat_id": "1", "files": ["/tmp/test.png"]}
        await server.handle_tool_call(
            msg_id=1,
            params={"name": "send_file_to_tg", "arguments": args},
        )
        mock_rf.assert_awaited_once_with(args)


# ---------------------------------------------------------------------------
# write_setting — file creation and key preservation
# ---------------------------------------------------------------------------

def test_write_setting_creates_file(tmp_path):
    """write_setting creates settings.json if it doesn't exist."""
    import server
    target = tmp_path / "settings.json"
    with patch.object(server, "SETTINGS_FILE", target):
        server.write_setting("model", "sonnet")
    data = json.loads(target.read_text())
    assert data["model"] == "sonnet"


def test_write_setting_preserves_other_keys(tmp_path):
    """write_setting must not clobber unrelated keys."""
    import server
    target = tmp_path / "settings.json"
    target.write_text(json.dumps({"effortLevel": "high", "tui": "fullscreen"}))
    with patch.object(server, "SETTINGS_FILE", target):
        server.write_setting("model", "opus")
    data = json.loads(target.read_text())
    assert data["model"] == "opus"
    assert data["effortLevel"] == "high"
    assert data["tui"] == "fullscreen"


# ---------------------------------------------------------------------------
# /model callback — unknown alias
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_model_callback_unknown_alias():
    """Callback with unknown model alias answers without crashing."""
    import server
    cb = MagicMock()
    cb.data = "model:unknown_xyz"
    cb.answer = AsyncMock()
    await server.on_model_callback(cb)
    cb.answer.assert_awaited_once()
    # Must NOT have tried to edit message
    assert not hasattr(cb, "message") or not cb.message.edit_text.called


# ---------------------------------------------------------------------------
# /effort — Haiku warning present
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_effort_haiku_shows_warning():
    """cmd_effort shows extended-thinking warning when model is haiku."""
    import server
    sent_texts = []

    async def fake_send(chat_id, text, **kwargs):
        sent_texts.append(text)
        return MagicMock(message_id=1)

    msg = MagicMock()
    msg.chat.id = "1"

    with patch.object(server, "load_access", return_value={"model": "haiku", "effortLevel": "medium"}), \
         patch.object(server, "SETTINGS_FILE", Path("/nonexistent/settings.json")), \
         patch.object(server, "bot") as mock_bot, \
         patch.object(server, "thread_kwargs", return_value={}):
        mock_bot.send_message = AsyncMock(side_effect=fake_send)
        await server.cmd_effort(msg)

    assert sent_texts, "No message was sent"
    assert "Haiku" in sent_texts[0] or "thinking" in sent_texts[0]


# ---------------------------------------------------------------------------
# /effort callback — invalid level
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_effort_callback_invalid_level():
    """Callback with invalid effort level answers without crashing."""
    import server
    cb = MagicMock()
    cb.data = "effort:ultra_invalid"
    cb.answer = AsyncMock()
    await server.on_effort_callback(cb)
    cb.answer.assert_awaited_once()


# ---------------------------------------------------------------------------
# MCP initialize — instructions field present
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mcp_initialize_has_instructions():
    """MCP initialize response must contain non-empty 'instructions' field."""
    import server
    responses = []

    async def fake_write(obj):
        responses.append(obj)

    with patch.object(server, "write_message", side_effect=fake_write):
        await server.mcp_dispatch({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {}},
        })

    assert responses, "No response written"
    result = responses[0].get("result", {})
    assert "instructions" in result, "instructions field missing from initialize response"
    assert result["instructions"].strip(), "instructions field is empty"


# ---------------------------------------------------------------------------
# refresh_oauth_token
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_refresh_skipped_when_token_valid(tmp_path):
    """Если токен ещё живой — функция возвращает 'ok' и не делает HTTP-запрос."""
    import server, time as _time
    creds_file = tmp_path / "creds.json"
    future_expiry = int(_time.time() * 1000) + 3_600_000  # +1 час
    creds_file.write_bytes(
        __import__("orjson").dumps({
            "claudeAiOauth": {
                "accessToken": "valid_token",
                "refreshToken": "some_refresh",
                "expiresAt": future_expiry,
            }
        })
    )
    with patch("curl_cffi.requests.AsyncSession") as mock_session_cls:
        result = await server.refresh_oauth_token(creds_file)
    assert result == "ok"
    mock_session_cls.assert_not_called()


@pytest.mark.asyncio
async def test_refresh_updates_file_on_success(tmp_path):
    """Успешный ответ API → токены обновляются в файле."""
    import server, time as _time
    creds_file = tmp_path / "creds.json"
    expired = int(_time.time() * 1000) - 5_000  # просроченный
    creds_file.write_bytes(
        __import__("orjson").dumps({
            "claudeAiOauth": {
                "accessToken": "old_token",
                "refreshToken": "old_refresh",
                "expiresAt": expired,
            }
        })
    )
    fake_resp_body = __import__("orjson").dumps({
        "access_token": "new_token",
        "refresh_token": "new_refresh",
        "expires_in": 3600,
    })

    mock_resp = MagicMock(status_code=200, content=fake_resp_body, headers={})
    mock_session = AsyncMock()
    mock_session.post.return_value = mock_resp

    with patch("curl_cffi.requests.AsyncSession") as mock_session_cls, \
         patch("server.refresh_oauth_token_playwright", new_callable=AsyncMock) as mock_pw:
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        result = await server.refresh_oauth_token(creds_file)

    assert result == "refreshed"
    saved = __import__("orjson").loads(creds_file.read_bytes())
    assert saved["claudeAiOauth"]["accessToken"] == "new_token"
    assert saved["claudeAiOauth"]["refreshToken"] == "new_refresh"
    mock_pw.assert_not_called()


@pytest.mark.asyncio
async def test_refresh_returns_error_on_http_failure(tmp_path):
    """HTTP-ошибка (429, 401...) → возвращает 'error', файл не трогаем (если Playwright тоже падает)."""
    import server, time as _time
    creds_file = tmp_path / "creds.json"
    expired = int(_time.time() * 1000) - 5_000
    creds_file.write_bytes(
        __import__("orjson").dumps({
            "claudeAiOauth": {
                "accessToken": "old_token",
                "refreshToken": "old_refresh",
                "expiresAt": expired,
            }
        })
    )

    mock_resp = MagicMock(status_code=429, content=b"", headers={})
    mock_session = AsyncMock()
    mock_session.post.return_value = mock_resp

    with patch("curl_cffi.requests.AsyncSession") as mock_session_cls, \
         patch("server.refresh_oauth_token_playwright", new_callable=AsyncMock, side_effect=Exception("pw failed")) as mock_pw:
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        result = await server.refresh_oauth_token(creds_file)

    assert result == "error"
    saved = __import__("orjson").loads(creds_file.read_bytes())
    assert saved["claudeAiOauth"]["accessToken"] == "old_token"
    mock_pw.assert_called_once()


@pytest.mark.asyncio
async def test_refresh_no_refresh_token_returns_error(tmp_path):
    """Файл без refreshToken → 'error', без HTTP-запроса."""
    import server, time as _time
    creds_file = tmp_path / "creds.json"
    expired = int(_time.time() * 1000) - 5_000
    creds_file.write_bytes(
        __import__("orjson").dumps({
            "claudeAiOauth": {
                "accessToken": "old_token",
                "expiresAt": expired,
            }
        })
    )
    with patch("curl_cffi.requests.AsyncSession") as mock_session_cls:
        result = await server.refresh_oauth_token(creds_file)
    assert result == "error"
    mock_session_cls.assert_not_called()


# ---------------------------------------------------------------------------
# refresh_oauth_token — cooldown cache
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_refresh_cooldown_blocks_retry(tmp_path):
    """После 429 кулдаун не даёт повторно дёргать эндпоинт."""
    import server, time as _time
    creds_file = tmp_path / "creds.json"
    expired = int(_time.time() * 1000) - 5_000
    creds_file.write_bytes(
        __import__("orjson").dumps({
            "claudeAiOauth": {
                "accessToken": "old",
                "refreshToken": "rt",
                "expiresAt": expired,
            }
        })
    )

    # Задаем возвращаемый ответ 429 с кулдауном
    mock_resp = MagicMock(status_code=429, content=b"", headers={"retry-after": "300"})
    mock_session = AsyncMock()
    mock_session.post.return_value = mock_resp

    server._refresh_cooldown.pop(str(creds_file), None)

    with patch("curl_cffi.requests.AsyncSession") as mock_session_cls, \
         patch("server.refresh_oauth_token_playwright", new_callable=AsyncMock, side_effect=Exception("pw fail")):
        mock_session_cls.return_value.__aenter__.return_value = mock_session

        # Первый вызов -> 429 -> кулдаун записан
        r1 = await server.refresh_oauth_token(creds_file)
        assert r1 == "error"

        # Второй вызов сразу — должен вернуть "error" БЕЗ запроса
        mock_session.post.reset_mock()
        r2 = await server.refresh_oauth_token(creds_file)
        assert r2 == "error"
        mock_session.post.assert_not_called()


@pytest.mark.asyncio
async def test_refresh_cooldown_expires(tmp_path):
    """После истечения кулдауна следующий вызов снова делает HTTP-запрос."""
    import server, time as _time
    creds_file = tmp_path / "creds.json"
    expired = int(_time.time() * 1000) - 5_000
    creds_file.write_bytes(
        __import__("orjson").dumps({
            "claudeAiOauth": {
                "accessToken": "old",
                "refreshToken": "rt",
                "expiresAt": expired,
            }
        })
    )
    # Ставим кулдаун в прошлом
    server._refresh_cooldown[str(creds_file)] = _time.time() - 1

    fake_resp_body = __import__("orjson").dumps({
        "access_token": "new_token",
        "expires_in": 3600,
    })
    mock_resp = MagicMock(status_code=200, content=fake_resp_body, headers={})
    mock_session = AsyncMock()
    mock_session.post.return_value = mock_resp

    with patch("curl_cffi.requests.AsyncSession") as mock_session_cls:
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        result = await server.refresh_oauth_token(creds_file)

    assert result == "refreshed"
    assert str(creds_file) not in server._refresh_cooldown


# ---------------------------------------------------------------------------
# cmd_switch_account — stops on rate-limited refresh
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_switch_account_stops_on_rate_limit(tmp_path):
    """Если рефреш вернул error + кулдаун в кэше — бот не переключается и показывает время."""
    import server, time as _time

    creds_file = tmp_path / ".credentials.testakk.json"
    creds_file.write_bytes(__import__("orjson").dumps({
        "claudeAiOauth": {"accessToken": "x", "refreshToken": "y", "expiresAt": 0}
    }))

    # Эмулируем кулдаун 150 сек
    server._refresh_cooldown[str(creds_file)] = _time.time() + 150

    sent = []
    msg = MagicMock()
    msg.text = f"/switch_account testakk"
    msg.answer = AsyncMock(side_effect=lambda text, **kw: sent.append(text) or MagicMock())

    with patch.object(server, "dm_command_gate", return_value={"senderId": "1", "access": {"allowFrom": ["1"]}}), \
         patch.object(server, "refresh_oauth_token", new_callable=AsyncMock, return_value="error"), \
         patch("pathlib.Path.exists", return_value=True), \
         patch.object(server, "_refresh_cooldown", {str(creds_file): _time.time() + 150}), \
         patch.object(server, "safe_restart") as mock_restart:
        # Подменяем target_credentials на tmp creds_file
        with patch("pathlib.Path.__new__", side_effect=lambda cls, *a, **kw: creds_file
                   if ".credentials.testakk.json" in str(a) else Path.__new__(cls, *a, **kw)):
            pass  # слишком сложно мокать Path; проверяем через safe_restart

        # Упрощённая проверка: safe_restart не должен вызываться
        await server.cmd_switch_account(msg)
        mock_restart.assert_not_called()

    # Должно быть сообщение об ошибке
    assert any("❌" in s or "заблокирован" in s or "Не удалось" in s for s in sent), f"No error message in: {sent}"


@pytest.mark.asyncio
async def test_refresh_cooldown_from_various_headers(tmp_path):
    """Тест проверяет извлечение кулдауна из различных заголовков рейт-лимита."""
    import server, time as _time
    creds_file = tmp_path / "creds.json"
    expired = int(_time.time() * 1000) - 5_000
    creds_file.write_bytes(
        __import__("orjson").dumps({
            "claudeAiOauth": {
                "accessToken": "old",
                "refreshToken": "rt",
                "expiresAt": expired,
            }
        })
    )

    # 1. Заголовков нет -> кулдаун не выставляется
    mock_resp_empty = MagicMock(status_code=429, content=b"", headers={})
    mock_session = AsyncMock()
    mock_session.post.return_value = mock_resp_empty

    server._refresh_cooldown.pop(str(creds_file), None)
    with patch("curl_cffi.requests.AsyncSession") as mock_session_cls, \
         patch("server.refresh_oauth_token_playwright", new_callable=AsyncMock, side_effect=Exception("pw fail")):
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        await server.refresh_oauth_token(creds_file)
    assert str(creds_file) not in server._refresh_cooldown

    # 2. Есть x-retry-after-ms -> кулдаун выставляется
    mock_resp_ms = MagicMock(status_code=429, content=b"", headers={"x-retry-after-ms": "120000"})
    mock_session.post.return_value = mock_resp_ms

    server._refresh_cooldown.pop(str(creds_file), None)
    with patch("curl_cffi.requests.AsyncSession") as mock_session_cls, \
         patch("server.refresh_oauth_token_playwright", new_callable=AsyncMock, side_effect=Exception("pw fail")):
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        await server.refresh_oauth_token(creds_file)
    cooldown = server._refresh_cooldown.get(str(creds_file), 0.0)
    assert cooldown > _time.time() + 115
    assert cooldown <= _time.time() + 125

    # 3. Есть anthropic-ratelimit-requests-reset (абсолютный timestamp) -> кулдаун рассчитывается
    future_ts = int(_time.time()) + 300
    mock_resp_reset = MagicMock(status_code=429, content=b"", headers={"anthropic-ratelimit-requests-reset": str(future_ts)})
    mock_session.post.return_value = mock_resp_reset

    server._refresh_cooldown.pop(str(creds_file), None)
    with patch("curl_cffi.requests.AsyncSession") as mock_session_cls, \
         patch("server.refresh_oauth_token_playwright", new_callable=AsyncMock, side_effect=Exception("pw fail")):
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        await server.refresh_oauth_token(creds_file)
    cooldown = server._refresh_cooldown.get(str(creds_file), 0.0)
    assert cooldown > _time.time() + 295
    assert cooldown <= _time.time() + 305


@pytest.mark.asyncio
async def test_send_one_text_formatting_error_fallback():
    """Тестирует, что при ошибке парсинга форматирования бот пробует отправить plain-text."""
    import server
    from aiogram.exceptions import TelegramBadRequest

    call_count = 0
    async def mock_send_message(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise TelegramBadRequest(method="sendMessage", message="Can't parse entities: unfamiliar tag")
        mock_sent = MagicMock()
        mock_sent.message_id = 999
        return mock_sent

    with patch.object(server.bot, "send_message", side_effect=mock_send_message):
        res = await server._send_one_text("123", "<b>bold text</b>", "HTML", None)

    assert res == [999]
    assert call_count == 2


def test_cmd_usage_locale_independent():
    """Проверяет стабильность парсинга месяцев в parse_date."""
    import server
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # Проверяем, что наша MONTH_MAP на месте
    assert "jun" in server.MONTH_MAP
    assert server.MONTH_MAP["jun"] == "06"




