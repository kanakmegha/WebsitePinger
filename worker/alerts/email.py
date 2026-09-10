import smtplib
from email.mime.text import MIMEText
from worker.config import SMTP_USER, SMTP_PASS, ALERT_EMAIL

def send_alert(message):
    if not SMTP_USER:
        print("[ALERT]", message)
        return

    msg = MIMEText(message)
    msg["Subject"] = "Website Alert"
    msg["From"] = SMTP_USER
    msg["To"] = ALERT_EMAIL

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
    except Exception as e:
        print("Email error:", e)
