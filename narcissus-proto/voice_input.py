import speech_recognition as sr
from threading import Thread
import time

class VoiceListener(Thread):
    def __init__(self, event_queue):
        super().__init__()
        self.event_queue = event_queue
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.stop_listening = None
        
    def start_background_listening(self):
        print("🎤 Voice Listener Initializing...")
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source)
                self.recognizer.pause_threshold = 0.8 # Snappier response (was 1.2)
                self.recognizer.energy_threshold = 120 # minimum audio energy
            
            # Starts a background thread
            self.stop_listening = self.recognizer.listen_in_background(
                self.microphone, 
                self.callback,
                phrase_time_limit=None # Don't cut off hard
            )
            print("🎤 Listening for commands...")
        except Exception as e:
            print(f"🎤 Voice Init Error: {e}")

    def callback(self, recognizer, audio):
        try:
            # Revert to Google Speech Recognition (Cloud) per user preference
            # It handles noise/accents differently than local Whisper
            text = recognizer.recognize_google(audio).lower().strip()
            
            if text:
                print(f"🗣️ Heard (Google): '{text}'")
                
                # WAKE WORD Logic
                # Only process if addressed directly
                clean_text = text.lower().strip()
                # Remove punctuation from start
                clean_text = clean_text.lstrip(".,-! ")
                
                WAKE_WORDS = ["narcissus", "hey narcissus", "mirror", "hey mirror", "smart mirror"]
                
                detected_trigger = None
                for trigger in WAKE_WORDS:
                    if clean_text.startswith(trigger):
                        detected_trigger = trigger
                        break
                
                if detected_trigger:
                    # Strip trigger and send command
                    command = clean_text[len(detected_trigger):].strip().lstrip(".,-! ")
                    if command:
                        print(f"🚀 Wake Word '{detected_trigger}' detected! Command: '{command}'")
                        self.event_queue.put({"type": "voice", "content": command})
                    else:
                        print(f"⚠️ Wake Word '{detected_trigger}' detected, but no command followed.")
                else:
                     print(f"💤 Ignored (No Wake Word): '{text}'")
                
        except sr.UnknownValueError:
            pass # Silence is golden
        except sr.RequestError as e:
            print(f"🎤 Voice API Error: {e}")

    def run(self):
        # Thread run method just keeps the object alive, 
        # but listen_in_background handles the actual work.
        self.start_background_listening()
        while True:
            time.sleep(1)
            
    def stop(self):
        if self.stop_listening:
            self.stop_listening(wait_for_stop=False)
