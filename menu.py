import json
from pathlib import Path

import pygame

from constants import *
from levels import LEVEL_INFO
from progress import (
    load_progress,
    load_current_level,
    save_current_level,
    load_coins,
    load_owned,
    load_equipped,
    purchase_item,
    toggle_equip,
    equip_item,
    reset_levels,
)
from shop import SHOP_ITEMS, ITEM_PRICE
import audio
import pixel_art as art
from app_icon import apply_window_icon


from paths import app_dir

SETTINGS_PATH = app_dir() / "settings.json"
REPEAT_DELAY = 400
REPEAT_INTERVAL = 50

DEFAULT_SETTINGS = {
    "music_volume": 70,
    "sfx_volume": 80,
    "show_hints": True,
    "fullscreen": False,
}


def load_settings():
    if SETTINGS_PATH.exists():
        try:
            data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            return {**DEFAULT_SETTINGS, **data}
        except (json.JSONDecodeError, OSError):
            pass
    return DEFAULT_SETTINGS.copy()


def save_settings(settings):
    try:
        SETTINGS_PATH.write_text(
            json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        pass


class Button:
    def __init__(self, rect, label, action):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.action = action

    def draw(self, surf, font, hover=False, selected=False):
        art.draw_ui_panel(surf, self.rect, selected=selected, hover=hover)
        text = art.render_text(self.label, 16, YELLOW if selected else WHITE)
        surf.blit(text, text.get_rect(center=self.rect.center))

    def clicked(self, pos):
        return self.rect.collidepoint(pos)


class Menu:
    def __init__(self):
        pygame.init()
        self.settings = load_settings()
        self.fullscreen = self.settings["fullscreen"]
        self.screen = self._make_screen()
        pygame.display.set_caption("TOMANION — Меню")
        self.clock = pygame.time.Clock()
        self.font = art.pixel_font(16)
        self.title_font = art.pixel_font(28)
        self.small = art.pixel_font(14)
        self.screen_name = "main"
        self.level_scroll = 0
        self.level_selected = 0
        self.setting_index = 0
        self.start_level = 1
        self.result = None
        self.max_unlocked = load_progress()
        self.continue_level = load_current_level()
        self.coins = load_coins()
        self.owned = load_owned()
        self.equipped = load_equipped()
        self.shop_index = 0
        self.shop_message = ""
        self.shop_message_timer = 0
        self.settings_message = ""
        self.settings_message_timer = 0
        self._repeat_state = {}
        audio.configure(
            volume=self.settings["sfx_volume"],
            music_volume=self.settings["music_volume"],
        )

    def _sync_music(self):
        audio.configure(
            volume=self.settings["sfx_volume"],
            music_volume=self.settings["music_volume"],
        )
        if self.screen_name in ("main", "levels", "settings", "shop"):
            audio.play_menu_music()
        else:
            audio.stop_music()

    def _make_screen(self):
        flags = pygame.FULLSCREEN if self.fullscreen else 0
        screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        apply_window_icon()
        return screen

    def _main_buttons(self):
        y = 255
        step = 46
        return [
            Button((WIDTH // 2 - 140, y, 280, 44), ">  Играть", "play"),
            Button((WIDTH // 2 - 140, y + step, 280, 44), "#  Выбор уровня", "levels"),
            Button((WIDTH // 2 - 140, y + step * 2, 280, 44), "$  Магазин", "shop"),
            Button((WIDTH // 2 - 140, y + step * 3, 280, 44), "*  Настройки", "settings"),
            Button((WIDTH // 2 - 140, y + step * 4, 280, 44), "X  Выход", "quit"),
        ]

    def _settings_rows(self):
        s = self.settings
        return [
            ("music_volume", f"Музыка: {s['music_volume']}%", ["music_volume", -10, 10]),
            ("sfx_volume", f"Звуки: {s['sfx_volume']}%", ["sfx_volume", -10, 10]),
            ("show_hints", f"Подсказки: {'вкл' if s['show_hints'] else 'выкл'}", ["show_hints", "toggle"]),
            (
                "fullscreen",
                f"Полный экран: {'да' if s['fullscreen'] else 'нет'}",
                ["fullscreen", "toggle"],
            ),
            (
                "reset_levels",
                f"Сброс уровней (открыто: {self.max_unlocked}/30)",
                ["reset_levels", "action"],
            ),
        ]

    def _continue_level(self):
        return load_current_level()

    def _back_rect(self):
        return pygame.Rect(40, HEIGHT - 60, 160, 40)

    def _repeat(self, key_id, pressed, action):
        if not pressed:
            self._repeat_state.pop(key_id, None)
            return
        now = pygame.time.get_ticks()
        if key_id not in self._repeat_state:
            self._repeat_state[key_id] = {"start": now, "last": now}
            action()
            return
        state = self._repeat_state[key_id]
        delay = REPEAT_DELAY if state["last"] == state["start"] else REPEAT_INTERVAL
        if now - state["last"] >= delay:
            action()
            state["last"] = now

    def _process_held_keys(self):
        keys = pygame.key.get_pressed()
        if self.screen_name == "levels":
            self._repeat("level_up", keys[pygame.K_UP] or keys[pygame.K_w], self._level_up)
            self._repeat(
                "level_down", keys[pygame.K_DOWN] or keys[pygame.K_s], self._level_down
            )
        elif self.screen_name == "settings":
            rows = self._settings_rows()
            self._repeat(
                "setting_up",
                keys[pygame.K_UP] or keys[pygame.K_w],
                lambda: self._move_setting_index(-1, len(rows)),
            )
            self._repeat(
                "setting_down",
                keys[pygame.K_DOWN] or keys[pygame.K_s],
                lambda: self._move_setting_index(1, len(rows)),
            )
            action = rows[self.setting_index][2]
            if action[1] != "action":
                self._repeat(
                    "setting_left",
                    keys[pygame.K_LEFT] or keys[pygame.K_a],
                    lambda: self._adjust_setting(action, -1),
                )
                self._repeat(
                    "setting_right",
                    keys[pygame.K_RIGHT] or keys[pygame.K_d],
                    lambda: self._adjust_setting(action, 1),
                )
        elif self.screen_name == "shop":
            self._repeat(
                "shop_up",
                keys[pygame.K_UP] or keys[pygame.K_w],
                lambda: self._move_shop_index(-1),
            )
            self._repeat(
                "shop_down",
                keys[pygame.K_DOWN] or keys[pygame.K_s],
                lambda: self._move_shop_index(1),
            )

    def _level_up(self):
        self.level_selected = max(0, self.level_selected - 1)
        self._sync_level_scroll()

    def _level_down(self):
        self.level_selected = min(LEVELS_TOTAL - 1, self.level_selected + 1)
        self._sync_level_scroll()

    def _move_setting_index(self, direction, count):
        self.setting_index = (self.setting_index + direction) % count

    def _move_shop_index(self, direction):
        self.shop_index = (self.shop_index + direction) % len(SHOP_ITEMS)

    def _refresh_shop_state(self):
        self.coins = load_coins()
        self.owned = load_owned()
        self.equipped = load_equipped()

    def _shop_action(self):
        item = SHOP_ITEMS[self.shop_index]
        if item["id"] not in self.owned:
            result = purchase_item(item["id"], ITEM_PRICE)
            if result == "ok":
                equip_item(item["hero"], item["id"])
                self.shop_message = "Купил!"
            elif result == "nomoney":
                self.shop_message = f"Мало монет, надо {ITEM_PRICE}"
            else:
                self.shop_message = "Уже куплено"
        else:
            was_equipped = self.equipped.get(item["hero"]) == item["id"]
            toggle_equip(item["id"], item["hero"])
            self.shop_message = "Снято" if was_equipped else "Надето!"
        self.shop_message_timer = 120
        self._refresh_shop_state()

    def _reset_levels_action(self):
        reset_levels()
        self.max_unlocked = 1
        self.continue_level = 1
        self.settings_message = "Сбросила уровни — снова только 1-й"
        self.settings_message_timer = 150

    def run(self):
        while self.result is None:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.result = None
                    pygame.quit()
                    return None
                if event.type == pygame.KEYDOWN:
                    if not self._handle_key(event.key):
                        return self.result
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if not self._handle_click(event.pos):
                        return self.result

            self._process_held_keys()
            self._draw()
            self.clock.tick(FPS)

        audio.stop_music()
        pygame.display.set_caption("TOMANION — Апокалипсис Вредной Еды")
        return self.result

    def _handle_key(self, key):
        if key == pygame.K_ESCAPE:
            if self.screen_name == "main":
                self.result = None
                pygame.quit()
                return False
            self.screen_name = "main"
            return True

        if self.screen_name == "main" and key == pygame.K_RETURN:
            self._start_game(self._continue_level())
            return False

        if self.screen_name == "levels":
            if key == pygame.K_RETURN:
                if self.level_selected + 1 <= self.max_unlocked:
                    self._start_game(self.level_selected + 1)
                    return False

        if self.screen_name == "settings":
            rows = self._settings_rows()
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                action = rows[self.setting_index][2]
                if action[1] == "action":
                    self._reset_levels_action()
                else:
                    self._adjust_setting(action, 1)
            elif key == pygame.K_b:
                save_settings(self.settings)
                self.screen_name = "main"

        if self.screen_name == "shop":
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self._shop_action()

        return True

    def _handle_click(self, pos):
        if self.screen_name == "main":
            for btn in self._main_buttons():
                if btn.clicked(pos):
                    if btn.action == "play":
                        self._start_game(self._continue_level())
                        return False
                    if btn.action == "levels":
                        self.max_unlocked = load_progress()
                        self.screen_name = "levels"
                        self.level_selected = 0
                        self.level_scroll = 0
                    elif btn.action == "settings":
                        self.screen_name = "settings"
                        self.setting_index = 0
                    elif btn.action == "shop":
                        self.screen_name = "shop"
                        self.shop_index = 0
                        self.shop_message = ""
                        self._refresh_shop_state()
                    elif btn.action == "quit":
                        self.result = None
                        pygame.quit()
                        return False
                    return True

        if self.screen_name == "levels":
            list_top = 150
            for i in range(min(8, LEVELS_TOTAL - self.level_scroll)):
                idx = self.level_scroll + i
                row = pygame.Rect(120, list_top + i * 42, WIDTH - 240, 36)
                if row.collidepoint(pos):
                    self.level_selected = idx
                    if idx + 1 <= self.max_unlocked:
                        self._start_game(idx + 1)
                        return False
                    return True
            back = self._back_rect()
            if back.collidepoint(pos):
                self.screen_name = "main"
            return True

        if self.screen_name == "settings":
            rows = self._settings_rows()
            for i, (_, _, action) in enumerate(rows):
                row = pygame.Rect(120, 160 + i * 52, WIDTH - 240, 44)
                if row.collidepoint(pos):
                    self.setting_index = i
                    self._adjust_setting(action, 1)
                    return True
            back = self._back_rect()
            if back.collidepoint(pos):
                save_settings(self.settings)
                self.screen_name = "main"
            return True

        if self.screen_name == "shop":
            list_top = 118
            for i, item in enumerate(SHOP_ITEMS):
                row = pygame.Rect(80, list_top + i * 78, WIDTH - 160, 68)
                if row.collidepoint(pos):
                    self.shop_index = i
                    self._shop_action()
                    return True
            back = self._back_rect()
            if back.collidepoint(pos):
                self.screen_name = "main"
            return True

        return True

    def _adjust_setting(self, action, direction):
        key = action[0]
        mode = action[1]
        if mode == "action":
            if key == "reset_levels":
                self._reset_levels_action()
            return
        if mode == "toggle":
            self.settings[key] = not self.settings[key]
            if key == "fullscreen":
                self.fullscreen = self.settings["fullscreen"]
                self.screen = self._make_screen()
        else:
            step = action[1 if direction < 0 else 2]
            self.settings[key] = max(0, min(100, self.settings[key] + step))
        save_settings(self.settings)

    def _sync_level_scroll(self):
        visible = 8
        if self.level_selected < self.level_scroll:
            self.level_scroll = self.level_selected
        elif self.level_selected >= self.level_scroll + visible:
            self.level_scroll = self.level_selected - visible + 1

    def _start_game(self, level):
        audio.stop_music()
        save_current_level(level)
        save_settings(self.settings)
        self.result = (self.settings.copy(), level)

    def _draw(self):
        self._sync_music()
        if self.screen_name == "main":
            art.draw_menu_bg(self.screen, self.equipped)
            self._draw_main()
        else:
            art.draw_background(self.screen, 0)
            if self.screen_name == "levels":
                self._draw_levels()
            elif self.screen_name == "settings":
                self._draw_settings()
            elif self.screen_name == "shop":
                self._draw_shop()
        pygame.display.flip()

    def _draw_main(self):
        art.draw_title_banner(self.screen, 62, "TOMANION", "Апокалипсис Вредной Еды")

        coin_s = art.render_text(f"Монеты: {self.coins}", 15, YELLOW)
        self.screen.blit(coin_s, (WIDTH - coin_s.get_width() - 20, 18))

        story = [
            "Фастфуд захватил Свежgrad и увёл Лука.",
            "Помоги Томату освободить друзей",
            "и добраться до Суперзлодея — Вредной Еды.",
        ]
        y = 150
        for line in story:
            surf = art.render_text(line, 14, WHITE)
            self.screen.blit(surf, surf.get_rect(center=(WIDTH // 2, y)))
            y += 22

        mx, my = pygame.mouse.get_pos()
        for btn in self._main_buttons():
            btn.draw(self.screen, self.font, btn.rect.collidepoint(mx, my))

        hint = art.render_text(
            f"Enter — продолжить (ур. {self.continue_level}) | Esc — выход",
            14,
            (160, 160, 170),
        )
        self.screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT - 24)))

    def _draw_levels(self):
        art.draw_title_banner(self.screen, 38, "ВЫБОР УРОВНЯ")

        sections = [
            (1, 5, "Часть 1 — Томат один"),
            (6, 29, "Часть 2 — Вместе с Луком"),
            (30, 30, "Финал"),
        ]

        list_top = 150
        visible = 8
        for i in range(visible):
            idx = self.level_scroll + i
            if idx >= LEVELS_TOTAL:
                break
            info = LEVEL_INFO[idx]
            row = pygame.Rect(120, list_top + i * 42, WIDTH - 240, 36)
            selected = idx == self.level_selected
            hover = row.collidepoint(pygame.mouse.get_pos())
            art.draw_ui_panel(self.screen, row, selected=selected, hover=hover)
            label = f"{info['num']:>2}. {info['title']}"
            if info.get("boss"):
                label += "  BOSS"
            locked = info["num"] > self.max_unlocked
            if locked:
                label += "  [закрыт]"
            text = art.render_text(label, 16, (120, 120, 130) if locked else WHITE)
            self.screen.blit(text, (row.x + 12, row.y + 8))

        for start, end, name in sections:
            if start - 1 <= self.level_selected <= end - 1:
                sec = art.render_text(name, 14, CYAN)
                self.screen.blit(sec, (120, 118))

        nav = art.render_text(
            "↑↓ — выбор (удерживай) | Enter — играть | Esc — назад",
            14,
            (160, 160, 170),
        )
        self.screen.blit(nav, (120, HEIGHT - 50))

        mx, my = pygame.mouse.get_pos()
        back = self._back_rect()
        art.draw_ui_panel(self.screen, back, hover=back.collidepoint(mx, my))
        bt = art.render_text("< Назад", 16, WHITE)
        self.screen.blit(bt, bt.get_rect(center=back.center))

    def _draw_settings(self):
        if self.settings_message_timer > 0:
            self.settings_message_timer -= 1
        art.draw_title_banner(self.screen, 38, "НАСТРОЙКИ")

        rows = self._settings_rows()
        mx, my = pygame.mouse.get_pos()
        for i, (_, label, action) in enumerate(rows):
            row = pygame.Rect(120, 160 + i * 52, WIDTH - 240, 44)
            selected = i == self.setting_index
            hover = row.collidepoint(mx, my)
            art.draw_ui_panel(self.screen, row, selected=selected, hover=hover)
            color = RED if action[1] == "action" else WHITE
            text = art.render_text(label, 16, color)
            self.screen.blit(text, (row.x + 16, row.y + 12))

        tips = [
            "← → — изменить громкость и переключатели",
            "Enter — сбросить уровни (монеты и магазин сохранятся)",
        ]
        y = 430
        for line in tips:
            surf = art.render_text(line, 14, (150, 150, 160))
            self.screen.blit(surf, (120, y))
            y += 20

        if self.settings_message:
            msg = art.render_text(self.settings_message, 16, YELLOW)
            self.screen.blit(msg, msg.get_rect(center=(WIDTH // 2, HEIGHT - 78)))

        back = self._back_rect()
        art.draw_ui_panel(self.screen, back, hover=back.collidepoint(mx, my))
        bt = art.render_text("< Назад", 16, WHITE)
        self.screen.blit(bt, bt.get_rect(center=back.center))

    def _draw_shop(self):
        if self.shop_message_timer > 0:
            self.shop_message_timer -= 1
        art.draw_title_banner(self.screen, 38, "МАГАЗИН", "Аксессуары для героев")

        coin_s = art.render_text(f"Монеты: {self.coins}", 18, YELLOW)
        self.screen.blit(coin_s, (WIDTH - coin_s.get_width() - 40, 52))

        mx, my = pygame.mouse.get_pos()
        list_top = 118
        for i, item in enumerate(SHOP_ITEMS):
            row = pygame.Rect(80, list_top + i * 78, WIDTH - 160, 68)
            selected = i == self.shop_index
            hover = row.collidepoint(mx, my)
            art.draw_ui_panel(self.screen, row, selected=selected, hover=hover)

            is_tomato = item["hero"] == "tomato"
            facing = 1 if is_tomato else -1
            preview_y = row.y + row.h - (art.TOMATO_SIZE[1] if is_tomato else art.ONION_SIZE[1]) - 8
            art.draw_hero_preview(self.screen, row.x + 14, preview_y, is_tomato, facing, item["id"])

            hero_name = "Томат" if is_tomato else "Лук"
            title = art.render_text(f"{hero_name} — {item['name']}", 16, WHITE)
            self.screen.blit(title, (row.x + 72, row.y + 10))

            desc = art.render_text(item["desc"], 13, (170, 170, 180))
            self.screen.blit(desc, (row.x + 72, row.y + 30))

            owned = item["id"] in self.owned
            equipped = self.equipped.get(item["hero"]) == item["id"]
            if not owned:
                action = f"Купить — {ITEM_PRICE} монет"
                color = YELLOW if self.coins >= ITEM_PRICE else (140, 110, 90)
            elif equipped:
                action = "Надето (Enter — снять)"
                color = GOAL_HI
            else:
                action = "Куплено (Enter — надеть)"
                color = CYAN
            action_s = art.render_text(action, 14, color)
            self.screen.blit(action_s, (row.x + 72, row.y + 48))

        if self.shop_message:
            msg = art.render_text(self.shop_message, 16, YELLOW)
            self.screen.blit(msg, msg.get_rect(center=(WIDTH // 2, HEIGHT - 78)))

        nav = art.render_text(
            "↑↓ — выбор | Enter — купить / надеть | Esc — назад",
            14,
            (160, 160, 170),
        )
        self.screen.blit(nav, nav.get_rect(center=(WIDTH // 2, HEIGHT - 24)))

        back = self._back_rect()
        art.draw_ui_panel(self.screen, back, hover=back.collidepoint(mx, my))
        bt = art.render_text("< Назад", 16, WHITE)
        self.screen.blit(bt, bt.get_rect(center=back.center))


def run_menu():
    menu = Menu()
    return menu.run()
