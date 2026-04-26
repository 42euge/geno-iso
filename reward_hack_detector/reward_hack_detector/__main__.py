"""Allow ``python -m reward_hack_detector ...`` to invoke the CLI."""

from reward_hack_detector.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
