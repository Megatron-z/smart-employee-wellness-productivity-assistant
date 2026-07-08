import http.server
import socketserver
import webbrowser
import json
import threading
import sys
import os

PORT = 8001
COORDINATES_FILE = "GPS_location.txt"

# HTML Template with JavaScript to get precise geolocation
HTML_CONTENT = """
<!DOCTYPE html>
<html>
<head>
    <title>GPS Capture</title>
    <style>
        body { font-family: sans-serif; text-align: center; padding-top: 50px; background-color: #f0f2f5; }
        .card { background: white; padding: 30px; border-radius: 12px; display: inline-block; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
        button { background: #3b82f6; color: white; border: none; padding: 12px 24px; border-radius: 6px; cursor: pointer; font-weight: bold; }
        #status { margin-top: 20px; color: #64748b; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Precise GPS Capture</h2>
        <p>Please allow location access when prompted by the browser.</p>
        <button onclick="getLocation()">Get Precise Coordinates</button>
        <div id="status">Awaiting action...</div>
    </div>

    <script>
        function getLocation() {
            const status = document.getElementById('status');
            if (navigator.geolocation) {
                status.innerText = "Requesting permission...";
                navigator.geolocation.getCurrentPosition(
                    (position) => {
                        const lat = position.coords.latitude;
                        const lon = position.coords.longitude;
                        status.innerText = "Success! Sending " + lat + ", " + lon + " back to script...";
                        
                        // Send data back to the local python server
                        fetch('/', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ latitude: lat, longitude: lon })
                        }).then(() => {
                            status.innerText = "Done! You can close this tab and check the terminal.";
                            setTimeout(() => window.close(), 2000);
                        });
                    },
                    (error) => {
                        status.innerText = "Error: " + error.message;
                    },
                    { enableHighAccuracy: true, timeout: 5000, maximumAge: 0 }
                );
            } else {
                status.innerText = "Geolocation is not supported by this browser.";
            }
        }
    </script>
</body>
</html>
"""

class GPSHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(HTML_CONTENT.encode())

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data)
        
        lat = data.get('latitude')
        lon = data.get('longitude')
        
        print(f"\n[SUCCESS] Received Precise Coordinates from Browser:")
        print(f"Latitude: {lat}")
        print(f"Longitude: {lon}")
        
        # Save to GPS_location.txt
        with open(COORDINATES_FILE, "a") as f:
            f.write(f"\nPrecise GPS from Browser: Latitude: {lat}, Longitude: {lon}\n")
        
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok"}).encode())
        
        # Shutdown the server after receiving the data
        threading.Thread(target=self.server.shutdown).start()

def run_gps_bridge():
    print(f"Starting temporary local server on port {PORT}...")
    with socketserver.TCPServer(("", PORT), GPSHandler) as httpd:
        print(f"Opening browser to get precise location...")
        webbrowser.open(f"http://localhost:{PORT}")
        print("Waiting for browser input (click 'Allow' in the browser)...")
        httpd.serve_forever()
    print("Server shut down. Coordinates saved.")

if __name__ == "__main__":
    run_gps_bridge()
