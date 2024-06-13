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

def app():
    app = Flask(__name__)
    CORS(app)  # Enable CORS for all routes

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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4515.107 Safari/537.36"
    }

    session = requests.Session()
    session_lock = threading.Lock()

    def log_notification(userid, title, content, ncamp):
        data = {
            "userid": userid,
            "n_title": title,
            "campaign_name": ncamp,
            "n_content": content,
            "sent_at": datetime.utcnow().isoformat()
        }
        response = supabase.table('notification_recipients').insert(data).execute()
        print(response)
        print(f"Notification sent to user {userid} successfully.")

    def login():
        global session
        with session_lock:
            payload = {
                "email": CIL_EMAIL,
                "password": CIL_PASSWORD,
                "timezone": "Africa/Cairo"
            }
            login_response = session.post(url=CIL_LOGIN_URL, data=payload, headers=HEADER)
            return "Invalid email or password" not in login_response.text

    def send_notification(custid, ntitle, ncontent, ncamp):
        payload = {
            "notify_type": "Push_Notification",
            "title": ntitle,
            "content": ncontent,
            "user_type": "Customer",
            "user_ids[]": custid,
        }
        with session_lock:
            create_notif_response = session.post(url=CIL_NOTIF_URL, data=payload, headers=HEADER)
            if create_notif_response.status_code != 200:
                print(f"Error creating notification: {create_notif_response.text}")
            else:
                log_notification(custid, ntitle, ncontent, ncamp)

    def sendemail(ncamp, ntitle, ncontent, nsize):
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
        print('Email sent successfully!')

    @app.route('/send-notification', methods=['POST'])
    def send_notification_endpoint():
        data = request.json
        user_ids = data.get('user_ids', [])
        ntitle = data.get('title')
        ncontent = data.get('content')
        ncamp = data.get('campaign')

        if not login():
            return jsonify({'error': 'Login failed'}), 401

        def process_notification(user_id):
            send_notification(user_id, ntitle, ncontent, ncamp)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(process_notification, user_id) for user_id in user_ids]
            for future in as_completed(futures):
                future.result()

        sendemail(ncamp, ntitle, ncontent, len(user_ids))
        return jsonify({'message': 'Notifications sent successfully'})

    return app

if __name__ == '__main__':
    app = app()
    app.run(debug=True)
