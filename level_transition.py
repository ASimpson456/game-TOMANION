import math

import pygame

from constants import FPS, HEIGHT, WIDTH, YELLOW
import pixel_art as art

CELL = 16
CLOSE_FRAMES = 48
OPEN_FRAMES = 48
POST_EXIT_FRAMES = FPS
JUMP_FRAMES = 14
ASCEND_SPEED = 4.8
FLIP_FRAMES = 8


class LevelTransition:
    def __init__(self, tomato_start, onion_start=None, show_onion=True):
        self.frame = 0
        self.show_onion = show_onion
        self.tomato_start = tomato_start
        self.onion_start = onion_start
        self.cols = (WIDTH + CELL - 1) // CELL
        self.rows = (HEIGHT + CELL - 1) // CELL
        self._close_at = self._build_wave(CLOSE_FRAMES, reverse=False)
        self._open_at = self._build_wave(OPEN_FRAMES, reverse=True)
        self._exit_frame = None
        self._open_start = None

    @property
    def done(self):
        if self._open_start is None:
            return False
        return self.frame >= self._open_start + OPEN_FRAMES

    @property
    def load_level_frame(self):
        return self._open_start if self._open_start is not None else 10**9

    @property
    def opening_started(self):
        return self._open_start is not None

    def _build_wave(self, span, reverse=False):
        sources = (
            (0, 0),
            (WIDTH, 0),
            (0, HEIGHT),
            (WIDTH, HEIGHT),
            (WIDTH // 2, 0),
            (WIDTH // 2, HEIGHT),
            (0, HEIGHT // 2),
            (WIDTH, HEIGHT // 2),
        )
        delays = []
        max_d = 1.0
        for row in range(self.rows):
            for col in range(self.cols):
                cx = col * CELL + CELL // 2
                cy = row * CELL + CELL // 2
                d = min(math.hypot(cx - sx, cy - sy) for sx, sy in sources)
                max_d = max(max_d, d)
                delays.append(d)
        if reverse:
            return [int((max_d - d) / max_d * span) for d in delays]
        return [int(d / max_d * span) for d in delays]

    def _hero_positions(self):
        tx0, ty0 = self.tomato_start
        t = self.frame
        if t <= 0:
            return (tx0, ty0), self._onion_pos_for_tomato_y(ty0)

        if t < JUMP_FRAMES:
            p = t / JUMP_FRAMES
            hop = int(26 * 4 * p * (1 - p))
            ty = ty0 - hop
        else:
            ty = ty0 - 26 - int((t - JUMP_FRAMES) * ASCEND_SPEED)
        return (tx0, ty), self._onion_pos_for_tomato_y(ty0, ty)

    def _onion_pos_for_tomato_y(self, ty0, ty=None):
        if not self.show_onion or not self.onion_start:
            return (0, 0)
        ox0, oy0 = self.onion_start
        dy = (ty if ty is not None else ty0) - ty0
        return (ox0, oy0 + dy)

    def _tomato_off_screen(self):
        if self.frame <= 0:
            return False
        _, ty = self._hero_positions()[0]
        h = art.get_tomato_sprite(1).get_height()
        return ty + h < 0

    def update(self):
        self.frame += 1
        if self._exit_frame is None and self._tomato_off_screen():
            self._exit_frame = self.frame
        if self._exit_frame and self._open_start is None:
            if self.frame >= self._exit_frame + POST_EXIT_FRAMES:
                self._open_start = self.frame
        return self.done

    def _draw_rocket_exhaust(self, surf, nozzle_x, nozzle_y, frame):
        launch = frame
        thrust = 1.0
        if launch >= JUMP_FRAMES:
            thrust = 1.0 + min(1.8, (launch - JUMP_FRAMES) * 0.05)
        flicker = (frame * 3) % 7

        core_h = int(10 + thrust * 6)
        art.px(surf, nozzle_x - 4, nozzle_y, 8, core_h, (255, 250, 210))
        art.px(surf, nozzle_x - 3, nozzle_y + 2, 6, core_h - 2, (255, 230, 90))

        plume_len = int(36 + thrust * 72 + flicker * 2)
        bands = (
            (255, 210, 70),
            (255, 150, 40),
            (240, 90, 28),
            (190, 50, 22),
            (120, 28, 16),
            (70, 18, 12),
        )
        band_count = len(bands)
        row_count = plume_len // 3
        for row in range(row_count):
            y = nozzle_y + core_h + row * 3
            if y > HEIGHT - 8:
                break
            t = row / max(1, row_count)
            wobble = (frame + row * 3) % 5 - 2
            half_w = int(5 + t * 34) + wobble
            x = nozzle_x - half_w
            w = max(4, half_w * 2)
            h = 3 + (row & 1)
            col = bands[min(band_count - 1, int(t * band_count))]
            art.px(surf, x, y, w, h, col)

        for i in range(5):
            sy = nozzle_y + core_h + plume_len - 8 + i * 7 + (flicker % 3)
            if sy > HEIGHT - 6:
                continue
            sw = 10 + i * 5 + (frame + i) % 4
            art.px(surf, nozzle_x - sw // 2 + (i & 1) * 3, sy, sw, 4, (45, 28, 24))
            art.px(surf, nozzle_x - sw // 3, sy + 3, max(4, sw - 6), 3, (28, 18, 16))

    def _draw_heroes(self, surf):
        (tx, ty), (ox, oy) = self._hero_positions()
        nozzle_x = tx + art.TOMATO_SIZE[0] // 2
        if self.show_onion and self.onion_start:
            nozzle_x = (tx + art.TOMATO_SIZE[0] // 2 + ox + art.ONION_SIZE[0] // 2) // 2
        if self.show_onion and self.onion_start:
            nozzle_y = max(ty + art.TOMATO_SIZE[1], oy + art.ONION_SIZE[1]) - 6
        else:
            nozzle_y = ty + art.TOMATO_SIZE[1] - 6
        self._draw_rocket_exhaust(surf, nozzle_x, nozzle_y, self.frame)

        tomato = art.get_tomato_sprite(1)
        surf.blit(tomato, (tx, ty))
        if self.show_onion and self.onion_start:
            onion = art.get_onion_sprite(1)
            surf.blit(onion, (ox, oy))

    def _draw_grid(self, surf):
        open_start = self._open_start
        for row in range(self.rows):
            y = row * CELL
            for col in range(self.cols):
                idx = row * self.cols + col
                if self.frame < self._close_at[idx]:
                    continue

                scale = 1.0
                if open_start is not None:
                    elapsed = self.frame - open_start
                    if elapsed >= self._open_at[idx]:
                        scale = max(0.0, 1.0 - (elapsed - self._open_at[idx]) / FLIP_FRAMES)
                        if scale <= 0.02:
                            continue

                x = col * CELL
                h = max(2, int(CELL * scale))
                yy = y + (CELL - h) // 2
                art.px(surf, x, yy, CELL, h, (8, 8, 10))
                if scale > 0.55:
                    art.px(surf, x + 2, yy + 2, CELL - 4, max(2, h - 4), (16, 16, 18))

    def draw(self, surf, game=None):
        launch_phase = self._open_start is None
        opening = self._open_start is not None

        if opening and game is not None:
            game._draw_world()
            game._draw_hud()
        elif self.frame < CLOSE_FRAMES:
            if game is not None:
                game._draw_world(hide_players=True)
                game._draw_hud()
        else:
            surf.fill((8, 8, 10))

        self._draw_grid(surf)

        if launch_phase and not self._tomato_off_screen():
            self._draw_heroes(surf)

        if self.frame < CLOSE_FRAMES + 20:
            title = art.render_text("Уровень пройден!", 18, YELLOW)
            surf.blit(title, title.get_rect(center=(WIDTH // 2, 42)))
