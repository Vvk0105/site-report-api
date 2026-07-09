import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

from fastapi import UploadFile
from email.mime.application import MIMEApplication

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

    async def send_report_pdf(
        self,
        pdf: UploadFile,
        to_email: str,
        cc_email: str | None,
        subject: str,
        body: str,
        inspector_name: str,
        inspector_email: str,
    ):
        message = MIMEMultipart()

        message["From"] = f"{inspector_name} <{settings.SMTP_FROM}>"
        message["Reply-To"] = inspector_email
        message["To"] = to_email
        
        if cc_email:
            message["Cc"] = cc_email

        message["Subject"] = subject

        html = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, Helvetica, sans-serif; font-size:14px; color:#333;">
            {body.replace("\n", "<br>")}
        </body>
        </html>
        """

        message.attach(
            MIMEText(
                html,
                "html",
            )
        )

        pdf_bytes = await pdf.read()

        attachment = MIMEApplication(
            pdf_bytes,
            _subtype="pdf",
        )

        attachment.add_header(
            "Content-Disposition",
            "attachment",
            filename=pdf.filename,
        )

        message.attach(attachment)

        recipients = [to_email]

        if cc_email:
            recipients.append(cc_email)

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
            recipients,
            message.as_string(),
        )

        server.quit()