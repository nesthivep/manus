import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import aiofiles

from app.tool.base import BaseTool
from app.config import config


class EmailSender(BaseTool):
    name: str = "email_sender"
    description: str = """Send an email to a specified recipient.
Use this tool when you need to send emails for notifications, alerts, or any other communication.
The tool accepts the recipient's email address, subject, and body of the email .
"""  
    parameters: dict = {
        "type": "object",
        "properties": {
            "recipient_email": {
                "type": "string",
                "description": "(required) The recipient's email address."
            },
            "subject": {
                "type": "string",
                "description": "(required) The subject of the email."
            },
            "body": {
                "type": "string",
                "description": "(required) The body of the email."
            }
        },
        "required": ["recipient_email", "subject", "body"]
    }

    async def execute(self, recipient_email: str, subject: str, body: str) -> str:
        """
        Send an email using Gmail's SMTP server.

        Args:
            recipient_email (str): The recipient's email address.
            subject (str): The subject of the email.
            body (str): The body of the email.

        Returns:
            str: A message indicating the result of the email sending operation.
        """
        try:
            sender_email = config.email.sender_email
            app_password = config.email.app_password
            print(f"email send config {sender_email}")
            print(f"email send config {app_password}")
            # Create a multipart message
            message = MIMEMultipart()
            message['From'] = sender_email
            message['To'] = recipient_email
            message['Subject'] = subject
            message.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()  # Secure the connection
            server.login(sender_email, app_password)

            # Send the email
            server.sendmail(sender_email, recipient_email, message.as_string())
            server.quit()

            return f"Email successfully send to {recipient_email}"
        except Exception as e:
            return f"Failed to send email to {recipient_email}: {str(e)}"