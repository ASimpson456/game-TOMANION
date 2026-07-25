import sys
from pathlib import Path


def app_dir():
    """Папка с exe (или с исходниками при запуске через python)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def resource_dir():
    """Папка с ресурсами (внутри exe или рядом с исходниками)."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent
