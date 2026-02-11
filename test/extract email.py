import requests
from jose import jwt
 
# ORG server issuer
# ISSUER = "https://integrator-3291278.okta.com"
ISSUER = "https://integrator-4714775.okta.com"
 
# MUST match aud inside your ID token
# CLIENT_ID = "0oaztakr35wCwuEWk697"
CLIENT_ID = "0oaztaww8zVWgsbOt697"
 
def validate_id_token(id_token):
    # ORG server JWKS
    jwks = requests.get(f"{ISSUER}/oauth2/v1/keys").json()
   
    header = jwt.get_unverified_header(id_token)
    kid = header["kid"]
 
    key = next(k for k in jwks["keys"] if k["kid"] == kid)
 
    claims = jwt.decode(
        id_token,
        key,
        algorithms=["RS256"],
        audience=CLIENT_ID,
        issuer=ISSUER,
        options={"verify_at_hash": False}
    )
 
    return claims
 
if __name__ == "__main__":
    # PASTE RAW id_token here (no "ID Token:" prefix, no spaces, no newlines)
    ID_TOKEN = "eyJraWQiOiIycVJXeUhxazNFQk00amZMczh0TzVaSzN0LUhxemtTN3FxVVYwdGlfdDg0IiwiYWxnIjoiUlMyNTYifQ.eyJzdWIiOiIwMHV6dGE2Z3c4Yk13WTVQejY5NyIsIm5hbWUiOiJZYXNoIEd1cHRhIiwiZW1haWwiOiJndXB0YXlAb3BlbnRleHQuY29tIiwidmVyIjoxLCJpc3MiOiJodHRwczovL2ludGVncmF0b3ItNDcxNDc3NS5va3RhLmNvbSIsImF1ZCI6IjBvYXp0YXd3OHpWV2dzYk90Njk3IiwiaWF0IjoxNzcwMzU3MjU0LCJleHAiOjE3NzAzNjA4NTQsImp0aSI6IklELlVkQnhjcDJhTHhQdUJRUFNPMTVaZXNGT0pFTjd3c2xUdmNBZUtrbXpReG8iLCJhbXIiOlsibWZhIiwib3RwIiwicHdkIiwib2t0YV92ZXJpZnkiXSwiaWRwIjoiMDBvenQ5dmtxN25kelFoRVo2OTciLCJwcmVmZXJyZWRfdXNlcm5hbWUiOiJndXB0YXlAb3BlbnRleHQuY29tIiwiYXV0aF90aW1lIjoxNzcwMzU3MjI3LCJhdF9oYXNoIjoiMFFKOEFGNlVyc3FNcldkbWJLMlF2QSJ9.QMfNtsNfCK2zEIXWzp7Kgz6fa_8zGCWA3rXfZ4E9sF88D1nS-ucTBZ-UuNbb1D40Tv8JyP7WK4kdchK3Nl92JHa0yq_6ZTaLfoMpPkTMsasBhz8Nw1JjGCx_H7JJKWLnQA30sALRJpRrarLDRXoNBroJyRAi6ymk149qYqjYoUjx3SRZfT7Xw4shhyCbuaEUhWzsByFl6eqzUedKVLwXtgecCAFc014wITxiYFSGrrahmV3wCPvEQuMIt_pAsu2OVCDuv6_LOB5r2MCld21r2di3Zm3DcC_wmopjCfr2ZWUeQ90rRr187K8P5Km18JEFYpsA5gq8DZWSIFGaR3DgQw"
    print("Dot count:", ID_TOKEN.count("."))
 
    claims = validate_id_token(ID_TOKEN)
    print("\n✅ USER EMAIL:", claims["email"])