from __future__ import annotations

import argparse

from app.assistant import SaktiAssistant


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sakti Assistant desktop voice assistant")
    parser.add_argument(
        "--text",
        action="store_true",
        help="Use typed commands instead of microphone input.",
    )
    parser.add_argument(
        "--once",
        type=str,
        default=None,
        help="Run a single command and exit. Useful for testing.",
    )
    parser.add_argument(
        "--no-voice",
        action="store_true",
        help="Disable text-to-speech output.",
    )
    return parser.parse_args()


def main() -> None:
    try:
        args = parse_args()
        assistant = SaktiAssistant(text_mode=args.text or bool(args.once), voice_enabled=not args.no_voice)

        if args.once:
            assistant.handle_text(args.once)
            return

        assistant.run()
    except KeyboardInterrupt:
        print("Jarvis: Assistant shutting down.")


if __name__ == "__main__":
    main()
