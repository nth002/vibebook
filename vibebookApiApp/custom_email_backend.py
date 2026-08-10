# custom_email_backend.py
from django.core.mail.backends.smtp import EmailBackend
import smtplib
import ssl

class CustomEmailBackend(EmailBackend):
    def open_connection(self):
        """
        Opens a connection to the email server with proper SSL/TLS handling
        """
        if self.connection:
            return False

        try:
            if self.use_ssl:
                # For SSL (Port 465)
                context = ssl.create_default_context()
                self.connection = smtplib.SMTP_SSL(
                    host=self.host,
                    port=self.port,
                    timeout=self.timeout,
                    context=context
                )
            else:
                # For TLS (Port 587)
                self.connection = smtplib.SMTP(
                    host=self.host,
                    port=self.port,
                    timeout=self.timeout
                )
                if self.use_tls:
                    context = ssl.create_default_context()
                    self.connection.starttls(context=context)
            
            if self.username and self.password:
                self.connection.login(self.username, self.password)
            return True
        except Exception as e:
            if self.connection:
                self.connection.close()
                self.connection = None
            raise