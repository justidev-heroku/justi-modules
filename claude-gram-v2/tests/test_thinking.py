import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import server


class TestThinking(unittest.IsolatedAsyncioTestCase):
    async def test_start_thinking_creates_anim_task(self):
        server.bot = AsyncMock()
        mock_sent = MagicMock()
        mock_sent.message_id = 123
        server.bot.send_message.return_value = mock_sent
        
        server.active_thinking_tasks.clear()
        
        await server.start_thinking("12345", None)
        
        self.assertIn("12345", server.active_thinking_tasks)
        self.assertEqual(server.active_thinking_tasks["12345"]["msg_id"], 123)
        self.assertIsNotNone(server.active_thinking_tasks["12345"]["task"])
        
        task = server.active_thinking_tasks["12345"]["task"]
        server.stop_thinking("12345", None)
        await asyncio.sleep(0.001)
        self.assertTrue(task.cancelled())
        self.assertNotIn("12345", server.active_thinking_tasks)


class TestInboundHandling(unittest.IsolatedAsyncioTestCase):
    @patch("server.gate")
    @patch("server.route_ok", new_callable=AsyncMock)
    @patch("server.deliver", new_callable=AsyncMock)
    @patch("server._save_thread_id")
    @patch("server.threads_on")
    async def test_handle_inbound_locks_thread_id(self, mock_threads_on, mock_save, mock_deliver, mock_route_ok, mock_gate):
        mock_threads_on.return_value = True
        mock_gate.return_value = {
            "action": "allow",
            "access": {"ackReaction": None}
        }
        mock_route_ok.return_value = True
        
        server.session_thread_id = None
        server.bot = MagicMock()
        
        # Mock message
        msg = MagicMock()
        msg.chat.id = 12345
        msg.message_thread_id = 123456
        msg.message_id = 789
        msg.date = MagicMock()
        msg.reply_to_message = None
        
        await server.handle_inbound(msg, "Hello bot")
        
        self.assertEqual(server.session_thread_id, 123456)
        mock_save.assert_called_once_with(123456)
        mock_deliver.assert_called_once()


