from twilio.rest import Client
from dotenv import load_dotenv
import os
import requests
import time

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_SANDBOX_NUMBER = os.getenv("TWILIO_SANDBOX_NUMBER")

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def download_document_from_twilio(media_url, file_name, file_type):
    try:
        print(f"Downloading from Twilio: {media_url}")

        response = requests.get(
            media_url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN), timeout=30
        )

        if response.status_code != 200:
            print(f"Error downloading: Status {response.status_code}")
            return None

        temp_dir = "./temp_uploads"
        os.makedirs(temp_dir, exist_ok=True)

        full_name = f"{file_name}.{file_type}"
        temp_path = os.path.join(temp_dir, full_name)

        with open(temp_path, "wb") as f:
            f.write(response.content)

        size_kb = len(response.content) / 1024
        print(f"File downloaded: {temp_path} ({size_kb:.2f} KB)")

        return temp_path

    except Exception as e:
        print(f"Error downloading file: {e}")
        return None


def send_twilio_message(phone, text, max_retries=3):
    for attempt in range(max_retries):
        try:
            print(
                f"Sending message with Twilio (attempt {attempt + 1}/{max_retries}): {text[:50]}..."
            )
            print(f"From: {TWILIO_SANDBOX_NUMBER}")
            print(f"To: {phone}")

            message = twilio_client.messages.create(
                from_=TWILIO_SANDBOX_NUMBER,
                body=text,
                to=phone,
            )

            print(f"Message sent successfully. SID: {message.sid}")
            return {
                "success": True,
                "response": {"sid": message.sid, "status": message.status},
            }

        except Exception as e:
            print(f"ERROR ON ATTEMPT {attempt + 1}/{max_retries}: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(3 * (attempt + 1))
                continue
            else:
                print(f"FINAL ERROR after {max_retries} attempts: {str(e)}")
                return {"success": False, "error": str(e)}

    return {"success": False, "error": "Failed after all retries"}


def send_twilio_document(phone, document_url, caption=""):
    try:
        print(f"Sending document: {document_url}")

        message = twilio_client.messages.create(
            from_=TWILIO_SANDBOX_NUMBER,
            body=caption if caption else "Here is your document",
            media_url=[document_url],
            to=phone,
        )

        print(f"Document sent. SID: {message.sid}")
        return {"success": True, "response": {"sid": message.sid}}

    except Exception as e:
        print(f"ERROR sending document: {str(e)}")
        return {"success": False, "error": str(e)}


def extract_phone_from_twilio(from_field):
    if not from_field:
        return ""

    phone = from_field.replace("whatsapp:", "")
    phone = phone.replace("+", "")

    return phone
