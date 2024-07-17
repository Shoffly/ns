from flask import Flask, request, jsonify
import requests
import threading
import resend
import csv
import io
import base64
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from supabase import create_client, Client
from flask_cors import CORS
import logging

# APScheduler imports
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from pytz import timezone


def app():
    app = Flask(__name__)
    # Enable CORS for specific routes
    CORS(app, resources={
        r"/send-notification": {"origins": "*"},
        r"/schedule-notification": {"origins": "*"},
        r"/send-sms": {"origins": "*"},
        r"/schedule-sms": {"origins": "*"}
    })  # Allow all origins for both send-notification and schedule-notification

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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4515.107 Safari/537.36"
    }

    # Define session and session_lock at the global level
    session = requests.Session()
    session_lock = threading.Lock()

    # APScheduler setup
    scheduler = BackgroundScheduler(timezone=timezone('Africa/Cairo'))
    scheduler.start()

    def log_notification(userid, title, content, ncamp):
        try:
            data = {
                "userid": userid,
                "n_title": title,
                "campaign_name": ncamp,
                "n_content": content,
                "sent_at": datetime.utcnow().isoformat()
            }
            response = supabase.table('notification_recipients').insert(data).execute()
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
            login_response = session.post(url=CIL_LOGIN_URL, data=payload, headers=HEADER)
            if "Invalid email or password" in login_response.text:
                logging.error("Login failed")
                return False
            return True

    def send_notification(user, ntitle, ncontent, ncamp):
        personalized_content = ncontent.replace("{first_name}", user["first_name"])
        personalized_contentf = personalized_content.replace("{fav_item}", user["fav_item"])
        personalized_title = ntitle.replace("{first_name}", user["first_name"])
        personalized_titlef = personalized_title.replace("{fav_item}", user["fav_item"])
        payload = {
            "notify_type": "Push_Notification",
            "title": personalized_titlef,
            "content": personalized_contentf,
            "user_type": "Customer",
            "user_ids[]": user["user_id"],
        }
        with session_lock:
            create_notif_response = session.post(url=CIL_NOTIF_URL, data=payload, headers=HEADER)
            if create_notif_response.status_code != 200:
                logging.error(f"Error creating notification: {create_notif_response.text}")
            else:
                log_notification(user["user_id"], personalized_title, personalized_content, ncamp)

    def sendemail(ncamp, ntitle, ncontent, nsize, users):
        try:
            resend.api_key = "re_b5ZpKezD_C7tDvbcJt8xbqYeUz4J8wkwh"

            subject = f'Auto Notification report - {ncamp}'
            body = f'''
            <!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Campaign Receipt</title>
  <style>
    body{{ font-family: 'Poppins', sans-serif; margin: 0; padding: 0; background-color: #f5f5f5; }}
    .container{{ max-width: 600px; margin: 20px auto; padding: 20px; background-color: #fff; border-radius: 8px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1); }}
    .header{{ text-align: center; margin-bottom: 20px; }}
    .header img{{ max-width: 100%; height: auto; border-radius: 8px; }}
    .content{{ padding: 20px; }}
    .title{{ font-size: 24px; color: #333; margin-bottom: 10px; text-decoration: underline; text-decoration-color: #4caf50; }}
    .card{{ background-color: #f0f0f0; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
    .card p{{ margin-bottom: 10px; }}
    .card strong{{ font-weight: bold; }}
    .footer{{ text-align: center; color: #777; font-size: 14px; margin-top: 20px; }}
    @media (max-width: 600px) {{
      .container{{ margin: 10px; padding: 10px; }}
      .header img{{ border-radius: 4px; }}
      .content{{ padding: 10px; }}
      .title{{ font-size: 20px; }}
      .card{{ padding: 10px; }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <img src="https://cilantroretail.s3.ap-south-1.amazonaws.com/main/Nonito.png" alt="Campaign Image">
    </div>

    <div class="content">
      <h1 class="title">Campaign Receipt</h1>

      <div class="card">
        <h3>Hey,</h3>
        <p>Below are the details of your campaign:</p>

        <table style="width: 100%;">
         <tr>
            <td style="font-weight: bold;">Type:</td>
            <td>notification</td>
          </tr>
          <tr>
            <td style="font-weight: bold;">Title:</td>
            <td>{ ntitle }</td>
          </tr>
          <tr>
            <td style="font-weight: bold;">Content:</td>
            <td>{ ncontent }</td>
          </tr>
          <tr>
            <td style="font-weight: bold;">Audience Size:</td>
            <td>{ nsize }</td>
          </tr>
        </table>

        <p>Thank you!</p>
        <p>Until next time,</p>
        <p>Nonito</p>
      </div>
    </div>

    <div class="footer">
      &copy; 2024 Nonito. All rights reserved.
    </div>
  </div>
</body>
</html>

            '''

            # Create CSV file in memory
            csv_buffer = io.StringIO()
            csv_writer = csv.writer(csv_buffer)
            csv_writer.writerow(["User ID", "First Name", "Favorite Item"])  # CSV Header
            for user in users:
                csv_writer.writerow([user["user_id"], user["first_name"], user["fav_item"]])

            # Encode CSV content to base64
            csv_content = csv_buffer.getvalue().encode('utf-8')
            csv_base64 = base64.b64encode(csv_content).decode('utf-8')

            params = {
                "from": "campaigns@nonito.xyz",
                "to": ["yara.elkassabi@cilantrocafe.net","mohammed09ahmed@gmail.com"],
                "subject": subject,
                "html": body,
                "headers": {
                    "X-Entity-Ref-ID": "123456789"
                },
                "attachments": [
                    {
                        "filename": f"{ncamp}_recipients.csv",
                        "content": csv_base64,
                        "type": "text/csv"
                    }
                ]
            }

            email = resend.Emails.send(params)
            logging.info('Email sent successfully with attachment!')
            logging.debug(email)
        except Exception as e:
            logging.error(f"Error sending email: {e}")

    def process_notifications(users, ntitle, ncontent, ncamp):
        if not login():
            logging.error('Login failed')
            return

        with ThreadPoolExecutor(max_workers=25) as executor:
            futures = [executor.submit(send_notification, user, ntitle, ncontent, ncamp) for user in users]
            for future in as_completed(futures):
                future.result()

        sendemail(ncamp, ntitle, ncontent, len(users), users)

    def schedule_notification(scheduled_time, users, ntitle, ncontent, ncamp):
        try:
            scheduler.add_job(
                process_notifications,
                args=(users, ntitle, ncontent, ncamp),
                trigger=DateTrigger(run_date=scheduled_time),
                id=f'notification_job_{scheduled_time}',
            )
            logging.info(f"Notification scheduled for {scheduled_time} (Africa/Cairo)")
        except Exception as e:
            logging.error(f"Error scheduling notification: {e}")

    # Function to send the SMS
    def send_sms(sms_text, user):
        personalized_content = sms_text.replace("{first_name}", user["first_name"])
        personalized_contentf = personalized_content.replace("{fav_item}", user["fav_item"])
        payload = {
            'Username': 'CILANTRO',
            'Password': 'bJdY6HzXA9',
            'SMSText': personalized_contentf,
            'SMSLang': 'E',
            'SMSSender': 'CILANTRO',
            'SMSReceiver': user["user_number"]
        }

        try:
            response = requests.post('https://smsvas.vlserv.com/KannelSending/service.asmx/SendSMSWithDLR',
                                     data=payload)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            return str(e)

    def process_sms(users, smscontent):
        with ThreadPoolExecutor(max_workers=25) as executor:
            futures = [executor.submit(send_sms, smscontent, user) for user in users]
            for future in as_completed(futures):
                future.result()

    def schedule_sms(scheduled_time, users, ncontent):
        try:
            scheduler.add_job(
                process_sms,
                args=(users, ncontent),
                trigger=DateTrigger(run_date=scheduled_time),
                id=f'notification_sms_job_{scheduled_time}',
            )
            logging.info(f"SMS scheduled for {scheduled_time} (Africa/Cairo)")
        except Exception as e:
            logging.error(f"Error scheduling SMS: {e}")

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

            # Check if each user in the users list is a dictionary with the required keys
            for user in users:
                if not isinstance(user, dict):
                    logging.error("User data is not a dictionary")
                    return jsonify({'error': 'Invalid user format'}), 400
                if 'user_id' not in user or 'first_name' not in user or 'fav_item' not in user:
                    logging.error("User dictionary missing required keys")
                    return jsonify({'error': 'User data missing required keys'}), 400

            # Run the notification process in a separate thread
            threading.Thread(target=process_notifications, args=(users, ntitle, ncontent, ncamp)).start()

            return jsonify({'message': 'Notification process started'}), 202
        except Exception as e:
            logging.error(f"Error in send_notification_endpoint: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/schedule-notification', methods=['POST'])
    def schedule_notification_endpoint():
        try:
            data = request.json
            if not isinstance(data, dict):
                logging.error("Received data is not a dictionary")
                return jsonify({'error': 'Invalid input format'}), 400

            scheduled_time_str = data.get('scheduled_time')
            try:
                scheduled_time = datetime.strptime(scheduled_time_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                logging.error("Invalid scheduled time format")
                return jsonify({'error': 'Invalid scheduled time format, use YYYY-MM-DD HH:MM:SS'}), 400

            users = data.get('users', [])
            if not isinstance(users, list):
                logging.error("Users data is not a list")
                return jsonify({'error': 'Invalid users format'}), 400

            ntitle = data.get('title')
            ncontent = data.get('content')
            ncamp = data.get('campaign')

            threading.Thread(target=schedule_notification,
                             args=(scheduled_time, users, ntitle, ncontent, ncamp)).start()

            return jsonify({'message': 'Notification scheduled successfully'}), 202
        except Exception as e:
            logging.error(f"Error in schedule_notification_endpoint: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/schedule-sms', methods=['POST'])
    def schedule_sms_endpoint():
        try:
            data = request.json
            if not isinstance(data, dict):
                logging.error("Received data is not a dictionary")
                return jsonify({'error': 'Invalid input format'}), 400

            scheduled_time_str = data.get('scheduled_time')
            try:
                scheduled_time = datetime.strptime(scheduled_time_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                logging.error("Invalid scheduled time format")
                return jsonify({'error': 'Invalid scheduled time format, use YYYY-MM-DD HH:MM:SS'}), 400

            users = data.get('users', [])
            if not isinstance(users, list):
                logging.error("Users data is not a list")
                return jsonify({'error': 'Invalid users format'}), 400

            ncontent = data.get('smscontent')

            threading.Thread(target=schedule_sms,
                             args=(scheduled_time, users, ncontent)).start()

            return jsonify({'message': 'SMS scheduled successfully'}), 202
        except Exception as e:
            logging.error(f"Error in schedule_sms_endpoint: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/send-sms', methods=['POST'])
    def send_sms_endpoint():
        try:
            data = request.json
            if not isinstance(data, dict):
                logging.error("Received data is not a dictionary")
                return jsonify({'error': 'Invalid input format'}), 400

            users = data.get('users', [])
            if not isinstance(users, list):
                logging.error("Users data is not a list")
                return jsonify({'error': 'Invalid users format'}), 400

            smscontent = data.get('smscontent')

            # Check if each user in the users list is a dictionary with the required keys
            for user in users:
                if not isinstance(user, dict):
                    logging.error("User data is not a dictionary")
                    return jsonify({'error': 'Invalid user format'}), 400
                if 'user_number' not in user or 'first_name' not in user or 'fav_item' not in user:
                    logging.error("User dictionary missing required keys")
                    return jsonify({'error': 'User data missing required keys'}), 400

            # Run the notification process in a separate thread
            threading.Thread(target=process_sms, args=(users, smscontent)).start()

            return jsonify({'message': 'SMS process started'}), 202
        except Exception as e:
            logging.error(f"Error in send_SMS_endpoint: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    return app


if __name__ == '__main__':
    app = app()
    app.run(debug=False)
