# Speak Without Words

**Speak Without Words** is a real-time computer vision project that turns hand gestures into intent, voice, and system controls. Built with Python, OpenCV, MediaPipe, and Flask.



## 🌟 Features
* **Gesture Recognition:** Detects Stop, Wait, Peace, and Help signals.
* **🗣️ Voice Feedback:** Speaks the detected intent aloud using browser-native TTS.
* **🎚️ Jedi Mode (Volume Control):** Control system volume by pinching your fingers in the air.
* **Web Interface:** Clean UI built with Tailwind CSS.

## 🛠️ Tech Stack
* **Python 3.x**
* **OpenCV & MediaPipe** (Computer Vision)
* **Flask** (Backend Server)
* **JavaScript & Tailwind CSS** (Frontend)
* **Pycaw** (Windows Audio Control)

## 📦 Installation

1. Clone the repository:
   ```bash
   git clone [https://github.com/tanzirrabby/speak-without-words.git](https://github.com/YOUR_USERNAME/speak-without-words.git)
   cd speak-without-words
   
2.Create a virtual environment:
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate

3.Install dependencies:
pip install -r requirements.txt

4.Run the application:
python app.py

5.Open your browser to http://localhost:5000

**Contributing**
Feel free to open issues or submit pull requests to add new gestures!
