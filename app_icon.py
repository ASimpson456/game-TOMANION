"""Иконка TOMANION — томат для окна и exe."""

from pathlib import Path

import pygame

from constants import BG
import pixel_art as art

ICO_SIZES = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
_cache = {}


def render_tomato_icon(size):
    surf = pygame.Surface((size, size))
    surf.fill(BG)
    tomato = art._build_tomato()
    tw, th = tomato.get_size()
    pad = max(2, size // 16)
    scale = min((size - pad * 2) / tw, (size - pad * 2) / th)
    sw = max(1, int(tw * scale))
    sh = max(1, int(th * scale))
    scaled = pygame.transform.scale(tomato, (sw, sh))
    x = (size - sw) // 2
    y = (size - sh) // 2 - max(0, size // 32)
    surf.blit(scaled, (x, y))
    return surf


def _surface_to_pil(surf):
    from PIL import Image

    rgba = pygame.image.tostring(surf, "RGBA")
    return Image.frombytes("RGBA", surf.get_size(), rgba)


def get_icon_surface(size=64):
    if size not in _cache:
        if not pygame.get_init():
            pygame.init()
        _cache[size] = render_tomato_icon(size)
    return _cache[size]


def apply_window_icon():
    if not pygame.get_init():
        return
    try:
        pygame.display.set_icon(get_icon_surface(64))
    except pygame.error:
        pass


def write_icon_files(assets_dir=None):
    assets_dir = Path(assets_dir or Path(__file__).parent / "assets")
    assets_dir.mkdir(parents=True, exist_ok=True)
    if not pygame.get_init():
        pygame.init()

    master = _surface_to_pil(render_tomato_icon(256))
    ico_path = assets_dir / "tomato.ico"
    master.save(ico_path, format="ICO", sizes=ICO_SIZES)
    master.save(assets_dir / "tomato_icon.png")
    return ico_path
