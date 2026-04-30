from __future__ import annotations

import smtplib
from email.mime.text import MIMEText

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import bad_request
from app.services.runtime_config import get_enabled_service_config


class EmailService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _send_smtp(self, *, to_email: str, subject: str, body: str, config: dict) -> None:
        required = ["host", "port", "sender"]
        missing = [key for key in required if not config.get(key)]
        if missing:
            raise bad_request(f"邮件服务配置缺少字段: {', '.join(missing)}")
        username = config.get("username")
        password = config.get("password")
        sender = str(config["sender"])
        message = MIMEText(body, "plain", "utf-8")
        message["Subject"] = subject
        message["From"] = sender
        message["To"] = to_email
        port = int(config["port"])
        timeout = self.settings.external_service_timeout_seconds
        if config.get("use_ssl", False):
            server: smtplib.SMTP = smtplib.SMTP_SSL(str(config["host"]), port, timeout=timeout)
        else:
            server = smtplib.SMTP(str(config["host"]), port, timeout=timeout)
        try:
            if config.get("use_tls", True) and not config.get("use_ssl", False):
                server.starttls()
            if username and password:
                server.login(str(username), str(password))
            server.sendmail(sender, [to_email], message.as_string())
        finally:
            server.quit()

    def send_password_reset_code(self, db: Session | None, *, to_email: str, code: str) -> None:
        service = get_enabled_service_config(db, "email")
        if service is None:
            if self.settings.app_env == "production":
                raise bad_request("邮件服务未配置，请先在管理员服务配置中启用 email")
            return
        if service.provider == "mock":
            if self.settings.app_env == "production":
                raise bad_request("生产环境不能使用 mock 邮件服务")
            return
        if service.provider != "smtp":
            raise bad_request(f"暂不支持的邮件服务提供方: {service.provider}")
        body = f"你的课程学习助手验证码是：{code}，10 分钟内有效。若非本人操作，请忽略本邮件。"
        self._send_smtp(to_email=to_email, subject="课程学习助手密码重置验证码", body=body, config=service.config)

    def test_config(self, config: dict) -> dict:
        required = ["host", "port", "sender"]
        missing = [key for key in required if not config.get(key)]
        if missing:
            return {"success": False, "message": f"缺少字段: {', '.join(missing)}"}
        try:
            port = int(config["port"])
            timeout = self.settings.external_service_timeout_seconds
            if config.get("use_ssl", False):
                server: smtplib.SMTP = smtplib.SMTP_SSL(str(config["host"]), port, timeout=timeout)
            else:
                server = smtplib.SMTP(str(config["host"]), port, timeout=timeout)
            try:
                if config.get("use_tls", True) and not config.get("use_ssl", False):
                    server.starttls()
                if config.get("username") and config.get("password"):
                    server.login(str(config["username"]), str(config["password"]))
            finally:
                server.quit()
        except Exception as exc:
            return {"success": False, "message": f"SMTP 连接失败: {exc}"}
        return {"success": True, "message": "邮件服务配置可用"}


email_service = EmailService()
