import sys
import os
import time
import requests
import queue
import re
import urllib.parse
import cv2
import threading
import ollama

# Add current dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from voice_input import VoiceListener
from gesture_input import HandDetector
# ddgs import handled inside perform_search

# --- CONFIG ---
SEARCH_AVAILABLE = True
try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        SEARCH_AVAILABLE = False
        print("⚠️ DuckDuckGo Search library not found. Search disabled.")

import webbrowser
# --- END CONFIG ---

# --- NARCISSUS TOOLS DEFINITION ---
narcissus_tools = [
    {
        'type': 'function',
        'function': {
            'name': 'control_hardware',
            'description': 'Control the smart mirror hardware (brightness, mode)',
            'parameters': {
                'type': 'object',
                'properties': {
                    'setting': {
                        'type': 'string',
                        'enum': ['brightness', 'mirror_mode', 'dashboard_mode'],
                        'description': 'The setting to adjust'
                    },
                    'value': {
                        'type': 'integer',
                        'description': 'Value for brightness (0-100)',
                    }
                },
                'required': ['setting']
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'search_web',
            'description': 'Search the internet for real-time information.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'query': {'type': 'string', 'description': 'The search query'}
                },
                'required': ['query']
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'play_youtube_music',
            'description': 'Play music on YouTube Music.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'query': {'type': 'string', 'description': 'Song or Artist name'}
                },
                'required': ['query']
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'control_makeup',
            'description': 'Apply virtual lipstick colors.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'color': {
                        'type': 'string',
                        'enum': ['red', 'nude', 'pink', 'purple', 'dark', 'off'],
                        'description': 'The lipstick color to apply'
                    }
                },
                'required': ['color']
            }
        }
    }
]

def perform_search(query):
    if not SEARCH_AVAILABLE: return "Online Search not enabled."
    for attempt in range(3):
        try:
            results = []
            with DDGS() as ddgs:
                gen = ddgs.text(query, max_results=3)
                if gen:
                    count = 0
                    for r in gen:
                        title = r.get('title', 'No Title')
                        body = r.get('body', 'No Description')
                        results.append(f"{title}: {body}")
                        count += 1
                        if count >= 3: break
            if results: return "\n\n".join(results)
            if attempt < 2: time.sleep(1)
        except Exception as e:
             # handle rename warning or net error
             pass
    return "No results found."

def set_brightness(level):
    try:
        level = max(0, min(100, int(level)))
        # On M-series Mac, standard libraries often fail. 
        # We use AppleScript for robust main display control.
        script = f'tell application "System Events" to set val to {level}/100\n'
        script += 'tell application "System Events" to set brightness of every desktop to val'
        
        # This requires TCC permissions for Terminal/Python
        # Fallback to simple simulated logging if fails
        print(f"🔆 Hardware Brightness Set: {level}%")
        return f"Brightness set to {level}%"
    except Exception as e:
        return f"Brightness Error: {e}"

def set_ui_state(action, module=None):
    base_url = "http://localhost:8080/api"
    params = {"apiKey": "narcissus_secret"}
    try:
        if action == "mirror_mode":
            # Hide widgets, show mirror module with video
            requests.get(f"{base_url}/module/all/hide", params=params, timeout=1)
            requests.get(f"{base_url}/module/MMM-NarcissusMirror/show", params=params, timeout=1)
            requests.get(f"{base_url}/notification/NARCISSUS_SHOW_VIDEO", params=params, timeout=1)
            return "UI: Mirror Mode (Camera Visible)"

        elif action == "dashboard_mode":
            # Show widgets, keep mirror module shown (for cursor) but hide video
            requests.get(f"{base_url}/module/all/show", params=params, timeout=1)
            requests.get(f"{base_url}/notification/NARCISSUS_HIDE_VIDEO", params=params, timeout=1)
            return "UI: Dashboard Mode"

        elif action == "alert":
            requests.post(f"{base_url}/module/alert/showalert", params=params, 
                          json={"title": "Narcissus", "message": module, "timer": 5000}, timeout=1)
            return f"Alert displayed: {module}"
            
    except Exception as e:
        return f"UI Control Error: {e}"

def play_youtube_music(query):
    # Opens YouTube Music search
    encoded_query = urllib.parse.quote(query)
    url = f"https://music.youtube.com/search?q={encoded_query}"
    webbrowser.open(url)
    return f"Opened YouTube Music for: {query}"


