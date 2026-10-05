"""Which Qt platform (window system) to use, decided before the application starts.

Qt 6.4 on GNOME Wayland has to draw its own window frames with an old decoration
plugin; dialogs look dated and flicker when moved. Through XWayland GNOME draws the
frames itself. ``auto`` therefore picks X11 on GNOME Wayland sessions.
"""

from collections.abc import Mapping

SETTINGS_KEY = "ui/platform"
AUTO, WAYLAND, X11 = "auto", "wayland", "xcb"
CHOICES = (AUTO, WAYLAND, X11)


def choose_platform(env: Mapping[str, str], setting: str) -> str | None:
    """Value for QT_QPA_PLATFORM, or None to leave Qt's own choice.

    An explicit QT_QPA_PLATFORM in the environment always wins. X11 needs an X
    server (DISPLAY); Wayland stays as fallback in the list.
    """
    if env.get("QT_QPA_PLATFORM"):
        return None
    has_x = bool(env.get("DISPLAY"))
    if setting == WAYLAND:
        return "wayland" if env.get("WAYLAND_DISPLAY") else None
    if setting == X11:
        return "xcb;wayland" if has_x else None
    gnome_wayland = (
        env.get("XDG_SESSION_TYPE") == "wayland"
        and "GNOME" in env.get("XDG_CURRENT_DESKTOP", "").upper()
    )
    return "xcb;wayland" if gnome_wayland and has_x else None
