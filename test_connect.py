import urllib.request
import json
import sys

url = "http://127.0.0.1:16888/rpc"
data = json.dumps({"method": "health", "params": {}, "id": 1}).encode()

print("Testing:", url)

try:
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    resp = urllib.request.urlopen(req, timeout=10)
    print("OK! Status:", resp.status)
    print("Response:", resp.read().decode())
except Exception as e:
    print("FAILED:", type(e).__name__, e)