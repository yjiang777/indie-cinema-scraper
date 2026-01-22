"""Email notification service using SendGrid"""
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import os

class EmailService:
    def __init__(self):
        self.api_key = os.environ.get('SENDGRID_API_KEY')
        self.from_email = os.environ.get('FROM_EMAIL')
        
        if not self.api_key:
            raise ValueError("SENDGRID_API_KEY not set")
        if not self.from_email:
            raise ValueError("FROM_EMAIL not set")
        
        self.client = SendGridAPIClient(self.api_key)
    
    def send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """Send an email"""
        try:
            message = Mail(
                from_email=self.from_email,
                to_emails=to_email,
                subject=subject,
                html_content=html_content
            )
            
            response = self.client.send(message)
            return response.status_code == 202
            
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
    
    def send_director_screening_alert(self, user_email: str, director: str, screenings: list) -> bool:
        """Send alert for new director screenings"""
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #667eea;">🎬 New {director} Screenings!</h2>
            <p>Great news! We found new screenings for one of your favorite directors:</p>
            
            <div style="background: #f5f5f5; padding: 20px; border-radius: 10px; margin: 20px 0;">
                {''.join([f'''
                <div style="margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px solid #ddd;">
                    <h3 style="margin: 0 0 5px 0; color: #333;">{s['title']}</h3>
                    <p style="margin: 5px 0; color: #666;">
                        📍 {s['theater']}<br>
                        📅 {s['datetime']}<br>
                        {f'<a href="{s["ticket_url"]}" style="color: #667eea;">Get Tickets →</a>' if s.get('ticket_url') else ''}
                    </p>
                </div>
                ''' for s in screenings])}
            </div>
            
            <p>
                <a href="http://127.0.0.1:5000/dashboard" 
                   style="background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">
                    View in Dashboard
                </a>
            </p>
            
            <p style="color: #999; font-size: 0.9em; margin-top: 40px;">
                You're receiving this because {director} is one of your favorite directors.
                <br>
                <a href="http://127.0.0.1:5000/dashboard" style="color: #667eea;">Manage your favorites</a>
            </p>
        </body>
        </html>
        """
        
        return self.send_email(
            to_email=user_email,
            subject=f"🎬 New {director} Screenings in LA!",
            html_content=html
        )

    def send_theater_screening_alert(self, user_email: str, theater_name: str, screenings: list) -> bool:
        """Send alert for new screenings at a favorite theater"""
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #667eea;">🎭 New Screenings at {theater_name}!</h2>
            <p>Great news! New screenings have been added at one of your favorite theaters:</p>

            <div style="background: #f5f5f5; padding: 20px; border-radius: 10px; margin: 20px 0;">
                {''.join([f'''
                <div style="margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px solid #ddd;">
                    <h3 style="margin: 0 0 5px 0; color: #333;">{s['title']}</h3>
                    <p style="margin: 5px 0; color: #666;">
                        🎬 Directed by {s['director']}<br>
                        📅 {s['datetime']}<br>
                        {f'<a href="{s["ticket_url"]}" style="color: #667eea;">Get Tickets →</a>' if s.get('ticket_url') else ''}
                    </p>
                </div>
                ''' for s in screenings])}
            </div>

            <p>
                <a href="http://127.0.0.1:5000/dashboard"
                   style="background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">
                    View in Dashboard
                </a>
            </p>

            <p style="color: #999; font-size: 0.9em; margin-top: 40px;">
                You're receiving this because {theater_name} is one of your favorite theaters.
                <br>
                <a href="http://127.0.0.1:5000/dashboard" style="color: #667eea;">Manage your favorites</a>
            </p>
        </body>
        </html>
        """

        return self.send_email(
            to_email=user_email,
            subject=f"🎭 New Screenings at {theater_name}!",
            html_content=html
        )