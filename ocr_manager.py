import os
import base64
import json
import requests


class OCRManager:
    def __init__(self):
        self.api_key = ""
        self.base_url = ""
        self.model_name = ""
        self._load_config()
    
    def _load_config(self):
        config_path = "config.json"
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.api_key = config.get('ocr_api_key', '')
                    self.base_url = config.get('ocr_base_url', '')
                    self.model_name = config.get('ocr_model_name', '')
            except Exception as e:
                print(f"加载配置失败: {e}")
    
    def _save_config(self):
        config = {
            'ocr_api_key': self.api_key,
            'ocr_base_url': self.base_url,
            'ocr_model_name': self.model_name,
        }
        try:
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置失败: {e}")
    
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
        
        try:
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
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
                                    "url": f"data:image/png;base64,{image_data}"
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
                return False, f"API 调用失败: {response.status_code} - {response.text}"
                
        except requests.exceptions.Timeout:
            return False, "请求超时，请检查网络连接"
        except requests.exceptions.RequestException as e:
            return False, f"网络错误: {str(e)}"
        except Exception as e:
            return False, f"识别失败: {str(e)}"