from django.core.mail import send_mail
from django.conf import settings
from smtplib import SMTPException
import logging
import traceback

def send_password_reset_email(user, token, frontend_url):
    reset_url = f"{frontend_url}/reset-password/{token}"
    
    subject = "Password Reset Request - Lily Shop"
    
    html_message = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #f8f9fa; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; }}
            .button {{ display: inline-block; background-color: #007bff; color: white; 
                      padding: 10px 20px; text-decoration: none; border-radius: 4px; }}
            .footer {{ font-size: 12px; color: #6c757d; margin-top: 30px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>Password Reset</h2>
            </div>
            <div class="content">
                <p>Hello {user.username},</p>
                <p>We received a request to reset your password for your Lily Shop account.</p>
                <p>Click the button below to reset your password:</p>
                <p style="text-align: center;">
                    <a href="{reset_url}" class="button">Reset Password</a>
                </p>
                <p>If you didn't request a password reset, you can ignore this email.</p>
                <p>This link will expire in 30 minutes.</p>
                <p>If the button above doesn't work, copy and paste this URL into your browser:</p>
                <p>{reset_url}</p>
            </div>
            <div class="footer">
                <p>© {settings.SITE_NAME if hasattr(settings, 'SITE_NAME') else 'Lily Shop'} - All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    plain_message = f"""
    Hello {user.username},
    
    We received a request to reset your password for your Lily Shop account.
    
    Please go to the following link to reset your password:
    {reset_url}
    
    If you didn't request a password reset, you can ignore this email.
    
    This link will expire in 30 minutes.
    
    Best regards,
    Lily Shop Team
    """
    
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False, 
        )
        return True, "Email sent successfully"
    except SMTPException as e:
        error_msg = f"SMTP error sending email to {user.email}: {str(e)}"
        logging.error(error_msg)
        return False, error_msg
    except ConnectionRefusedError as e:
        error_msg = f"Connection refused error: {str(e)}"
        logging.error(error_msg)
        return False, error_msg 
    except Exception as e:
        error_msg = f"Unexpected error sending email: {str(e)}\n{traceback.format_exc()}"
        logging.error(error_msg)
        return False, error_msg