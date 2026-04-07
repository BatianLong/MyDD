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
if not CLASSIC_PALETTE:
    CLASSIC_PALETTE = [
        {
            "id": 0,
            "beadId": "A1",
            "code": "A1",
            "name": "MARD A1",
            "hex": "#FFFFFF",
            "rgb": [255, 255, 255],
            "category": CATEGORY_SOLID,
        }
    ]


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
        "total": len(CLASSIC_PALETTE),
        "categories": CATEGORIES,
        "category_counts": dict(counts),
    }
