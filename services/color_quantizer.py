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
    
    def __init__(self, palette=None, distance_metric='ciede2000', dither=True):
        """
        初始化颜色量化器
        
        Args:
            palette: 自定义色板，默认使用经典拼豆色卡
            distance_metric: 颜色距离算法，支持 ciede2000 / lab_euclidean
            dither: 是否启用误差扩散抖动
        """
        self.palette = palette or get_palette()
        self.distance_metric = distance_metric if distance_metric in ('ciede2000', 'lab_euclidean') else 'ciede2000'
        self.dither = bool(dither)
        # 将色卡的 RGB 值转换为 numpy 数组，便于计算
        self.palette_colors = np.array([c["rgb"] for c in self.palette])
        self.palette_by_id = {c["id"]: c for c in self.palette}
        # 颜色 id 到颜色信息的字典映射
        self.palette_dict = get_palette_dict()
        # LAB 颜色缓存，避免重复计算
        self.lab_cache = {}
        # 最近邻颜色缓存（key: RGB int tuple）
        self.nearest_cache = {}
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
        # 缓存可显著减少抖动量化中的重复计算
        key = (
            int(np.clip(rgb[0], 0, 255)),
            int(np.clip(rgb[1], 0, 255)),
            int(np.clip(rgb[2], 0, 255)),
        )
        cached = self.nearest_cache.get(key)
        if cached is not None:
            return cached

        # 将目标颜色转换为 LAB 空间
        target_lab = self._rgb_to_lab(key)
        
        min_dist = float('inf')
        nearest_idx = None
        
        # 同类像素化工具通常用 ΔE 度量（而不是 RGB 欧氏距离）提升色感一致性
        for color in self.palette:
            color_lab = self.lab_cache[color["id"]]
            if self.distance_metric == 'lab_euclidean':
                dist = float(np.linalg.norm(target_lab - color_lab))
            else:
                dist = self._delta_e_ciede2000(target_lab, color_lab)
                # CIEDE2000 在极端情况下可能出现非有限值，回退到 LAB 欧氏距离兜底。
                if not np.isfinite(dist):
                    dist = float(np.linalg.norm(target_lab - color_lab))

            if not np.isfinite(dist):
                continue

            if dist < min_dist:
                min_dist = dist
                nearest_idx = color["id"]

        # 全量兜底，避免异常情况下全部回落到默认 0 号色。
        if nearest_idx is None:
            nearest_idx = self.palette[0]["id"] if self.palette else 0

        self.nearest_cache[key] = nearest_idx
        return nearest_idx

    def _delta_e_ciede2000(self, lab1, lab2):
        """
        CIEDE2000 色差公式。
        该公式对亮度/色度/色相的感知更接近人眼。
        """
        L1, a1, b1 = float(lab1[0]), float(lab1[1]), float(lab1[2])
        L2, a2, b2 = float(lab2[0]), float(lab2[1]), float(lab2[2])

        C1 = (a1 * a1 + b1 * b1) ** 0.5
        C2 = (a2 * a2 + b2 * b2) ** 0.5
        C_bar = (C1 + C2) / 2.0

        C_bar7 = C_bar ** 7
        G = 0.5 * (1 - (C_bar7 / (C_bar7 + 25 ** 7)) ** 0.5) if C_bar > 0 else 0.0

        a1p = (1 + G) * a1
        a2p = (1 + G) * a2
        C1p = (a1p * a1p + b1 * b1) ** 0.5
        C2p = (a2p * a2p + b2 * b2) ** 0.5

        h1p = np.degrees(np.arctan2(b1, a1p)) % 360
        h2p = np.degrees(np.arctan2(b2, a2p)) % 360

        dLp = L2 - L1
        dCp = C2p - C1p

        if C1p * C2p == 0:
            dhp = 0.0
        else:
            dh = h2p - h1p
            if dh > 180:
                dh -= 360
            elif dh < -180:
                dh += 360
            dhp = dh
        dHp = 2 * (C1p * C2p) ** 0.5 * np.sin(np.radians(dhp / 2.0))

        L_bar_p = (L1 + L2) / 2.0
        C_bar_p = (C1p + C2p) / 2.0

        if C1p * C2p == 0:
            h_bar_p = h1p + h2p
        else:
            h_sum = h1p + h2p
            h_diff = abs(h1p - h2p)
            if h_diff > 180:
                if h_sum < 360:
                    h_bar_p = (h_sum + 360) / 2.0
                else:
                    h_bar_p = (h_sum - 360) / 2.0
            else:
                h_bar_p = h_sum / 2.0

        T = (
            1
            - 0.17 * np.cos(np.radians(h_bar_p - 30))
            + 0.24 * np.cos(np.radians(2 * h_bar_p))
            + 0.32 * np.cos(np.radians(3 * h_bar_p + 6))
            - 0.20 * np.cos(np.radians(4 * h_bar_p - 63))
        )

        d_theta = 30 * np.exp(-(((h_bar_p - 275) / 25) ** 2))
        R_C = 2 * ((C_bar_p ** 7) / (C_bar_p ** 7 + 25 ** 7)) ** 0.5 if C_bar_p > 0 else 0
        S_L = 1 + (0.015 * ((L_bar_p - 50) ** 2)) / (20 + ((L_bar_p - 50) ** 2)) ** 0.5
        S_C = 1 + 0.045 * C_bar_p
        S_H = 1 + 0.015 * C_bar_p * T
        R_T = -np.sin(np.radians(2 * d_theta)) * R_C

        kL = 1.0
        kC = 1.0
        kH = 1.0

        dE_sq = (
            (dLp / (kL * S_L)) ** 2
            + (dCp / (kC * S_C)) ** 2
            + (dHp / (kH * S_H)) ** 2
            + R_T * (dCp / (kC * S_C)) * (dHp / (kH * S_H))
        )
        # 数值误差保护：避免对负数开根导致 NaN。
        if dE_sq < 0:
            dE_sq = 0.0
        return float(dE_sq ** 0.5)

    def _resize_contain_center(self, image, width, height):
        """
        等比缩放 + 居中贴合目标画布，避免拉伸和偏角落填充。
        """
        if image.mode != 'RGB':
            image = image.convert('RGB')

        src_w, src_h = image.size
        if src_w <= 0 or src_h <= 0:
            return Image.new('RGB', (width, height), (255, 255, 255))

        scale = min(width / src_w, height / src_h)
        new_w = max(1, int(round(src_w * scale)))
        new_h = max(1, int(round(src_h * scale)))

        resized = image.resize((new_w, new_h), Image.LANCZOS)
        canvas = Image.new('RGB', (width, height), (255, 255, 255))
        offset_x = (width - new_w) // 2
        offset_y = (height - new_h) // 2
        canvas.paste(resized, (offset_x, offset_y))
        return canvas

    def _extract_dominant_grid_rgb(self, image, width, height, cell_scale=4):
        """
        先放大到 (width*cell_scale, height*cell_scale) 再按小块提取主导色。
        这样比直接缩到 width*height 再取像素更能保留边缘和色阶结构。
        """
        hi_w = max(width, width * max(2, int(cell_scale)))
        hi_h = max(height, height * max(2, int(cell_scale)))
        hi_img = self._resize_contain_center(image, hi_w, hi_h)
        hi = np.array(hi_img, dtype=np.uint8)

        # 预计算网格边界，确保每个像素都落在某个单元内。
        xs = np.linspace(0, hi_w, num=width + 1, dtype=np.int32)
        ys = np.linspace(0, hi_h, num=height + 1, dtype=np.int32)

        grid_rgb = np.zeros((height, width, 3), dtype=np.float32)
        for gy in range(height):
            y0, y1 = int(ys[gy]), int(ys[gy + 1])
            if y1 <= y0:
                y1 = min(hi_h, y0 + 1)
            for gx in range(width):
                x0, x1 = int(xs[gx]), int(xs[gx + 1])
                if x1 <= x0:
                    x1 = min(hi_w, x0 + 1)

                block = hi[y0:y1, x0:x1]
                if block.size == 0:
                    grid_rgb[gy, gx] = [255, 255, 255]
                    continue

                # 4-bit 量化桶用于统计主导色（4096 桶）。
                q = (block // 16).astype(np.int32)
                code = q[:, :, 0] * 256 + q[:, :, 1] * 16 + q[:, :, 2]
                flat_code = code.reshape(-1)
                hist = np.bincount(flat_code, minlength=4096)
                dom = int(np.argmax(hist))
                mask = (flat_code == dom)

                flat_rgb = block.reshape(-1, 3).astype(np.float32)
                if np.any(mask):
                    rgb = flat_rgb[mask].mean(axis=0)
                else:
                    rgb = flat_rgb.mean(axis=0)
                grid_rgb[gy, gx] = rgb

        return grid_rgb

    def _cleanup_speckles(self, pixels):
        """
        轻量杂色清理：对孤立点做邻域主色替换。
        """
        h = len(pixels)
        w = len(pixels[0]) if h else 0
        if h == 0 or w == 0:
            return pixels

        src = [row[:] for row in pixels]
        out = [row[:] for row in pixels]

        for y in range(h):
            for x in range(w):
                center = src[y][x]
                counter = {}
                for ny in range(max(0, y - 1), min(h, y + 2)):
                    for nx in range(max(0, x - 1), min(w, x + 2)):
                        if nx == x and ny == y:
                            continue
                        cid = src[ny][nx]
                        counter[cid] = counter.get(cid, 0) + 1

                same_count = counter.get(center, 0)
                if same_count >= 2:
                    continue

                major_id = center
                major_count = 0
                for cid, cnt in counter.items():
                    if cnt > major_count:
                        major_count = cnt
                        major_id = cid
                if major_id != center and major_count >= 4:
                    out[y][x] = major_id

        return out

    def _merge_similar_regions(self, pixels, threshold=22.0):
        """
        基于 BFS 的区域合并：把颜色距离较近的连通区域合并为区域主色。
        思路参考同类开源实现中的“区域颜色合并”。
        """
        h = len(pixels)
        w = len(pixels[0]) if h else 0
        if h == 0 or w == 0:
            return pixels

        visited = [[False] * w for _ in range(h)]
        out = [row[:] for row in pixels]

        def color_dist(id1, id2):
            c1 = self.palette_by_id.get(id1, {}).get("rgb", [255, 255, 255])
            c2 = self.palette_by_id.get(id2, {}).get("rgb", [255, 255, 255])
            dr = float(c1[0] - c2[0])
            dg = float(c1[1] - c2[1])
            db = float(c1[2] - c2[2])
            return (dr * dr + dg * dg + db * db) ** 0.5

        for y in range(h):
            for x in range(w):
                if visited[y][x]:
                    continue

                seed = out[y][x]
                queue = [(x, y)]
                visited[y][x] = True
                region = []
                counts = {}

                while queue:
                    cx, cy = queue.pop()
                    cid = out[cy][cx]
                    region.append((cx, cy))
                    counts[cid] = counts.get(cid, 0) + 1

                    for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                        if nx < 0 or ny < 0 or nx >= w or ny >= h or visited[ny][nx]:
                            continue
                        nid = out[ny][nx]
                        if color_dist(seed, nid) <= threshold:
                            visited[ny][nx] = True
                            queue.append((nx, ny))

                if len(region) < 3:
                    continue

                major_id = max(counts.items(), key=lambda kv: kv[1])[0]
                for rx, ry in region:
                    out[ry][rx] = major_id

        return out
    
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
        
        # 先做主导色像素化，再映射到拼豆色板。
        work = self._extract_dominant_grid_rgb(image, width, height, cell_scale=4).astype(np.float32)

        pixels = [[0 for _ in range(width)] for _ in range(height)]
        used_color_ids = set()

        if self.dither:
            # Floyd-Steinberg 误差扩散（蛇形扫描）：
            # 在固定色卡下通常能得到更平滑的色阶过渡。
            for y in range(height):
                if y % 2 == 0:
                    x_iter = range(width)
                    forward = True
                else:
                    x_iter = range(width - 1, -1, -1)
                    forward = False

                for x in x_iter:
                    old = np.clip(work[y, x], 0, 255)
                    color_id = self.find_nearest_color((old[0], old[1], old[2]))
                    new = np.array(self.palette_by_id[color_id]["rgb"], dtype=np.float32)
                    pixels[y][x] = color_id
                    used_color_ids.add(color_id)

                    err = old - new
                    work[y, x] = new

                    if forward:
                        if x + 1 < width:
                            work[y, x + 1] += err * (7 / 16)
                        if y + 1 < height and x - 1 >= 0:
                            work[y + 1, x - 1] += err * (3 / 16)
                        if y + 1 < height:
                            work[y + 1, x] += err * (5 / 16)
                        if y + 1 < height and x + 1 < width:
                            work[y + 1, x + 1] += err * (1 / 16)
                    else:
                        if x - 1 >= 0:
                            work[y, x - 1] += err * (7 / 16)
                        if y + 1 < height and x + 1 < width:
                            work[y + 1, x + 1] += err * (3 / 16)
                        if y + 1 < height:
                            work[y + 1, x] += err * (5 / 16)
                        if y + 1 < height and x - 1 >= 0:
                            work[y + 1, x - 1] += err * (1 / 16)
        else:
            # 无抖动模式：保留更干净的块面，但过渡会更硬。
            for y in range(height):
                for x in range(width):
                    old = np.clip(work[y, x], 0, 255)
                    color_id = self.find_nearest_color((old[0], old[1], old[2]))
                    pixels[y][x] = color_id
                    used_color_ids.add(color_id)

        # 后处理：先做区域合并，再做孤点清理。
        pixels = self._merge_similar_regions(pixels, threshold=22.0)
        pixels = self._cleanup_speckles(pixels)
        used_color_ids = set()
        for row in pixels:
            used_color_ids.update(row)
        
        # 返回完整色卡，保证前端可按色号 id 直接索引颜色。
        max_id = max(self.palette_dict.keys()) if self.palette_dict else 0
        dense_palette = []
        for cid in range(max_id + 1):
            if cid in self.palette_dict:
                dense_palette.append(self.palette_dict[cid])
            else:
                dense_palette.append({
                    "id": cid,
                    "beadId": f"UNK{cid}",
                    "code": f"UNK{cid}",
                    "name": f"Color {cid}",
                    "hex": "#FFFFFF",
                    "rgb": [255, 255, 255],
                    "category": "实色"
                })
        
        return pixels, dense_palette
