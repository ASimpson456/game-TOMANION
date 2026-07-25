import math

import pygame

from constants import *
import audio
import pixel_art as art


def enemy_feet_rect(entity):
    return pygame.Rect(entity.rect.x + 2, entity.rect.bottom - 8, entity.rect.w - 4, 10)


def keep_enemy_off_cola(entity, hazards):
    """Не даёт наземным врагам заходить на разлитую колу."""
    if not entity.alive or not hazards:
        return
    feet = enemy_feet_rect(entity)
    for hazard in hazards:
        if not feet.colliderect(hazard.rect):
            continue
        on_left = entity.rect.centerx <= hazard.rect.centerx
        if on_left:
            entity.rect.right = hazard.rect.left
        else:
            entity.rect.left = hazard.rect.right
        entity.reflect_from_hazard(on_left)
        entity.sync_attachments()
        return


def sync_enemy_attachments(enemy):
    enemy.sync_attachments()


def shift_enemy_patrol(enemy, dx):
    enemy.shift_patrol(dx)


def clamp_enemy_patrol(enemy):
    enemy.clamp_patrol()
    enemy.sync_attachments()


def separate_enemies(enemies, gap=14):
    """Разводит врагов, чтобы они не стояли/не шли вплотную друг к другу."""
    living = [e for e in enemies if e.alive]
    for i, a in enumerate(living):
        for b in living[i + 1 :]:
            pad = gap // 2
            if not a.rect.inflate(pad, pad).colliderect(b.rect.inflate(pad, pad)):
                continue
            dx = b.rect.centerx - a.rect.centerx
            if dx == 0:
                dx = 1
            overlap = (a.rect.width + b.rect.width) // 2 + gap - abs(dx)
            if overlap <= 0:
                continue
            shift = (overlap + 1) // 2
            if dx > 0:
                a.rect.x -= shift
                b.rect.x += shift
            else:
                a.rect.x += shift
                b.rect.x -= shift
            clamp_enemy_patrol(a)
            clamp_enemy_patrol(b)
            if a.rect.colliderect(b.rect.inflate(pad, pad)):
                a.reverse_apart(-1 if dx > 0 else 1)
                b.reverse_apart(1 if dx > 0 else -1)
            sync_enemy_attachments(a)
            sync_enemy_attachments(b)


class RectSprite:
    def __init__(self, x, y, w, h, color):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = color
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False
        self.alive = True

    def draw(self, surf, cam_x=0):
        pass


