"""Загрузка пиксельных SVG-спрайтов (только rect + transform)."""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pygame


def _parse_color(value):
    value = (value or "#ffffff").strip()
    if value.startswith("#"):
        h = value[1:]
        if len(h) == 3:
            h = "".join(ch * 2 for ch in h)
        return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))
    return (255, 255, 255)


def _parse_transform(text):
    if not text:
        return [(1, 0, 0, 1, 0, 0)]
    transforms = []
    for kind, body in re.findall(r"(translate|matrix)\(([^)]+)\)", text):
        nums = [float(n) for n in re.findall(r"[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?", body)]
        if kind == "translate":
            tx = nums[0]
            ty = nums[1] if len(nums) > 1 else 0.0
            transforms.append((1, 0, 0, 1, tx, ty))
        elif len(nums) >= 6:
            transforms.append(tuple(nums[:6]))
    return transforms or [(1, 0, 0, 1, 0, 0)]


def _apply_transform(x, y, transforms):
    for a, b, c, d, e, f in transforms:
        x, y = a * x + c * y + e, b * x + d * y + f
    return x, y


def _rect_points(x, y, w, h, transforms):
    corners = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    return [_apply_transform(px, py, transforms) for px, py in corners]


def scale_nearest(surf, size):
    src = surf
    dst_w, dst_h = size

    while True:
        src_w, src_h = src.get_size()
        if src_w <= dst_w * 2 or src_h <= dst_h * 2:
            break
        nw, nh = src_w // 2, src_h // 2
        half = pygame.Surface((nw, nh), pygame.SRCALPHA)
        for y in range(nh):
            sy = y * 2
            for x in range(nw):
                half.set_at((x, y), src.get_at((x * 2, sy)))
        src = half

    src_w, src_h = src.get_size()
    if (src_w, src_h) == (dst_w, dst_h):
        return src
    dst = pygame.Surface(size, pygame.SRCALPHA)
    for y in range(dst_h):
        sy = y * src_h // dst_h
        for x in range(dst_w):
            sx = x * src_w // dst_w
            dst.set_at((x, y), src.get_at((sx, sy)))
    return dst


def load_svg_sprite(path, size=None):
    root = ET.parse(path).getroot()
    width = float(re.sub(r"[^\d.]", "", root.get("width", "64")) or 64)
    height = float(re.sub(r"[^\d.]", "", root.get("height", "64")) or 64)
    surf = pygame.Surface((int(width), int(height)), pygame.SRCALPHA)

    for elem in root.iter():
        if not elem.tag.endswith("rect"):
            continue
        fill = elem.get("fill")
        if not fill or fill == "none":
            continue
        x = float(elem.get("x", 0))
        y = float(elem.get("y", 0))
        w = float(elem.get("width", 0))
        h = float(elem.get("height", 0))
        if w <= 0 or h <= 0:
            continue
        transforms = _parse_transform(elem.get("transform"))
        points = [
            (int(round(px)), int(round(py)))
            for px, py in _rect_points(x, y, w, h, transforms)
        ]
        pygame.draw.polygon(surf, _parse_color(fill), points)

    if size:
        surf = scale_nearest(surf, size)
    return surf
