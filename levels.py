from constants import FRAGILE, HEIGHT, LEVELS_TOTAL, METAL, PLATFORM, WIDTH
import pygame
from entities import (
    Boss,
    BurgerSpike,
    ColaSpill,
    DonutPatrol,
    ExplosiveCola,
    Goal,
    JumpingFries,
    Lever,
    MayoTurret,
    Player,
    Tile,
    Trampoline,
    WeightButton,
    shift_enemy_patrol,
    sync_enemy_attachments,
)


def floor(w=2200):
    return [
        Tile(0, HEIGHT - 40, w, 40),
        Tile(0, 0, 12, HEIGHT, METAL),
        Tile(w - 12, 0, 12, HEIGHT, METAL),
    ]


def floor_with_gaps(w, gaps):
    tiles = [
        Tile(0, 0, 12, HEIGHT, METAL),
        Tile(w - 12, 0, 12, HEIGHT, METAL),
    ]
    x = 0
    for gap_x, gap_w in sorted(gaps):
        if gap_x > x:
            tiles.append(Tile(x, HEIGHT - 40, gap_x - x, 40))
        x = gap_x + gap_w
    if x < w - 12:
        tiles.append(Tile(x, HEIGHT - 40, w - 12 - x, 40))
    return tiles


def goal_at_end(world_w, size=50):
    x = world_w - 12 - 24 - size
    y = HEIGHT - 40 - size
    return Goal(x, y, size, size)


def _platforms(solids, specs, color=PLATFORM):
    for x, y, w, h in specs:
        solids.append(Tile(x, y, w, h, color))


def _trampolines(items, specs, power=-17.5):
    for spec in specs:
        if len(spec) == 5:
            x, y, w, h, power = spec
        elif len(spec) == 4:
            x, y, w, h = spec
        else:
            x, y, w = spec
            h = 14
        items.append(Trampoline(x, y, w, h, power))


def _tramp_before_gaps(trampolines, gaps, offset=72, width=80):
    """Батуты на полу перед каждой пропастью с колой."""
    specs = []
    prev_end = 0
    for gx, gw in sorted(gaps):
        if gx - prev_end >= 140:
            specs.append((max(60, gx - offset), HEIGHT - 52, width, 14))
        prev_end = gx + gw
    _trampolines(trampolines, specs)


