"""
PerlerCraft 拼豆图案生成器 - API 服务端

Flask 后端服务，提供图片转拼豆图案的 API 接口。
支持图片上传、颜色量化、图案生成等功能。
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
import numpy as np
import base64
import io
import os
from collections import deque

# 导入自定义模块
from services.color_quantizer import ColorQuantizer
from data.palette import get_palette, get_palette_meta

# 创建 Flask 应用
app = Flask(__name__)

# 启用 CORS，允许跨域请求（小程序需要）
CORS(app)


def _safe_decode_image(image_base64):
    if not image_base64:
        return None, ("image_base64 is required", 400)
    if len(image_base64) > 2_000_000:
        return None, ("image payload too large, compress before upload", 413)

    image_data = base64.b64decode(image_base64)
    if len(image_data) > 1_500_000:
        return None, ("decoded image too large, compress before upload", 413)

    image = Image.open(io.BytesIO(image_data)).convert('RGB')
    if image.width > 4096 or image.height > 4096:
        return None, ("image dimensions too large, compress before upload", 413)
    return image, None


def _largest_component(mask):
    h, w = mask.shape
    visited = np.zeros((h, w), dtype=bool)
    best_points = []

    for y in range(h):
        for x in range(w):
            if not mask[y, x] or visited[y, x]:
                continue

            q = deque([(y, x)])
            visited[y, x] = True
            points = [(y, x)]

            while q:
                cy, cx = q.popleft()
                for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
                    if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = True
                        q.append((ny, nx))
                        points.append((ny, nx))

            if len(points) > len(best_points):
                best_points = points

    if not best_points:
        return mask

    out = np.zeros_like(mask)
    ys, xs = zip(*best_points)
    out[np.array(ys), np.array(xs)] = True
    return out


def _segment_foreground_white_bg(image):
    arr = np.array(image.convert('RGB'), dtype=np.int16)
    h, w, _ = arr.shape

    border = np.concatenate(
        [arr[0, :, :], arr[-1, :, :], arr[:, 0, :], arr[:, -1, :]],
        axis=0
    )
    bg = np.median(border, axis=0)

    diff = np.abs(arr - bg).sum(axis=2)
    border_diff = np.abs(border - bg).sum(axis=1)
    thr = int(max(24, min(120, np.percentile(border_diff, 85) + 10)))

    candidate_bg = diff <= thr
    bg_mask = np.zeros((h, w), dtype=bool)
    q = deque()

    for x in range(w):
        if candidate_bg[0, x]:
            q.append((0, x))
            bg_mask[0, x] = True
        if candidate_bg[h - 1, x] and not bg_mask[h - 1, x]:
            q.append((h - 1, x))
            bg_mask[h - 1, x] = True
    for y in range(h):
        if candidate_bg[y, 0] and not bg_mask[y, 0]:
            q.append((y, 0))
            bg_mask[y, 0] = True
        if candidate_bg[y, w - 1] and not bg_mask[y, w - 1]:
            q.append((y, w - 1))
            bg_mask[y, w - 1] = True

    while q:
        cy, cx = q.popleft()
        for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
            if 0 <= ny < h and 0 <= nx < w and candidate_bg[ny, nx] and not bg_mask[ny, nx]:
                bg_mask[ny, nx] = True
                q.append((ny, nx))

    fg_mask = ~bg_mask
    fg_mask = _largest_component(fg_mask)

    out = arr.astype(np.uint8).copy()
    out[~fg_mask] = [255, 255, 255]
    return Image.fromarray(out, mode='RGB')


@app.route('/')
def index():
    """
    根路径 - 服务健康检查
    
    Returns:
        JSON: 服务信息和版本号
    """
    return jsonify({
        "code": 0,
        "message": "PerlerCraft API Server",
        "version": "1.0.0"
    })


@app.route('/api/convert', methods=['POST'])
def convert_image():
    """
    图片转拼豆图案接口
    
    接收 Base64 编码的图片，转换为指定尺寸的拼豆图案。
    
    请求体:
        {
            "image_base64": "图片Base64编码",
            "width": 35,      // 目标宽度
            "height": 35      // 目标高度
        }
    
    返回:
        {
            "code": 0,
            "data": {
                "width": 35,
                "height": 35,
                "pixels": [[0, 1, 2, ...], ...],  // 像素矩阵
                "colors": [{...}, ...]              // 使用的颜色
            }
        }
    """
    try:
        # 获取请求参数
        data = request.json
        image_base64 = data.get('image_base64')
        width = data.get('width', 35)
        height = data.get('height', 35)
        
        image, err = _safe_decode_image(image_base64)
        if err:
            msg, code = err
            return jsonify({
                "code": code,
                "message": msg
            }), code
        
        # 创建颜色量化器并处理图片
        quantizer = ColorQuantizer()
        pixels, used_colors = quantizer.quantize_image(image, width, height)
        
        # 返回结果
        return jsonify({
            "code": 0,
            "data": {
                "width": width,
                "height": height,
                "pixels": pixels,
                "colors": used_colors
            }
        })
    
    except Exception as e:
        # 错误处理
        return jsonify({
            "code": 500,
            "message": str(e)
        }), 500


@app.route('/api/preprocess/remove-bg', methods=['POST'])
def remove_bg_api():
    try:
        data = request.json or {}
        image_base64 = data.get('image_base64')
        image, err = _safe_decode_image(image_base64)
        if err:
            msg, code = err
            return jsonify({
                "code": code,
                "message": msg
            }), code

        result = _segment_foreground_white_bg(image)
        buffer = io.BytesIO()
        result.save(buffer, format='PNG')
        result_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        return jsonify({
            "code": 0,
            "data": {
                "image_base64": result_base64,
                "width": result.width,
                "height": result.height
            }
        })
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": str(e)
        }), 500


@app.route('/api/palette', methods=['GET'])
def get_palette_api():
    """
    获取拼豆色卡接口
    
    返回可用的拼豆颜色列表。
    
    Query参数:
        type: 色卡类型，默认 "classic"
    
    返回:
        {
            "code": 0,
            "data": [
                {"id": 0, "name": "白色", "hex": "#FFFFFF", "rgb": [255, 255, 255]},
                ...
            ]
        }
    """
    palette_type = request.args.get('type', 'classic')
    category = request.args.get('category')
    palette = get_palette(palette_type, category=category)
    return jsonify({
        "code": 0,
        "data": palette,
        "meta": get_palette_meta()
    })


@app.route('/api/sizes', methods=['GET'])
def get_sizes():
    """
    获取可选的图案尺寸接口
    
    返回支持的拼豆网格尺寸选项。
    
    返回:
        {
            "code": 0,
            "data": [
                {"value": 29, "label": "29×29", "description": "入门级"},
                {"value": 35, "label": "35×35", "description": "标准"},
                {"value": 48, "label": "48×48", "description": "进阶"},
                {"value": 58, "label": "58×58", "description": "复杂"}
            ]
        }
    """
    sizes = [
        {"value": 29, "label": "29×29", "description": "入门级"},
        {"value": 35, "label": "35×35", "description": "标准"},
        {"value": 48, "label": "48×48", "description": "进阶"},
        {"value": 58, "label": "58×58", "description": "复杂"}
    ]
    return jsonify({
        "code": 0,
        "data": sizes
    })


if __name__ == '__main__':
    # 获取端口号（Railway 等平台通过环境变量提供）
    port = int(os.environ.get('PORT', 5000))
    # 生产环境关闭 debug 模式
    app.run(host='0.0.0.0', port=port, debug=False)
