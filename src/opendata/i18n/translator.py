import gettext
from collections.abc import Callable
from pathlib import Path

# Global variable to hold the current translation function
_current_t: Callable[[str], str] = gettext.gettext


def setup_i18n(lang: str = "en"):
    """Configures the translation based on the selected language."""
    global _current_t
    locales_dir = Path(__file__).parent

    if lang == "en":
        _current_t = gettext.gettext
    else:
        try:
            translation = gettext.translation(
                "messages", localedir=str(locales_dir), languages=[lang], fallback=True
            )
            _current_t = translation.gettext
        except Exception:
            _current_t = gettext.gettext


def _(text: str) -> str:
    """Dynamic translation wrapper."""
    return _current_t(text)
