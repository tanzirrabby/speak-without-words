import cv2
import mediapipe as mp
import math
import numpy as np
import os
import urllib.request
from ctypes import cast, POINTER
try:
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
except Exception:
    CLSCTX_ALL = None
    AudioUtilities = None
    IAudioEndpointVolume = None
    print("[WARN] pycaw/comtypes not available; volume control disabled.")

class VideoCamera(object):
    def __init__(self):
        self.video = cv2.VideoCapture(0)
        
        
        self.current_intent = "Listening..."
        # Intent smoothing buffer to avoid transient flicker
        self.intent_buffer = []
        self.intent_buffer_size = 3
        self.hands = None
        self.mp_draw = None
        self.hand_detector = None  # MediaPipe Tasks HandLandmarker (fallback)

        try:
            if hasattr(mp, 'solutions'):
                self.mp_hands = mp.solutions.hands
                self.hands = self.mp_hands.Hands(
                    max_num_hands=1,
                    min_detection_confidence=0.7,
                    min_tracking_confidence=0.5
                )
                self.mp_draw = mp.solutions.drawing_utils
            else:
                raise AttributeError("mediapipe 'solutions' not available")
        except Exception:
            print("[WARN] mediapipe 'solutions' API not available; attempting Tasks API fallback.")
            try:
                from mediapipe.tasks import python as mp_tasks_python
                from mediapipe.tasks.python import vision as mp_vision
                from mediapipe.tasks.python.vision.core import image as mp_image

                models_dir = os.path.join(os.path.dirname(__file__), 'models')
                os.makedirs(models_dir, exist_ok=True)
                model_path = os.path.join(models_dir, 'hand_landmarker.task')
                if not os.path.exists(model_path):
                    print('[INFO] Downloading hand_landmarker model...')
                    urllib.request.urlretrieve(
                        'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task',
                        model_path
                    )

                base_options = mp_tasks_python.BaseOptions(model_asset_path=model_path)
                options = mp_vision.HandLandmarkerOptions(
                    base_options=base_options,
                    num_hands=1,
                    min_hand_detection_confidence=0.7,
                    min_tracking_confidence=0.5
                )
                self.hand_detector = mp_vision.HandLandmarker.create_from_options(options)
                self.mp_tasks_vision = mp_vision
                self.mp_image = mp_image
                print('[INFO] MediaPipe Tasks HandLandmarker initialized.')
            except Exception as e:
                print(f"[WARN] MediaPipe Tasks API unavailable or failed to init: {e}. Running without gesture detection.")
                self.hand_detector = None

        # --- VOLUME CONTROL SETUP (WINDOWS) ---
        try:
            devices = AudioUtilities.GetSpeakers()
            # pycaw has had variations: older versions expose Activate, newer expose EndpointVolume
            if hasattr(devices, 'Activate'):
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                self.volume = cast(interface, POINTER(IAudioEndpointVolume))
            else:
                # EndpointVolume is typically a comtypes pointer to IAudioEndpointVolume
                self.volume = devices.EndpointVolume

            # Get volume range and store
            self.vol_range = self.volume.GetVolumeRange()
            # vol_range looks like (-65.25, 0.0, 0.03125) -> (Min, Max, Step)
            self.min_vol = self.vol_range[0]
            self.max_vol = self.vol_range[1]
        except Exception as e:
            print(f"Audio control setup failed: {e}")
            self.volume = None

    def __del__(self):
        self.video.release()

    def get_system_volume_percent(self):
        """Return current system volume as an integer percent [0-100], or None if unavailable."""
        if not self.volume:
            return None
        try:
            curr = self.volume.GetMasterVolumeLevel()
            percent = int(np.interp(curr, [self.min_vol, self.max_vol], [0, 100]))
            return max(0, min(100, percent))
        except Exception as e:
            print(f"[WARN] Reading system volume failed: {e}")
            return None

    def count_fingers(self, lm_list):
        """Returns list of 1s and 0s for [Thumb, Index, Middle, Ring, Pinky]"""
        fingers = []
        
        # Thumb (Right Hand Logic)
        if lm_list[4][1] < lm_list[3][1]: # Check X coordinate
            fingers.append(1)
        else:
            fingers.append(0)

        # 4 Fingers
        tips = [8, 12, 16, 20]
        pips = [6, 10, 14, 18]
        for tip, pip in zip(tips, pips):
            if lm_list[tip][2] < lm_list[pip][2]: # Check Y coordinate
                fingers.append(1)
            else:
                fingers.append(0)
        return fingers

    def get_frame(self):
        success, image = self.video.read()
        if not success: return None, "Error"

        image = cv2.flip(image, 1)
        h, w, c = image.shape
        
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        detected_intent = "Listening..."
        lm_list = []
        # Volume display variables (kept across the frame)
        current_vol_per = None
        current_vol_bar = None

        # Preferred: MediaPipe Solutions API
        if self.hands is not None:
            results = self.hands.process(image_rgb)
            if results and results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    if self.mp_draw:
                        self.mp_draw.draw_landmarks(image, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                    for id, lm in enumerate(hand_landmarks.landmark):
                        cx, cy = int(lm.x * w), int(lm.y * h)
                        lm_list.append([id, cx, cy])

        # Fallback: MediaPipe Tasks HandLandmarker
        elif self.hand_detector is not None:
            try:
                mp_image_obj = self.mp_image.Image(self.mp_image.ImageFormat.SRGB, image_rgb)
                detection_result = self.hand_detector.detect(mp_image_obj)
                if detection_result and detection_result.hand_landmarks:
                    # Use first detected hand for gestures
                    hand_landmarks = detection_result.hand_landmarks[0]
                    for id, lm in enumerate(hand_landmarks):
                        cx, cy = int(lm.x * w), int(lm.y * h)
                        lm_list.append([id, cx, cy])
                        cv2.circle(image, (cx, cy), 3, (0, 255, 0), -1)
                    # Try to draw connections if available
                    try:
                        connections = self.mp_tasks_vision.HandLandmarkConnections.HAND_CONNECTIONS
                        for conn in connections:
                            x1, y1 = int(hand_landmarks[conn.start].x * w), int(hand_landmarks[conn.start].y * h)
                            x2, y2 = int(hand_landmarks[conn.end].x * w), int(hand_landmarks[conn.end].y * h)
                            cv2.line(image, (x1, y1), (x2, y2), (0, 255, 0), 1)
                    except Exception:
                        pass
            except Exception as e:
                print(f"[WARN] Tasks detection failed: {e}")

        # Analyze Basic Gestures (applies to either API results)
        if lm_list:
            fingers = self.count_fingers(lm_list)
            total_fingers = fingers.count(1)

            # Map common finger patterns to intents
            if total_fingers == 0:
                detected_intent = "WAIT"
            elif total_fingers == 5:
                # If the wrist is high in the frame, interpret as HELP (hand raised)
                wrist_y = lm_list[0][2]
                if wrist_y < h * 0.25:
                    detected_intent = "HELP"
                else:
                    detected_intent = "STOP"
            elif total_fingers == 2 and fingers[1] == 1 and fingers[2] == 1:
                detected_intent = "PEACE"
            elif fingers[1] == 1 and fingers[4] == 1 and fingers[2] == 0 and fingers[3] == 0:
                detected_intent = "ROCK ON"

            # Jedi Mode (Volume Control): Thumb + Index up, Middle down
            if fingers[0] == 1 and fingers[1] == 1 and fingers[2] == 0:
                detected_intent = "VOLUME CTRL"

                # Get coordinates of Thumb Tip (4) and Index Tip (8)
                x1, y1 = lm_list[4][1], lm_list[4][2]
                x2, y2 = lm_list[8][1], lm_list[8][2]
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

                # Draw visual guides
                cv2.circle(image, (x1, y1), 10, (255, 0, 255), cv2.FILLED)
                cv2.circle(image, (x2, y2), 10, (255, 0, 255), cv2.FILLED)
                cv2.line(image, (x1, y1), (x2, y2), (255, 0, 255), 3)

                # Calculate Length
                length = math.hypot(x2 - x1, y2 - y1)

                # Hand Range: 50 (closed) to 250 (open)
                # Vol Range: -65 (min) to 0 (max)
                if self.volume:
                    vol = np.interp(length, [50, 250], [self.min_vol, self.max_vol])
                    try:
                        self.volume.SetMasterVolumeLevel(vol, None)
                    except Exception as e:
                        print(f"[WARN] Setting volume failed: {e}")

                    # After setting, read exact value for display
                    try:
                        curr = self.volume.GetMasterVolumeLevel()
                        vol_per = int(np.interp(curr, [self.min_vol, self.max_vol], [0, 100]))
                        vol_bar_y = int(np.interp(vol_per, [0, 100], [400, 150]))
                        current_vol_per = vol_per
                        current_vol_bar = vol_bar_y
                    except Exception as e:
                        current_vol_per = None
                        current_vol_bar = None

            # Stabilize intent: require a short run of identical detections before switching
            self.intent_buffer.append(detected_intent)
            if len(self.intent_buffer) > self.intent_buffer_size:
                self.intent_buffer.pop(0)

            stable_intent = self.current_intent
            if len(self.intent_buffer) == self.intent_buffer_size and len(set(self.intent_buffer)) == 1:
                stable_intent = self.intent_buffer[-1]

            # Log when intent actually changes (after stabilization)
            if stable_intent != self.current_intent:
                print(f"[INFO] Intent changed: {self.current_intent} -> {stable_intent}")

            detected_intent = stable_intent

            # Draw detected intent label for feedback
            try:
                cv2.putText(image, detected_intent, (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
            except Exception:
                pass

        # Draw persistent volume bar on left side
        if current_vol_per is None and self.volume:
            current_vol_per = self.get_system_volume_percent()
            if current_vol_per is not None:
                current_vol_bar = int(np.interp(current_vol_per, [0, 100], [400, 150]))

        # Draw bar background
        bar_x1, bar_x2 = 50, 85
        bar_y1, bar_y2 = 150, 400
        # Border
        cv2.rectangle(image, (bar_x1, bar_y1), (bar_x2, bar_y2), (0, 255, 0), 3)
        if current_vol_per is not None:
            cv2.rectangle(image, (bar_x1, int(current_vol_bar)), (bar_x2, bar_y2), (0, 255, 0), cv2.FILLED)
            cv2.putText(image, f'{int(current_vol_per)}%', (40, 450), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        else:
            # Dimmed placeholder when volume unavailable
            cv2.putText(image, 'N/A', (40, 450), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (128, 128, 128), 2)

        self.current_intent = detected_intent
        ret, jpeg = cv2.imencode('.jpg', image)
        return jpeg.tobytes(), detected_intent