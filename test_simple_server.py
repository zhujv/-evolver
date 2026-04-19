import http.server
import socketserver
import json

PORT = 16889

class SimpleHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(b'<html><body><h1>Simple Server Ready</h1></body></html>')
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        try:
            request = json.loads(body)
            if request.get('method') == 'health':
                response = {'result': {'status': 'healthy'}, 'id': request.get('id')}
            else:
                response = {'error': {'code': -32601, 'message': 'Method not found'}, 'id': request.get('id')}
        except:
            response = {'error': {'code': -32600, 'message': 'Invalid JSON'}, 'id': None}
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())
    
    def log_message(self, format, *args):
        pass

class SimpleHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

if __name__ == '__main__':
    print(f'Simple server listening on http://127.0.0.1:{PORT}')
    httpd = SimpleHTTPServer(('127.0.0.1', PORT), SimpleHandler)
    httpd.serve_forever()
