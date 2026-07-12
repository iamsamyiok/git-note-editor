import os
import json
import requests
from chat_model import Message
from path_helper import get_data_file_path


class AIService:
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
                print(f"加载 AI 配置失败: {e}")
    
    def is_configured(self):
        return bool(self.api_key and self.base_url and self.model_name)
    
    def generate_reply(self, messages: list[Message], user_input: str = ""):
        if not self.is_configured():
            return False, "AI 配置未完成，请先在设置中配置 API"
        
        try:
            url = f"{self.base_url.rstrip('/')}/chat/completions"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }
            
            prompt_messages = []
            for msg in messages[-10:]:
                if msg.message_type == "text":
                    prompt_messages.append({
                        "role": "assistant" if msg.sender == "AI" else "user",
                        "content": msg.content
                    })
            
            if user_input:
                prompt_messages.append({"role": "user", "content": user_input})
            
            if not prompt_messages:
                prompt_messages.append({"role": "user", "content": "你好"})
            
            payload = {
                "model": self.model_name,
                "messages": prompt_messages,
                "max_tokens": 2000,
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                reply = result['choices'][0]['message']['content']
                return True, reply.strip()
            else:
                return False, f"API 调用失败: {response.status_code}"
                
        except requests.exceptions.Timeout:
            return False, "请求超时"
        except requests.exceptions.RequestException as e:
            return False, f"网络错误: {str(e)}"
        except Exception as e:
            return False, f"AI 回复失败: {str(e)}"