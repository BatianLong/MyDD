"""
PerlerCraft palette data.

Unified bead color schema:
- id: internal numeric index used by pixel matrix
- beadId/code: standard MARD bead code (for display)
- name: color display name
- hex/rgb: color values
- category: color category
"""

import csv
from collections import Counter
from pathlib import Path

CATEGORY_SOLID = "实色"
CATEGORIES = [CATEGORY_SOLID]

_PALETTE_FILE = Path(__file__).with_name("mard_221.csv")


def _hex_to_rgb(hex_color):
    value = str(hex_color).strip().upper()
    if not value.startswith("#") or len(value) != 7:
        return [255, 255, 255]
    return [int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16)]


def _load_mard_solid_palette():
    palette = []
    if not _PALETTE_FILE.exists():
        return palette

    with _PALETTE_FILE.open("r", encoding="utf-8-sig", newline="") as fp:
        reader = csv.DictReader(fp)
        for index, row in enumerate(reader):
            bead_id = str(row.get("code", "")).strip().upper()
            hex_color = str(row.get("hex", "")).strip().upper()
            if not bead_id or not hex_color:
                continue

            palette.append({
                "id": index,
                "beadId": bead_id,
                "code": bead_id,
                "name": f"MARD {bead_id}",
                "hex": hex_color,
                "rgb": _hex_to_rgb(hex_color),
                "category": CATEGORY_SOLID,
            })
    return palette


CLASSIC_PALETTE = _load_mard_solid_palette()
IS_FALLBACK_PALETTE = False


def _build_builtin_fallback_palette():
    # 部署包丢失 csv 时的安全兜底色板：
    # 至少保证不是“全白单色”，避免整条链路退化不可用。
    fallback_hex = [
        "#FFFFFF", "#111111", "#F2F2F2", "#808080",
        "#E74C3C", "#FF7F50", "#F39C12", "#F1C40F",
        "#2ECC71", "#27AE60", "#1ABC9C", "#16A085",
        "#3498DB", "#2980B9", "#6C5CE7", "#8E44AD",
        "#FF69B4", "#E84393", "#A0522D", "#C39A6B",
        "#00BCD4", "#7FDBFF", "#B8E986", "#FFD166",
    ]
    palette = []
    for idx, hex_color in enumerate(fallback_hex):
        bead = f"FB{idx + 1:02d}"
        palette.append({
            "id": idx,
            "beadId": bead,
            "code": bead,
            "name": f"Fallback {bead}",
            "hex": hex_color,
            "rgb": _hex_to_rgb(hex_color),
            "category": CATEGORY_SOLID,
        })
    return palette


if not CLASSIC_PALETTE or len(CLASSIC_PALETTE) < 8:
    CLASSIC_PALETTE = _build_builtin_fallback_palette()
    IS_FALLBACK_PALETTE = True


def get_palette(name="classic", category=None):
    del name  # reserved for future multi-palette support
    palette = CLASSIC_PALETTE
    if category:
        palette = [c for c in palette if c.get("category") == category]
    return palette


def get_palette_dict():
    return {c["id"]: c for c in CLASSIC_PALETTE}


def get_palette_meta():
    counts = Counter(c.get("category", CATEGORY_SOLID) for c in CLASSIC_PALETTE)
    return {
        "standard": "MARD",
        "fallback": IS_FALLBACK_PALETTE,
        "total": len(CLASSIC_PALETTE),
        "categories": CATEGORIES,
        "category_counts": dict(counts),
    }
