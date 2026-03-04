from __future__ import annotations

import hashlib


_TARGET_COLORS = (
    '#4E79A7',
    '#F28E2B',
    '#E15759',
    '#76B7B2',
    '#59A14F',
    '#EDC948',
    '#B07AA1',
    '#FF9DA7',
    '#9C755F',
    '#BAB0AC',
    '#1F77B4',
    '#FF7F0E',
    '#2CA02C',
    '#D62728',
    '#9467BD',
    '#8C564B',
    '#E377C2',
    '#7F7F7F',
    '#BCBD22',
    '#17BECF',
)


def target_color_hex(target_id: str | None) -> str:
    """Return deterministic high-contrast color for a target ID."""
    if not target_id:
        return _TARGET_COLORS[0]

    digest = hashlib.sha256(target_id.encode('utf-8')).digest()
    index = int.from_bytes(digest[:2], byteorder='big') % len(_TARGET_COLORS)
    return _TARGET_COLORS[index]


def target_text_color_hex(background_hex: str) -> str:
    """Return black/white text color for readable contrast on background."""
    bg = background_hex.lstrip('#')
    red = int(bg[0:2], 16)
    green = int(bg[2:4], 16)
    blue = int(bg[4:6], 16)
    luma = (0.299 * red) + (0.587 * green) + (0.114 * blue)
    return '#000000' if luma >= 160 else '#FFFFFF'
