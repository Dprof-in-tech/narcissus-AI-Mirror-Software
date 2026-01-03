import cv2
import mediapipe as mp
import time
import math
import numpy as np

# Import TASKS API
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

class HandDetector:
    def __init__(self):
        # Create HandLandmarker options
        base_options = python.BaseOptions(model_asset_path='hand_landmarker.task')
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=1,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            running_mode=vision.RunningMode.VIDEO)
            
        self.landmarker = vision.HandLandmarker.create_from_options(options)
        
        # State
        self.zone_timer = 0
        self.current_zone = None
        self.required_hold_time = 1.0
        
        # Cursor Smoothing
        self.prev_x = -1
        self.prev_y = -1
        self.alpha = 0.5
        self.start_time_ms = int(time.time() * 1000)

    def find_gestures(self, frame):
        """
        Returns: gesture_name, frame, cursor_pos
        """
        # Convert to MP Image
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        
        # Timestamp for Video Mode
        timestamp = int(time.time() * 1000) - self.start_time_ms
        
        # Detect
        # detect_for_video returns a HandLandmarkerResult
        detection_result = self.landmarker.detect_for_video(mp_image, timestamp)
        
        h, w, c = frame.shape
        cursor_pos = {'x': -1, 'y': -1}
        gesture = None
        
        if detection_result.hand_landmarks:
            # We asked for 1 hand
            hand_lms = detection_result.hand_landmarks[0]
            
            # --- Draw Logic (Custom, since solutions.drawing_utils might be missing) ---
            # Index Tip is index 8
            # Wrist 0, ThumbCMC 1, ThumbMCP 2, ThumbIP 3, ThumbTip 4
            # IndexMCP 5, IndexPIP 6, IndexDIP 7, IndexTip 8
            # ...
            
            # Draw Connections (Simple subset for viz)
            connections = [
                (0,1), (1,2), (2,3), (3,4), # Thumb
                (0,5), (5,6), (6,7), (7,8), # Index
                (5,9), (9,10), (10,11), (11,12), # Middle
                (9,13), (13,14), (14,15), (15,16), # Ring
                (13,17), (17,18), (18,19), (19,20), # Pinky
                (0,17) # Wrist
            ]
            
            points = []
            for lm in hand_lms:
                px, py = int(lm.x * w), int(lm.y * h)
                points.append((px, py))
                cv2.circle(frame, (px, py), 3, (0, 255, 0), -1)
                
            for start_idx, end_idx in connections:
                if start_idx < len(points) and end_idx < len(points):
                    cv2.line(frame, points[start_idx], points[end_idx], (0, 255, 0), 1)

            # --- Cursor Logic ---
            index_tip = hand_lms[8]
            
            # Smoothing
            if self.prev_x == -1: self.prev_x, self.prev_y = index_tip.x, index_tip.y
            
            smooth_x = (self.alpha * index_tip.x) + ((1 - self.alpha) * self.prev_x)
            smooth_y = (self.alpha * index_tip.y) + ((1 - self.alpha) * self.prev_y)
            
            self.prev_x, self.prev_y = smooth_x, smooth_y
            cursor_pos = {'x': smooth_x, 'y': smooth_y}
            
            cx, cy = int(smooth_x * w), int(smooth_y * h)
            cv2.circle(frame, (cx, cy), 15, (255, 0, 255), cv2.FILLED)

            # --- Zone Logic ---
            detected_zone = None
            if smooth_x < 0.2: detected_zone = "LEFT_ZONE"
            elif smooth_x > 0.8: detected_zone = "RIGHT_ZONE"
            
            if detected_zone:
                if detected_zone == self.current_zone:
                    if time.time() - self.zone_timer > self.required_hold_time:
                        if detected_zone == "LEFT_ZONE": gesture = "HOLD_LEFT"
                        elif detected_zone == "RIGHT_ZONE": gesture = "HOLD_RIGHT"
                        self.zone_timer = time.time() + 2.0 # Cooldown
                else:
                    self.current_zone = detected_zone
                    self.zone_timer = time.time()
            else:
                self.current_zone = None
                self.zone_timer = 0
        else:
            self.prev_x = -1
            self.current_zone = None

        # Viz Zones
        zone_w = int(w * 0.2)
        cv2.rectangle(frame, (0, 0), (zone_w, h), (0, 255, 0), 2)
        cv2.rectangle(frame, (w-zone_w, 0), (w, h), (0, 255, 0), 2)

        return gesture, frame, cursor_pos
