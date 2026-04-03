import os
import sys

from gui import MeetingScraperApp
from scraper import MeetingsScraper


def validate_gui_environment() -> str | None:
    if not sys.platform.startswith("linux"):
        return None

    if os.environ.get("QT_QPA_PLATFORM"):
        return None

    has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    if has_display:
        return None

    return (
        "No graphical display was detected. This application is a desktop Qt app and "
        "must be launched from an X11 or Wayland session. If you only need a "
        "non-interactive startup check inside a container, run it with "
        "QT_QPA_PLATFORM=offscreen."
    )


if __name__ == "__main__":
    environment_error = validate_gui_environment()
    if environment_error is not None:
        print(environment_error, file=sys.stderr)
        raise SystemExit(1)

    scraper = MeetingsScraper()
    app = MeetingScraperApp()
    sys.exit(app.run(scraper))
