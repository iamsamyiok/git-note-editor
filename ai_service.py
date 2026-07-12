import os
import json
import logging
import requests
from PyQt5.QtCore import QThread, pyqtSignal

from chat_model import Message
from path_helper import get_data_file_path


logger = logging.getLogger(__name__)


class AIService:
    def __init__(self):
        self.api_key = ""
        self.base_url = ""
        self.model_name = ""
        self.system_prompt = ""
        self._load_config()

    def _load_config(self):
        config_path = get_data_file_path("config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 优先读 chat_* 配置；若不存在则回退到 ocr_*（向后兼容）
                    self.api_key = config.get('chat_api_key') or config.get('ocr_api_key', '')
                    self.base_url = config.get('chat_base_url') or config.get('ocr_base_url', '')
                    self.model_name = config.get('chat_model_name') or config.get('ocr_model_name', '')
                    self.system_prompt = config.get('chat_system_prompt', '')
            except Exception as e:
                logger.exception("加载 AI 配置失败: %s", e)

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
            # system prompt 优先放在最前
            if self.system_prompt:
                prompt_messages.append({
                    "role": "system",
                    "content": self.system_prompt
                })

            for msg in messages[-20:]:
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
                return False, f"API 调用失败 ({response.status_code}): {response.text[:500]}"

        except requests.exceptions.Timeout:
            return False, "请求超时"
        except requests.exceptions.RequestException as e:
            return False, f"网络错误: {str(e)}"
        except Exception as e:
            return False, f"AI 回复失败: {str(e)}"


class AIReplyThread(QThread):
    reply_ready = pyqtSignal(bool, str)  # success, result

    def __init__(self, ai_service, messages):
        super().__init__()
        self.ai_service = ai_service
        self.messages = messages

    def run(self):
        success, result = self.ai_service.generate_reply(self.messages)
        self.reply_ready.emit(success, result)
