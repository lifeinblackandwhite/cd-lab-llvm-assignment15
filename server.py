import http.server
import socketserver
import json
import tempfile
import subprocess
import os

PORT = 8000

class DashboardRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.end_headers()

    def do_POST(self):
        if self.path == '/compile':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                c_code = data.get('c_code', '')
                
                with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
                    f.write(c_code)
                    temp_c_file = f.name
                
                temp_ll_file = temp_c_file.replace('.c', '.ll')
                
                result = subprocess.run(
                    ["clang", "-emit-llvm", "-S", "-O0", temp_c_file, "-o", temp_ll_file],
                    capture_output=True, text=True
                )
                
                if result.returncode == 0:
                    with open(temp_ll_file, 'r') as f:
                        ir_code = f.read()
                    
                    response_data = {
                        "status": "success",
                        "ir": ir_code
                    }
                else:
                    response_data = {
                        "status": "error",
                        "error": result.stderr
                    }
                    
                if os.path.exists(temp_c_file):
                    os.remove(temp_c_file)
                if os.path.exists(temp_ll_file):
                    os.remove(temp_ll_file)

            except Exception as e:
                response_data = {
                    "status": "error",
                    "error": str(e)
                }

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
        else:
            self.send_error(404, "Endpoint not found")

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), DashboardRequestHandler) as httpd:
        print(f"Serving at port {PORT}")
        httpd.serve_forever()
