"""Launch the product operator console from source or a standalone package."""

import os


os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

from app.operator_console.quick_application import main


if __name__ == "__main__":
    raise SystemExit(main())