class Player(RectSprite):
    kind = "player"

    def __init__(self, x, y, tomato=True):
        self.is_tomato = tomato
        if tomato:
            super().__init__(x, y, art.TOMATO_SIZE[0], art.TOMATO_SIZE[1], TOMATO_COLOR)
            self.speed = 4.2
            self.jump = -11.5
            self.max_hp = 5
            self.shield_timer = 0
            self.tackle_timer = 0
            self.tackle_cooldown = 0
        else:
            super().__init__(x, y, art.ONION_SIZE[0], art.ONION_SIZE[1], ONION_COLOR)
            self.speed = 5.8
            self.jump = -14.0
            self.max_hp = 3
            self.arrow_cooldown = 0
            self.ladder_arrows = []
        self.accessory = None
        self.hp = self.max_hp
        self.invuln = 0
        self.facing = 1
        self.damage_mult = 1.0
        self.max_jumps = 2 if tomato else 1
        self.jumps_remaining = self.max_jumps
        self._jump_held = False

    def can_fit_vent(self):
        return not self.is_tomato

    def update_physics(self, solids, fragile, dt_scale=1):
        if not self.alive:
            return
        self.vy += GRAVITY * dt_scale
        if self.vy > 16:
            self.vy = 16

        self.rect.x += int(self.vx * dt_scale)
        self._collide_x(solids, fragile)

        self.rect.y += int(self.vy * dt_scale)
        self.on_ground = False
        self._collide_y(solids, fragile)

        if self.invuln > 0:
            self.invuln -= 1
        if self.is_tomato:
            if self.shield_timer > 0:
                self.shield_timer -= 1
            if self.tackle_timer > 0:
                self.tackle_timer -= 1
            if self.tackle_cooldown > 0:
                self.tackle_cooldown -= 1
        else:
            if self.arrow_cooldown > 0:
                self.arrow_cooldown -= 1

        if self.on_ground:
            self.jumps_remaining = self.max_jumps

    def clamp_world_bounds(self, world_w, world_h=HEIGHT):
        if not self.alive:
            return
        if self.rect.left < 0:
            self.rect.left = 0
            if self.vx < 0:
                self.vx = 0
        if self.rect.right > world_w:
            self.rect.right = world_w
            if self.vx > 0:
                self.vx = 0
        if self.rect.top < 0:
            self.rect.top = 0
            if self.vy < 0:
                self.vy = 0
        if self.rect.bottom > world_h:
            self.rect.bottom = world_h
            if self.vy > 0:
                self.vy = 0
            self.on_ground = True

    def _collide_x(self, solids, fragile):
        for group in (solids, fragile):
            for tile in group:
                if not tile.alive:
                    continue
                if self.rect.colliderect(tile.rect):
                    if self.vx > 0:
                        self.rect.right = tile.rect.left
                        if tile.breakable and self.is_tomato and (
                            self.tackle_timer > 0 or abs(self.vx) > 6
                        ):
                            tile.destroy()
                    elif self.vx < 0:
                        self.rect.left = tile.rect.right
                        if tile.breakable and self.is_tomato and (
                            self.tackle_timer > 0 or abs(self.vx) > 6
                        ):
                            tile.destroy()
                    self.vx = 0

    def _collide_y(self, solids, fragile):
        for group in (solids, fragile):
            for tile in group:
                if not tile.alive:
                    continue
                if self.rect.colliderect(tile.rect):
                    if self.vy > 0:
                        self.rect.bottom = tile.rect.top
                        self.vy = 0
                        self.on_ground = True
                        if tile.breakable and self.is_tomato and self.tackle_timer > 0:
                            tile.destroy()
                    elif self.vy < 0:
                        self.rect.top = tile.rect.bottom
                        self.vy = 0

    def move_input(self, left, right, jump):
        if not self.alive:
            return
        self.vx = 0
        if left:
            self.vx = -self.speed
            self.facing = -1
        if right:
            self.vx = self.speed
            self.facing = 1
        jump_pressed = jump and not self._jump_held
        self._jump_held = jump
        if jump_pressed and self.jumps_remaining > 0:
            self.vy = self.jump
            self.jumps_remaining -= 1
            self.on_ground = False

    def super_ability(self, projectiles, soft_walls):
        if not self.alive:
            return None
        if self.is_tomato:
            if self.tackle_cooldown > 0 or self.tackle_timer > 0:
                return "cooldown"
            self.tackle_timer = 28
            self.tackle_cooldown = 45
            self.vx = 11 * self.facing
            self.shield_timer = 28
            return "tackle"
        if self.arrow_cooldown > 0:
            return "cooldown"
        self.arrow_cooldown = 18
        ax = self.rect.centerx + 26 * self.facing
        ay = self.rect.centery - 4
        projectiles.append(Arrow(ax, ay, self.facing, ladder=True))
        for wall in soft_walls:
            if wall.rect.collidepoint(ax, ay):
                wall.add_rung(ax, ay)
        return "arrow"

    def shield_active(self):
        return self.is_tomato and self.shield_timer > 0

    def tackle_active(self):
        return self.is_tomato and self.tackle_timer > 0

    def hurt(self, dmg=1):
        if self.invuln > 0 or not self.alive:
            return
        if self.shield_active():
            return
        self.hp -= max(1, int(dmg * getattr(self, "damage_mult", 1.0)))
        self.invuln = 40
        audio.play("hit")
        if self.hp <= 0:
            self.alive = False

    def draw(self, surf, cam_x=0):
        art.draw_player(surf, self, cam_x)
        if not self.is_tomato:
            for lx, ly in self.ladder_arrows:
                art.px(surf, lx - cam_x - 3, ly - 2, 6, 4, ONION_GREEN)


