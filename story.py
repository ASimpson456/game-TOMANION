"""Вступительная и финальная история TOMANION."""

import math

import pygame

from constants import FPS, HEIGHT, WIDTH, CYAN, GOAL, GOAL_HI, JUNK, ONION_TOP, RED, WHITE, YELLOW
import audio
import pixel_art as art
from app_icon import apply_window_icon

SLIDE_HOLD = 150
CHAR_DELAY = 2

INTRO_SLIDES = [
    {
        "title": "Город Свежgrad",
        "lines": [
            "Давным-давно в городе Свежgrad",
            "овощи и фрукты жили дружно.",
        ],
        "scene": "peace",
    },
    {
        "title": "Откуда взялся фастфуд",
        "lines": [
            "Но за горой построили заводы Вредной Еды.",
            "Там жарили бургеры сутками и варили липкую колу.",
            "Однажды с горизонта поднялось чёрное жирное облако.",
            "Бургеры, картошка фри и майонезные шипы захватили улицы.",
            "Они похитили Лука — и многих других жителей города:",
            "морковок, огурцов, яблок... кто не успел спрятаться.",
        ],
        "scene": "invasion",
    },
    {
        "title": "Последняя надежда",
        "lines": [
            "Не сдался только храбрый Томат.",
            "Он поклялся освободить Лука и всех похищенных,",
            "вернуть свежесть в родной город.",
            "Так началась его битва с фастфудом...",
        ],
        "scene": "heroes",
    },
]

OUTRO_SLIDES = [
    {
        "title": "Победа!",
        "lines": [
            "Томат и Лук одолели главу Вредной Еды!",
            "Последний бургер рухнул, майонезная буря стихла.",
            "Фастфуд больше не правит улицами Свежgrad.",
        ],
        "scene": "victory",
    },
    {
        "title": "Возвращение",
        "lines": [
            "Жирный туман рассеялся над городом.",
            "Лук и все похищенные жители вернулись домой:",
            "морковки, огурцы, яблоки, вишни, брокколи...",
            "Овощи и фрукты снова живут на своих местах!",
        ],
        "scene": "return",
    },
    {
        "title": "Свежgrad снова дома",
        "lines": [
            "Город зеленеет и пахнет свежестью.",
            "Жители благодарят героев — Томат и Лук спасли всех.",
            "Праздник длится до заката... но кто знает,",
            "может, жирное зло вернётся когда-нибудь.",
        ],
        "scene": "celebration",
    },
]


