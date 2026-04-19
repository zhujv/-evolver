import urllib.request
import json

try:
    req = urllib.request.Request(
        'http://localhost:16888/rpc',
        data=json.dumps({"method": "health", "params": {}, "id": 1}).encode(),
        headers={'Content-Type': 'application/json'}
    )
    resp = urllib.request.urlopen(req, timeout=5)
    print("OK:", resp.read().decode())
except Exception as e:
    print("ERROR:", e)