from __future__ import annotations

import smtplib
from datetime import datetime
from html import escape
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import bad_request
from app.db import session as db_session
from app.db.models import SystemErrorLog
from app.services.runtime_config import get_enabled_service_config


class EmailService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _send_smtp(
        self,
        *,
        to_email: str,
        subject: str,
        text_body: str,
        config: dict,
        html_body: str | None = None,
    ) -> None:
        required = ["host", "port", "sender"]
        missing = [key for key in required if not config.get(key)]
        if missing:
            raise bad_request(f"邮件服务配置缺少字段: {', '.join(missing)}")
        username = config.get("username")
        password = config.get("password")
        sender = str(config["sender"])
        if html_body:
            message = MIMEMultipart("alternative")
            message.attach(MIMEText(text_body, "plain", "utf-8"))
            message.attach(MIMEText(html_body, "html", "utf-8"))
        else:
            message = MIMEText(text_body, "plain", "utf-8")
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

    def _send_link_email(
        self,
        db: Session | None,
        *,
        to_email: str,
        subject: str,
        text_body: str,
        html_body: str,
    ) -> None:
        service = get_enabled_service_config(db, "email")
        if service is None:
            raise bad_request("邮件服务未配置，请先在管理员服务配置中启用 email")
        if service.provider != "smtp":
            raise bad_request(f"暂不支持的邮件服务提供方: {service.provider}")
        self._send_smtp(
            to_email=to_email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            config=service.config,
        )

    def _auth_link_template(
        self,
        *,
        title: str,
        subtitle: str,
        body_html: str,
        action_label: str,
        link: str,
        note_html: str = "",
    ) -> str:
        safe_link = escape(link, quote=True)
        current_year = datetime.now().year
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(title)}</title>
</head>
<body style="margin:0;padding:0;background-color:#F8FAFC;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,'PingFang SC','Microsoft YaHei',sans-serif;">
  <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color:#F8FAFC;padding:40px 0;">
    <tr>
      <td align="center">
        <table width="90%" border="0" cellspacing="0" cellpadding="0" style="max-width:540px;background-color:#FFFFFF;border:1px solid #E2E8F0;border-radius:8px;box-shadow:0 4px 6px -1px rgba(0,0,0,0.05);overflow:hidden;">
          <tr>
            <td style="padding:40px 40px 20px 40px;border-bottom:1px solid #F1F5F9;">
              <table width="100%" border="0" cellspacing="0" cellpadding="0">
                <tr>
                  <td style="font-size:22px;font-weight:600;color:#0F172A;">
                    <span style="display:inline-block;margin-right:8px;color:#0A8B9C;font-weight:700;">智</span>{escape(title)}
                  </td>
                </tr>
                <tr>
                  <td style="font-size:12px;color:#64748B;padding-top:8px;font-family:'Courier New',Courier,monospace;letter-spacing:0.5px;">
                    {escape(subtitle)}
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding:30px 40px 40px 40px;">
              <table width="100%" border="0" cellspacing="0" cellpadding="0">
                <tr>
                  <td style="font-size:15px;color:#334155;line-height:1.7;padding-bottom:25px;">
                    {body_html}
                  </td>
                </tr>
                <tr>
                  <td align="left" style="padding-bottom:25px;">
                    <a href="{safe_link}" target="_blank" style="background-color:#0A8B9C;color:#FFFFFF;display:inline-block;padding:12px 32px;font-size:15px;font-weight:500;text-decoration:none;border-radius:6px;">
                      {escape(action_label)}
                    </a>
                  </td>
                </tr>
                {note_html}
                <tr>
                  <td style="font-size:13px;color:#94A3B8;line-height:1.6;border-top:1px dashed #E2E8F0;padding-top:20px;">
                    如果按钮无法点击，请复制以下链接粘贴至浏览器：<br>
                    <a href="{safe_link}" target="_blank" style="color:#0A8B9C;text-decoration:none;word-break:break-all;">{safe_link}</a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
        <table width="90%" border="0" cellspacing="0" cellpadding="0" style="max-width:540px;margin-top:20px;">
          <tr>
            <td align="center" style="font-size:12px;color:#94A3B8;line-height:1.5;">
              此邮件由系统自动发送，请勿直接回复。<br>
              &copy; {current_year} 智学黑板. 保留所有权利。
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    def send_password_reset_link(self, db: Session | None, *, to_email: str, link: str) -> None:
        text_body = (
            "您好！\n\n"
            "我们收到了您账号的密码重置请求。请打开以下链接设置新密码，10 分钟内有效：\n\n"
            f"{link}\n\n"
            "如果您并未请求重置密码，请忽略此邮件。找不到邮件时，请查看垃圾邮件或垃圾箱。"
        )
        html_body = self._auth_link_template(
            title="找回密码",
            subtitle="ClassAgent Learning Console",
            body_html="您好！<br><br>我们收到了您账号的密码重置请求。请点击下方按钮设置您的新密码。链接 10 分钟内有效：",
            action_label="重置密码",
            link=link,
            note_html=(
                '<tr><td style="font-size:14px;color:#64748B;padding-bottom:25px;">'
                "如果您并未请求重置密码，请忽略此邮件。您的账号仍然安全。"
                "</td></tr>"
            ),
        )
        self._send_link_email(
            db,
            to_email=to_email,
            subject="找回您的密码 - 智学黑板",
            text_body=text_body,
            html_body=html_body,
        )

    def send_registration_link(self, db: Session | None, *, to_email: str, link: str) -> None:
        text_body = (
            "您好！\n\n"
            "感谢您注册智学黑板。请打开以下链接验证邮箱地址并完成学生账号注册，10 分钟内有效：\n\n"
            f"{link}\n\n"
            "若非本人操作，请忽略本邮件。找不到邮件时，请查看垃圾邮件或垃圾箱。"
        )
        html_body = self._auth_link_template(
            title="欢迎来到智学黑板",
            subtitle="ClassAgent Learning Console",
            body_html=(
                "您好！<br><br>"
                "感谢您注册。加入课程、继续课时、向 AI 提问，把每天的学习进度稳稳记录下来。"
                "<br><br>请点击下方按钮验证您的邮箱地址，完成最终注册。链接 10 分钟内有效："
            ),
            action_label="验证邮箱地址",
            link=link,
        )
        self._send_link_email(
            db,
            to_email=to_email,
            subject="欢迎来到智学黑板 - 验证您的邮箱",
            text_body=text_body,
            html_body=html_body,
        )

    def _log_background_email_error(self, *, source: str, to_email: str, exc: Exception) -> None:
        try:
            with db_session.SessionLocal() as db:
                db.add(
                    SystemErrorLog(
                        level="error",
                        source=source,
                        message=str(exc),
                        detail={"to_email": to_email},
                    )
                )
                db.commit()
        except Exception:
            pass

    def send_registration_link_background(self, *, to_email: str, link: str) -> None:
        try:
            with db_session.SessionLocal() as db:
                self.send_registration_link(db, to_email=to_email, link=link)
        except Exception as exc:
            self._log_background_email_error(
                source="email.registration_link",
                to_email=to_email,
                exc=exc,
            )

    def send_password_reset_link_background(self, *, to_email: str, link: str) -> None:
        try:
            with db_session.SessionLocal() as db:
                self.send_password_reset_link(db, to_email=to_email, link=link)
        except Exception as exc:
            self._log_background_email_error(
                source="email.password_reset_link",
                to_email=to_email,
                exc=exc,
            )

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
