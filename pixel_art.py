"""Пиксель-арт рендер в стиле референсов Томата и Лука."""

from pathlib import Path

import pygame

from constants import *
from paths import resource_dir

ASSETS = resource_dir() / "assets"
_cache = {}

TOMATO_SIZE = (42, 46)
ONION_SIZE = (26, 52)
BLOCK = 2



from svg_sprite import scale_nearest as _scale_nearest


def _load_sprite(name, size):
    game_path = ASSETS / f"{name}_game.png"
    if game_path.exists():
        img = pygame.image.load(str(game_path)).convert_alpha()
        if img.get_size() == size:
            return img

    png_path = ASSETS / f"{name}.png"
    if png_path.exists():
        img = pygame.image.load(str(png_path)).convert_alpha()
        return _scale_nearest(img, size)
    svg_path = ASSETS / f"{name}.svg"
    if svg_path.exists():
        from svg_sprite import load_svg_sprite

        return load_svg_sprite(svg_path, size)
    return None


def get_tomato_sprite(facing=1):
    key = f"tomato_{facing}"
    if key not in _cache:
        s = _load_sprite("tomato", TOMATO_SIZE) or _build_tomato()
        if facing < 0:
            s = pygame.transform.flip(s, True, False)
        _cache[key] = s
    return _cache[key]


def get_onion_sprite(facing=1):
    key = f"onion_{facing}"
    if key not in _cache:
        s = _load_sprite("onion", ONION_SIZE) or _build_onion()
        if facing < 0:
            s = pygame.transform.flip(s, True, False)
        _cache[key] = s
    return _cache[key]


def px(surf, x, y, w, h, color):
    pygame.draw.rect(surf, color, (int(x), int(y), int(w), int(h)))


def outline_rect(surf, rect, fill, hi=None, lo=None, border=OUTLINE):
    r = pygame.Rect(rect)
    px(surf, r.x, r.y, r.w, r.h, fill)
    if hi:
        px(surf, r.x + 2, r.y + 2, r.w - 4, 2, hi)
    if lo:
        px(surf, r.x + 2, r.bottom - 4, r.w - 4, 2, lo)
    pygame.draw.rect(surf, border, r, 2)


