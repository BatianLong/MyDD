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

_PALETTE_FILES = [
    Path(__file__).with_name("mard_221.csv"),
    Path(__file__).with_name("mard_291.csv"),
]


def _hex_to_rgb(hex_color):
    value = str(hex_color).strip().upper()
    if not value.startswith("#") or len(value) != 7:
        return [255, 255, 255]
    return [int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16)]


def _load_mard_solid_palette():
    for file_path in _PALETTE_FILES:
        if not file_path.exists():
            continue

        palette = []
        with file_path.open("r", encoding="utf-8-sig", newline="") as fp:
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
        if len(palette) >= 8:
            return palette
    return []


CLASSIC_PALETTE = _load_mard_solid_palette()
IS_FALLBACK_PALETTE = False


def _build_builtin_fallback_palette():
    # 部署包丢失 csv 时的安全兜底色板：
    # 至少保证不是“全白单色”，且使用 MARD 标准代码子集（非 FB 前缀）。
    fallback_data = [
        ("A1", "#FAF4C8"), ("A2", "#FFFFD5"), ("A3", "#FEFF8B"), ("A4", "#FBED56"),
        ("A5", "#F4D738"), ("A6", "#FEAC4C"), ("A7", "#FE8B4C"), ("A8", "#FFDA45"),
        ("A9", "#FF995B"), ("A10", "#F77C31"), ("A11", "#FFDD99"), ("A12", "#FE9F72"),
        ("A13", "#FFC365"), ("A14", "#FD543D"), ("A15", "#FFF365"), ("A16", "#FFFF9F"),
        ("A17", "#FFE36E"), ("A18", "#FEBE7D"), ("A19", "#FD7C72"), ("A20", "#FFD568"),
        ("B1", "#FDECE3"), ("B2", "#FBE1D5"), ("B3", "#F9D4BD"), ("B4", "#F3B8A4"),
    ]
    palette = []
    for idx, item in enumerate(fallback_data):
        bead = item[0]
        hex_color = item[1]
        palette.append({
            "id": idx,
            "beadId": bead,
            "code": bead,
            "name": f"MARD {bead}",
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


def is_fallback_palette():
    """Whether the runtime palette is fallback data (not official MARD dataset)."""
    return IS_FALLBACK_PALETTE