def _tighten_platforms(level_num, solids, start=12, min_w=50):
    """Поздние уровни — уже площадки, точнее прыжки (как в Dadish)."""
    if level_num < start:
        return
    shrink = min(18, ((level_num - start) // 2 + 1) * 3)
    for tile in solids:
        if tile.color != PLATFORM or tile.rect.height != 20:
            continue
        r = tile.rect
        nw = max(min_w, r.width - shrink)
        if nw >= r.width:
            continue
        nx = r.x + (r.width - nw) // 2
        tile.rect = pygame.Rect(nx, r.y, nw, r.height)


def _space_enemies(enemies, min_gap=72):
    """Стартовые позиции врагов не должны пересекаться."""
    ordered = sorted(enemies, key=lambda e: e.rect.x)
    for i in range(1, len(ordered)):
        prev = ordered[i - 1]
        cur = ordered[i]
        need = prev.rect.right + min_gap
        if cur.rect.left < need:
            shift = need - cur.rect.left
            cur.rect.x += shift
            shift_enemy_patrol(cur, shift)
            sync_enemy_attachments(cur)


def _door(solids, doors, key, x, y, w, h):
    doors[key] = Tile(x, y, w, h, METAL)
    solids.append(doors[key])


def _coop_pair():
    return True, Player(120, HEIGHT - 120, tomato=False)


def _boss_arena(solids, doors, boss_x, boss_name, hp, fire_interval=5.0):
    _platforms(
        solids,
        [
            (boss_x - 280, HEIGHT - 160, 120, 20),
            (boss_x - 140, HEIGHT - 220, 90, 20),
            (boss_x - 60, HEIGHT - 240, 100, 20),
        ],
    )
    return Boss(boss_name, boss_x, HEIGHT - 160, hp, fire_interval=fire_interval)


def _boss_fire_interval(level_num):
    order = {10: 0, 15: 1, 20: 2, 25: 3, 30: 4}
    return 5.0 - order.get(level_num, 0) * 0.5


def _scale_late_enemies(n, enemies):
    """Чуть крепче обычные враги на поздних уровнях."""
    if n < 14:
        return
    bonus = 1 + (n - 14) // 8
    for enemy in enemies:
        enemy.hp = max(enemy.hp, 2 + bonus)


def build_level(n):
    SOLO_W = {1: 1400, 2: 1800, 3: 2000, 4: 2200, 5: 2400}
    W = SOLO_W.get(n, 2200)

    solids = floor(W)
    fragile = []
    soft = []
    buttons = []
    levers = []
    doors = {}
    turrets = []
    enemies = []
    boss = None
    hazards = []
    trampolines = []
    tomato = Player(80, HEIGHT - 120, tomato=True)
    onion = None
    coop = False
    onion_caged = False
    cage = None
    press = None
    vent_block = None
    title = f"Уровень {n}"
    hint = ""

    if n == 1:
        title = "Уровень 1: Первые шаги"
        hint = "WASD — бег и прыжок. Бетон безопасен, разлитая кола — смертельна!"
        h = HEIGHT
        solids = [
            Tile(0, 0, 12, h, METAL),
            Tile(W - 12, 0, 12, h, METAL),
            Tile(12, h - 40, 320, 40, METAL),
            Tile(420, h - 40, 120, 40, METAL),
            Tile(620, h - 40, 280, 40, METAL),
            Tile(980, h - 40, 160, 40, METAL),
            Tile(1200, h - 40, W - 1212, 40, METAL),
            Tile(180, h - 120, 90, 20, METAL),
            Tile(360, h - 160, 80, 20, METAL),
            Tile(520, h - 130, 90, 20, METAL),
            Tile(760, h - 170, 85, 20, METAL),
            Tile(940, h - 140, 90, 20, METAL),
            Tile(1120, h - 110, 100, 20, METAL),
        ]
        hazards = [
            ColaSpill(332, h - 40, 88, 40),
            ColaSpill(900, h - 40, 80, 40),
        ]
    elif n == 2:
        W = 1800
        title = "Уровень 2: Сила тарана"
        hint = "R — таран. Разбей хрупкую стену в конце и перепрыгивай пропасти!"
        cola_gaps = [(240, 75), (430, 75), (620, 80), (820, 80), (1020, 75), (1220, 75), (1420, 75)]
        solids = floor_with_gaps(W, cola_gaps)
        fragile = [
            Tile(180, HEIGHT - 100, 70, 20, FRAGILE, breakable=True),
            Tile(350, HEIGHT - 140, 70, 20, FRAGILE, breakable=True),
            Tile(520, HEIGHT - 110, 70, 20, FRAGILE, breakable=True),
            Tile(690, HEIGHT - 165, 70, 20, FRAGILE, breakable=True),
            Tile(860, HEIGHT - 125, 70, 20, FRAGILE, breakable=True),
            Tile(1030, HEIGHT - 175, 70, 20, FRAGILE, breakable=True),
            Tile(1200, HEIGHT - 135, 70, 20, FRAGILE, breakable=True),
            Tile(1380, HEIGHT - 155, 70, 20, FRAGILE, breakable=True),
            Tile(W - 62, 12, 50, HEIGHT - 52, FRAGILE, breakable=True),
        ]
        hazards = [ColaSpill(gx, HEIGHT - 40, gw, 40) for gx, gw in cola_gaps]
        enemies.append(DonutPatrol(1280, HEIGHT - 76, W - 80))
    elif n == 3:
        W = 2000
        title = "Уровень 3: Живой щит"
        hint = "R — щит от майонеза. Батут — наверх. Платформы над колой!"
        cola_gaps = [(280, 110), (620, 100), (960, 105), (1300, 95)]
        solids = floor_with_gaps(W, cola_gaps)
        hazards = [ColaSpill(gx, HEIGHT - 40, gw, 40) for gx, gw in cola_gaps]
        _tramp_before_gaps(trampolines, cola_gaps)
        _trampolines(trampolines, [(120, HEIGHT - 52, 80, 14)])
        _platforms(
            solids,
            [
                (300, HEIGHT - 175, 85, 20),
                (680, HEIGHT - 220, 80, 20),
                (1060, HEIGHT - 265, 85, 20),
                (1440, HEIGHT - 300, 80, 20),
                (1780, HEIGHT - 260, 85, 20),
            ],
        )
        turrets = [MayoTurret(520, HEIGHT - 120, 1), MayoTurret(980, HEIGHT - 120, 1), MayoTurret(1420, HEIGHT - 120, -1)]
        enemies.append(JumpingFries(1680, HEIGHT - 76))
    elif n == 4:
        W = 2200
        title = "Уровень 4: Обходной путь"
        hint = "Батут подбрасывает наверх. Сверху не пройти — найди рычаг и открой мост!"
        h = HEIGHT
        cola_gaps = [(220, 85), (520, 90), (1360, 110)]
        solids = floor_with_gaps(W, cola_gaps)
        hazards = [ColaSpill(gx, h - 40, gw, 40) for gx, gw in cola_gaps]
        _trampolines(trampolines, [(100, h - 52, 80, 14), (430, h - 52, 80, 14), (980, h - 52, 80, 14)])
        vent_block = Tile(820, h - 225, 110, 55, METAL)
        solids.append(vent_block)
        _platforms(
            solids,
            [
                (130, h - 175, 85, 20),
                (380, h - 220, 80, 20),
                (780, h - 265, 85, 20),
                (1180, h - 300, 80, 20),
                (1540, h - 270, 85, 20),
            ],
        )
        levers.append(Lever(1600, h - 350, "bridge"))
        doors["bridge"] = Tile(1480, h - 80, 110, 20, METAL)
        solids.append(doors["bridge"])
        turrets = [MayoTurret(980, h - 120, 1)]
        enemies.append(BurgerSpike(620, h - 76, 420, 1180))
        enemies.append(ExplosiveCola(760, h - 76, 520, 980))
    elif n == 5:
        W = 2200
        title = "Уровень 5: Спасение Лука"
        hint = "Пресс опускает клетку. Батут — на платформы. R — таран → E — Лук к цели."
        onion_caged = True
        onion = Player(1680, HEIGHT - 260, tomato=False)
        cage = Tile(1660, HEIGHT - 280, 60, 80, METAL)
        cola_gaps = [(880, 130), (1180, 110)]
        solids = floor_with_gaps(W, cola_gaps)
        hazards = [ColaSpill(gx, HEIGHT - 40, gw, 40) for gx, gw in cola_gaps]
        _trampolines(trampolines, [(650, HEIGHT - 52, 82, 14), (1280, HEIGHT - 52, 80, 14)])
        solids.append(cage)
        press = WeightButton(460, HEIGHT - 50, 90, 20, need_heavy=True)
        buttons.append(press)
        fragile.append(Tile(1660, HEIGHT - 280, 60, 20, FRAGILE, breakable=True))
        doors["rescue"] = Tile(1722, HEIGHT - 180, 20, 140, METAL)
        solids.append(doors["rescue"])
        _platforms(
            solids,
            [
                (660, HEIGHT - 165, 90, 20),
                (820, HEIGHT - 198, 85, 20),
                (980, HEIGHT - 228, 85, 20),
                (1140, HEIGHT - 252, 85, 20),
                (1300, HEIGHT - 272, 85, 20),
                (1480, HEIGHT - 288, 85, 20),
                (1640, HEIGHT - 298, 85, 20),
            ],
        )
        turrets = [MayoTurret(1000, HEIGHT - 120, 1)]
        enemies.append(JumpingFries(1480, HEIGHT - 76))
    elif n == 6:
        coop = True
        onion = Player(140, HEIGHT - 120, tomato=False)
        title = "Уровень 6: Первый бой вместе"
        hint = "E — смена. Батут — наверх. Оба должны добраться до цели!"
        cola_gaps = [(400, 100), (900, 110), (1400, 100)]
        solids = floor_with_gaps(W, cola_gaps)
        hazards = [ColaSpill(gx, HEIGHT - 40, gw, 40) for gx, gw in cola_gaps]
        _trampolines(trampolines, [(120, HEIGHT - 52, 80, 14), (780, HEIGHT - 52, 80, 14), (1280, HEIGHT - 52, 80, 14)])
        _platforms(
            solids,
            [
                (300, HEIGHT - 175, 85, 20),
                (720, HEIGHT - 220, 80, 20),
                (1100, HEIGHT - 265, 85, 20),
                (1480, HEIGHT - 300, 80, 20),
                (1820, HEIGHT - 260, 85, 20),
            ],
        )
        enemies.append(BurgerSpike(1180, HEIGHT - 76, 1120, 1380))
    elif n == 7:
        coop = True
        onion = Player(120, HEIGHT - 120, tomato=False)
        title = "Уровень 7: Узкий проход"
        hint = "Лук — вентиляция, Томат — батут и платформы. E — смена."
        cola_gaps = [(480, 100), (1120, 105)]
        solids = floor_with_gaps(W, cola_gaps)
        hazards = [ColaSpill(gx, HEIGHT - 40, gw, 40) for gx, gw in cola_gaps]
        _trampolines(trampolines, [(120, HEIGHT - 52, 80, 14), (980, HEIGHT - 52, 80, 14)])
        fragile.append(Tile(680, HEIGHT - 100, 50, 20, FRAGILE, breakable=True))
        vent_block = Tile(900, HEIGHT - 180, 90, 50, METAL)
        solids.append(vent_block)
        _platforms(
            solids,
            [
                (320, HEIGHT - 175, 85, 20),
                (760, HEIGHT - 220, 80, 20),
                (1120, HEIGHT - 265, 85, 20),
                (1560, HEIGHT - 230, 80, 20),
            ],
        )
        enemies.append(BurgerSpike(280, HEIGHT - 76, 200, 400))
        enemies.append(JumpingFries(1220, HEIGHT - 76))
    elif n == 8:
        coop = True
        onion = Player(120, HEIGHT - 120, tomato=False)
        title = "Уровень 8: Две кнопки"
        hint = "Батут — к кнопкам. Томат — тяжёлая, Лук — лёгкая."
        cola_gaps = [(260, 130), (720, 140)]
        solids = floor_with_gaps(W, cola_gaps)
        hazards = [ColaSpill(gx, HEIGHT - 40, gw, 40) for gx, gw in cola_gaps]
        _trampolines(trampolines, [(180, HEIGHT - 52, 80, 14), (620, HEIGHT - 52, 82, 14), (980, HEIGHT - 52, 80, 14)])
        _platforms(
            solids,
            [
                (720, HEIGHT - 175, 85, 20),
                (980, HEIGHT - 220, 80, 20),
                (1280, HEIGHT - 260, 85, 20),
                (1620, HEIGHT - 230, 80, 20),
            ],
        )
        buttons.append(WeightButton(480, HEIGHT - 50, 60, 20, need_heavy=True))
        buttons.append(WeightButton(620, HEIGHT - 50, 50, 20, need_heavy=False))
        doors["gate"] = Tile(920, HEIGHT - 140, 20, 100, METAL)
        solids.append(doors["gate"])
        enemies.append(JumpingFries(880, HEIGHT - 76))
        enemies.append(DonutPatrol(1040, HEIGHT - 76, 1500))
    elif n == 9:
        coop = True
        onion = Player(120, HEIGHT - 120, tomato=False)
        title = "Уровень 9: Стрела и рычаг"
        hint = "Батут — наверх. Стрела в рычаг (T), таран по стене (R)."
        cola_gaps = [(480, 95), (880, 100), (1320, 90)]
        solids = floor_with_gaps(W, cola_gaps)
        hazards = [ColaSpill(gx, HEIGHT - 40, gw, 40) for gx, gw in cola_gaps]
        _tramp_before_gaps(trampolines, cola_gaps)
        soft.append(Tile(720, HEIGHT - 260, 30, 120, soft=True))
        levers.append(Lever(780, HEIGHT - 300, "bridge"))
        doors["bridge"] = Tile(950, HEIGHT - 80, 100, 20, METAL)
        solids.append(doors["bridge"])
        fragile.append(Tile(520, HEIGHT - 100, 60, 20, FRAGILE, breakable=True))
        _platforms(
            solids,
            [
                (380, HEIGHT - 175, 85, 20),
                (760, HEIGHT - 220, 80, 20),
                (1100, HEIGHT - 265, 85, 20),
                (1480, HEIGHT - 240, 80, 20),
            ],
        )
        turrets = [MayoTurret(640, HEIGHT - 120, 1)]
        enemies.append(BurgerSpike(1180, HEIGHT - 76, 1185, 1650))
    elif n == 10:
        coop = True
        onion = Player(120, HEIGHT - 120, tomato=False)
        title = "Уровень 10: Мини-босс"
        hint = "Победите бургер-босса! R — щит, T — стрелы."
        boss = Boss("Бургер-Босс", 1300, HEIGHT - 160, 14, fire_interval=_boss_fire_interval(10))
        solids.append(Tile(900, HEIGHT - 160, 120, 20))
        solids.append(Tile(1100, HEIGHT - 220, 90, 20))
        enemies.append(JumpingFries(760, HEIGHT - 76))
        enemies.append(JumpingFries(1020, HEIGHT - 76))
    elif n == 11:
        coop = True
        onion = Player(120, HEIGHT - 120, tomato=False)
        title = "Уровень 11: Взрывная кола"
        hint = "Батут — наверх. Томат (R) прикрывает Лука от взрыва."
        cola_gaps = [(380, 90), (720, 100), (1060, 95), (1400, 90)]
        solids = floor_with_gaps(W, cola_gaps)
        hazards = [ColaSpill(gx, HEIGHT - 40, gw, 40) for gx, gw in cola_gaps]
        _tramp_before_gaps(trampolines, cola_gaps)
        _platforms(
            solids,
            [
                (340, HEIGHT - 175, 85, 20),
                (760, HEIGHT - 220, 80, 20),
                (1120, HEIGHT - 265, 85, 20),
                (1500, HEIGHT - 300, 80, 20),
                (1820, HEIGHT - 260, 85, 20),
            ],
        )
        enemies.append(ExplosiveCola(820, HEIGHT - 76))
        enemies.append(ExplosiveCola(1180, HEIGHT - 76, 980, 1500))
        turrets = [MayoTurret(540, HEIGHT - 120, 1)]
    elif n == 12:
        coop = True
        onion = Player(120, HEIGHT - 120, tomato=False)
        title = "Уровень 12: Пончик-патруль"
        hint = "Батут — наверх. Прыгайте на врагов сверху. Томат — таран."
        cola_gaps = [(320, 85), (680, 90), (1040, 85), (1400, 90)]
        solids = floor_with_gaps(W, cola_gaps)
        hazards = [ColaSpill(gx, HEIGHT - 40, gw, 40) for gx, gw in cola_gaps]
        _tramp_before_gaps(trampolines, cola_gaps)
        _trampolines(trampolines, [(120, HEIGHT - 52, 80, 14)])
        _platforms(
            solids,
            [
                (300, HEIGHT - 175, 85, 20),
                (720, HEIGHT - 220, 80, 20),
                (1100, HEIGHT - 265, 85, 20),
                (1480, HEIGHT - 300, 80, 20),
                (1820, HEIGHT - 260, 85, 20),
            ],
        )
        enemies.append(DonutPatrol(900, HEIGHT - 76, 1180))
        enemies.append(DonutPatrol(1320, HEIGHT - 76, 1680))
    elif n == 13:
        W = 1900
        coop, onion = _coop_pair()
        title = "Уровень 13: Канализация с колой"
        hint = "Батут — через пропасти. Внизу смертельная кола!"
        cola_gaps = [(320, 100), (680, 100), (1040, 100), (1400, 100)]
        solids = floor_with_gaps(W, cola_gaps)
        hazards = [ColaSpill(gx, HEIGHT - 40, gw, 40) for gx, gw in cola_gaps]
        _tramp_before_gaps(trampolines, cola_gaps)
        _trampolines(trampolines, [(120, HEIGHT - 52, 80, 14)])
        _platforms(
            solids,
            [
                (300, HEIGHT - 175, 85, 20),
                (720, HEIGHT - 220, 80, 20),
                (1100, HEIGHT - 265, 85, 20),
                (1480, HEIGHT - 240, 80, 20),
            ],
        )
        enemies.append(BurgerSpike(1050, HEIGHT - 76, 850, 1500))
    elif n == 14:
        coop, onion = _coop_pair()
        title = "Уровень 14: Перекрёстный обстрел"
        hint = "Батут — наверх. Томат (R) прикрывает, Лук проскакивает."
        cola_gaps = [(775, 130)]
        solids = floor_with_gaps(W, cola_gaps)
        hazards = [ColaSpill(gx, HEIGHT - 40, gw, 40) for gx, gw in cola_gaps]
        turrets = [
            MayoTurret(420, HEIGHT - 120, 1),
            MayoTurret(900, HEIGHT - 120, 1),
            MayoTurret(1280, HEIGHT - 120, -1),
        ]
        _trampolines(trampolines, [(120, HEIGHT - 52, 80, 14), (620, HEIGHT - 52, 80, 14), (1020, HEIGHT - 52, 80, 14)])
        _platforms(
            solids,
            [
                (280, HEIGHT - 175, 85, 20),
                (620, HEIGHT - 230, 80, 20),
                (980, HEIGHT - 280, 85, 20),
                (1340, HEIGHT - 240, 80, 20),
                (1680, HEIGHT - 200, 85, 20),
            ],
        )
        enemies.append(JumpingFries(1680, HEIGHT - 76))
        enemies.append(JumpingFries(320, HEIGHT - 76))
    elif n == 15:
        coop, onion = _coop_pair()
        title = "Уровень 15: Чизбургер"
        hint = "Мини-босс! Томат — щит и таран, Лук — стрелы (T)."
        boss = _boss_arena(solids, doors, 1320, "Чизбургер", 16, fire_interval=_boss_fire_interval(15))
        enemies.append(JumpingFries(980, HEIGHT - 76))
        enemies.append(JumpingFries(1160, HEIGHT - 76))
    elif n == 16:
        W = 1750
        coop, onion = _coop_pair()
        title = "Уровень 16: Хрупкий мост"
        hint = "Хрупкие плиты — не стойте, бегите! Мост и платформы рушатся."
        solids = floor_with_gaps(W, [(460, 620)])
        hazards = [ColaSpill(460, HEIGHT - 40, 620, 40)]
        for fx in range(480, 1060, 50):
            fragile.append(Tile(fx, HEIGHT - 100, 45, 20, FRAGILE, breakable=True))
        fragile.append(Tile(380, HEIGHT - 180, 80, 20, FRAGILE, breakable=True))
        fragile.append(Tile(1120, HEIGHT - 180, 80, 20, FRAGILE, breakable=True))
        enemies.append(BurgerSpike(720, HEIGHT - 76, 500, 980))
        enemies.append(DonutPatrol(900, HEIGHT - 76, 1200))
    elif n == 17:
        coop, onion = _coop_pair()
        title = "Уровень 17: Вентиляционный туннель"
        hint = "Лук — внизу, Томат — батут и платформы сверху."
        h = HEIGHT
        solids.append(Tile(580, h - 110, 28, 70, METAL))
        solids.append(Tile(642, h - 110, 28, 70, METAL))
        solids.append(Tile(870, h - 110, 28, 70, METAL))
        solids.append(Tile(932, h - 110, 28, 70, METAL))
        vent_block = Tile(710, h - 225, 90, 55, METAL)
        solids.append(vent_block)
        solids.append(Tile(1010, h - 225, 90, 55, METAL))
        _trampolines(trampolines, [(120, h - 52, 80, 14), (520, h - 52, 80, 14), (1100, h - 52, 80, 14)])
        _platforms(
            solids,
            [
                (320, h - 175, 85, 20),
                (720, h - 230, 80, 20),
                (1080, h - 275, 85, 20),
                (1420, h - 240, 80, 20),
                (1720, h - 200, 85, 20),
            ],
        )
        enemies.append(BurgerSpike(1280, h - 76, 1180, 1580))
        enemies.append(JumpingFries(980, h - 76))
        enemies.append(BurgerSpike(620, h - 76, 500, 900))
    elif n == 18:
        coop, onion = _coop_pair()
        title = "Уровень 18: Секретные ворота"
        hint = "Батут — наверх. Оба героя — на кнопки одновременно!"
        cola_gaps = [(280, 120), (880, 100)]
        solids = floor_with_gaps(W, cola_gaps)
        hazards = [ColaSpill(gx, HEIGHT - 40, gw, 40) for gx, gw in cola_gaps]
        buttons.append(WeightButton(460, HEIGHT - 50, 70, 20, need_heavy=True))
        buttons.append(WeightButton(640, HEIGHT - 50, 55, 20, need_heavy=False))
        _door(solids, doors, "gate", 1080, HEIGHT - 150, 20, 110)
        _trampolines(trampolines, [(980, HEIGHT - 52, 80, 14), (1380, HEIGHT - 52, 80, 14)])
        _platforms(
            solids,
            [
                (980, HEIGHT - 175, 85, 20),
                (1280, HEIGHT - 220, 80, 20),
                (1620, HEIGHT - 260, 85, 20),
            ],
        )
        enemies.append(DonutPatrol(1180, HEIGHT - 76, 1520))
        enemies.append(JumpingFries(980, HEIGHT - 76))
    elif n == 19:
        coop, onion = _coop_pair()
        title = "Уровень 19: Картофельная крепость"
        hint = "Батут — наверх. Таран (R) по стене, Лук прикрывает стрелами."
        cola_gaps = [(560, 105), (860, 100)]
        solids = floor_with_gaps(W, cola_gaps)
        hazards = [ColaSpill(gx, HEIGHT - 40, gw, 40) for gx, gw in cola_gaps]
        fragile.append(Tile(720, HEIGHT - 160, 45, 160, FRAGILE, breakable=True))
        soft.append(Tile(980, HEIGHT - 280, 35, 200, soft=True))
        levers.append(Lever(1040, HEIGHT - 320, "bridge"))
        _door(solids, doors, "bridge", 1180, HEIGHT - 90, 110, 20)
        _tramp_before_gaps(trampolines, cola_gaps)
        _platforms(
            solids,
            [
                (420, HEIGHT - 175, 85, 20),
                (780, HEIGHT - 220, 80, 20),
                (1040, HEIGHT - 265, 85, 20),
                (1320, HEIGHT - 230, 80, 20),
            ],
        )
        turrets = [MayoTurret(600, HEIGHT - 120, 1), MayoTurret(1120, HEIGHT - 120, -1)]
        enemies.append(BurgerSpike(980, HEIGHT - 76, 980, 1160))
    elif n == 20:
        coop, onion = _coop_pair()
        title = "Уровень 20: Король фри"
        hint = "Мини-босс! Прыгайте на врага с платформ, стрелы в спину."
        boss = _boss_arena(solids, doors, 1340, "Король фри", 18, fire_interval=_boss_fire_interval(20))
        enemies.append(JumpingFries(900, HEIGHT - 76))
        enemies.append(JumpingFries(1120, HEIGHT - 76))
        enemies.append(JumpingFries(760, HEIGHT - 76))
    elif n == 21:
        coop, onion = _coop_pair()
        title = "Уровень 21: Пончиковая горка"
        hint = "Батут — наверх над колой. Томат — таран!"
        cola_gaps = [(300, 1320)]
        solids = floor_with_gaps(W, cola_gaps)
        hazards = [ColaSpill(300, HEIGHT - 40, 1320, 40)]
        _trampolines(trampolines, [(180, HEIGHT - 52, 80, 14), (720, HEIGHT - 52, 80, 14), (1260, HEIGHT - 52, 80, 14), (1700, HEIGHT - 52, 80, 14)])
        _platforms(
            solids,
            [
                (300, HEIGHT - 165, 85, 20),
                (540, HEIGHT - 200, 85, 20),
                (780, HEIGHT - 235, 85, 20),
                (1020, HEIGHT - 265, 85, 20),
                (1260, HEIGHT - 255, 85, 20),
                (1500, HEIGHT - 225, 85, 20),
                (1740, HEIGHT - 195, 85, 20),
            ],
        )
        enemies.append(DonutPatrol(180, HEIGHT - 76, 280))
        enemies.append(DonutPatrol(1680, HEIGHT - 76, 1900))
        enemies.append(JumpingFries(1420, HEIGHT - 76))
        enemies.append(JumpingFries(1780, HEIGHT - 76))
    elif n == 22:
        coop, onion = _coop_pair()
        title = "Уровень 22: Минное поле"
        hint = "Батут — наверх. Томат (R) прикрывает Лука от взрыва."
        cola_gaps = [(380, 85), (720, 90), (1060, 85), (1400, 90)]
        solids = floor_with_gaps(W, cola_gaps)
        hazards = [ColaSpill(gx, HEIGHT - 40, gw, 40) for gx, gw in cola_gaps]
        _tramp_before_gaps(trampolines, cola_gaps)
        _platforms(
            solids,
            [
                (340, HEIGHT - 175, 85, 20),
                (760, HEIGHT - 220, 80, 20),
                (1120, HEIGHT - 265, 85, 20),
                (1500, HEIGHT - 300, 80, 20),
                (1820, HEIGHT - 260, 85, 20),
            ],
        )
        enemies.append(ExplosiveCola(620, HEIGHT - 76, 470, 700))
        enemies.append(ExplosiveCola(1000, HEIGHT - 76, 960, 1140))
        enemies.append(ExplosiveCola(1520, HEIGHT - 76, 1490, 1680))
        turrets = [MayoTurret(980, HEIGHT - 120, 1)]
    elif n == 23:
        coop, onion = _coop_pair()
        title = "Уровень 23: Башня лука"
        hint = "Батут — наверх. Стрелы (T) в мягкую стену, поднимайтесь."
        cola_gaps = [(380, 100), (720, 95)]
        solids = floor_with_gaps(W, cola_gaps)
        hazards = [ColaSpill(gx, HEIGHT - 40, gw, 40) for gx, gw in cola_gaps]
        soft.append(Tile(860, HEIGHT - 360, 40, 300, soft=True))
        _tramp_before_gaps(trampolines, cola_gaps)
        _platforms(
            solids,
            [
                (420, HEIGHT - 175, 85, 20),
                (680, HEIGHT - 230, 80, 20),
                (900, HEIGHT - 280, 85, 20),
                (1180, HEIGHT - 240, 80, 20),
            ],
        )
        levers.append(Lever(1180, HEIGHT - 240, "exit"))
        _door(solids, doors, "exit", 1380, HEIGHT - 140, 20, 100)
        turrets = [MayoTurret(720, HEIGHT - 120, 1), MayoTurret(980, HEIGHT - 120, -1)]
        enemies.append(JumpingFries(1320, HEIGHT - 76))
    elif n == 24:
        coop, onion = _coop_pair()
        title = "Уровень 24: Двойной рычаг"
        hint = "Батут — наверх. Два рычага — два пути."
        cola_gaps = [(560, 90), (980, 95), (1440, 85)]
        solids = floor_with_gaps(W, cola_gaps)
        hazards = [ColaSpill(gx, HEIGHT - 40, gw, 40) for gx, gw in cola_gaps]
        levers.append(Lever(480, HEIGHT - 300, "door_a"))
        levers.append(Lever(1080, HEIGHT - 280, "door_b"))
        _door(solids, doors, "door_a", 660, HEIGHT - 130, 20, 90)
        _door(solids, doors, "door_b", 1260, HEIGHT - 110, 110, 20)
        fragile.append(Tile(820, HEIGHT - 100, 55, 20, FRAGILE, breakable=True))
        _tramp_before_gaps(trampolines, cola_gaps)
        _platforms(
            solids,
            [
                (420, HEIGHT - 175, 85, 20),
                (780, HEIGHT - 230, 80, 20),
                (1140, HEIGHT - 275, 85, 20),
                (1500, HEIGHT - 240, 80, 20),
            ],
        )
        enemies.append(BurgerSpike(1185, HEIGHT - 76, 1185, 1420))
        enemies.append(JumpingFries(1680, HEIGHT - 76))
        turrets = [MayoTurret(1180, HEIGHT - 120, -1)]
    elif n == 25:
        coop, onion = _coop_pair()
        title = "Уровень 25: Майонезный исполин"
        hint = "Мини-босс и турели! Щит + стрелы — единственный путь."
        boss = _boss_arena(solids, doors, 1360, "Майонезный исполин", 20, fire_interval=_boss_fire_interval(25))
        turrets = [
            MayoTurret(980, HEIGHT - 120, 1),
            MayoTurret(1180, HEIGHT - 120, -1),
            MayoTurret(760, HEIGHT - 120, 1),
        ]
        enemies.append(JumpingFries(880, HEIGHT - 76))
    elif n == 26:
        W = 2300
        coop, onion = _coop_pair()
        title = "Уровень 26: Великие пропасти"
        hint = "Батут — через пропасти. E — смена, оба до цели!"
        cola_gaps = [(340, 100), (720, 100), (1100, 100), (1480, 100), (1860, 100)]
        solids = floor_with_gaps(W, cola_gaps)
        hazards = [ColaSpill(gx, HEIGHT - 40, gw, 40) for gx, gw in cola_gaps]
        _trampolines(trampolines, [(120, HEIGHT - 52, 80, 14), (648, HEIGHT - 52, 80, 14)])
        _platforms(
            solids,
            [
                (300, HEIGHT - 175, 85, 20),
                (720, HEIGHT - 220, 80, 20),
                (1100, HEIGHT - 265, 85, 20),
                (1480, HEIGHT - 300, 80, 20),
                (1860, HEIGHT - 260, 85, 20),
            ],
        )
        enemies.append(JumpingFries(620, HEIGHT - 76))
        enemies.append(JumpingFries(1180, HEIGHT - 76))
    elif n == 27:
        W = 2200
        coop, onion = _coop_pair()
        title = "Уровень 27: Бургерный коридор"
        hint = "Батут — наверх над колой. E — оба до цели!"
        cola_gaps = [(240, 1720)]
        solids = floor_with_gaps(W, cola_gaps)
        hazards = [ColaSpill(gx, HEIGHT - 40, gw, 40) for gx, gw in cola_gaps]
        _trampolines(trampolines, [(160, HEIGHT - 52, 80, 14), (720, HEIGHT - 52, 80, 14), (1320, HEIGHT - 52, 80, 14), (1880, HEIGHT - 52, 80, 14)])
        _platforms(
            solids,
            [
                (320, HEIGHT - 175, 85, 20),
                (720, HEIGHT - 220, 80, 20),
                (1120, HEIGHT - 265, 85, 20),
                (1520, HEIGHT - 300, 80, 20),
                (1920, HEIGHT - 260, 85, 20),
            ],
        )
        enemies.append(BurgerSpike(620, HEIGHT - 76, 520, 760))
        enemies.append(BurgerSpike(1180, HEIGHT - 76, 1080, 1320))
        enemies.append(BurgerSpike(1680, HEIGHT - 76, 1580, 1820))
        enemies.append(JumpingFries(1960, HEIGHT - 76))
    elif n == 28:
        coop, onion = _coop_pair()
        title = "Уровень 28: Смешанный штурм"
        hint = "Батут — наверх. Меняйтесь (E) и используйте суперспособности."
        cola_gaps = [(420, 110), (860, 115), (1300, 100)]
        solids = floor_with_gaps(W, cola_gaps)
        hazards = [ColaSpill(gx, HEIGHT - 40, gw, 40) for gx, gw in cola_gaps]
        _tramp_before_gaps(trampolines, cola_gaps)
        _trampolines(trampolines, [(120, HEIGHT - 52, 80, 14)])
        _platforms(
            solids,
            [
                (320, HEIGHT - 175, 85, 20),
                (760, HEIGHT - 220, 80, 20),
                (1120, HEIGHT - 265, 85, 20),
                (1480, HEIGHT - 300, 80, 20),
                (1820, HEIGHT - 260, 85, 20),
            ],
        )
        enemies.append(BurgerSpike(1185, HEIGHT - 76, 1185, 1420))
        enemies.append(JumpingFries(1680, HEIGHT - 76))
        enemies.append(ExplosiveCola(1520, HEIGHT - 76, 1490, 1750))
        enemies.append(DonutPatrol(180, HEIGHT - 76, 400))
        turrets = [MayoTurret(750, HEIGHT - 120, 1), MayoTurret(1200, HEIGHT - 120, -1)]
    elif n == 29:
        coop, onion = _coop_pair()
        title = "Уровень 29: Предфинальный рубеж"
        hint = "Батут — к воротам. Кнопки, турели и враги — всё сразу!"
        cola_gaps = [(760, 110), (1180, 115), (1620, 100)]
        solids = floor_with_gaps(W, cola_gaps)
        hazards = [ColaSpill(gx, HEIGHT - 40, gw, 40) for gx, gw in cola_gaps]
        buttons.append(WeightButton(500, HEIGHT - 50, 70, 20, need_heavy=True))
        buttons.append(WeightButton(680, HEIGHT - 50, 55, 20, need_heavy=False))
        _door(solids, doors, "gate", 980, HEIGHT - 160, 20, 120)
        turrets = [MayoTurret(1100, HEIGHT - 120, 1), MayoTurret(1480, HEIGHT - 120, -1)]
        _trampolines(trampolines, [(980, HEIGHT - 52, 80, 14), (1380, HEIGHT - 52, 80, 14), (1680, HEIGHT - 52, 80, 14)])
        _platforms(
            solids,
            [
                (980, HEIGHT - 175, 85, 20),
                (1280, HEIGHT - 220, 80, 20),
                (1580, HEIGHT - 265, 85, 20),
                (1820, HEIGHT - 230, 80, 20),
            ],
        )
        enemies.append(ExplosiveCola(1380, HEIGHT - 76, 1200, 1700))
        enemies.append(BurgerSpike(1680, HEIGHT - 76, 1580, 1900))
        enemies.append(JumpingFries(1960, HEIGHT - 76))
        fragile.append(Tile(1820, HEIGHT - 100, 50, 20, FRAGILE, breakable=True))
    elif n == 30:
        coop, onion = _coop_pair()
        boss = Boss(
            "Суперзлодей: Вредная Еда",
            W - 420,
            HEIGHT - 180,
            30,
            fire_interval=_boss_fire_interval(30),
        )
        title = "Уровень 30: Финал"
        hint = "Победите главного босса вместе!"
        _platforms(
            solids,
            [
                (W - 720, HEIGHT - 200, 120, 20),
                (W - 560, HEIGHT - 260, 90, 20),
                (W - 480, HEIGHT - 320, 80, 20),
            ],
        )
        turrets = [MayoTurret(W - 860, HEIGHT - 120, 1), MayoTurret(W - 640, HEIGHT - 120, -1)]
        enemies.append(ExplosiveCola(W - 980, HEIGHT - 76, W - 1100, W - 560))
        enemies.append(JumpingFries(W - 780, HEIGHT - 76))
        enemies.append(JumpingFries(W - 620, HEIGHT - 76))

    _scale_late_enemies(n, enemies)
    _space_enemies(enemies)
    _tighten_platforms(n, solids)

    goal = goal_at_end(W)

    return {
        "num": n,
        "title": title,
        "hint": hint,
        "solids": solids,
        "fragile": fragile,
        "soft": soft,
        "buttons": buttons,
        "levers": levers,
        "doors": doors,
        "turrets": turrets,
        "enemies": enemies,
        "hazards": hazards,
        "trampolines": trampolines,
        "boss": boss,
        "goal": goal,
        "tomato": tomato,
        "onion": onion,
        "coop": coop,
        "onion_caged": onion_caged,
        "cage": cage,
        "press": press,
        "vent_block": vent_block,
        "world_w": W,
    }


LEVEL_TITLES = {
    1: "Первые шаги",
    2: "Сила тарана",
    3: "Живой щит",
    4: "Обходной путь",
    5: "Спасение Лука",
    6: "Первый бой вместе",
    7: "Узкий проход",
    8: "Две кнопки",
    9: "Стрела и рычаг",
    10: "Мини-босс",
    11: "Взрывная кола",
    12: "Пончик-патруль",
    13: "Канализация с колой",
    14: "Перекрёстный обстрел",
    15: "Чизбургер",
    16: "Хрупкий мост",
    17: "Вентиляционный туннель",
    18: "Секретные ворота",
    19: "Картофельная крепость",
    20: "Король фри",
    21: "Пончиковая горка",
    22: "Минное поле",
    23: "Башня лука",
    24: "Двойной рычаг",
    25: "Майонезный исполин",
    26: "Великие пропасти",
    27: "Бургерный коридор",
    28: "Смешанный штурм",
    29: "Предфинальный рубеж",
    30: "Финал — Суперзлодей",
}

LEVEL_INFO = []
for n in range(1, LEVELS_TOTAL + 1):
    title = LEVEL_TITLES.get(n, "Совместный штурм" if n > 5 else f"Уровень {n}")
    LEVEL_INFO.append(
        {
            "num": n,
            "title": title,
            "boss": n in (10, 15, 20, 25, 30),
            "solo": n <= 5,
        }
    )
