"""Проверка уровней перед релизом."""

from constants import HEIGHT, LEVELS_TOTAL, WIDTH
from levels import LEVEL_INFO, build_level


def check_level(n):
    data = build_level(n)
    issues = []
    world_w = data["world_w"]

    required = (
        "title",
        "hint",
        "solids",
        "goal",
        "tomato",
        "enemies",
        "world_w",
    )
    for key in required:
        if key not in data:
            issues.append(f"нет поля: {key}")

    if data["tomato"].rect.right > world_w:
        issues.append("томат за пределами карты")
    if data["tomato"].rect.bottom > HEIGHT:
        issues.append("томат ниже пола")

    goal = data["goal"]
    if goal.rect.right > world_w - 12:
        issues.append("цель за краем мира")
    if goal.rect.bottom > HEIGHT:
        issues.append("цель ниже пола")

    if data["onion"] and data["onion"].rect.right > world_w:
        issues.append("лук за пределами карты")

    if data["boss"] and not data["boss"].alive:
        issues.append("босс мёртв на старте")

    for i, enemy in enumerate(data["enemies"]):
        if not enemy.alive:
            issues.append(f"враг {i} мёртв на старте")
        if enemy.rect.bottom > HEIGHT + 4:
            issues.append(f"враг {i} ниже пола")
        x_min = getattr(enemy, "x_min", None)
        x_max = getattr(enemy, "x_max", None)
        if x_min is not None and x_max is not None and x_min >= x_max:
            issues.append(f"враг {i}: кривой патруль ({x_min}..{x_max})")
        x1 = getattr(enemy, "x1", None)
        x2 = getattr(enemy, "x2", None)
        if x1 is not None and x2 is not None and x1 >= x2:
            issues.append(f"враг {i}: кривой патруль пончика ({x1}..{x2})")

    info = next(x for x in LEVEL_INFO if x["num"] == n)
    if info["boss"] and not data["boss"]:
        issues.append("босс должен быть, но его нет")
    if info["solo"] and data["coop"]:
        issues.append("solo-уровень помечен как coop")

    return data, issues


def main():
    failed = []
    summary = []
    for n in range(1, LEVELS_TOTAL + 1):
        try:
            data, issues = check_level(n)
        except Exception as exc:
            failed.append((n, [f"ошибка сборки: {exc}"]))
            continue
        if issues:
            failed.append((n, issues))
        summary.append(
            (
                n,
                data["title"],
                len(data["enemies"]),
                data["boss"].name if data["boss"] else "-",
                data["world_w"],
            )
        )

    print(f"Проверено уровней: {LEVELS_TOTAL}\n")
    for n, title, enemies, boss, world_w in summary:
        mark = "OK" if not any(f[0] == n for f in failed) else "FAIL"
        print(f"[{mark}] {n:2d} | враги={enemies:2d} | босс={boss:24s} | W={world_w} | {title}")

    if failed:
        print("\nПроблемы:")
        for n, issues in failed:
            print(f"  Уровень {n}:")
            for issue in issues:
                print(f"    - {issue}")
        raise SystemExit(1)

    print("\nВсе уровни прошли проверку.")


if __name__ == "__main__":
    main()
