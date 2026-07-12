import os
import io
import base64
import json
import logging
import requests
from PyQt5.QtCore import QThread, pyqtSignal

from path_helper import get_data_file_path


logger = logging.getLogger(__name__)


# 文件扩展名 -> MIME 类型映射表
_MIME_MAP = {
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif': 'image/gif',
    '.bmp': 'image/bmp',
    '.webp': 'image/webp',
    '.tiff': 'image/tiff',
    '.tif': 'image/tiff',
}

# 大图压缩：最长边超过此值时按比例缩放
_MAX_IMAGE_SIDE = 1568


def _guess_mime_type(image_path: str) -> str:
    """根据文件扩展名推断 MIME 类型，未知时回退到 image/png。"""
    ext = os.path.splitext(image_path)[1].lower()
    return _MIME_MAP.get(ext, 'image/png')


def _encode_image(image_path: str):
    """读取并压缩图片，返回 (base64_str, mime_type)。

    若图片最长边超过 _MAX_IMAGE_SIDE，使用 Pillow 等比缩放后再编码。
    编码格式优先沿用原扩展名；不支持的格式回退到 PNG。
    """
    ext = os.path.splitext(image_path)[1].lower()
    mime = _guess_mime_type(image_path)

    try:
        from PIL import Image
        img = Image.open(image_path)
        # 统一为可保存的模式
        if img.mode not in ('RGB', 'RGBA', 'L', 'LA', 'P'):
            img = img.convert('RGB')

        # 等比缩放
        if max(img.width, img.height) > _MAX_IMAGE_SIDE:
            ratio = _MAX_IMAGE_SIDE / max(img.width, img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS)

        # 决定保存格式
        if ext in ('.jpg', '.jpeg'):
            save_fmt = 'JPEG'
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
        elif ext == '.png':
            save_fmt = 'PNG'
        elif ext == '.gif':
            save_fmt = 'GIF'
        elif ext == '.bmp':
            save_fmt = 'BMP'
        elif ext == '.webp':
            save_fmt = 'WEBP'
        else:
            save_fmt = 'PNG'
            mime = 'image/png'

        buffer = io.BytesIO()
        img.save(buffer, format=save_fmt)
        image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return image_data, mime
    except Exception as e:
        logger.exception("Pillow 处理图片失败，回退到原始字节读取: %s", e)
        # 回退方案：直接读取原始字节
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        return image_data, mime


class OCRManager:
    def __init__(self):
        self.api_key = ""
        self.base_url = ""
        self.model_name = ""
        self._load_config()

    def _load_config(self):
        config_path = get_data_file_path("config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.api_key = config.get('ocr_api_key', '')
                    self.base_url = config.get('ocr_base_url', '')
                    self.model_name = config.get('ocr_model_name', '')
            except Exception as e:
                logger.exception("加载配置失败: %s", e)

    def _save_config(self):
        config = {
            'ocr_api_key': self.api_key,
            'ocr_base_url': self.base_url,
            'ocr_model_name': self.model_name,
        }
        try:
            config_path = get_data_file_path("config.json")
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.exception("保存配置失败: %s", e)

    def is_configured(self):
        return bool(self.api_key and self.base_url and self.model_name)

    def set_config(self, api_key, base_url, model_name):
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self._save_config()

    def recognize_image(self, image_path):
        if not self.is_configured():
            return False, "OCR 配置未完成，请先在设置中配置 API"

        if not os.path.exists(image_path):
            return False, f"图片文件不存在: {image_path}"

        try:
            image_data, mime_type = _encode_image(image_path)

            url = f"{self.base_url.rstrip('/')}/chat/completions"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }

            prompt = """请识别这张图片中的所有文字内容。
要求：
1. 保留原有的段落结构
2. 不要添加任何额外的说明或标注
3. 如果是表格，请用 Markdown 表格格式输出
4. 直接输出识别的文字，不要其他内容
"""

            payload = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 4000
            }

            response = requests.post(url, json=payload, headers=headers, timeout=60)

            if response.status_code == 200:
                result = response.json()
                text = result['choices'][0]['message']['content']
                return True, text.strip()
            else:
                return False, f"API 调用失败 ({response.status_code}): {response.text[:500]}"

        except requests.exceptions.Timeout:
            return False, "请求超时，请检查网络连接"
        except requests.exceptions.RequestException as e:
            return False, f"网络错误: {str(e)}"
        except Exception as e:
            return False, f"识别失败: {str(e)}"


class OCRThread(QThread):
    ocr_ready = pyqtSignal(bool, str)  # success, result

    def __init__(self, ocr_manager, image_path):
        super().__init__()
        self.ocr_manager = ocr_manager
        self.image_path = image_path

    def run(self):
        success, result = self.ocr_manager.recognize_image(self.image_path)
        self.ocr_ready.emit(success, result)
