# meta developer: @justidev

from .. import loader, utils


@loader.tds
class NeBukvalnoMod(loader.Module):
    """Добавляет «не буквально» после каждого слова."""

    strings = {
        "name": "NeBukvalno",
        "enabled": "✅ Режим «не буквально» включён.",
        "disabled": "❌ Режим «не буквально» выключен.",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "ENABLED",
                False,
                "Включён ли режим",
                validator=loader.validators.Boolean(),
            )
        )
        self._busy = set()

    @loader.command()
    async def Nebukv(self, message):
        """Включить/выключить режим: .Nebukv"""
        self.config["ENABLED"] = not self.config["ENABLED"]

        if self.config["ENABLED"]:
            await utils.answer(message, self.strings("enabled"))
        else:
            await utils.answer(message, self.strings("disabled"))

    @loader.watcher()
    async def watcher(self, message):
        if not self.config["ENABLED"]:
            return

        # Только исходящие сообщения
        if not getattr(message, "out", False):
            return

        # Не обрабатываем сообщения самого модуля
        if message.id in self._busy:
            return

        text = message.raw_text
        if not text:
            return

        # Не обрабатываем команды
        if text.startswith("."):
            return

        words = text.split()

        if not words:
            return

        new_text = " ".join(
            f"{word} не буквально" for word in words
        )

        if new_text == text:
            return

        self._busy.add(message.id)

        try:
            await message.edit(new_text)
        except Exception:
            pass
        finally:
            self._busy.discard(message.id)
