from google_auth_oauthlib.flow import InstalledAppFlow
from pathlib import Path

CLIENT = '/home/lazywork/workspace/runtime/tokens/google_oauth_client.json'
TOKEN  = '/home/lazywork/workspace/runtime/tokens/google_workspace_all.json'

SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/gmail.readonly',
]

flow = InstalledAppFlow.from_client_secrets_file(CLIENT, SCOPES)
flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
print("\nOpen this URL in your browser:\n")
print(auth_url)
print("\nPaste the authorization code here:")
code = input("> ").strip()
flow.fetch_token(code=code)
creds = flow.credentials
Path(TOKEN).write_text(creds.to_json())
print("Token saved:", TOKEN)