def pixel_eyes(surf, cx, cy, tall=10, wide=3, gap=4):
    left = cx - gap // 2 - wide
    right = cx + gap // 2
    px(surf, left, cy - tall // 2, wide, tall, OUTLINE)
    px(surf, right, cy - tall // 2, wide, tall, OUTLINE)


def pixel_legs(surf, cx, bottom, leg_h=6, gap=6, wide=3):
    px(surf, cx - gap // 2 - wide, bottom - leg_h, wide, leg_h, OUTLINE)
    px(surf, cx + gap // 2, bottom - leg_h, wide, leg_h, OUTLINE)


def _build_tomato():
    w, h = 21, 23
    s = pygame.Surface((w * BLOCK, h * BLOCK), pygame.SRCALPHA)
    ox, oy = BLOCK, BLOCK
    body = pygame.Rect(ox + 2, oy + 4, 17 * BLOCK, 15 * BLOCK)
    pygame.draw.ellipse(s, RED, body)
    pygame.draw.ellipse(s, OUTLINE, body, BLOCK)
    hi = body.inflate(-body.w // 2, -body.h // 2)
    hi.x += body.w // 3
    hi.y += 2
    pygame.draw.ellipse(s, RED_HI, hi)
    lo = pygame.Rect(body.x + 2, body.bottom - 8, body.w // 2, 6)
    pygame.draw.ellipse(s, RED_LO, lo)
    px(s, body.centerx - BLOCK, body.y - 4, BLOCK * 2, BLOCK * 2, OUTLINE)
    px(s, body.centerx - BLOCK * 2, body.y - 6, BLOCK, BLOCK, (40, 170, 60))
    px(s, body.centerx + BLOCK, body.y - 6, BLOCK, BLOCK, (40, 170, 60))
    pixel_eyes(s, body.centerx, body.centery - 2, tall=8, wide=BLOCK, gap=6)
    pixel_legs(s, body.centerx, body.bottom + 2, leg_h=5, gap=8, wide=BLOCK)
    return _scale_nearest(s, TOMATO_SIZE)


def _build_onion():
    w, h = 13, 26
    s = pygame.Surface((w * BLOCK, h * BLOCK), pygame.SRCALPHA)
    body = pygame.Rect(BLOCK * 2, BLOCK * 4, 9 * BLOCK, 20 * BLOCK)
    for row in range(body.h // BLOCK):
        t = row / max(1, body.h // BLOCK - 1)
        col = (
            int(ONION_TOP[0] + (ONION_BOT[0] - ONION_TOP[0]) * t),
            int(ONION_TOP[1] + (ONION_BOT[1] - ONION_TOP[1]) * t),
            int(ONION_TOP[2] + (ONION_BOT[2] - ONION_TOP[2]) * t),
        )
        px(s, body.x, body.y + row * BLOCK, body.w, BLOCK, col)
    pygame.draw.rect(s, OUTLINE, body, BLOCK)
    for i in (-1, 0, 1):
        px(s, body.centerx + i * BLOCK * 2 - BLOCK // 2, body.y - BLOCK * 3, BLOCK, BLOCK * 3, OUTLINE)
    pixel_eyes(s, body.centerx, body.y + 8, tall=12, wide=BLOCK, gap=4)
    pixel_legs(s, body.centerx, body.bottom + 2, leg_h=5, gap=4, wide=BLOCK)
    return _scale_nearest(s, ONION_SIZE)


def draw_background(surf, cam_x=0):
    surf.fill(BG)
    for y in range(0, HEIGHT, 16):
        shade = BG_TOP if (y // 16) % 2 == 0 else BG
        px(surf, 0, y, WIDTH, 16, shade)
    for i in range(12):
        cx = (i * 137 - cam_x // 3) % (WIDTH + 80) - 40
        cy = 40 + (i * 29) % 120
        px(surf, cx, cy, 24, 8, (40, 36, 52))
        px(surf, cx + 8, cy - 6, 16, 8, (48, 42, 58))


def draw_tile(surf, rect, cam_x, kind="solid"):
    r = rect.move(-cam_x, 0)
    if kind == "fragile":
        outline_rect(surf, r, FRAGILE, FRAGILE, FRAGILE_LO)
        for x in range(r.x + 4, r.right - 4, 8):
            px(surf, x, r.centery, 4, 4, FRAGILE_LO)
    elif kind == "metal":
        outline_rect(surf, r, METAL, METAL_HI, (80, 82, 96))
        for x in range(r.x + 6, r.right - 6, 14):
            px(surf, x, r.y + 4, 4, 4, OUTLINE)
    elif kind == "soft":
        outline_rect(surf, r, (210, 180, 130), (240, 210, 160), (160, 130, 90))
    else:
        outline_rect(surf, r, PLATFORM, PLATFORM_HI, PLATFORM_LO)
        for x in range(r.x + 6, r.right - 6, 12):
            px(surf, x, r.y + 6, 6, 2, PLATFORM_LO)


def draw_goal(surf, rect, cam_x):
    r = rect.move(-cam_x, 0)
    outline_rect(surf, r, GOAL, GOAL_HI, (60, 140, 80))
    px(surf, r.centerx - 2, r.centery - 8, 4, 16, WHITE)
    px(surf, r.x + 6, r.y + 6, 6, 6, GOAL_HI)
    px(surf, r.right - 12, r.y + 6, 6, 6, GOAL_HI)


def draw_button_tile(surf, rect, cam_x, pressed=False):
    r = rect.move(-cam_x, 0)
    col = YELLOW if pressed else METAL
    outline_rect(surf, r, col, WHITE if pressed else METAL_HI, JUNK_LO)
    if pressed:
        px(surf, r.x + 4, r.y + 2, r.w - 8, r.h - 4, (200, 170, 60))


def draw_lever(surf, rect, cam_x, on=False):
    r = rect.move(-cam_x, 0)
    col = GOAL if on else WHITE
    outline_rect(surf, r.inflate(4, 4), METAL, METAL_HI, OUTLINE)
    px(surf, r.x + 4, r.centery - 6, 16, 12, col)


def draw_cage(surf, rect, cam_x):
    r = rect.move(-cam_x, 0)
    outline_rect(surf, r, (70, 72, 88), METAL_HI, OUTLINE)
    for x in range(r.x + 4, r.right - 4, 10):
        px(surf, x, r.y + 2, 3, r.h - 4, OUTLINE)
    for y in range(r.y + 4, r.bottom - 4, 12):
        px(surf, r.x + 2, y, r.w - 4, 3, OUTLINE)


def draw_player(surf, player, cam_x):
    if not player.alive:
        return
    sprite = get_tomato_sprite(player.facing) if player.is_tomato else get_onion_sprite(player.facing)
    r = player.rect.move(-cam_x, 0)
    x = r.centerx - sprite.get_width() // 2
    y = r.bottom - sprite.get_height()
    if player.invuln and (player.invuln // 4) % 2:
        tint = sprite.copy()
        tint.fill((255, 255, 255, 80), special_flags=pygame.BLEND_RGBA_ADD)
        surf.blit(tint, (x, y))
    else:
        surf.blit(sprite, (x, y))
    accessory = getattr(player, "accessory", None)
    if accessory:
        draw_accessory(
            surf,
            accessory,
            x,
            y,
            sprite.get_width(),
            sprite.get_height(),
            player.facing,
            player.is_tomato,
        )
    if player.is_tomato and player.shield_active():
        sr = pygame.Rect(x - 4, y - 4, sprite.get_width() + 8, sprite.get_height() + 8)
        pygame.draw.rect(surf, CYAN, sr, 2)


def draw_accessory(surf, accessory_id, x, y, w, h, facing, is_tomato):
    if accessory_id in ("tomato_hat", "onion_hat"):
        _draw_hat(surf, x, y, w, facing)
    elif accessory_id == "tomato_sword":
        _draw_decor_sword(surf, x, y, w, h, facing)
    elif accessory_id == "onion_bow":
        _draw_decor_bow(surf, x, y, w, h, facing)


def _draw_hat(surf, x, y, w, facing):
    brim_w = max(18, w + 6)
    brim_x = x + w // 2 - brim_w // 2
    brim_y = y + 2
    px(surf, brim_x, brim_y + 6, brim_w, 4, (120, 80, 40))
    px(surf, brim_x + brim_w // 2 - 8, brim_y, 16, 8, (160, 100, 50))
    px(surf, brim_x + brim_w // 2 - 5, brim_y - 6, 10, 8, (180, 50, 50))
    pygame.draw.rect(surf, OUTLINE, pygame.Rect(brim_x, brim_y + 6, brim_w, 4), 1)


def _draw_decor_sword(surf, x, y, w, h, facing):
    side = 1 if facing >= 0 else -1
    sx = x + w - 4 if side > 0 else x - 6
    sy = y + h // 2 - 8
    px(surf, sx, sy, 4, 22, METAL_HI)
    px(surf, sx - 2 * side, sy + 16, 8, 3, (120, 90, 50))
    px(surf, sx + side, sy - 4, 2, 6, YELLOW)


def _draw_decor_bow(surf, x, y, w, h, facing):
    side = -1 if facing >= 0 else 1
    bx = x + 4 if side < 0 else x + w - 10
    by = y + h // 2 - 6
    for i in range(5):
        px(surf, bx + i * side, by + abs(i - 2) * 2, 3, 3, (120, 80, 40))
    px(surf, bx + 2 * side, by + 4, 10, 2, ONION_TOP)


def draw_hero_preview(surf, x, y, is_tomato, facing=1, accessory=None):
    sprite = get_tomato_sprite(facing) if is_tomato else get_onion_sprite(facing)
    surf.blit(sprite, (x, y))
    if accessory:
        draw_accessory(
            surf,
            accessory,
            x,
            y,
            sprite.get_width(),
            sprite.get_height(),
            facing,
            is_tomato,
        )


def draw_arrow(surf, rect, cam_x):
    r = rect.move(-cam_x, 0)
    px(surf, r.x, r.centery - 2, r.w, 4, ONION_TOP)
    px(surf, r.right - 4, r.centery - 6, 4, 12, ONION_TOP)
    pygame.draw.rect(surf, OUTLINE, r.inflate(0, 4), 1)


def draw_burger(surf, rect, cam_x, spike_rect):
    r = rect.move(-cam_x, 0)
    outline_rect(surf, r, JUNK, (220, 180, 100), JUNK_LO)
    px(surf, r.x + 4, r.y + 6, r.w - 8, 4, (160, 100, 50))
    px(surf, r.x + 4, r.y + 14, r.w - 8, 4, (120, 80, 40))
    pixel_eyes(surf, r.centerx, r.centery - 2, tall=6, wide=2, gap=6)
    sr = spike_rect.move(-cam_x, 0)
    pygame.draw.polygon(
        surf,
        YELLOW,
        [(sr.centerx, sr.top), (sr.left, sr.bottom), (sr.right, sr.bottom)],
    )
    pygame.draw.polygon(
        surf,
        OUTLINE,
        [(sr.centerx, sr.top), (sr.left, sr.bottom), (sr.right, sr.bottom)],
        1,
    )


def draw_fries(surf, rect, cam_x):
    r = rect.move(-cam_x, 0)
    outline_rect(surf, r, FRAGILE, FRAGILE, FRAGILE_LO)
    pixel_eyes(surf, r.centerx, r.centery, tall=5, wide=2, gap=5)
    for i in range(3):
        px(surf, r.x + 6 + i * 8, r.y - 8 - (i % 2) * 4, 4, 10, YELLOW)


def draw_cola(surf, rect, cam_x, fuse=-1):
    r = rect.move(-cam_x, 0)
    outline_rect(surf, r, RED, RED_HI, RED_LO)
    px(surf, r.x + 6, r.y + 4, r.w - 12, r.h - 10, (240, 240, 240))
    px(surf, r.x + 8, r.y + 8, r.w - 16, 8, RED)
    pixel_eyes(surf, r.centerx, r.y + 10, tall=5, wide=2, gap=4)
    if fuse > 0:
        pulse = 4 + (fuse % 8)
        pygame.draw.rect(surf, YELLOW, r.inflate(pulse, pulse), 2)


def draw_donut(surf, rect, cam_x, turbo=False):
    r = rect.move(-cam_x, 0)
    col = (255, 160, 200) if not turbo else (255, 100, 160)
    outline_rect(surf, r, col, (255, 200, 220), (180, 80, 120))
    hole = pygame.Rect(r.centerx - 6, r.centery - 6, 12, 12)
    px(surf, hole.x, hole.y, hole.w, hole.h, BG)
    pixel_eyes(surf, r.centerx, r.y + 10, tall=5, wide=2, gap=5)
    if turbo:
        px(surf, r.right - 6, r.centery, 8, 4, (120, 60, 180))


def draw_turret(surf, rect, cam_x):
    r = rect.move(-cam_x, 0)
    outline_rect(surf, r, (240, 238, 220), WHITE, (180, 178, 160))
    pixel_eyes(surf, r.centerx, r.centery - 2, tall=6, wide=2, gap=4)
    px(surf, r.right - 4, r.centery - 2, 10, 4, OUTLINE)


def draw_cola_spill(surf, rect, cam_x):
    r = rect.move(-cam_x, 0)
    cola_dark = (22, 12, 8)
    cola_mid = (38, 22, 14)
    cola_hi = (58, 34, 22)
    px(surf, r.x, r.y + 4, r.w, r.h - 4, cola_dark)
    px(surf, r.x + 2, r.y + 6, r.w - 4, r.h - 10, cola_mid)
    for i in range(0, max(1, r.w // 18)):
        bx = r.x + 8 + i * 18
        px(surf, bx, r.y + 8, 6, 4, cola_hi)
        px(surf, bx + 2, r.y + 6, 3, 2, (72, 44, 28))
    pygame.draw.rect(surf, OUTLINE, r, 1)


def draw_trampoline(surf, rect, cam_x, squish=0):
    r = rect.move(-cam_x, 0)
    squash = min(6, squish)
    pad = r.inflate(0, squash)
    pad.y += squash // 2
    outline_rect(surf, pad, (28, 120, 130), CYAN, (18, 80, 92))
    for x in range(pad.x + 4, pad.right - 4, 8):
        px(surf, x, pad.centery - 2, 4, 4, (120, 230, 240))
    px(surf, pad.x + 6, pad.y + 3, pad.w - 12, 3, YELLOW)
    px(surf, pad.x + 10, pad.bottom - 5, pad.w - 20, 2, (200, 170, 40))
    for side in (pad.x + 2, pad.right - 6):
        px(surf, side, pad.y - 4, 4, pad.h + 6, METAL)


def draw_mayo(surf, rect, cam_x):
    r = rect.move(-cam_x, 0)
    px(surf, r.x, r.y, r.w, r.h, (250, 250, 220))
    pygame.draw.rect(surf, OUTLINE, r, 1)


def draw_fireball(surf, rect, cam_x):
    r = rect.move(-cam_x, 0)
    outline_rect(surf, r, (255, 120, 30), (255, 210, 70), (180, 60, 10))
    px(surf, r.x + 3, r.y + 3, r.w - 6, r.h - 6, (255, 230, 90))


def draw_boss(surf, rect, cam_x, hp, max_hp):
    r = rect.move(-cam_x, 0)
    outline_rect(surf, r, (120, 30, 30), RED, (80, 20, 20))
    px(surf, r.x + 8, r.y + 16, r.w - 16, 8, JUNK)
    px(surf, r.x + 8, r.y + 28, r.w - 16, 8, (160, 100, 50))
    px(surf, r.x + 8, r.y + 40, r.w - 16, 8, JUNK_LO)
    pixel_eyes(surf, r.centerx, r.y + 24, tall=14, wide=3, gap=10)
    bar_w = int(r.w * hp / max_hp)
    px(surf, r.x, r.y - 10, r.w, 6, OUTLINE)
    px(surf, r.x + 1, r.y - 9, max(0, bar_w - 2), 4, RED_HI)


def draw_ui_panel(surf, rect, selected=False, hover=False):
    fill = (70, 100, 70) if selected else ((60, 55, 80) if hover else (45, 40, 58))
    outline_rect(surf, rect, fill, (90, 85, 110) if not selected else GOAL_HI, OUTLINE)


def draw_title_banner(surf, y, title, subtitle=None):
    banner = pygame.Rect(WIDTH // 2 - 220, y - 18, 440, 56 if subtitle else 40)
    outline_rect(surf, banner, (35, 32, 50), (55, 50, 72), OUTLINE)
    t = render_text(title, 28, YELLOW)
    surf.blit(t, t.get_rect(center=(WIDTH // 2, y + 2)))
    if subtitle:
        s = render_text(subtitle, 14, CYAN)
        surf.blit(s, s.get_rect(center=(WIDTH // 2, y + 28)))


def draw_hud_panel(surf, lines, tomato_hp, tomato_max, onion_hp=None, onion_max=None, active_tomato=True):
    panel_h = 8 + len(lines) * 18 + 28
    panel = pygame.Rect(8, 8, min(WIDTH - 16, 520), panel_h)
    outline_rect(surf, panel, (30, 28, 42), (50, 46, 64), OUTLINE)

    y = panel.y + 10
    for i, (text, color, size) in enumerate(lines):
        t = render_text(text, size, color)
        surf.blit(t, (panel.x + 12, y))
        y += t.get_height() + 2

    bar_y = panel.bottom - 22
    draw_hp_bar(surf, panel.x + 12, bar_y, 180, tomato_hp, tomato_max, RED, RED_HI)
    if onion_hp is not None and onion_max is not None:
        draw_hp_bar(surf, panel.x + 210, bar_y, 140, onion_hp, onion_max, ONION_TOP, ONION_BOT)
        tag = render_text("T" if active_tomato else "L", 12, YELLOW)
        surf.blit(tag, (panel.x + 360, bar_y - 2))


def draw_hp_bar(surf, x, y, w, hp, max_hp, col, hi):
    px(surf, x, y, w, 10, OUTLINE)
    fill_w = max(0, int((w - 4) * hp / max_hp))
    px(surf, x + 2, y + 2, fill_w, 6, col)
    if fill_w > 4:
        px(surf, x + 2, y + 2, fill_w - 2, 2, hi)


def draw_menu_bg(surf, equipped=None):
    draw_background(surf, 0)
    eq = equipped or {}
    margin_x = 24
    margin_y = 32
    draw_hero_preview(
        surf,
        margin_x,
        HEIGHT - TOMATO_SIZE[1] - margin_y,
        True,
        1,
        eq.get("tomato"),
    )
    draw_hero_preview(
        surf,
        WIDTH - ONION_SIZE[0] - margin_x,
        HEIGHT - ONION_SIZE[1] - margin_y,
        False,
        -1,
        eq.get("onion"),
    )


def pixel_font(size):
    return pygame.font.SysFont("courier new", size, bold=True)


def render_text(text, size, color=WHITE):
    return pixel_font(size).render(text, True, color)


def draw_text_center(surf, text, y, size=20, color=WHITE):
    t = render_text(text, size, color)
    surf.blit(t, t.get_rect(center=(WIDTH // 2, y)))
