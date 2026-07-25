import pygame

from constants import *
from entities import BurgerSpike, ExplosiveCola, Player, keep_enemy_off_cola, separate_enemies
from levels import build_level
from level_transition import LevelTransition
from progress import unlock_level, save_current_level, load_coins, save_coins, load_equipped
import audio
import pixel_art as art
from app_icon import apply_window_icon

DIFFICULTY = {
    "easy": {"enemy_hp": 0.7, "boss_hp": 0.75, "player_damage": 0.5},
    "normal": {"enemy_hp": 1.0, "boss_hp": 1.0, "player_damage": 1.0},
    "hard": {"enemy_hp": 1.5, "boss_hp": 1.35, "player_damage": 1.5},
}
TRANSITION_DELAY = 90
COINS_PER_KILL = 100


class VolumeSlider:
    TRACK_H = 14
    KNOB_W = 18

    def __init__(self, y, label, key):
        self.label = label
        self.key = key
        self.track = pygame.Rect(WIDTH // 2 - 160, y, 320, self.TRACK_H)

    def knob_rect(self, value):
        x = self.track.x + int((self.track.w - self.KNOB_W) * value / 100)
        return pygame.Rect(x, self.track.y - 2, self.KNOB_W, self.track.h + 4)

    def value_at(self, x):
        rel = max(0, min(self.track.w, x - self.track.x))
        return max(0, min(100, int(rel / self.track.w * 100)))

    def hit_test(self, pos, value):
        return self.track.collidepoint(pos) or self.knob_rect(value).collidepoint(pos)

    def draw(self, surf, value):
        label_s = art.render_text(f"{self.label}: {value}%", 16, WHITE)
        surf.blit(label_s, (self.track.x, self.track.y - 24))
        pygame.draw.rect(surf, (35, 32, 48), self.track)
        pygame.draw.rect(surf, OUTLINE, self.track, 2)
        fill_w = int(self.track.w * value / 100)
        if fill_w:
            pygame.draw.rect(surf, GOAL, (self.track.x, self.track.y, fill_w, self.track.h))
        art.draw_ui_panel(surf, self.knob_rect(value), selected=True)


class Game:
    def __init__(self, settings=None, start_level=1):
        self.settings = settings or {}
        self.diff = DIFFICULTY.get(self.settings.get("difficulty", "normal"), DIFFICULTY["normal"])
        self.show_hints = self.settings.get("show_hints", True)
        pygame.init()
        flags = pygame.FULLSCREEN if self.settings.get("fullscreen") else 0
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        apply_window_icon()
        pygame.display.set_caption("TOMANION — Апокалипсис Вредной Еды")
        self.clock = pygame.time.Clock()
        self.font = art.pixel_font(16)
        self.big = art.pixel_font(22)
        self.level_num = start_level or 1
        self.state = "play"
        self.paused = False
        self.message_timer = 0
        self.transition_timer = 0
        self.active_is_tomato = True
        self.level_transition = None
        self._transition_loaded = False
        self.level_attempts = 1
        self.coins = load_coins()
        self.equipped = load_equipped()
        self.pause_sliders = [
            VolumeSlider(HEIGHT // 2 - 20, "Музыка", "music_volume"),
            VolumeSlider(HEIGHT // 2 + 40, "Звуки", "sfx_volume"),
        ]
        self._dragging_slider = None
        self.load_level(self.level_num)
        audio.configure(
            volume=self.settings.get("sfx_volume", 80),
            music_volume=self.settings.get("music_volume", 70),
        )
        audio.play_gameplay_music()

    def load_level(self, n, reset_attempts=True):
        if reset_attempts:
            self.level_attempts = 1
        data = build_level(n)
        self.data = data
        self.solids = data["solids"]
        self.fragile = data["fragile"]
        self.soft = data["soft"]
        self.buttons = data["buttons"]
        self.levers = data["levers"]
        self.doors = data["doors"]
        self.turrets = data["turrets"]
        self.enemies = data["enemies"]
        self.hazards = data.get("hazards", [])
        self.trampolines = data.get("trampolines", [])
        self.boss = data["boss"]
        self.goal = data["goal"]
        self.tomato = data["tomato"]
        self.onion = data["onion"]
        self.coop = data["coop"]
        self.onion_caged = data["onion_caged"]
        self.cage = data["cage"]
        self.press = data["press"]
        self.vent_block = data["vent_block"]
        self.projectiles = []
        self.blobs = []
        self.fireballs = []
        self.cam_x = 0
        self.active_is_tomato = True
        self.message_timer = 180
        self.transition_timer = 0
        self.paused = False
        audio.configure(
            volume=self.settings.get("sfx_volume", 80),
            music_volume=self.settings.get("music_volume", 70),
        )
        if self.coop or (self.onion and not self.onion_caged):
            pass
        elif self.onion_caged:
            self.onion = data["onion"]

        mult = self.diff["enemy_hp"]
        for enemy in self.enemies:
            enemy.hp = max(1, int(enemy.hp * mult))
        if self.boss:
            self.boss.max_hp = max(1, int(self.boss.max_hp * self.diff["boss_hp"]))
            self.boss.hp = self.boss.max_hp
        dmg = self.diff["player_damage"]
        self.tomato.damage_mult = dmg
        if self.onion:
            self.onion.damage_mult = dmg
        self._apply_cosmetics()

    def _apply_cosmetics(self):
        if self.tomato:
            self.tomato.accessory = self.equipped.get("tomato")
        if self.onion:
            self.onion.accessory = self.equipped.get("onion")

    def _flush_coins(self):
        save_coins(self.coins)

    @property
    def players(self):
        ps = [self.tomato]
        if self.onion and (self.coop or not self.onion_caged):
            ps.append(self.onion)
        elif self.onion_caged and self.onion and not self.onion.alive:
            ps.append(self.onion)
        return [p for p in ps if p]

    def active_player(self):
        if self.coop or (self.level_num >= 5 and self.onion and not self.onion_caged):
            return self.tomato if self.active_is_tomato else self.onion
        return self.tomato

    def all_players_for_physics(self):
        ps = [self.tomato]
        if self.onion:
            if self.coop or not self.onion_caged:
                ps.append(self.onion)
        return ps

    def _apply_volume_settings(self):
        audio.configure(
            volume=self.settings.get("sfx_volume", 80),
            music_volume=self.settings.get("music_volume", 70),
        )
        from menu import save_settings

        save_settings(self.settings)

    def _set_slider_value(self, slider, value):
        value = max(0, min(100, int(value)))
        if self.settings.get(slider.key) == value:
            return
        self.settings[slider.key] = value
        self._apply_volume_settings()

    def _handle_pause_pointer(self, pos, pressed):
        if not self.paused or self.state != "play":
            self._dragging_slider = None
            return
        if not pressed:
            self._dragging_slider = None
            return
        for slider in self.pause_sliders:
            if slider.hit_test(pos, self.settings.get(slider.key, 0)):
                self._dragging_slider = slider
                self._set_slider_value(slider, slider.value_at(pos[0]))
                return
        self._dragging_slider = None

    def _handle_pause_motion(self, pos):
        if self._dragging_slider:
            self._set_slider_value(
                self._dragging_slider,
                self._dragging_slider.value_at(pos[0]),
            )

    def handle_input(self):
        keys = pygame.key.get_pressed()
        p = self.active_player()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._flush_coins()
                return "quit"
            if self.paused and self.state == "play":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._handle_pause_pointer(event.pos, True)
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self._handle_pause_pointer(event.pos, False)
                elif event.type == pygame.MOUSEMOTION:
                    self._handle_pause_motion(event.pos)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    save_current_level(self.level_num)
                    self._flush_coins()
                    return "menu"
                if event.key == pygame.K_p and self.state == "play":
                    self.paused = not self.paused
                    if not self.paused:
                        self._dragging_slider = None
                        self._apply_volume_settings()
                if event.key == pygame.K_RETURN and self.state in ("win", "gameover", "level_transition", "complete"):
                    self.transition_timer = 0
                    if self.state == "level_transition" and self.level_transition:
                        self._finish_level_transition()
                    if self.state == "complete":
                        self._flush_coins()
                        return "victory"
                if not p or not p.alive:
                    continue
                if event.key == pygame.K_e and self.onion and (
                    self.coop or (self.level_num >= 5 and not self.onion_caged)
                ):
                    self.active_is_tomato = not self.active_is_tomato
                    audio.play("switch")
                if event.key == pygame.K_r and p.is_tomato:
                    p.super_ability(self.projectiles, self.soft)
                if event.key == pygame.K_t and p and not p.is_tomato:
                    p.super_ability(self.projectiles, self.soft)

        if not p or not p.alive or self.state != "play" or self.paused:
            return True

        left = keys[pygame.K_a] or keys[pygame.K_LEFT]
        right = keys[pygame.K_d] or keys[pygame.K_RIGHT]
        jump = keys[pygame.K_w] or keys[pygame.K_UP] or keys[pygame.K_SPACE]
        p.move_input(left, right, jump)
        return True

    def update(self):
        if self.paused:
            return

        if self.state == "level_transition":
            if self.level_transition:
                if not self._transition_loaded and self.level_transition.opening_started:
                    self._advance_to_next_level()
                    self._transition_loaded = True
                if self.level_transition.update():
                    self._finish_level_transition()
            return

        if self.state == "win":
            self.transition_timer -= 1
            if self.transition_timer <= 0:
                self.next_level()
            return

        if self.state == "gameover":
            self.transition_timer -= 1
            if self.transition_timer <= 0:
                self.level_attempts += 1
                self.load_level(self.level_num, reset_attempts=False)
                self.state = "play"
            return

        if self.state == "complete":
            return

        if self.state != "play":
            return

        players = self.all_players_for_physics()
        inactive = [p for p in players if p is not self.active_player()]
        for p in inactive:
            p.vx *= 0.8
            p.move_input(False, False, False)

        for p in players:
            if p.alive:
                p.update_physics(self.solids, self.fragile)
                p.clamp_world_bounds(self.data["world_w"])

        for tile in self.fragile:
            if not tile.alive or not tile.breakable:
                continue
            stood_on = False
            for p in players:
                if not p.alive or not p.on_ground:
                    continue
                feet = pygame.Rect(p.rect.x + 2, p.rect.bottom - 6, p.rect.w - 4, 8)
                if feet.colliderect(tile.rect):
                    stood_on = True
                    tile.stand_timer += 1
                    if tile.stand_timer >= 36:
                        tile.destroy()
                        audio.play("break")
                    break
            if not stood_on:
                tile.stand_timer = max(0, tile.stand_timer - 3)

        for tramp in self.trampolines:
            tramp.update()
            for p in players:
                tramp.try_bounce(p)

        for hazard in self.hazards:
            for p in players:
                if not p.alive:
                    continue
                feet = pygame.Rect(p.rect.x + 2, p.rect.bottom - 8, p.rect.w - 4, 10)
                if feet.colliderect(hazard.rect) or p.rect.colliderect(hazard.rect):
                    p.hp = 0
                    p.alive = False
                    audio.play("hit")

        for btn in self.buttons:
            btn.check(players)
        if "gate" in self.doors:
            has_light = any(not b.need_heavy for b in self.buttons)
            heavy_on = any(b.pressed for b in self.buttons if b.need_heavy)
            if has_light:
                light_on = any(b.pressed for b in self.buttons if not b.need_heavy)
                if heavy_on and light_on:
                    self.doors["gate"].alive = False
            elif heavy_on:
                self.doors["gate"].alive = False

        if self.press and self.press.pressed and self.cage and self.cage.alive:
            floor_top = HEIGHT - 40
            if self.cage.rect.bottom < floor_top:
                dy = min(4, floor_top - self.cage.rect.bottom)
                self.cage.rect.y += dy
                if self.onion_caged and self.onion:
                    self.onion.rect.y += dy
            if self.cage.rect.bottom >= floor_top:
                self.cage.breakable = True

        if self.cage and self.cage.alive:
            for tile in self.fragile:
                if tile.alive and abs(tile.rect.x - self.cage.rect.x) <= 2:
                    tile.rect.topleft = (self.cage.rect.x, self.cage.rect.y)

        for lever in self.levers:
            for proj in self.projectiles:
                lever.hit_by_arrow(proj)
            if lever.activated and lever.remote_id in self.doors:
                self.doors[lever.remote_id].alive = False

        for turret in self.turrets:
            turret.update(self.blobs, players)

        for blob in self.blobs:
            blob.update(players)
        self.blobs = [b for b in self.blobs if b.alive]

        for fireball in self.fireballs:
            fireball.update(players, self.solids)
        self.fireballs = [f for f in self.fireballs if f.alive]

        for enemy in self.enemies:
            enemy.update(players, self.solids)
            keep_enemy_off_cola(enemy, self.hazards)
        separate_enemies(self.enemies)
        killed = sum(1 for e in self.enemies if not e.alive)
        if killed:
            self.coins += killed * COINS_PER_KILL
        self.enemies = [e for e in self.enemies if e.alive]

        for proj in self.projectiles:
            proj.update()
            for enemy in self.enemies:
                if not proj.alive:
                    break
                if isinstance(enemy, ExplosiveCola) and proj.rect.colliderect(enemy.rect):
                    enemy.hit_by_arrow()
                elif isinstance(enemy, BurgerSpike) and proj.rect.colliderect(enemy.rect):
                    enemy.hurt(1)
                    proj.alive = False
            if self.boss and self.boss.alive and proj.rect.colliderect(self.boss.rect):
                self.boss.hurt(1)
                proj.alive = False
        self.projectiles = [p for p in self.projectiles if p.alive]

        if self.boss and self.boss.alive:
            self.boss.update(players, self.solids, self.fireballs)
        elif self.boss and not self.boss.alive and "boss" in self.doors:
            self.doors["boss"].alive = False

        if self.vent_block and self.tomato.alive:
            if self.tomato.rect.colliderect(self.vent_block.rect):
                self.tomato.rect.left = self.vent_block.rect.left - self.tomato.rect.width

        if self.onion_caged and self.onion and self.cage and not self.cage.alive:
            self.onion_caged = False
            self.coop = True
            self.onion.rect.y = HEIGHT - 120
            self.message_timer = 120
            if "rescue" in self.doors:
                self.doors["rescue"].alive = False

        focus = self.active_player() or self.tomato
        if focus.alive:
            self.cam_x = max(0, min(focus.rect.centerx - WIDTH // 3, self.data["world_w"] - WIDTH))

        if any(not p.alive for p in players):
            self.state = "gameover"
            self.transition_timer = TRANSITION_DELAY
            return

        alive_players = players

        if self.boss and not self.boss.alive and self.goal:
            pass
        elif self.boss and self.boss.alive:
            return

        reached = any(p.alive and p.rect.colliderect(self.goal.rect) for p in alive_players)
        if self.onion_caged:
            reached = False
        elif self.coop:
            goal_zone = self.goal.rect.inflate(100, 50)
            if self.level_num == 5:
                reached = (
                    self.onion
                    and self.onion.alive
                    and self.onion.rect.colliderect(goal_zone)
                )
            else:
                reached = (
                    self.tomato.alive
                    and self.onion
                    and self.onion.alive
                    and self.tomato.rect.colliderect(goal_zone)
                    and self.onion.rect.colliderect(goal_zone)
                )
        if reached:
            unlock_level(self.level_num)
            if self.level_num >= LEVELS_TOTAL:
                audio.play_level_complete_music(audio.GAME_COMPLETE_MUSIC)
                self.state = "complete"
                self.transition_timer = TRANSITION_DELAY
            else:
                audio.play_level_complete_music()
                tomato_start, onion_start = self._transition_hero_starts()
                show_onion = onion_start is not None
                self.level_transition = LevelTransition(
                    tomato_start=tomato_start,
                    onion_start=onion_start,
                    show_onion=show_onion,
                )
                self._transition_loaded = False
                self.state = "level_transition"

    def _transition_hero_starts(self):
        cam = self.cam_x
        t_sprite = art.get_tomato_sprite(self.tomato.facing)
        tx = self.tomato.rect.centerx - cam - t_sprite.get_width() // 2
        ty = self.tomato.rect.bottom - t_sprite.get_height()
        onion_start = None
        if self.onion and (self.coop or (self.level_num >= 5 and not self.onion_caged)):
            o_sprite = art.get_onion_sprite(self.onion.facing)
            ox = self.onion.rect.centerx - cam - o_sprite.get_width() // 2
            oy = self.onion.rect.bottom - o_sprite.get_height()
            onion_start = (ox, oy)
        return (tx, ty), onion_start

    def _advance_to_next_level(self):
        self.level_num += 1
        save_current_level(self.level_num)
        self.load_level(self.level_num)

    def _finish_level_transition(self):
        if not self._transition_loaded:
            self._advance_to_next_level()
        self.level_transition = None
        self._transition_loaded = False
        self.state = "play"
        audio.play_gameplay_music()

    def next_level(self):
        if self.level_num >= LEVELS_TOTAL:
            save_current_level(self.level_num)
            self.state = "complete"
            return
        self.level_num += 1
        save_current_level(self.level_num)
        self.load_level(self.level_num)
        self.state = "play"

    def draw(self):
        if self.state == "level_transition" and self.level_transition:
            self.level_transition.draw(self.screen, self)
            pygame.display.flip()
            return

        self._draw_world()
        self._draw_hud()

        if self.state == "win":
            self._overlay("Уровень пройден!")
        elif self.state == "gameover":
            self._overlay("Поражение...")
        elif self.state == "complete":
            self._overlay("ПОБЕДА! Enter — финал истории")
        elif self.paused:
            self._draw_pause_menu()

        pygame.display.flip()

    def _draw_world(self, hide_players=False):
        art.draw_background(self.screen, self.cam_x)
        cam = self.cam_x

        for group in (self.solids, self.fragile, self.soft):
            for tile in group:
                tile.draw(self.screen, cam)

        for hazard in self.hazards:
            hazard.draw(self.screen, cam)

        for tramp in self.trampolines:
            tramp.draw(self.screen, cam)

        for door in self.doors.values():
            door.draw(self.screen, cam)

        if self.cage and self.cage.alive:
            art.draw_cage(self.screen, self.cage.rect, cam)

        for btn in self.buttons:
            art.draw_button_tile(self.screen, btn.rect, cam, btn.pressed)

        for lever in self.levers:
            art.draw_lever(self.screen, lever.rect, cam, lever.activated)

        self.goal.draw(self.screen, cam)

        for turret in self.turrets:
            turret.draw(self.screen, cam)
        for blob in self.blobs:
            blob.draw(self.screen, cam)
        for fireball in self.fireballs:
            fireball.draw(self.screen, cam)
        for enemy in self.enemies:
            enemy.draw(self.screen, cam)
        if self.boss and self.boss.alive:
            self.boss.draw(self.screen, cam)

        for proj in self.projectiles:
            proj.draw(self.screen, cam)

        if not hide_players:
            for p in self.all_players_for_physics():
                p.draw(self.screen, cam)

    def _draw_hud(self):
        d = self.data
        lines = [(d["title"], YELLOW, 18)]
        lines.append((f"Монеты: {self.coins}", YELLOW, 14))
        if self.level_attempts > 1:
            lines.append((f"Попытка: {self.level_attempts}", (180, 180, 190), 14))
        if self.show_hints:
            lines.append((d["hint"], (200, 200, 210), 14))
        if self.coop or (self.level_num >= 5 and not self.onion_caged):
            active = "Томат" if self.active_is_tomato else "Лук"
            lines.append((f"Активен: {active} | E — смена | оба у цели!", CYAN, 14))
        lines.append(("WASD — движение | E — смена героя | R/T — супер | P — пауза | Esc — меню", (160, 160, 170), 14))

        onion_hp = onion_max = None
        if self.onion and (self.coop or not self.onion_caged):
            onion_hp = self.onion.hp
            onion_max = self.onion.max_hp

        art.draw_hud_panel(
            self.screen,
            lines,
            self.tomato.hp,
            self.tomato.max_hp,
            onion_hp,
            onion_max,
            self.active_is_tomato,
        )

        if self.message_timer > 0:
            self.message_timer -= 1

    def _overlay(self, text):
        s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        self.screen.blit(s, (0, 0))
        panel = pygame.Rect(WIDTH // 2 - 220, HEIGHT // 2 - 40, 440, 80)
        art.draw_ui_panel(self.screen, panel, selected=True)
        surf = art.render_text(text, 18, YELLOW)
        self.screen.blit(surf, surf.get_rect(center=panel.center))

    def _draw_pause_menu(self):
        s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        self.screen.blit(s, (0, 0))

        panel = pygame.Rect(WIDTH // 2 - 240, HEIGHT // 2 - 120, 480, 240)
        art.draw_ui_panel(self.screen, panel, selected=True)

        title = art.render_text("ПАУЗА", 22, YELLOW)
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, panel.y + 36)))

        for slider in self.pause_sliders:
            slider.draw(self.screen, self.settings.get(slider.key, 0))

        hint = art.render_text("P — продолжить | Esc — меню", 14, (160, 160, 170))
        self.screen.blit(hint, hint.get_rect(center=(WIDTH // 2, panel.bottom - 24)))

    def run(self):
        while True:
            action = self.handle_input()
            if action in ("menu", "quit"):
                return action
            self.update()
            self.draw()
            self.clock.tick(FPS)


def run_game():
    from menu import run_menu
    from story import run_intro, run_outro

    while True:
        result = run_menu()
        if not result:
            break
        settings, start_level = result
        if start_level == 1 and not run_intro(settings):
            break
        game = Game(settings, start_level)
        end = game.run()
        if end == "quit":
            break
        if end == "victory":
            run_outro(settings)
    pygame.quit()
