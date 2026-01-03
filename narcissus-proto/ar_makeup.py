import cv2
import mediapipe as mp
import time
import numpy as np

# Import TASKS API
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

class ARMakeup:
    def __init__(self):
        # Create FaceLandmarker options
        base_options = python.BaseOptions(model_asset_path='face_landmarker.task')
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False, 
            num_faces=1,
            running_mode=vision.RunningMode.VIDEO)
            
        self.landmarker = vision.FaceLandmarker.create_from_options(options)
        self.start_time_ms = int(time.time() * 1000)
        
        # State
        self.enabled = False
        self.current_color = None # None or (B, G, R)
        self.lipstick_opacity = 0.5
        
        # Color Palette
        self.COLORS = {
            "red": (0, 0, 200),
            "nude": (150, 150, 220), # Sort of a beige/pink
            "pink": (180, 130, 255),
            "purple": (128, 0, 128),
            "dark": (30, 30, 100)
        }

        # ORDERED Indices for Polygon Filling (Donut Mask)
        # Outer Contour (Clockwise)
        self.LIPS_OUTER_LOWER = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291]
        self.LIPS_OUTER_UPPER = [291, 409, 270, 269, 267, 0, 37, 39, 40, 185, 61]
        self.LIPS_OUTER = self.LIPS_OUTER_LOWER + self.LIPS_OUTER_UPPER[1:] 
        
        # Inner Contour (Mouth Hole)
        self.LIPS_INNER_LOWER = [78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308]
        self.LIPS_INNER_UPPER = [308, 415, 310, 311, 312, 13, 82, 81, 80, 191, 78]
        self.LIPS_INNER = self.LIPS_INNER_LOWER + self.LIPS_INNER_UPPER[1:] 
        
        # Cache for lip hull to check collisions
        self.current_lip_mask = None

    def set_color(self, color_name):
        if color_name == "off":
            self.enabled = False
            self.current_color = None
            return "Makeup removed."
            
        if color_name in self.COLORS:
            self.current_color = self.COLORS[color_name]
            self.enabled = True
            return f"Applying {color_name} lipstick."
        else:
            return f"Color {color_name} not found."

    def cycle_color(self):
        color_keys = list(self.COLORS.keys())
        if self.current_color is None:
            new_key = color_keys[0]
        else:
            # Find current index
            try:
                # This is a bit hacky comparing tuples values, but works for limited set
                curr_idx = -1
                for i, k in enumerate(color_keys):
                    if self.COLORS[k] == self.current_color:
                        curr_idx = i
                        break
                next_idx = (curr_idx + 1) % len(color_keys)
                new_key = color_keys[next_idx]
            except:
                new_key = color_keys[0]
        
        self.set_color(new_key)
        return new_key

    def check_touch(self, cursor_x, cursor_y, frame_w, frame_h):
        """
        Check if normalized cursor (0.0-1.0) is inside the lip mask.
        cursor_x: 0.0 (Left) to 1.0 (Right)
        """
        if self.current_lip_mask is None: return False
        
        # Scale cursor
        cx, cy = int(cursor_x * frame_w), int(cursor_y * frame_h)
        
        # Check against mask (255 where lips are)
        # Boundary check
        if 0 <= cx < frame_w and 0 <= cy < frame_h:
            # If mask pixel > 0, it's a hit
            if self.current_lip_mask[cy, cx] > 0:
                return True
        return False

    def process_frame(self, frame):
        # Always run detection to get landmarks for touch, even if disabled?
        # Yes, need landmarks for "Touch to apply".
        
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        timestamp = int(time.time() * 1000) - self.start_time_ms
        
        # Detect
        detection_result = self.landmarker.detect_for_video(mp_image, timestamp)
        
        h, w, c = frame.shape
        output_frame = frame
        
        # Reset mask each frame
        self.current_lip_mask = np.zeros((h, w), dtype=np.uint8)
        
        if detection_result.face_landmarks:
            face_lms = detection_result.face_landmarks[0]
            
            def get_points(indices):
                pts = []
                for idx in indices:
                    lm = face_lms[idx]
                    px, py = int(lm.x * w), int(lm.y * h)
                    pts.append((px, py))
                return np.array(pts, dtype=np.int32)

            outer_pts = get_points(self.LIPS_OUTER)
            inner_pts = get_points(self.LIPS_INNER)
            
            # Create Donut Mask for Collision & Rendering
            cv2.fillPoly(self.current_lip_mask, [outer_pts], 255)
            cv2.fillPoly(self.current_lip_mask, [inner_pts], 0)
            
            # If Enabled, Render
            if self.enabled and self.current_color is not None:
                mask = self.current_lip_mask.copy()
                mask = cv2.GaussianBlur(mask, (7, 7), 0)
                
                # Color Layer
                colored_layer = np.zeros_like(frame)
                colored_layer[:] = self.current_color
                
                # Blend (Manual implementation for speed/clarity)
                # Convert to float
                img_float = frame.astype(np.float32) / 255.0
                color_float = colored_layer.astype(np.float32) / 255.0
                mask_float = mask.astype(np.float32) / 255.0
                mask_float = np.stack([mask_float]*3, axis=2)
                
                alpha_map = mask_float * self.lipstick_opacity
                
                out_float = (color_float * alpha_map) + (img_float * (1.0 - alpha_map))
                output_frame = (out_float * 255).astype(np.uint8)
                
        return output_frame