class ColaSpill:
    """Разлитая кола на полу — смертельна при касании."""

    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)

    def draw(self, surf, cam_x):
        art.draw_cola_spill(surf, self.rect, cam_x)


class Trampoline:
    """Батут — подбрасывает героя вверх."""

    def __init__(self, x, y, w=72, h=14, power=-17.5):
        self.rect = pygame.Rect(x, y, w, h)
        self.power = power
        self.cooldown = 0
        self.squish = 0

    def update(self):
        if self.cooldown > 0:
            self.cooldown -= 1
        if self.squish > 0:
            self.squish -= 1

    def try_bounce(self, player):
        if not player.alive or self.cooldown > 0:
            return False
        feet = pygame.Rect(player.rect.x + 4, player.rect.bottom - 10, player.rect.w - 8, 12)
        if not feet.colliderect(self.rect):
            return False
        if player.vy < -3:
            return False
        player.vy = self.power
        player.on_ground = False
        player.rect.bottom = self.rect.top
        self.cooldown = 12
        self.squish = 8
        audio.play("bounce")
        return True

    def draw(self, surf, cam_x):
        art.draw_trampoline(surf, self.rect, cam_x, self.squish)


class Arrow:
    def __init__(self, x, y, direction, ladder=False):
        self.rect = pygame.Rect(x, y, 18, 6)
        self.vx = 12 * direction
        self.alive = True
        self.ladder = ladder

    def update(self):
        self.rect.x += int(self.vx)
        if self.rect.right < -50 or self.rect.left > WIDTH + 2000:
            self.alive = False

    def draw(self, surf, cam_x):
        if not self.alive:
            return
        art.draw_arrow(surf, self.rect, cam_x)


class Tile:
    def __init__(self, x, y, w, h, color=PLATFORM, breakable=False, soft=False):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = color
        self.breakable = breakable
        self.soft = soft
        self.alive = True
        self.rungs = []
        self.stand_timer = 0

    def destroy(self):
        if self.breakable:
            self.alive = False

    def add_rung(self, x, y):
        if self.soft:
            self.rungs.append((x, y))

    def draw(self, surf, cam_x):
        if not self.alive:
            return
        kind = "fragile" if self.breakable else "soft" if self.soft else "solid"
        if self.color == METAL:
            kind = "metal"
        art.draw_tile(surf, self.rect, cam_x, kind)
        for rx, ry in self.rungs:
            art.px(surf, rx - cam_x - 4, ry - 2, 8, 4, ONION_GREEN)


class WeightButton:
    def __init__(self, x, y, w, h, need_heavy=True):
        self.rect = pygame.Rect(x, y, w, h)
        self.need_heavy = need_heavy
        self.pressed = False

    def check(self, players):
        heavy_on = any(
            p.alive and p.is_tomato and p.rect.colliderect(self.rect.inflate(0, 8))
            for p in players
        )
        light_on = any(
            p.alive and not p.is_tomato and p.rect.colliderect(self.rect)
            for p in players
        )
        if self.need_heavy:
            self.pressed = heavy_on
        else:
            self.pressed = light_on or heavy_on


class Lever:
    def __init__(self, x, y, remote_id):
        self.rect = pygame.Rect(x, y, 24, 24)
        self.remote_id = remote_id
        self.activated = False

    def hit_by_arrow(self, arrow):
        if arrow.alive and self.rect.colliderect(arrow.rect):
            self.activated = True
            arrow.alive = False


class Goal:
    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)

    def draw(self, surf, cam_x):
        art.draw_goal(surf, self.rect, cam_x)


class Enemy:
    kind = "enemy"

    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 36, 36)
        self.alive = True
        self.hp = 2

    def sync_attachments(self):
        pass

    def shift_patrol(self, dx):
        pass

    def clamp_patrol(self):
        pass

    def reverse_apart(self, direction):
        pass

    def reflect_from_hazard(self, on_left_side):
        pass

    def update(self, players, solids):
        pass

    def hurt(self, dmg=1):
        self.hp -= dmg
        if self.hp <= 0:
            self.alive = False

    def draw(self, surf, cam_x):
        if not self.alive:
            return
        art.outline_rect(surf, self.rect.move(-cam_x, 0), JUNK, (220, 180, 100), JUNK_LO)


