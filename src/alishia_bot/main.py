from __future__ import annotations

from dotenv import load_dotenv

from alishia_bot.bot import AlishiaBot


def main() -> int:
    load_dotenv()

    bot = AlishiaBot()
    print("Alishia Bot — type a message (Ctrl+C or 'quit' to exit)\n")

    while True:
        try:
            message = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            return 0

        if message.lower() in {"quit", "exit", "q"}:
            print("Bye!")
            return 0

        response = bot.handle(message)
        print(f"bot> {response.text}\n")
