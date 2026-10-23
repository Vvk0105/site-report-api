import html
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from app.core.config import settings
from app.utils.email import clean_header, display_address

SMTP_TIMEOUT_SECONDS = 30


class EmailService:

    async def _send(self, message: MIMEMultipart, recipients: list[str]) -> None:
        # aiosmtplib is async, so SMTP I/O no longer blocks the event loop.
        await aiosmtplib.send(
            message,
            sender=settings.SMTP_FROM,
            recipients=recipients,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USERNAME,
            password=settings.SMTP_PASSWORD,
            use_tls=settings.SMTP_SSL,
            start_tls=False if settings.SMTP_SSL else None,
            timeout=SMTP_TIMEOUT_SECONDS,
        )

    async def send_otp(self, email: str, otp: str) -> None:
        message = MIMEMultipart()
        message["From"] = settings.SMTP_FROM
        message["To"] = email
        message["Subject"] = "Your Site Reports Login OTP"

        html_body = f"""
        <html>
        <body>
        <h2>Site Reports</h2>
        <p>Your OTP is</p>
        <h1>{html.escape(otp)}</h1>
        <p>This OTP expires in 5 minutes.</p>
        </body>
        </html>
        """

        message.attach(MIMEText(html_body, "html", "utf-8"))

        await self._send(message, [email])

    async def send_report_pdf(
        self,
        *,
        pdf_bytes: bytes,
        filename: str,
        to_email: str,
        cc_email: str | None,
        subject: str,
        body: str,
        inspector_name: str,
        inspector_email: str,
    ) -> None:
        message = MIMEMultipart()
        message["From"] = display_address(inspector_name, settings.SMTP_FROM)
        message["Reply-To"] = clean_header(inspector_email)
        message["To"] = clean_header(to_email)

        recipients = [to_email]

        if cc_email:
            message["Cc"] = clean_header(cc_email)
            recipients.append(cc_email)

        message["Subject"] = clean_header(subject)

        # Escape the free-text body so it cannot inject markup into the email.
        safe_body = html.escape(body).replace("\n", "<br>")

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, Helvetica, sans-serif; font-size:14px; color:#333;">
            {safe_body}
        </body>
        </html>
        """

        message.attach(MIMEText(html_body, "html", "utf-8"))

        attachment = MIMEApplication(pdf_bytes, _subtype="pdf")
        attachment.add_header(
            "Content-Disposition",
            "attachment",
            filename=clean_header(filename) or "report.pdf",
        )
        message.attach(attachment)

        await self._send(message, recipients)