class HorizontalPatrolEnemy(Enemy):
    """Наземный враг с горизонтальным патрулем (x_min / x_max)."""

    def __init__(self, x, y, x_min, x_max, vx):
        super().__init__(x, y)
        self.vx = vx
        self.x_min = x_min
        self.x_max = x_max

    def shift_patrol(self, dx):
        self.x_min += dx
        self.x_max += dx

    def clamp_patrol(self):
        if self.rect.left < self.x_min:
            self.rect.left = self.x_min
        if self.rect.right > self.x_max:
            self.rect.right = self.x_max

    def reverse_apart(self, direction):
        if direction < 0:
            self.vx = -abs(self.vx) if self.vx else -1.5
        else:
            self.vx = abs(self.vx) if self.vx else 1.5

    def reflect_from_hazard(self, on_left_side):
        if on_left_side:
            if self.vx >= 0:
                self.vx = -abs(self.vx) if self.vx else -1.5
        elif self.vx <= 0:
            self.vx = abs(self.vx) if self.vx else 1.5


class RangePatrolEnemy(Enemy):
    """Наземный враг с патрулем между двумя X-координатами (x1 / x2)."""

    def __init__(self, x, y, x2, vx):
        super().__init__(x, y)
        self.x1 = min(x, x2)
        self.x2 = max(x, x2)
        self.vx = vx

    def shift_patrol(self, dx):
        self.x1 += dx
        self.x2 += dx

    def clamp_patrol(self):
        if self.rect.left < self.x1:
            self.rect.left = self.x1
        if self.rect.right > self.x2:
            self.rect.right = self.x2

    def reverse_apart(self, direction):
        if direction < 0:
            self.vx = -abs(self.vx) if self.vx else -1.5
        else:
            self.vx = abs(self.vx) if self.vx else 1.5

    def reflect_from_hazard(self, on_left_side):
        if on_left_side:
            if self.vx >= 0:
                self.vx = -abs(self.vx) if self.vx else -1.5
        elif self.vx <= 0:
            self.vx = abs(self.vx) if self.vx else 1.5


class BurgerSpike(HorizontalPatrolEnemy):
    def __init__(self, x, y, x_min=100, x_max=1800):
        super().__init__(x, y, x_min, x_max, 1.5)
        self.spike = pygame.Rect(x + 10, y - 14, 16, 18)

    def sync_attachments(self):
        self.spike.centerx = self.rect.centerx

    def update(self, players, solids):
        if not self.alive:
            return
        self.rect.x += int(self.vx)
        self.spike.centerx = self.rect.centerx
        if self.rect.left < self.x_min or self.rect.right > self.x_max:
            self.vx *= -1
        hitbox = self.rect.union(self.spike)
        for p in players:
            if not p.alive:
                continue
            if not p.rect.colliderect(hitbox):
                continue
            if (
                not p.is_tomato
                and p.vy > 0
                and p.rect.bottom <= self.rect.top + 12
                and self.rect.left + 6 < p.rect.centerx < self.rect.right - 6
            ):
                self.hurt(2)
                p.vy = -10
                continue
            if p.is_tomato and p.tackle_active() and abs(p.vx) > 5:
                self.hurt(2)
                p.vx *= -0.3
                continue
            p.hurt()

    def draw(self, surf, cam_x):
        if not self.alive:
            return
        art.draw_burger(surf, self.rect, cam_x, self.spike)


