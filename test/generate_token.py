import base64
import requests
 
# ==============================
# CONFIG (replace with yours)
# ==============================
 
OKTA_DOMAIN = "https://integrator-4714775.okta.com"
 
CLIENT_ID = "0oaztaww8zVWgsbOt697"
CLIENT_SECRET = "iDz4Y-bcm_dTyNInq6YP7YBpC-MckB3L6esxyMBj75BEAGn7gavQBVsv7ToWKS6F"
 
REDIRECT_URI = "http://localhost:8080/authorization-code/callback"
 
# Paste your authorization code here
AUTH_CODE = "sTqm2Kl_TPwKAlg8iMFfXCU1yzuP6p9EhYpdjmIdBXI"

# ==============================
 
token_url = f"{OKTA_DOMAIN}/oauth2/v1/token"
 
# Encode client_id:client_secret
basic_auth = base64.b64encode(
    f"{CLIENT_ID}:{CLIENT_SECRET}".encode()
).decode()
 
headers = {
    "Authorization": f"Basic {basic_auth}",
    "Content-Type": "application/x-www-form-urlencoded"
}
 
data = {
    "grant_type": "authorization_code",
    "code": AUTH_CODE,
    "redirect_uri": REDIRECT_URI
}
 
response = requests.post(token_url, headers=headers, data=data)
 
print("Status:", response.status_code)
 
 
print("Access Token:", response.json().get("access_token"))
print("-------------------------------------------")
 
print("ID Token:",response.json().get("id_token"))