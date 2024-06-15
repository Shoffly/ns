from flask import Flask, request, jsonify
import requests
import threading
import smtplib
import ssl
from email.message import EmailMessage
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from supabase import create_client, Client
from flask_cors import CORS
import logging

def app():
    app = Flask(__name__)
    CORS(app)  # Enable CORS for all routes
    
    # Set up logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Supabase client setup
    supabase_url = 'https://zkkjvqlrfaorjwwcnlkz.supabase.co'
    supabase_key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inpra2p2cWxyZmFvcmp3d2NubGt6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MTY0NDg5NjIsImV4cCI6MjAzMjAyNDk2Mn0.nrhg7Dd7Z7hNyd6RElwzY0URzYN-UW5BiMYdvOmzk2g'
    supabase: Client = create_client(supabase_url, supabase_key)
    
    # Notification login and sending
    CIL_LOGIN_URL = 'https://appadmin.cilantro.cafe/authpanel/login/checklogin'
    CIL_NOTIF_URL = 'https://appadmin.cilantro.cafe/authpanel/notification/add'
    CIL_EMAIL = "admin@cilantro.com"
    CIL_PASSWORD = "admin@123"
    HEADER = {
        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4515.107 Safari/537.36"
    }
    
    # Define session and session_lock at the global level
    session = requests.Session()
    session_lock = threading.Lock()
    
    
    def log_notification(userid, title, content, ncamp):
        try:
            data = {
                "userid": userid,
                "n_title": title,
                "campaign_name": ncamp,
                "n_content": content,
                "sent_at": datetime.utcnow().isoformat()
            }
            response = supabase.table('notification_recipients').insert(
                data).execute()
            logging.info(f"Notification sent to user {userid} successfully.")
            logging.debug(response)
        except Exception as e:
            logging.error(f"Error logging notification: {e}")
    
    
    def login():
        with session_lock:
            payload = {
                "email": CIL_EMAIL,
                "password": CIL_PASSWORD,
                "timezone": "Africa/Cairo"
            }
            login_response = session.post(url=CIL_LOGIN_URL,
                                          data=payload,
                                          headers=HEADER)
            if "Invalid email or password" in login_response.text:
                logging.error("Login failed")
                return False
            return True
    
    
    def send_notification(user, ntitle, ncontent, ncamp):
        personalized_content = ncontent.replace("{first_name}", user["first_name"])
        personalized_title = ntitle.replace("{first_name}", user["first_name"])
        payload = {
            "notify_type": "Push_Notification",
            "title": personalized_title,
            "content": personalized_content,
            "user_type": "Customer",
            "user_ids[]": user["user_id"],
        }
        with session_lock:
            create_notif_response = session.post(url=CIL_NOTIF_URL,
                                                 data=payload,
                                                 headers=HEADER)
            if create_notif_response.status_code != 200:
                logging.error(
                    f"Error creating notification: {create_notif_response.text}")
            else:
                log_notification(user["user_id"], personalized_title,
                                 personalized_content, ncamp)
    
    
    def sendemail(ncamp, ntitle, ncontent, nsize):
        try:
            email_sender = 'sunnymoh44@gmail.com'
            email_p = 'qywokurzqrfpcufp'
            email_to = 'yara.elkassabi@cilantrocafe.net'
            subject = f'Auto Notification report - {ncamp}'
            body = f'''
            <html>
            <body>
                <p>Hey,</p>
                <p>Below are the details of the campaign:</p>
                <table>
                    <tr>
                        <td><strong>Title:</strong></td>
                        <td>{ntitle}</td>
                    </tr>
                    <tr>
                        <td><strong>Content:</strong></td>
                        <td>{ncontent}</td>
                    </tr>
                    <tr>
                        <td><strong>Audience Size:</strong></td>
                        <td>{nsize}</td>
                    </tr>
                </table>
                <p>Thank you!</p>
                <p>Best regards,</p>
                <p>Galil</p>
            </body>
            </html>
            '''
            em = EmailMessage()
            em['From'] = email_sender
            em['To'] = email_to
            em['Subject'] = subject
            em.add_alternative(body, subtype='html')
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
                smtp.login(email_sender, email_p)
                smtp.sendmail(email_sender, email_to, em.as_string())
            logging.info('Email sent successfully!')
        except Exception as e:
            logging.error(f"Error sending email: {e}")
    
    
    @app.route('/send-notification', methods=['POST'])
    def send_notification_endpoint():
        try:
            data = request.json
            if not isinstance(data, dict):
                logging.error("Received data is not a dictionary")
                return jsonify({'error': 'Invalid input format'}), 400
    
            users = data.get('users', [])
            if not isinstance(users, list):
                logging.error("Users data is not a list")
                return jsonify({'error': 'Invalid users format'}), 400
    
            ntitle = data.get('title')
            ncontent = data.get('content')
            ncamp = data.get('campaign')
    
            if not login():
                return jsonify({'error': 'Login failed'}), 401
    
            # Check if each user in the users list is a dictionary with the required keys
            for user in users:
                if not isinstance(user, dict):
                    logging.error("User data is not a dictionary")
                    return jsonify({'error': 'Invalid user format'}), 400
                if 'user_id' not in user or 'first_name' not in user:
                    logging.error("User dictionary missing required keys")
                    return jsonify({'error':
                                    'User data missing required keys'}), 400
    
            def process_notification(user):
                send_notification(user, ntitle, ncontent, ncamp)
    
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [
                    executor.submit(process_notification, user) for user in users
                ]
                for future in as_completed(futures):
                    future.result()
    
            sendemail(ncamp, ntitle, ncontent, len(users))
            return jsonify({'message': 'Notifications sent successfully'})
        except Exception as e:
            logging.error(f"Error in send_notification_endpoint: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    return app
    

if __name__ == '__main__':
    app = app()
    app.run(debug=True)
