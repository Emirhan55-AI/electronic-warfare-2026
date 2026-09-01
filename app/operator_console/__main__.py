"""Release module entry point for the operator console."""

import os


os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

from .quick_application import main


if __name__ == "__main__":
    raise SystemExit(main())
