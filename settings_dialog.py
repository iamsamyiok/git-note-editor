import json
import os
import logging
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QGroupBox, QPushButton, QMessageBox, QProgressBar, QApplication,
    QFormLayout, QTabWidget, QWidget
)
from PyQt5.QtCore import Qt
import requests
from path_helper import get_data_file_path


logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setMinimumWidth(560)
        self._load_config()
        self._init_ui()

    def _load_config(self):
        # AI 聊天配置
        self.chat_api_key = ""
        self.chat_base_url = ""
        self.chat_model_name = ""
        self.chat_system_prompt = ""
        # OCR 识别配置
        self.ocr_api_key = ""
        self.ocr_base_url = ""
        self.ocr_model_name = ""

        config_path = get_data_file_path("config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # OCR 配置
                    self.ocr_api_key = config.get('ocr_api_key', '')
                    self.ocr_base_url = config.get('ocr_base_url', '')
                    self.ocr_model_name = config.get('ocr_model_name', '')
                    # AI 聊天配置（向后兼容：若 chat_* 不存在，从 ocr_* 复制）
                    self.chat_api_key = config.get('chat_api_key') or self.ocr_api_key
                    self.chat_base_url = config.get('chat_base_url') or self.ocr_base_url
                    self.chat_model_name = config.get('chat_model_name') or self.ocr_model_name
                    self.chat_system_prompt = config.get('chat_system_prompt', '')
            except Exception as e:
                logger.exception("加载配置失败: %s", e)

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # ===== AI 聊天配置 =====
        chat_group = QGroupBox("AI 聊天配置")
        chat_layout = QVBoxLayout()

        api_key_layout = QHBoxLayout()
        api_key_layout.addWidget(QLabel("API Key:"))
        self.chat_api_key_edit = QLineEdit(self.chat_api_key)
        self.chat_api_key_edit.setPlaceholderText("输入 AI 聊天 API Key")
        self.chat_api_key_edit.setEchoMode(QLineEdit.Password)
        api_key_layout.addWidget(self.chat_api_key_edit)
        chat_layout.addLayout(api_key_layout)

        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("Base URL:"))
        self.chat_url_edit = QLineEdit(self.chat_base_url)
        self.chat_url_edit.setPlaceholderText("例如：https://api.openai.com/v1")
        url_layout.addWidget(self.chat_url_edit)
        chat_layout.addLayout(url_layout)

        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Model Name:"))
        self.chat_model_edit = QLineEdit(self.chat_model_name)
        self.chat_model_edit.setPlaceholderText("例如：gpt-4o-mini 或 qwen-plus")
        model_layout.addWidget(self.chat_model_edit)
        chat_layout.addLayout(model_layout)

        prompt_layout = QVBoxLayout()
        prompt_layout.addWidget(QLabel("System Prompt:"))
        self.chat_prompt_edit = QLineEdit(self.chat_system_prompt)
        self.chat_prompt_edit.setPlaceholderText("可选：自定义 system prompt，留空则不发送")
        prompt_layout.addWidget(self.chat_prompt_edit)
        chat_layout.addLayout(prompt_layout)

        chat_help = QLabel(
            "说明：\n"
            "1. 用于 AI 聊天功能的 LLM API\n"
            "2. Base URL 格式：https://api.openai.com/v1\n"
            "3. 若留空将自动复用 OCR 配置"
        )
        chat_help.setStyleSheet("color: #666; font-size: 12px;")
        chat_layout.addWidget(chat_help)

        chat_group.setLayout(chat_layout)
        layout.addWidget(chat_group)

        # ===== OCR 识别配置 =====
        ocr_group = QGroupBox("OCR 识别配置")
        ocr_layout = QVBoxLayout()

        ocr_key_layout = QHBoxLayout()
        ocr_key_layout.addWidget(QLabel("API Key:"))
        self.ocr_api_key_edit = QLineEdit(self.ocr_api_key)
        self.ocr_api_key_edit.setPlaceholderText("输入 OCR 识别 API Key")
        self.ocr_api_key_edit.setEchoMode(QLineEdit.Password)
        ocr_key_layout.addWidget(self.ocr_api_key_edit)
        ocr_layout.addLayout(ocr_key_layout)

        ocr_url_layout = QHBoxLayout()
        ocr_url_layout.addWidget(QLabel("Base URL:"))
        self.ocr_url_edit = QLineEdit(self.ocr_base_url)
        self.ocr_url_edit.setPlaceholderText("例如：https://api.openai.com/v1")
        ocr_url_layout.addWidget(self.ocr_url_edit)
        ocr_layout.addLayout(ocr_url_layout)

        ocr_model_layout = QHBoxLayout()
        ocr_model_layout.addWidget(QLabel("Model Name:"))
        self.ocr_model_edit = QLineEdit(self.ocr_model_name)
        self.ocr_model_edit.setPlaceholderText("例如：gpt-4o 或 gpt-4-vision-preview")
        ocr_model_layout.addWidget(self.ocr_model_edit)
        ocr_layout.addLayout(ocr_model_layout)

        test_btn = QPushButton("测试连接")
        test_btn.clicked.connect(self._test_connection)
        self.test_btn = test_btn
        ocr_layout.addWidget(test_btn)

        ocr_help_text = QLabel(
            "说明：\n"
            "1. 支持多模态的 LLM API（如 OpenAI GPT-4 Vision）\n"
            "2. Base URL 格式：https://api.openai.com/v1\n"
            "3. 确保所选模型支持图片识别\n"
            "4. 测试连接仅对 https URL 进行，且不会发送 API Key"
        )
        ocr_help_text.setStyleSheet("color: #666; font-size: 12px;")
        ocr_layout.addWidget(ocr_help_text)

        ocr_group.setLayout(ocr_layout)
        layout.addWidget(ocr_group)

        # ===== 底部按钮 =====
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def _test_connection(self):
        base_url = self.ocr_url_edit.text().strip()
        model_name = self.ocr_model_edit.text().strip()

        if not base_url:
            QMessageBox.warning(self, "提示", "请填写 Base URL")
            return

        # 仅对 https URL 进行测试，避免明文发送敏感信息
        if not base_url.lower().startswith("https://"):
            QMessageBox.warning(
                self, "安全提示",
                "出于安全考虑，仅支持对 https:// 开头的 URL 进行测试连接。\n"
                "请确认 Base URL 协议为 https。"
            )
            return

        self.test_btn.setText("测试中...")
        self.test_btn.setEnabled(False)
        QApplication.processEvents()

        try:
            url = f"{base_url.rstrip('/')}/models"
            # 测试连接时故意不携带真实 API Key，使用占位符
            headers = {'Authorization': 'Bearer test_key'}
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                QMessageBox.information(self, "成功", "API 连接成功！")
            elif response.status_code in (401, 403):
                QMessageBox.information(
                    self, "可达",
                    f"服务器可达（{response.status_code}），但需要正确的 API Key 才能访问。\n"
                    f"请保存配置后实际使用时验证。"
                )
            else:
                QMessageBox.warning(
                    self, "失败",
                    f"连接失败 ({response.status_code}):\n{response.text[:500]}"
                )
        except requests.exceptions.Timeout:
            QMessageBox.warning(self, "错误", "连接超时，请检查网络或 URL 是否正确")
        except requests.exceptions.ConnectionError as e:
            QMessageBox.warning(self, "错误", f"连接错误：无法连接到服务器\n{str(e)[:300]}")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"连接错误: {str(e)}")
        finally:
            self.test_btn.setText("测试连接")
            self.test_btn.setEnabled(True)

    def get_config(self):
        return {
            # AI 聊天配置
            'chat_api_key': self.chat_api_key_edit.text().strip(),
            'chat_base_url': self.chat_url_edit.text().strip(),
            'chat_model_name': self.chat_model_edit.text().strip(),
            'chat_system_prompt': self.chat_prompt_edit.text().strip(),
            # OCR 识别配置
            'ocr_api_key': self.ocr_api_key_edit.text().strip(),
            'ocr_base_url': self.ocr_url_edit.text().strip(),
            'ocr_model_name': self.ocr_model_edit.text().strip(),
        }
