import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings


class EmailService:

    async def send_otp(
        self,
        email: str,
        otp: str,
    ):

        message = MIMEMultipart()

        message["From"] = settings.SMTP_FROM

        message["To"] = email

        message["Subject"] = "Your Site Reports Login OTP"

        html = f"""
        <html>
        <body>

        <h2>Site Reports</h2>

        <p>Your OTP is</p>

        <h1>{otp}</h1>

        <p>This OTP expires in 5 minutes.</p>

        </body>
        </html>
        """

        message.attach(
            MIMEText(
                html,
                "html",
            )
        )

        if settings.SMTP_SSL:

            server = smtplib.SMTP_SSL(
                settings.SMTP_HOST,
                settings.SMTP_PORT,
            )

        else:

            server = smtplib.SMTP(
                settings.SMTP_HOST,
                settings.SMTP_PORT,
            )

            server.starttls()

        server.login(
            settings.SMTP_USERNAME,
            settings.SMTP_PASSWORD,
        )

        server.sendmail(
            settings.SMTP_FROM,
            email,
            message.as_string(),
        )

        server.quit()