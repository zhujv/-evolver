import urllib.request
import json

req = urllib.request.Request(
    'http://127.0.0.1:16888/rpc',
    data=json.dumps({"method": "health", "params": {}, "id": 1}).encode(),
    headers={'Content-Type': 'application/json'}
)

try:
    resp = urllib.request.urlopen(req, timeout=5)
    print("Status:", resp.status)
    print("Body:", resp.read().decode())
except urllib.error.HTTPError as e:
    print("HTTPError:", e.code, e.read().decode())
except Exception as e:
    print("Error:", e)