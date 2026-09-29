import os
import smtplib
import urllib.parse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path

def _load_env_if_needed():
    """Fallback loader for .env without requiring python-dotenv."""
    for base_dir in [Path.cwd(), Path(__file__).resolve().parent.parent.parent]:
        env_file = base_dir / ".env"
        if env_file.exists():
            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k not in os.environ:
                            os.environ[k] = v
                break
            except Exception:
                pass

_load_env_if_needed()

class EmailDispatcher:
    def __init__(self):
        _load_env_if_needed()
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "").strip()
        self.smtp_pass = os.getenv("SMTP_PASS", "").strip()
        self.tracking_url = os.getenv("TRACKING_BASE_URL", "http://localhost:8085").strip()

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
        except smtplib.SMTPAuthenticationError as auth_err:
            err_str = str(auth_err)
            if "5.7.9" in err_str or "Application-specific password" in err_str:
                hint = (
                    "Gmail requires a 16-character App Password (not your personal Google account password).\n"
                    "Generate one at: https://myaccount.google.com/apppasswords and set SMTP_PASS in .env"
                )
            else:
                hint = "SMTP Authentication failed. Please check SMTP_USER and SMTP_PASS."
            print(f"[Dispatcher Error]: {auth_err}\n[Hint]: {hint}")
            return {"status": "failed", "error": err_str, "hint": hint}
        except Exception as e:
            print(f"[Dispatcher Error]: {e}")
            return {"status": "failed", "error": str(e)}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ascend Outreach Email Dispatcher")
    parser.add_argument("--to", required=True, help="Recipient email address")
    parser.add_argument("--subject", default="⚡ Ascend Engine: Test Outreach Dispatch", help="Email subject")
    parser.add_argument("--attach-cv", action="store_true", help="Attach generated CV PDF if found")
    args = parser.parse_args()

    dispatcher = EmailDispatcher()
    sample_text = (
        "Hello,\n\n"
        "This is an automated test dispatch from the Ascend Career Acceleration Engine.\n"
        "All telemetry tracking links and SMTP delivery pipelines are functioning.\n\n"
        "Target Scale Repository: https://github.com/nainwalsanju/ascend\n\n"
        "Best regards,\n"
        f"{os.getenv('CANDIDATE_NAME', 'Candidate')}"
    )
    plain, html = dispatcher.inject_tracking(sample_text, "cli-test-tracking-001", ["https://github.com/nainwalsanju/ascend"])
    
    cv_path = None
    if args.attach_cv:
        possible = Path.cwd() / "resume" / "rendercv_output" / "Sanjay_Nainwal_CV.pdf"
        if possible.exists():
            cv_path = possible

    result = dispatcher.send_email(
        to_email=args.to,
        subject=args.subject,
        plain_body=plain,
        html_body=html,
        attachment_path=cv_path
    )
    print("\nResult:", result)