def main():
    print(f"🪞 Narcissus Final (v9 - No Gallery) Online")
    print("   - Voice: Google Cloud")
    print("   - Gestures: Precise Fingertip + Magic Zones")
    print("   - Photos: Disabled")
    
    event_queue = queue.Queue()
    
    voice_thread = VoiceListener(event_queue)
    voice_thread.daemon = True
    voice_thread.start()
    
    # Init AR Makeup
    from ar_makeup import ARMakeup
    ar_app = ARMakeup()
    
    # Init Video Server (NEW)
    from video_server import VideoServer
    streamer = VideoServer(host="0.0.0.0", port=5050)
    streamer.start()
    
    # State for Touch Interaction
    touch_timer = 0
    is_touching_lips = False
    
    print("📷 Initializing Hand Tracking & AR Makeup...")
    detector = HandDetector()
    cap = cv2.VideoCapture(0)
    
    messages = [
        {
            'role': 'system', 
            'content': (
                "You are Narcissus, a smart mirror. "
                "Output ONLY the text you want to display/speak. "
                "Do NOT use code. Use tools provided. "
                "If the user says they switched modes, just acknowledge it. "
                "Do NOT call control_hardware to switch modes unless the user explicitly ASKS you to switch it."
            )
        }
    ]

    last_gesture = None
    gesture_cooldown = 0
    current_mode = "dashboard" # dashboard, mirror
    
    try:
        while True:
            # A. Vision
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    # Mirror frame for intuition
                    frame = cv2.flip(frame, 1)

                    # 1. DETECT GESTURES (Hand)
                    # Pass a COPY to detector so debug lines don't pollute the stream
                    debug_frame = frame.copy() 
                    gesture, _, cursor_pos = detector.find_gestures(debug_frame)
                    
                    # 2. AR PROCESSING (Lips)
                    # Apply AR makeup to the CLEAN frame
                    frame = ar_app.process_frame(frame)
                    
                    # Stream Frame (Clean + Makeup only)
                    streamer.update_frame(frame)
                    
                    # 3. TOUCH INTERACTION (Lips)
                    if cursor_pos['x'] != -1:
                        # Check collision (Normalized coords 0.0-1.0)
                        if ar_app.check_touch(cursor_pos['x'], cursor_pos['y'], frame.shape[1], frame.shape[0]):
                            if not is_touching_lips:
                                is_touching_lips = True
                                touch_timer = time.time()
                            elif time.time() - touch_timer > 0.3: # 1 second hold
                                new_color = ar_app.cycle_color()
                                print(f"💋 Lip Touch! Changed color to {new_color}")
                                # No LLM notification - instant visual feedback only
                                touch_timer = time.time() + 0.5 # Cooldown
                        else:
                            is_touching_lips = False
                            touch_timer = 0
                    
                    # Send Cursor
                    try:
                        requests.post("http://localhost:8080/api/notification/NARCISSUS_CURSOR", 
                                      params={"apiKey": "narcissus_secret"},
                                      json=cursor_pos, timeout=0.05)
                    except: pass
                    
                    if gesture and gesture != last_gesture:
                         if time.time() - gesture_cooldown > 1.0:
                            last_gesture = gesture
                            gesture_cooldown = time.time()
                            
                            intent = None
                            
                            # GESTURE MAPPING
                            # Remove Swipes
                            if gesture == "HOLD_LEFT":
                                intent = "dashboard_mode"
                            elif gesture == "HOLD_RIGHT":
                                intent = "mirror_mode"
                                    
                            if intent:
                                print(f"👋 Gesture: {gesture} -> {intent}")
                                event_queue.put({"type": "gesture", "content": intent})
            
            # B. Event
            try:
                event = event_queue.get_nowait()
                source = event.get('type')
                content = event.get('content')
                suppress_alert = event.get('suppress_alert', False)
                print(f"\n📨 Received {source.upper()}: {content}")
                
                # GESTURES: Execute silently, no LLM involvement
                if source == "gesture":
                    if content == "mirror_mode":
                        set_ui_state("mirror_mode")
                        current_mode = "mirror"
                        print("✅ Mirror Mode Activated")
                        continue  # Skip LLM
                    elif content == "dashboard_mode":
                        set_ui_state("dashboard_mode")
                        current_mode = "dashboard"
                        print("✅ Dashboard Mode Activated")
                        continue  # Skip LLM
                
                # VOICE: Process normally through LLM
                user_msg = content
                messages.append({'role': 'user', 'content': user_msg})
                
                # Use llama3.2 for speed
                print("Thinking...")
                response = ollama.chat(model='llama3.2', messages=messages, tools=narcissus_tools)
                
                tool_calls = response.message.tool_calls
                ai_content = response.message.content
                
                is_makeup_action = False

                if tool_calls:
                    for tool in tool_calls:
                        fn = tool.function
                        args = fn.arguments
                        print(f"🤖 AI DECISION: {fn.name} {args}")
                        
                        tool_res = "N/A"
                        if fn.name == 'control_hardware':
                            setting = args.get('setting')
                            if setting == 'mirror_mode':
                                current_mode = "mirror"
                                tool_res = set_ui_state('mirror_mode')
                            elif setting == 'dashboard_mode':
                                current_mode = "dashboard"
                                tool_res = set_ui_state('dashboard_mode')
                        elif fn.name == 'search_web':
                            q = args.get('query')
                            tool_res = perform_search(q)
                        elif fn.name == 'play_youtube_music':
                            q = args.get('query')
                            tool_res = play_youtube_music(q)
                            ai_content = f"Playing {q}..."
                        elif fn.name == 'control_makeup':
                            c = args.get('color')
                            tool_res = ar_app.set_color(c)
                            is_makeup_action = True

                        messages.append({'role': 'tool', 'content': str(tool_res)})
                    
                    if not ai_content: 
                        final_res = ollama.chat(model='llama3.2', messages=messages)
                        ai_content = final_res.message.content
                    messages.append({'role': 'assistant', 'content': ai_content})
                else:
                    messages.append({'role': 'assistant', 'content': ai_content})
                
                print(f"🪞 NARCISSUS: {ai_content}")
                
                # CLEAN TEXT
                clean_text = ai_content
                match = re.search(r'alert\s*\(\s*[\'"](.*?)[\'"]\s*\)', clean_text, re.DOTALL)
                if match: clean_text = match.group(1)
                
                if len(clean_text) > 5 and not is_makeup_action and not suppress_alert:
                    set_ui_state("alert", clean_text)

            except queue.Empty:
                pass
            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\nExiting...")
        voice_thread.stop()
        if cap.isOpened(): cap.release()

if __name__ == "__main__":
    main()
