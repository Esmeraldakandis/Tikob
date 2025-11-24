import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
FROM_EMAIL = os.environ.get('FROM_EMAIL', 'noreply@tikob.app')

def send_email(to_email, subject, html_content):
    """Send email using SendGrid"""
    if not SENDGRID_API_KEY:
        print(f"WARNING: SENDGRID_API_KEY not set. Would send email to {to_email}: {subject}")
        return False
    
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        message = Mail(
            from_email=FROM_EMAIL,
            to_emails=to_email,
            subject=subject,
            html_content=html_content
        )
        response = sg.send(message)
        return response.status_code == 202
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def send_contribution_notification(user_email, group_name, amount, contributor_name):
    """Notify group members of a new contribution"""
    subject = f"New Contribution in {group_name}"
    html_content = f"""
    <html>
        <body style="font-family: 'Playfair Display', serif; background-color: #F5F3EF; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 8px;">
                <h2 style="color: #1A3A52;">💰 New Contribution</h2>
                <p>Great news! <strong>{contributor_name}</strong> just contributed <strong>${amount:.2f}</strong> to <strong>{group_name}</strong>.</p>
                <p style="color: #666;">Keep up the great savings momentum!</p>
                <hr style="border: 1px solid #D4AF37; margin: 20px 0;">
                <p style="font-size: 12px; color: #999;">TiKòb - Community Savings Made Simple</p>
            </div>
        </body>
    </html>
    """
    return send_email(user_email, subject, html_content)

def send_approval_notification(user_email, group_name, approved=True):
    """Notify user of approval/rejection"""
    status = "approved" if approved else "rejected"
    emoji = "✅" if approved else "❌"
    subject = f"Your request to join {group_name} has been {status}"
    
    html_content = f"""
    <html>
        <body style="font-family: 'Playfair Display', serif; background-color: #F5F3EF; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 8px;">
                <h2 style="color: #1A3A52;">{emoji} Membership {status.title()}</h2>
                <p>Your request to join <strong>{group_name}</strong> has been <strong>{status}</strong>.</p>
                {"<p>You can now start contributing and tracking your savings with the group!</p>" if approved else "<p>Please contact the group admin for more information.</p>"}
                <hr style="border: 1px solid #D4AF37; margin: 20px 0;">
                <p style="font-size: 12px; color: #999;">TiKòb - Community Savings Made Simple</p>
            </div>
        </body>
    </html>
    """
    return send_email(user_email, subject, html_content)

def send_badge_notification(user_email, badge_name, badge_description):
    """Notify user of new badge achievement"""
    subject = f"🏆 You earned a new badge: {badge_name}!"
    
    html_content = f"""
    <html>
        <body style="font-family: 'Playfair Display', serif; background-color: #F5F3EF; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 8px;">
                <h2 style="color: #D4AF37;">🏆 Achievement Unlocked!</h2>
                <h3 style="color: #1A3A52;">{badge_name}</h3>
                <p>{badge_description}</p>
                <p style="color: #666;">Keep up the amazing work on your savings journey!</p>
                <hr style="border: 1px solid #D4AF37; margin: 20px 0;">
                <p style="font-size: 12px; color: #999;">TiKòb - Community Savings Made Simple</p>
            </div>
        </body>
    </html>
    """
    return send_email(user_email, subject, html_content)

def send_payout_notification(user_email, group_name, amount, recipient_name):
    """Notify group members of a payout"""
    subject = f"Payout from {group_name}"
    html_content = f"""
    <html>
        <body style="font-family: 'Playfair Display', serif; background-color: #F5F3EF; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 8px;">
                <h2 style="color: #1A3A52;">💸 Payout Recorded</h2>
                <p><strong>{recipient_name}</strong> received a payout of <strong>${amount:.2f}</strong> from <strong>{group_name}</strong>.</p>
                <p style="color: #666;">Transaction logged successfully.</p>
                <hr style="border: 1px solid #D4AF37; margin: 20px 0;">
                <p style="font-size: 12px; color: #999;">TiKòb - Community Savings Made Simple</p>
            </div>
        </body>
    </html>
    """
    return send_email(user_email, subject, html_content)
