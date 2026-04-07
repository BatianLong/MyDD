"""
PerlerCraft palette data.

Unified bead color schema:
- id: unified bead code (int)
- name: color display name (zh-CN)
- hex: color hex value
- rgb: RGB tuple
- category: 实色 / 珠光 / 果冻 / 细闪 / 银光 / 追光 / 温变
"""

from collections import Counter

CATEGORY_SOLID = "实色"
CATEGORY_PEARL = "珠光"
CATEGORY_JELLY = "果冻"
CATEGORY_GLITTER = "细闪"
CATEGORY_METALLIC = "银光"
CATEGORY_GLOW = "追光"
CATEGORY_THERMO = "温变"

CATEGORIES = [
    CATEGORY_SOLID,
    CATEGORY_PEARL,
    CATEGORY_JELLY,
    CATEGORY_GLITTER,
    CATEGORY_METALLIC,
    CATEGORY_GLOW,
    CATEGORY_THERMO,
]


def _c(color_id, name, hex_color, rgb, category=CATEGORY_SOLID):
    return {
        "id": int(color_id),
        "name": str(name),
        "hex": str(hex_color).upper(),
        "rgb": [int(rgb[0]), int(rgb[1]), int(rgb[2])],
        "category": category,
    }


# Current project palette (50 colors) mapped into unified schema.
# Note: this is a base subset and can be expanded to a full 221-color library later.
CLASSIC_PALETTE = [
    _c(0, "白色", "#FFFFFF", (255, 255, 255)),
    _c(1, "黑色", "#1A1A1A", (26, 26, 26)),
    _c(2, "灰色", "#9E9E9E", (158, 158, 158)),
    _c(3, "浅灰", "#C0C0C0", (192, 192, 192)),
    _c(4, "深灰", "#696969", (105, 105, 105)),
    _c(5, "红色", "#E31C25", (227, 28, 37)),
    _c(6, "深红", "#8B0000", (139, 0, 0)),
    _c(7, "浅红", "#FF6B6B", (255, 107, 107)),
    _c(8, "橙红", "#FF4136", (255, 65, 54)),
    _c(9, "橙色", "#FF851B", (255, 133, 27)),
    _c(10, "杏色", "#FFDC00", (255, 220, 0)),
    _c(11, "黄色", "#FFEB3B", (255, 235, 59)),
    _c(12, "柠檬黄", "#FFF700", (255, 247, 0)),
    _c(13, "金黄", "#FFD700", (255, 215, 0)),
    _c(14, "棕色", "#8B4513", (139, 69, 19)),
    _c(15, "浅棕", "#CD853F", (205, 133, 63)),
    _c(16, "深棕", "#5D4037", (93, 64, 55)),
    _c(17, "驼色", "#D2B48C", (210, 180, 140)),
    _c(18, "绿色", "#00A86B", (0, 168, 107)),
    _c(19, "深绿", "#228B22", (34, 139, 34)),
    _c(20, "浅绿", "#90EE90", (144, 238, 144)),
    _c(21, "军绿", "#556B2F", (85, 107, 47)),
    _c(22, "薄荷绿", "#98FF98", (152, 255, 152)),
    _c(23, "青色", "#008B8B", (0, 139, 139)),
    _c(24, "蓝色", "#0077BE", (0, 119, 190)),
    _c(25, "深蓝", "#0047AB", (0, 71, 171)),
    _c(26, "浅蓝", "#87CEEB", (135, 206, 235)),
    _c(27, "天蓝", "#00BFFF", (0, 191, 255)),
    _c(28, "藏蓝", "#1F456E", (31, 69, 110)),
    _c(29, "宝蓝", "#4169E1", (65, 105, 225)),
    _c(30, "紫色", "#8F00FF", (143, 0, 255)),
    _c(31, "深紫", "#6A0DAD", (106, 13, 173)),
    _c(32, "浅紫", "#E6E6FA", (230, 230, 250)),
    _c(33, "紫罗兰", "#EE82EE", (238, 130, 238)),
    _c(34, "粉色", "#FF69B4", (255, 105, 180)),
    _c(35, "浅粉", "#FFB6C1", (255, 182, 193)),
    _c(36, "深粉", "#FF1493", (255, 20, 147)),
    _c(37, "桃色", "#FFCBA4", (255, 203, 164)),
    _c(38, "肤色", "#FFDCB9", (255, 220, 185)),
    _c(39, "酒红", "#722F37", (114, 47, 55)),
    _c(40, "玫瑰金", "#B76E79", (183, 110, 121), CATEGORY_METALLIC),
    _c(41, "珊瑚色", "#FF7F50", (255, 127, 80)),
    _c(42, "海蓝", "#40E0D0", (64, 224, 208)),
    _c(43, "墨绿", "#355E3B", (53, 94, 59)),
    _c(44, "荧光绿", "#39FF14", (57, 255, 20), CATEGORY_GLOW),
    _c(45, "粉绿", "#77DD77", (119, 221, 119)),
    _c(46, "雾霾蓝", "#9DB4C0", (157, 180, 192), CATEGORY_PEARL),
    _c(47, "香芋紫", "#DA8FDC", (218, 143, 220), CATEGORY_PEARL),
    _c(48, "奶茶色", "#C8A47A", (200, 164, 122)),
    _c(49, "烟灰粉", "#E0B0B0", (224, 176, 176), CATEGORY_JELLY),
]


def get_palette(name="classic", category=None):
    palette = CLASSIC_PALETTE
    if category:
      palette = [c for c in palette if c.get("category") == category]
    return palette


def get_palette_dict():
    return {c["id"]: c for c in CLASSIC_PALETTE}


def get_palette_meta():
    counts = Counter(c.get("category", CATEGORY_SOLID) for c in CLASSIC_PALETTE)
    return {
        "total": len(CLASSIC_PALETTE),
        "categories": CATEGORIES,
        "category_counts": dict(counts),
    }
