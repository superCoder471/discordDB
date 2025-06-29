import webhook_url
WEBHOOK_URL = webhook_url.WEBHOOK_URL

import requests
import json

# The text you want to send
message = "!select_all users"

payload = {
    "content": message
}

response = requests.post(
    WEBHOOK_URL,
    data=json.dumps(payload),
    headers={"Content-Type": "application/json"}
)

if response.status_code == 204:
    print("Message sent successfully!")
else:
    print(f"Failed to send message. Status code: {response.status_code}")