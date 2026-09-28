import os
import smtplib
import urllib.parse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASS = os.getenv("SMTP_PASS", "").strip()
TRACKING_BASE_URL = os.getenv("TRACKING_BASE_URL", "http://localhost:8085").strip()

class EmailDispatcher:
    def __init__(self):
        self.smtp_host = SMTP_HOST
        self.smtp_port = SMTP_PORT
        self.smtp_user = SMTP_USER
        self.smtp_pass = SMTP_PASS
        self.tracking_url = TRACKING_BASE_URL

    def inject_tracking(self, text_body: str, tracking_id: str, links_to_wrap: list[str] = None) -> tuple[str, str]:
        """
        Produces plaintext and HTML bodies with tracking pixel and wrapped click links.
        """
        links_to_wrap = links_to_wrap or []
        
        # Convert plain text to basic HTML paragraphs
        html_paragraphs = "".join([f"<p>{p.replace(chr(10), '<br/>')}</p>" for p in text_body.split("\n\n")])
        
        # Wrap links with click tracker
        wrapped_html = html_paragraphs
        for link in links_to_wrap:
            encoded = urllib.parse.quote(link, safe="")
            tracked_link = f"{self.tracking_url}/t/c/{tracking_id}?url={encoded}"
            wrapped_html = wrapped_html.replace(link, f'<a href="{tracked_link}" target="_blank">{link}</a>')
        
        # Inject 1x1 tracking pixel
        pixel_tag = f'<img src="{self.tracking_url}/t/o/{tracking_id}" width="1" height="1" alt="" style="display:none;" />'
        final_html = f"<html><body>{wrapped_html}{pixel_tag}</body></html>"
        
        return text_body, final_html

    def send_email(
        self,
        to_email: str,
        subject: str,
        plain_body: str,
        html_body: str,
        attachment_path: Path = None
    ) -> dict:
        """
        Sends email via SMTP or runs in DRY_RUN mode if credentials are not set.
        """
        if not self.smtp_user or not self.smtp_pass:
            print(f"[Dispatcher DRY_RUN] Would send to {to_email} with subject: {subject}")
            return {"status": "dry_run", "message": "SMTP credentials not provided; logged as dry run."}

        sender_name = os.getenv("CANDIDATE_NAME", "Candidate")
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{sender_name} <{self.smtp_user}>"
        msg["To"] = to_email
        msg["Subject"] = subject

        part1 = MIMEText(plain_body, "plain")
        part2 = MIMEText(html_body, "html")
        msg.attach(part1)
        msg.attach(part2)

        if attachment_path and attachment_path.exists():
            with open(attachment_path, "rb") as f:
                attach = MIMEApplication(f.read(), _subtype="pdf")
                attach.add_header("Content-Disposition", "attachment", filename=attachment_path.name)
                msg.attach(attach)

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=15) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.sendmail(self.smtp_user, [to_email], msg.as_string())
            print(f"[Dispatcher Success] Email dispatched to {to_email}")
            return {"status": "sent", "message": "Email sent successfully."}
        except Exception as e:
            print(f"[Dispatcher Error]: {e}")
            return {"status": "failed", "error": str(e)}
