from flask import Flask, Response
import threading
import cv2
import time

# Global reference to the output frame
output_frame = None
lock = threading.Lock()

app = Flask(__name__)

def generate():
    global output_frame, lock
    while True:
        with lock:
            if output_frame is None:
                continue
            
            # Encode frame
            (flag, encodedImage) = cv2.imencode(".jpg", output_frame)
            
            if not flag: continue
            
        # Yield byte stream
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
              bytearray(encodedImage) + b'\r\n')
        # Cap FPS to avoid overwhelming network
        time.sleep(0.016)

@app.route("/video_feed")
def video_feed():
    return Response(generate(), mimetype = "multipart/x-mixed-replace; boundary=frame")

class VideoServer:
    def __init__(self, host="0.0.0.0", port=5050):
        self.host = host
        self.port = port
        self.thread = threading.Thread(target=self.run, daemon=True)
    
    def run(self):
        print(f"🎥 Starting Video Stream at http://{self.host}:{self.port}/video_feed")
        # Disable Flask logging
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        app.run(host=self.host, port=self.port, debug=False, threaded=True, use_reloader=False)

    def start(self):
        self.thread.start()

    def update_frame(self, frame):
        global output_frame, lock
        with lock:
            output_frame = frame.copy()
