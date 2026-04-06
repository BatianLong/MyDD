"""
PerlerCraft 拼豆图案生成器 - API 服务端

Flask 后端服务，提供图片转拼豆图案的 API 接口。
支持图片上传、颜色量化、图案生成等功能。
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
import base64
import io
import os

# 导入自定义模块
from services.color_quantizer import ColorQuantizer
from data.palette import get_palette

# 创建 Flask 应用
app = Flask(__name__)

# 启用 CORS，允许跨域请求（小程序需要）
CORS(app)


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
        
        # 参数验证
        if not image_base64:
            return jsonify({
                "code": 400,
                "message": "image_base64 is required"
            }), 400
        
        # Base64 解码为图片
        image_data = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_data))
        
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
    palette = get_palette(palette_type)
    return jsonify({
        "code": 0,
        "data": palette
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