class StoryPlayer:
    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()

    def play(self, slides, allow_skip=True):
        for slide in slides:
            if not self._play_slide(slide, allow_skip):
                return False
        return True

    def _play_slide(self, slide, allow_skip):
        title = slide["title"]
        lines = slide["lines"]
        scene = slide.get("scene", "peace")
        full_text = "\n".join(lines)
        frame = 0
        done_typing = False

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE and allow_skip:
                        return True
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if done_typing:
                            return True
                        frame = len(full_text) * CHAR_DELAY + SLIDE_HOLD

            frame += 1
            chars = min(len(full_text), frame // CHAR_DELAY)
            done_typing = chars >= len(full_text)
            if done_typing and frame >= len(full_text) * CHAR_DELAY + SLIDE_HOLD:
                return True

            self._draw(slide, title, lines, chars, frame, scene)
            pygame.display.flip()
            self.clock.tick(FPS)

    def _draw(self, slide, title, lines, chars, frame, scene):
        art.draw_background(self.screen, frame * 2)
        self._draw_scene(scene, frame)

        panel = pygame.Rect(40, 70, WIDTH - 80, HEIGHT - 150)
        art.draw_ui_panel(self.screen, panel, selected=True)

        title_s = art.render_text(title, 20, YELLOW)
        self.screen.blit(title_s, title_s.get_rect(midtop=(WIDTH // 2, panel.y + 14)))

        full_text = "\n".join(lines)
        shown = full_text[:chars]
        y = panel.y + 52
        for line in shown.split("\n"):
            surf = art.render_text(line, 15, WHITE)
            self.screen.blit(surf, (panel.x + 20, y))
            y += surf.get_height() + 8

        hint = art.render_text("Enter — дальше | Esc — пропустить", 13, (150, 150, 165))
        self.screen.blit(hint, hint.get_rect(midbottom=(WIDTH // 2, HEIGHT - 18)))

    def _draw_scene(self, scene, frame):
        bob = int(math.sin(frame * 0.08) * 6)
        tomato = art.get_tomato_sprite(1)
        onion = art.get_onion_sprite(-1)

        if scene == "peace":
            self.screen.blit(tomato, (120, HEIGHT - 140 + bob))
            self.screen.blit(onion, (200, HEIGHT - 148 - bob))
            for i, col in enumerate((GOAL, GOAL_HI, ONION_TOP, (255, 200, 80))):
                x = 340 + i * 90 + int(math.sin(frame * 0.05 + i) * 4)
                art.px(self.screen, x, HEIGHT - 90, 22, 28, col)

        elif scene == "invasion":
            # Заводы на горизонте и жирное облако
            art.px(self.screen, WIDTH - 220, HEIGHT - 200, 80, 70, (60, 55, 50))
            art.px(self.screen, WIDTH - 200, HEIGHT - 230, 40, 30, (45, 42, 38))
            for i in range(4):
                sx = WIDTH - 180 + i * 22 + int(math.sin(frame * 0.04 + i) * 8)
                sy = HEIGHT - 250 - int(frame * 0.3 + i * 15) % 80
                art.px(self.screen, sx, sy, 28, 20, (40, 35, 30))
            self.screen.blit(tomato, (90, HEIGHT - 130 + bob))
            self.screen.blit(onion, (170, HEIGHT - 138 - bob))
            for i in range(5):
                x = 320 + i * 110 + int(math.sin(frame * 0.06 + i * 1.7) * 12)
                y = HEIGHT - 120 + int(math.cos(frame * 0.07 + i) * 8)
                art.px(self.screen, x, y, 34, 30, JUNK)
                art.px(self.screen, x + 8, y - 10, 18, 12, RED)

        elif scene == "heroes":
            cx = WIDTH // 2
            self.screen.blit(tomato, (cx - 80, HEIGHT - 150 + bob))
            self.screen.blit(onion, (cx + 10, HEIGHT - 158 - bob))
            spark = art.render_text("VS", 22, RED)
            self.screen.blit(spark, spark.get_rect(center=(cx, HEIGHT - 200)))

        elif scene == "victory":
            cx = WIDTH // 2
            self.screen.blit(tomato, (cx - 90, HEIGHT - 145 + bob))
            self.screen.blit(onion, (cx + 20, HEIGHT - 153 - bob))
            for i in range(6):
                t = max(0, frame - i * 8)
                art.px(
                    self.screen,
                    80 + i * 130,
                    HEIGHT - 100 - int(math.sin(t * 0.1) * 10),
                    16,
                    16,
                    (180, 60, 40),
                )

        elif scene == "return":
            self.screen.blit(tomato, (100, HEIGHT - 140 + bob))
            self.screen.blit(onion, (180, HEIGHT - 148 - bob))
            cols = (
                (255, 140, 50),
                GOAL,
                GOAL_HI,
                ONION_TOP,
                (255, 220, 80),
                (200, 100, 180),
            )
            for i, col in enumerate(cols):
                if frame < i * 12:
                    continue
                x = 280 + (i % 3) * 100
                y = HEIGHT - 130 - (i // 3) * 55 + int(math.sin(frame * 0.06 + i) * 5)
                art.px(self.screen, x, y, 24, 30, col)

        elif scene == "celebration":
            cx = WIDTH // 2
            self.screen.blit(tomato, (cx - 70, HEIGHT - 140 + bob))
            self.screen.blit(onion, (cx + 10, HEIGHT - 148 - bob))
            for i in range(8):
                ang = frame * 0.04 + i * math.pi / 4
                x = cx + int(math.cos(ang) * 120)
                y = HEIGHT - 210 + int(math.sin(ang) * 40)
                art.px(self.screen, x, y, 10, 10, YELLOW if i % 2 else GOAL_HI)


def _make_screen(settings):
    flags = pygame.FULLSCREEN if settings.get("fullscreen") else 0
    return pygame.display.set_mode((WIDTH, HEIGHT), flags)


def run_intro(settings):
    pygame.init()
    screen = _make_screen(settings)
    apply_window_icon()
    pygame.display.set_caption("TOMANION — История")
    audio.configure(
        volume=settings.get("sfx_volume", 80),
        music_volume=settings.get("music_volume", 70),
    )
    audio.play_menu_music()
    return StoryPlayer(screen).play(INTRO_SLIDES)


def run_outro(settings):
    screen = _make_screen(settings)
    apply_window_icon()
    pygame.display.set_caption("TOMANION — Финал")
    audio.play_level_complete_music(audio.GAME_COMPLETE_MUSIC)
    return StoryPlayer(screen).play(OUTRO_SLIDES)
