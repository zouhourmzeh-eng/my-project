import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings
import os

def send_recovery_email(to_email: str, code: str):
    smtp_host = settings.SMTP_HOST
    smtp_port = settings.SMTP_PORT
    smtp_user = settings.SMTP_USER
    smtp_pass = settings.SMTP_PASS.replace(" ", "")
    smtp_from = settings.SMTP_FROM

    print(f"DEBUG: Attempting to send recovery email to user email: {to_email}...")
    # If not configured, just log to console
    if not all([smtp_host, smtp_user, smtp_pass, smtp_from]):
        print(f"\n[MOCK EMAIL] To: {to_email} | Code: {code}")
        print("Set SMTP_HOST, SMTP_USER, etc. in .env to send real emails.\n")
        return

    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_from
        msg["To"] = to_email
        msg["Subject"] = "QMS SMQ - Password Recovery Code"

        body = f"""
        Hello,

        Your password recovery code is: {code}

        This code will expire in 15 minutes.
        If you did not request this, please ignore this email.

        Best regards,
        QMS Platform Team
        """
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            # Explicitly set to_addrs to ensure it is sent to the requested user's email 
            # and not defaulted or overridden by the SMTP server
            server.send_message(msg, to_addrs=[to_email])
        print(f"Email sent successfully directly to user: {to_email}")
    except Exception as e:
        print(f"Failed to send email to {to_email}: {str(e)}")


def send_verification_email(to_email: str, code: str):
    smtp_host = settings.SMTP_HOST
    smtp_port = settings.SMTP_PORT
    smtp_user = settings.SMTP_USER
    smtp_pass = settings.SMTP_PASS.replace(" ", "")
    smtp_from = settings.SMTP_FROM

    print(f"DEBUG: Attempting to send verification email to user email: {to_email}...")
    # If not configured, just log to console
    if not all([smtp_host, smtp_user, smtp_pass, smtp_from]):
        print(f"\n[MOCK EMAIL] To: {to_email} | Code: {code}")
        print("Set SMTP_HOST, SMTP_USER, etc. in .env to send real emails.\n")
        return

    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_from
        msg["To"] = to_email
        msg["Subject"] = "QMS SMQ - Email Verification Code"

        body = f"""
        Hello,

        Thank you for registering on the QMS Platform.
        Your email verification code is: {code}

        This code will expire in 5 minutes.
        If you did not request this, please ignore this email.

        Best regards,
        QMS Platform Team
        """
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg, to_addrs=[to_email])
        print(f"Verification email sent successfully to: {to_email}")
    except Exception as e:
        print(f"Failed to send verification email to {to_email}: {str(e)}")