class JumpingFries(Enemy):
    HOP_VY = -8.5
    HOP_INTERVAL = 72
    MAX_FALL = 10

    def __init__(self, x, y):
        super().__init__(x, y)
        self.base_y = y
        self.vy = 0.0
        self.on_ground = True
        self.hop_timer = 18 + (int(x) % 48)

    def update(self, players, solids):
        if not self.alive:
            return
        if self.on_ground:
            self.hop_timer -= 1
            if self.hop_timer <= 0:
                self.vy = self.HOP_VY
                self.on_ground = False
                self.hop_timer = self.HOP_INTERVAL
        else:
            self.vy += GRAVITY
            if self.vy > self.MAX_FALL:
                self.vy = self.MAX_FALL

        self.rect.y += int(self.vy)
        if self.rect.y >= self.base_y:
            self.rect.y = self.base_y
            self.vy = 0
            self.on_ground = True

        for p in players:
            if p.alive and self.rect.colliderect(p.rect):
                if p.shield_active():
                    self.hurt(2)
                else:
                    p.hurt()

    def draw(self, surf, cam_x):
        if not self.alive:
            return
        art.draw_fries(surf, self.rect, cam_x)


class ExplosiveCola(HorizontalPatrolEnemy):
    def __init__(self, x, y, x_min=80, x_max=1900):
        super().__init__(x, y, x_min, x_max, 1.2)
        self.fuse = -1

    def update(self, players, solids):
        if not self.alive:
            return
        self.rect.x += int(self.vx)
        if self.rect.left < self.x_min or self.rect.right > self.x_max:
            self.vx *= -1
        for p in players:
            if not p.alive:
                continue
            if self.rect.colliderect(p.rect) and self.fuse < 0:
                self.fuse = 120
            if p.is_tomato and abs(p.rect.centerx - self.rect.centerx) < 60:
                self.fuse = 120 if self.fuse < 0 else self.fuse
        if self.fuse >= 0:
            self.fuse -= 1
            if self.fuse == 0:
                self.explode(players)
                self.alive = False

    def hit_by_arrow(self):
        self.fuse = 120 if self.fuse < 0 else self.fuse

    def explode(self, players):
        blast = self.rect.inflate(120, 120)
        for p in players:
            if p.alive and blast.colliderect(p.rect):
                if p.is_tomato and p.shield_active():
                    continue
                behind = not p.is_tomato and any(
                    t.alive
                    and t.is_tomato
                    and t.shield_active()
                    and t.rect.colliderect(p.rect.inflate(30, 30))
                    for t in players
                )
                if behind:
                    continue
                p.hurt(2)

    def draw(self, surf, cam_x):
        if not self.alive:
            return
        art.draw_cola(surf, self.rect, cam_x, self.fuse)


class DonutPatrol(RangePatrolEnemy):
    PATROL_SPEED = 2.0

    def __init__(self, x, y, x2):
        super().__init__(x, y, x2, 0)
        self.rect.left = max(self.x1, min(self.rect.left, self.x2 - self.rect.width))
        self.vx = self.PATROL_SPEED if self.rect.centerx <= (self.x1 + self.x2) // 2 else -self.PATROL_SPEED

    def update(self, players, solids):
        if not self.alive:
            return
        self.rect.x += int(round(self.vx))
        if self.rect.left <= self.x1:
            self.rect.left = self.x1
            self.vx = abs(self.PATROL_SPEED)
        elif self.rect.right >= self.x2:
            self.rect.right = self.x2
            self.vx = -abs(self.PATROL_SPEED)
        for p in players:
            if p.alive and self.rect.colliderect(p.rect):
                if p.is_tomato and p.tackle_active():
                    self.hurt(3)
                    self.vx = -abs(self.vx) * 0.5 if self.vx > 0 else abs(self.vx) * 0.5
                else:
                    p.hurt()

    def draw(self, surf, cam_x):
        if not self.alive:
            return
        art.draw_donut(surf, self.rect, cam_x, turbo=False)


class MayoTurret:
    def __init__(self, x, y, direction=1):
        self.rect = pygame.Rect(x, y, 28, 28)
        self.direction = direction
        self.cooldown = 60

    def update(self, blobs, players):
        self.cooldown -= 1
        if self.cooldown > 0:
            return
        target = None
        for p in players:
            if p.alive and p.rect.x * self.direction > self.rect.x * self.direction:
                target = p
                break
        if target:
            blobs.append(MayoBlob(self.rect.centerx, self.rect.centery, 6 * self.direction, 2))
            self.cooldown = 90

    def draw(self, surf, cam_x):
        art.draw_turret(surf, self.rect, cam_x)


