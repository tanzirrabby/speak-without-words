from flask import Flask, render_template, Response, jsonify
from camera import VideoCamera

app = Flask(__name__)
video_stream = VideoCamera()

@app.route('/')
def index():
    return render_template('index.html')

def gen(camera):
    """Generator function to stream video frames"""
    while True:
        frame, intent = camera.get_frame()
        if frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(gen(video_stream),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/status')
def status():
    """API endpoint for Frontend to get the current intent"""
    return jsonify(intent=video_stream.current_intent)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)