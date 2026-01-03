# 🪞 Narcissus Smart Mirror (Prototype v9)

Narcissus is a privacy-first, commercially viable AI smart mirror "Virtual Twin". It combines a classic **MagicMirror²** interface with a powerful **Python/AI Backend** that enables:

*   **👁️ Computer Vision**: Hand tracking, precise fingertip cursor, and gestural control.
*   **💄 AR Virtual Makeup**: Real-time lipstick overlay with "Touch-to-Change" (touch your lips in the mirror!).
*   **🎤 Voice Intelligence**: Natural language control via Ollama (Llama 3.2), capable of answering questions, changing settings, and searching the web.
*   **🔒 Privacy**: All AI processing happens locally (or via private API), with no persistent video cloud storage.

---

## 🏗️ Architecture

The system consists of two main components:

1.  **THE FACE (Frontend)**: 
    *   **Tech**: Node.js, MagicMirror² Framework.
    *   **Role**: Displays the UI (Clock, Weather, News) and renders the AR video feedback.
    *   **Location**: `MagicMirror/`

2.  **THE BRAIN (Backend)**: 
    *   **Tech**: Python 3.10+, MediaPipe, OpenCV, Flask, Ollama.
    *   **Role**: Handles camera input, detects gestures/faces, applies AR, manages state, and streams the processed video to the frontend.
    *   **Location**: `narcissus-proto/`

---

## 🛠️ Prerequisites

*   **Hardware**: Mac (M-Series recommended for performance) or Linux machine with Webcam & Microphone.
*   **Software**: 
    *   [Node.js](https://nodejs.org/) (v20+)
    *   [Python](https://www.python.org/) (v3.10 or v3.11)
    *   [Ollama](https://ollama.com/) (running `llama3.2`)

---

## 🚀 Installation

### 1. Backend Setup (The Brain)

Navigate to the backend folder and set up the Python environment:

```bash
cd narcissus-proto

# Create Virtual Environment (Python 3.10 or 3.11)
python3 -m venv venv

# Activate Environment
source venv/bin/activate

# Install Dependencies
pip install -r requirements.txt
```

**Note for Mac Users**: You may need to install `portaudio` for microphone access:
```bash
brew install portaudio
```

### 2. Frontend Setup (The Face)

Navigate to the frontend folder and install Node dependencies:

```bash
cd ../MagicMirror

# Install Dependencies
npm install
```

The configuration is already set up in `config/config.js` to include the Narcissus modules.

---

## 🎮 How to Run

You need to run **two terminal sessions** simultaneously.

### Terminal 1: Application Backend
```bash
cd narcissus-proto
source venv/bin/activate
python simulation_multimodal.py
```
*Wait until you see "Starting Video Stream" and "Listening for commands..."*

### Terminal 2: MagicMirror Interface
```bash
cd MagicMirror
npm run start
```

---

## ✨ Features & Usage

### 👄 AR Virtual Lipstick
*   **Voice**: Say "Mirror, I want red lips" (or pink, purple, nude, dark).
*   **Touch**: 👆 **Touch your own lips** in the mirror reflection and **hold for 1 second**. The color will cycle instantly!

### 👋 Gestures
*   **Open Hand (Hold Left)**: Switch to **Dashboard Mode** (Widgets visible, Video hidden).
*   **Closed Fist (Hold Right)**: Switch to **Mirror Mode** (Full-screen Video).
*(Check `simulation_multimodal.py` logs for active gestures)*

### 🧠 Voice Assistant
*   **Wake Word**: "Hey Mirror" or "Mirror".
*   **Commands**:
    *   "Turn brightness up/down" to 50%"
    *   "Who is the president of France?" (Uses DuckDuckGo)
    *   "Play some jazz" (Opens YouTube Music)

---

## 📁 Directory Structure

*   `narcissus-proto/`:
    *   `simulation_multimodal.py`: Main entry point.
    *   `ar_makeup.py`: AR logic (MediaPipe Face Mesh).
    *   `gesture_input.py`: Hand tracking logic.
    *   `video_server.py`: Flask MJPEG streamer.
*   `MagicMirror/`:
    *   `modules/MMM-NarcissusMirror/`: Custom module to display the Python stream.
    *   `config/config.js`: Main configuration file.

---

## 🐛 Troubleshooting

*   **"Camera not found"**: Ensure no other app (Zoom, FaceTime) is using the webcam.
*   **"Address in use"**: If the backend fails to start, check if port `5050` is free.
*   **Slow Voice**: Ensure Ollama is running (`ollama serve`) and the model `llama3.2` is pulled.

---
*Project Narcissus - 2025*
