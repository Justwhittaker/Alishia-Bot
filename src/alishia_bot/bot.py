from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class BotResponse:
    text: str


class AlishiaBot:
    """Rule-based starter bot. Swap in LLM or platform adapters as you grow."""

    def handle(self, message: str) -> BotResponse:
        normalized = message.strip().lower()

        if not normalized:
            return BotResponse("Say something and I'll respond.")

        if normalized in {"hi", "hello", "hey"}:
            return BotResponse("Hey — Alishia Bot is online. What can I help with?")

        if normalized in {"help", "?"}:
            return BotResponse(
                "Commands: hello, help, time, echo <text>. "
                "Edit src/alishia_bot/bot.py to add your own behavior."
            )

        if normalized == "time":
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            return BotResponse(f"The current time is {now}.")

        echo_match = re.fullmatch(r"echo\s+(.+)", normalized)
        if echo_match:
            return BotResponse(echo_match.group(1))

        return BotResponse(
            f"I heard: {message.strip()}. Try `help` to see what I can do."
        )
