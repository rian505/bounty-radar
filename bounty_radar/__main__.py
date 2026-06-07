"""Allow ``python -m bounty_radar``."""
from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
