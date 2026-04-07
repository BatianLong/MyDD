"""
颜色量化模块

将图片中的颜色映射到拼豆色卡中最接近的颜色。
使用 LAB 色彩空间进行颜色距离计算，人眼对色彩差异的感知更准确。
"""

import numpy as np
from PIL import Image
from data.palette import get_palette, get_palette_dict


class ColorQuantizer:
    """
    颜色量化器
    
    将图片中的每个像素映射到拼豆色卡中最接近的颜色。
    使用 LAB 色彩空间进行颜色比较，比 RGB 空间更符合人眼感知。
    """
    
    def __init__(self, palette=None):
        """
        初始化颜色量化器
        
        Args:
            palette: 自定义色板，默认使用经典拼豆色卡
        """
        self.palette = palette or get_palette()
        # 将色卡的 RGB 值转换为 numpy 数组，便于计算
        self.palette_colors = np.array([c["rgb"] for c in self.palette])
        # 颜色 id 到颜色信息的字典映射
        self.palette_dict = get_palette_dict()
        # LAB 颜色缓存，避免重复计算
        self.lab_cache = {}
        # 预计算所有色卡颜色的 LAB 值
        self._precompute_lab()
    
    def _precompute_lab(self):
        """预计算所有色卡颜色的 LAB 值，避免重复计算"""
        for color in self.palette:
            rgb = color["rgb"]
            self.lab_cache[color["id"]] = self._rgb_to_lab(rgb)
    
    def _rgb_to_lab(self, rgb):
        """
        将 RGB 颜色转换为 LAB 色彩空间
        
        LAB 色彩空间中，L 表示亮度，a 表示红绿轴，b 表示黄蓝轴。
        使用 LAB 空间计算颜色距离更符合人眼感知。
        
        Args:
            rgb: RGB 元组，如 (255, 128, 0)
        
        Returns:
            np.array: LAB 值 [L, a, b]
        """
        r, g, b = rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0
        
        # Gamma 校正 - 将 sRGB 转换为线性 RGB
        r = ((r + 0.055) / 1.055) ** 2.4 if r > 0.04045 else r / 12.92
        g = ((g + 0.055) / 1.055) ** 2.4 if g > 0.04045 else g / 12.92
        b = ((b + 0.055) / 1.055) ** 2.4 if b > 0.04045 else b / 12.92
        
        # RGB 转 XYZ 色彩空间（使用 D65 白点）
        x = (r * 0.4124 + g * 0.3576 + b * 0.1805) / 0.95047
        y = (r * 0.2126 + g * 0.7152 + b * 0.0722) / 1.00000
        z = (r * 0.0193 + g * 0.1192 + b * 0.9505) / 1.08883
        
        # XYZ 转 Lab（使用 D65 白点）
        x = x ** (1/3) if x > 0.008856 else (7.787 * x) + (16 / 116)
        y = y ** (1/3) if y > 0.008856 else (7.787 * y) + (16 / 116)
        z = z ** (1/3) if z > 0.008856 else (7.787 * z) + (16 / 116)
        
        L = (116 * y) - 16
        a = 500 * (x - y)
        b_val = 200 * (y - z)
        
        return np.array([L, a, b_val])
    
    def find_nearest_color(self, rgb):
        """
        找到色卡中最接近给定 RGB 颜色的颜色
        
        Args:
            rgb: RGB 元组，如 (255, 128, 0)
        
        Returns:
            int: 最接近颜色的 id
        """
        # 将目标颜色转换为 LAB 空间
        target_lab = self._rgb_to_lab(rgb)
        
        min_dist = float('inf')
        nearest_idx = 0
        
        # 遍历所有色卡颜色，计算欧氏距离
        for color in self.palette:
            color_lab = self.lab_cache[color["id"]]
            # 计算 LAB 空间中的欧氏距离
            dist = np.linalg.norm(target_lab - color_lab)
            if dist < min_dist:
                min_dist = dist
                nearest_idx = color["id"]
        
        return nearest_idx
    
    def quantize_image(self, image, width, height):
        """
        将图片量化为拼豆图案
        
        Args:
            image: PIL Image 对象
            width: 目标宽度（像素数）
            height: 目标高度（像素数）
        
        Returns:
            tuple: (pixels, used_colors)
                - pixels: 二维数组，每个元素是颜色 id
                - used_colors: 实际使用的颜色列表
        """
        # 确保图片是 RGB 模式
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        original_width, original_height = image.size
        
        # 计算缩放后的尺寸（保持宽高比）
        # 短的边会填满目标尺寸，长的边会有留白（用黑色填充）
        if original_width > original_height:
            new_width = width
            new_height = int(height * (original_height / original_width))
        else:
            new_height = height
            new_width = int(width * (original_height / original_width))
        
        # 缩放图片（使用 LANCZOS 插值，质量较好）
        img = image.resize((new_width, new_height), Image.LANCZOS)
        
        # 转换为 numpy 数组，便于批量处理
        img_array = np.array(img)
        
        pixels = []
        used_color_ids = set()
        
        # 黑色 id，用于填充空白区域
        black_color_id = 1
        
        # 遍历目标尺寸的每个像素
        for y in range(height):
            row = []
            for x in range(width):
                # 如果在缩放后的图片范围内，取对应像素
                if x < new_width and y < new_height:
                    pixel = img_array[y, x]
                    # 找到最接近的颜色
                    color_idx = self.find_nearest_color(tuple(pixel[:3]))
                else:
                    # 超出范围的区域填充为黑色
                    color_idx = black_color_id
                row.append(color_idx)
                used_color_ids.add(color_idx)
            pixels.append(row)
        
        # 返回完整色卡，保证前端可按色号 id 直接索引颜色。
        max_id = max(self.palette_dict.keys()) if self.palette_dict else 0
        dense_palette = []
        for cid in range(max_id + 1):
            if cid in self.palette_dict:
                dense_palette.append(self.palette_dict[cid])
            else:
                dense_palette.append({
                    "id": cid,
                    "name": f"Color {cid}",
                    "hex": "#FFFFFF",
                    "rgb": [255, 255, 255],
                    "category": "实色"
                })
        
        return pixels, dense_palette
