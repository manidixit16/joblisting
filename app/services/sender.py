"""Send an approved application by email.

Safety model:
- Only applications with status == approved may be sent (enforced by caller).
- EMAIL_DRY_RUN (default true) writes a .eml file to ./outbox instead of
  actually sending, so you can verify everything before going live.
"""
from __future__ import annotations

import os
import smtplib
import ssl
from datetime import datetime, timezone
from email.message import EmailMessage

from ..config import get_settings

OUTBOX_DIR = "outbox"


class SendResult:
    def __init__(self, delivered: bool, detail: str):
        self.delivered = delivered
        self.detail = detail


def _build_message(to_email: str, subject: str, body: str, attachments: dict[str, str]) -> EmailMessage:
    s = get_settings()
    msg = EmailMessage()
    from_addr = s.from_email or s.smtp_username or "no-reply@example.com"
    msg["From"] = f"{s.from_name} <{from_addr}>" if s.from_name else from_addr
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)
    for filename, content in attachments.items():
        msg.add_attachment(
            content.encode("utf-8"),
            maintype="text",
            subtype="plain",
            filename=filename,
        )
    return msg


def send_application(
    to_email: str,
    subject: str,
    body: str,
    resume: str = "",
    cover_letter: str = "",
) -> SendResult:
    """Send (or dry-run) an application email. Returns a SendResult."""
    if not to_email:
        return SendResult(False, "No recipient email address available for this job.")

    attachments: dict[str, str] = {}
    if resume:
        attachments["resume.txt"] = resume
    if cover_letter:
        attachments["cover_letter.txt"] = cover_letter

    msg = _build_message(to_email, subject, body, attachments)
    s = get_settings()

    if s.email_dry_run or not s.smtp_host:
        os.makedirs(OUTBOX_DIR, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        safe = to_email.replace("@", "_at_").replace("/", "_")
        path = os.path.join(OUTBOX_DIR, f"{stamp}-{safe}.eml")
        with open(path, "wb") as fh:
            fh.write(bytes(msg))
        return SendResult(True, f"DRY RUN: written to {path} (no email actually sent).")

    try:
        if s.smtp_use_tls:
            context = ssl.create_default_context()
            with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=30) as server:
                server.starttls(context=context)
                if s.smtp_username:
                    server.login(s.smtp_username, s.smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=30) as server:
                if s.smtp_username:
                    server.login(s.smtp_username, s.smtp_password)
                server.send_message(msg)
    except Exception as exc:  # noqa: BLE001 - surface any SMTP error to the user
        return SendResult(False, f"SMTP error: {exc}")

    return SendResult(True, f"Sent to {to_email}.")