class MayoBlob:
    def __init__(self, x, y, vx, vy):
        self.rect = pygame.Rect(x, y, 12, 12)
        self.vx = vx
        self.vy = vy
        self.alive = True

    def update(self, players):
        self.rect.x += int(self.vx)
        self.rect.y += int(self.vy)
        for p in players:
            if p.alive and self.rect.colliderect(p.rect):
                if p.shield_active():
                    self.alive = False
                else:
                    p.hurt()
                    self.alive = False
        if self.rect.right < 0 or self.rect.left > 2500:
            self.alive = False

    def draw(self, surf, cam_x):
        if not self.alive:
            return
        art.draw_mayo(surf, self.rect, cam_x)


class FireBall:
    SPEED = 4.5
    SIZE = 14

    def __init__(self, x, y, vx, vy):
        half = self.SIZE // 2
        self.rect = pygame.Rect(int(x - half), int(y - half), self.SIZE, self.SIZE)
        self.vx = vx
        self.vy = vy
        self.alive = True

    def update(self, players, solids):
        self.rect.x += int(self.vx)
        self.rect.y += int(self.vy)
        for tile in solids:
            if getattr(tile, "alive", True) and self.rect.colliderect(tile.rect):
                self.alive = False
                return
        for p in players:
            if not p.alive:
                continue
            if self.rect.colliderect(p.rect):
                if p.shield_active():
                    self.alive = False
                else:
                    p.hurt()
                    self.alive = False
                return
        if (
            self.rect.right < -40
            or self.rect.left > 3000
            or self.rect.bottom < -40
            or self.rect.top > HEIGHT + 40
        ):
            self.alive = False

    def draw(self, surf, cam_x):
        if not self.alive:
            return
        art.draw_fireball(surf, self.rect, cam_x)


class Boss:
    def __init__(self, name, x, y, hp, fire_interval=5.0):
        self.name = name
        self.rect = pygame.Rect(x, y, 80, 80)
        self.hp = hp
        self.max_hp = hp
        self.alive = True
        self.fire_interval = fire_interval
        self.fire_cooldown = int(fire_interval * FPS)
        self.tackle_hit_cooldown = 0

    TACKLE_HIT_COOLDOWN = 55

    def _spawn_fireballs(self, fireballs):
        spacing = art.TOMATO_SIZE[0] * 2 * 0.88
        radius = self.rect.width // 2 + 10
        count = max(6, int(round(2 * math.pi * radius / spacing)))
        cx, cy = self.rect.centerx, self.rect.centery
        for i in range(count):
            angle = 2 * math.pi * i / count
            vx = FireBall.SPEED * math.cos(angle)
            vy = FireBall.SPEED * math.sin(angle)
            sx = cx + radius * math.cos(angle)
            sy = cy + radius * math.sin(angle)
            fireballs.append(FireBall(sx, sy, vx, vy))

    def update(self, players, solids, fireballs):
        if self.tackle_hit_cooldown > 0:
            self.tackle_hit_cooldown -= 1
        self.fire_cooldown -= 1
        if self.fire_cooldown <= 0:
            self._spawn_fireballs(fireballs)
            self.fire_cooldown = max(1, int(self.fire_interval * FPS))
        for p in players:
            if not p.alive:
                continue
            if p.rect.colliderect(self.rect):
                if p.is_tomato and p.tackle_active():
                    if self.tackle_hit_cooldown <= 0:
                        self.hurt(2)
                        self.tackle_hit_cooldown = self.TACKLE_HIT_COOLDOWN
                    continue
                p.hurt()

    def hurt(self, dmg=1):
        self.hp -= dmg
        if self.hp <= 0:
            self.alive = False

    def draw(self, surf, cam_x):
        if not self.alive:
            return
        art.draw_boss(surf, self.rect, cam_x, self.hp, self.max_hp)
