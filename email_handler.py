import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_HOST = "smtp.hostinger.com"
SMTP_PORT = 465
SENDER_EMAIL = "info@vouches.my"
SENDER_PASSWORD = "CAWES30/1!a" 
RECIPIENT_EMAIL = "mueller.david@mail.com"

def send_vouch_notification(vouch_by, vouch_text):
    """Sends a standardized email notification when a new vouch is added."""
    subject = f"New Vouch Added from Telegram Bot ({vouch_by})"
    body = (
        f"Source: Telegram Bot\n"
        f"User: {vouch_by}\n"
        f"Vouch: {vouch_text}"
    )

    message = MIMEMultipart()
    message["From"] = SENDER_EMAIL
    message["To"] = RECIPIENT_EMAIL
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, message.as_string())
        print(f"Email notification for vouch by {vouch_by} sent successfully.")
        return True
    except Exception as e:
        print(f"ERROR: Could not send email for vouch by {vouch_by}. Reason: {e}")
        return False