class TestUsageCommand(unittest.IsolatedAsyncioTestCase):
    @patch("server.dm_command_gate")
    @patch("server.Path.exists")
    @patch("asyncio.create_subprocess_exec")
    async def test_cmd_usage_success(self, mock_exec, mock_exists, mock_gate):
        mock_gate.return_value = {
            "senderId": "123",
            "access": {"allowFrom": ["123"]}
        }
        mock_exists.return_value = True
        
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (
            b"Current session: 10% used \xc2\xb7 resets Jun 29, 3am (UTC)\n"
            b"Current week (all models): 66% used \xc2\xb7 resets Jul 2, 3:59am (UTC)\n",
            b""
        )
        mock_exec.return_value = mock_process
        
        msg = AsyncMock()
        progress_msg = AsyncMock()
        msg.answer.return_value = progress_msg
        
        import datetime
        class MockDatetime(datetime.datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime.datetime(2026, 6, 28, 22, 0, 0, tzinfo=datetime.timezone.utc)
                
        with patch("server.datetime.datetime", MockDatetime):
            await server.cmd_usage(msg)
            
        msg.answer.assert_called_once_with(f"<b>{server.EMOJI_REFRESH} Запрашиваю лимиты использования...</b>", parse_mode="HTML")
        progress_msg.edit_text.assert_called_once()
        text_arg = progress_msg.edit_text.call_args[0][0]
        
        self.assertIn("Сессия: 10% · сброс через ~5ч (29 июн, 03:00 UTC)", text_arg)
        self.assertIn("Неделя: 66% · сброс 2 июл, 03:59 UTC", text_arg)

    @patch("server.dm_command_gate")
    @patch("server.Path.exists")
    @patch("asyncio.create_subprocess_exec")
    async def test_cmd_usage_subscription_success(self, mock_exec, mock_exists, mock_gate):
        mock_gate.return_value = {
            "senderId": "123",
            "access": {"allowFrom": ["123"]}
        }
        mock_exists.return_value = True
        
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (
            b"You are currently using your subscription to power your Claude Code usage\n"
            b"Last 24h \xc2\xb7 2087 requests \xc2\xb7 4 sessions\n"
            b"100% of your usage came from subagent-heavy sessions\n",
            b""
        )
        mock_exec.return_value = mock_process
        
        msg = AsyncMock()
        progress_msg = AsyncMock()
        msg.answer.return_value = progress_msg
        
        await server.cmd_usage(msg)
        
        msg.answer.assert_called_once_with(f"<b>{server.EMOJI_REFRESH} Запрашиваю лимиты использования...</b>", parse_mode="HTML")
        progress_msg.edit_text.assert_called_once()
        text_arg = progress_msg.edit_text.call_args[0][0]
        
        self.assertIn("Подписка Claude Code активна", text_arg)
        self.assertIn("Активность за 24ч: <b>2087</b> запросов, <b>4</b> сессий", text_arg)
        self.assertIn("100% запросов пришлось на: <i>subagent-heavy sessions</i>", text_arg)


class TestResumeCommand(unittest.IsolatedAsyncioTestCase):
    @patch("server.dm_command_gate")
    @patch("server.Path")
    @patch("server.get_active_session_id")
    async def test_cmd_resume_render(self, mock_get_active_session_id, mock_path_class, mock_gate):
        mock_get_active_session_id.return_value = "session1"
        mock_gate.return_value = {
            "senderId": "123",
            "access": {"allowFrom": ["123"]}
        }
        
        # Mock instances of Path
        mock_path_inst = MagicMock()
        mock_path_class.return_value = mock_path_inst
        mock_path_inst.exists.return_value = True
        mock_path_inst.read_text.return_value = ""
        
        # glob should return mock file paths: one populated, one empty
        mock_file1 = MagicMock()
        mock_file1.stat.return_value.st_size = 1048576  # 1 MB
        mock_file1.stat.return_value.st_mtime = 1782684755.0
        mock_file1.stem = "session1"
        mock_file1.__fspath__.return_value = "session1.jsonl"
        
        mock_file2 = MagicMock()
        mock_file2.stat.return_value.st_size = 524288  # 0.5 MB
        mock_file2.stat.return_value.st_mtime = 1782600000.0
        mock_file2.stem = "session2"
        mock_file2.__fspath__.return_value = "session2.jsonl"
        
        mock_path_inst.glob.return_value = [mock_file1, mock_file2]
        
        import builtins
        original_open = builtins.open
        
        import io, contextlib
        def open_side_effect(file, *args, **kwargs):
            if file is mock_file1:
                return contextlib.closing(io.StringIO('{"type":"user","message":{"role":"user","content":"Hello server"}}\n'))
            elif file is mock_file2:
                return contextlib.closing(io.StringIO(''))
            return original_open(file, *args, **kwargs)
            
        msg = AsyncMock()
        
        with patch("builtins.open", side_effect=open_side_effect):
            await server.cmd_resume(msg)
            
        msg.answer.assert_called_once()
        text_arg = msg.answer.call_args[0][0]
        kb_arg = msg.answer.call_args[1]["reply_markup"]
        
        self.assertIn("Выберите сессию Claude Code для возобновления:", text_arg)
        found_btn1 = False
        found_btn2 = False
        for row in kb_arg.inline_keyboard:
            for btn in row:
                if "Hello server" in btn.text:
                    found_btn1 = True
                    self.assertIn("1.00 MB", btn.text)
                    self.assertEqual(btn.callback_data, "res:sel:session1")
                    # session1 has newest mtime → should be active
                    self.assertEqual(btn.style, "success")
                    self.assertEqual(btn.icon_custom_emoji_id, "5958376256788502078")
                elif "Нью сессия (" in btn.text:
                    found_btn2 = True
                    self.assertIn("0.50 MB", btn.text)
                    self.assertEqual(btn.callback_data, "res:sel:session2")
                    # session2 is NOT active
                    self.assertEqual(btn.style, "primary")
                    self.assertEqual(btn.icon_custom_emoji_id, "5870528606328852614")
                    
        self.assertTrue(found_btn1)
        self.assertTrue(found_btn2)


class TestAccountManagement(unittest.IsolatedAsyncioTestCase):
    @patch("server.dm_command_gate")
    @patch("server.Path")
    @patch("server.safe_restart")
    async def test_cmd_delete_account_success(self, mock_restart, mock_path, mock_gate):
        mock_gate.return_value = {
            "senderId": "123",
            "access": {"allowFrom": ["123"]}
        }
        
        # We need mock instances for files
        mock_target_cred = MagicMock()
        mock_target_cred.exists.return_value = True
        mock_target_json = MagicMock()
        mock_target_json.exists.return_value = True
        
        mock_active_cred = MagicMock()
        mock_active_cred.exists.return_value = True
        mock_active_cred.read_text.return_value = "secret1"
        mock_target_cred.read_text.return_value = "secret2" # not active
        mock_active_json = MagicMock()
        mock_active_json.exists.return_value = True

        def path_side_effect(arg):
            if "credentials.test_acc.json" in arg:
                return mock_target_cred
            elif "claude.test_acc.json" in arg:
                return mock_target_json
            elif "credentials.json" in arg:
                return mock_active_cred
            elif ".claude.json" in arg:
                return mock_active_json
            return MagicMock()
            
        mock_path.side_effect = path_side_effect
        
        msg = AsyncMock()
        msg.text = "/delete_account test_acc"
        
        await server.cmd_delete_account(msg)
        
        mock_target_cred.unlink.assert_called_once()
        mock_target_json.unlink.assert_called_once()
        mock_restart.assert_not_called()
        msg.answer.assert_called_once_with(f"{server.EMOJI_SUCCESS} Профиль <code>test_acc</code> успешно удален.", parse_mode="HTML")

    @patch("server.dm_command_gate")
    @patch("server.Path")
    @patch("server.safe_restart")
    async def test_cmd_delete_active_account_success(self, mock_restart, mock_path, mock_gate):
        mock_gate.return_value = {
            "senderId": "123",
            "access": {"allowFrom": ["123"]}
        }
        
        mock_target_cred = MagicMock()
        mock_target_cred.exists.return_value = True
        mock_target_json = MagicMock()
        mock_target_json.exists.return_value = True
        
        mock_active_cred = MagicMock()
        mock_active_cred.exists.return_value = True
        mock_active_cred.read_text.return_value = "secret_active"
        mock_target_cred.read_text.return_value = "secret_active" # active!
        mock_active_json = MagicMock()
        mock_active_json.exists.return_value = True

        def path_side_effect(arg):
            if "credentials.active_acc.json" in arg:
                return mock_target_cred
            elif "claude.active_acc.json" in arg:
                return mock_target_json
            elif "credentials.json" in arg:
                return mock_active_cred
            elif ".claude.json" in arg:
                return mock_active_json
            return MagicMock()
            
        mock_path.side_effect = path_side_effect
        
        msg = AsyncMock()
        msg.text = "/delete_account active_acc"
        
        await server.cmd_delete_account(msg)
        
        mock_target_cred.unlink.assert_called_once()
        mock_target_json.unlink.assert_called_once()
        mock_active_cred.unlink.assert_called_once()
        mock_active_json.unlink.assert_called_once()
        mock_restart.assert_called_once()
        msg.answer.assert_called_once_with(
            f"<b>{server.EMOJI_SUCCESS} Профиль <code>active_acc</code> успешно удален</b>\n"
            f"<blockquote>{server.EMOJI_REFRESH} Бот перезапускается...</blockquote>",
            parse_mode="HTML"
        )


if __name__ == "__main__":
    unittest.main()
