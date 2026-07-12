import json
import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QGroupBox, QPushButton, QMessageBox, QProgressBar
)
from PyQt5.QtCore import Qt
import requests


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setMinimumWidth(500)
        self._load_config()
        self._init_ui()
    
    def _load_config(self):
        self.api_key = ""
        self.base_url = ""
        self.model_name = ""
        
        config_path = "config.json"
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.api_key = config.get('ocr_api_key', '')
                    self.base_url = config.get('ocr_base_url', '')
                    self.model_name = config.get('ocr_model_name', '')
            except:
                pass
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        ocr_group = QGroupBox("OCR 设置")
        ocr_layout = QVBoxLayout()
        
        api_key_layout = QHBoxLayout()
        api_key_layout.addWidget(QLabel("API Key:"))
        self.api_key_edit = QLineEdit(self.api_key)
        self.api_key_edit.setPlaceholderText("输入 API Key")
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        api_key_layout.addWidget(self.api_key_edit)
        ocr_layout.addLayout(api_key_layout)
        
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("Base URL:"))
        self.url_edit = QLineEdit(self.base_url)
        self.url_edit.setPlaceholderText("例如：https://api.openai.com/v1")
        url_layout.addWidget(self.url_edit)
        ocr_layout.addLayout(url_layout)
        
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Model Name:"))
        self.model_edit = QLineEdit(self.model_name)
        self.model_edit.setPlaceholderText("例如：gpt-4o 或 gpt-4-vision-preview")
        model_layout.addWidget(self.model_edit)
        ocr_layout.addLayout(model_layout)
        
        test_btn = QPushButton("测试连接")
        test_btn.clicked.connect(self._test_connection)
        self.test_btn = test_btn
        ocr_layout.addWidget(test_btn)
        
        help_text = QLabel(
            "说明：\n"
            "1. 支持多模态的 LLM API（如 OpenAI GPT-4 Vision）\n"
            "2. Base URL 格式：https://api.openai.com/v1\n"
            "3. 确保所选模型支持图片识别"
        )
        help_text.setStyleSheet("color: #666; font-size: 12px;")
        ocr_layout.addWidget(help_text)
        
        ocr_group.setLayout(ocr_layout)
        layout.addWidget(ocr_group)
        
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
        api_key = self.api_key_edit.text().strip()
        base_url = self.url_edit.text().strip()
        model_name = self.model_edit.text().strip()
        
        if not all([api_key, base_url, model_name]):
            QMessageBox.warning(self, "提示", "请填写完整的配置信息")
            return
        
        self.test_btn.setText("测试中...")
        self.test_btn.setEnabled(False)
        self.processEvents()
        
        try:
            url = f"{base_url.rstrip('/')}/models"
            headers = {'Authorization': f'Bearer {api_key}'}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                QMessageBox.information(self, "成功", "API 连接成功！")
            else:
                QMessageBox.warning(
                    self, "失败",
                    f"连接失败: {response.status_code}\n{response.text}"
                )
        except Exception as e:
            QMessageBox.warning(self, "错误", f"连接错误: {str(e)}")
        finally:
            self.test_btn.setText("测试连接")
            self.test_btn.setEnabled(True)
    
    def get_config(self):
        return {
            'ocr_api_key': self.api_key_edit.text().strip(),
            'ocr_base_url': self.url_edit.text().strip(),
            'ocr_model_name': self.model_edit.text().strip()
        }