# ⚡ STARK LAB — Hand Gesture 3D Viewer

> *"Sometimes you gotta run before you can walk."* — Tony Stark

Control and inspect 3D models using nothing but your hand gestures — just like Tony Stark in the Iron Man movies. Your webcam tracks your hand in real time using AI, and you can rotate, zoom, and tilt any 3D model without touching your keyboard or mouse.

---

## 📸 What It Looks Like

```
┌─────────────────────────────────────────────────────┐
│  STARK LAB  //  ✋ ROTATE ▶  //  MK1.STL  //  60fps │
│                                                     │
│  ┌──────────────┐                                   │
│  │ ✋  ROTATE   │     [  3D Model spins here  ]     │
│  │ ─────────── │                                   │
│  └──────────────┘              ┌──────────────────┐ │
│                                │  📷 Camera Feed  │ │
│                                │  (hand landmarks)│ │
│  ════════════════════════════  └──────────────────┘ │
└─────────────────────────────────────────────────────┘
```

---

## 🖥️ Requirements

### Hardware
- A computer with a **webcam** (built-in laptop camera works great)
- Any modern PC / laptop running **Ubuntu Linux**

### Software
- Python 3.8 or higher
- pip3 (Python package manager)

---

## 🚀 Installation — Step by Step

### Step 1 — Open Terminal
Press `Ctrl + Alt + T` to open a terminal window.

### Step 2 — Create a project folder
```bash
mkdir ~/starklab
cd ~/starklab
```

### Step 3 — Install all required packages
```bash
pip3 install pyopengl pyopengl-accelerate glfw numpy opencv-python mediapipe==0.10.9
```

> ⏳ This may take 2–5 minutes. Let it finish completely.

### Step 4 — Install tkinter (for file dialogs)
```bash
sudo apt install python3-tk
```

### Step 5 — Download the Stark Lab script
Download `starklab.py` from the project and place it inside `~/starklab/`.

### Step 6 — Get a 3D model (STL file)
Download any free STL file from one of these websites:
- 🌐 [thingiverse.com](https://www.thingiverse.com) — search "Iron Man", "robot", "gear"
- 🌐 [printables.com](https://www.printables.com) — high quality models
- 🌐 [free3d.com](https://free3d.com) — search and filter by STL format

After downloading, unzip the file if needed. You'll get a file ending in `.stl` or `.STL`.

### Step 7 — Run Stark Lab
```bash
cd ~/starklab
python3 starklab.py /path/to/your/model.stl
```

**Example:**
```bash
python3 starklab.py /home/knight/MK1.STL
```

---

## 🖐️ Gesture Controls

Hold each gesture steady for **2.5 seconds** to activate it. This prevents accidental switches when moving between gestures. A countdown bar shows on screen while it's activating.

| Gesture | How to do it | What it does |
|---|---|---|
| ✋ Open Hand | Spread all 5 fingers open | **Rotate mode** |
| ↔️ Wave Right | Open hand, move right | Rotate clockwise |
| ↔️ Wave Left | Open hand, move left | Rotate anti-clockwise |
| 🤏 Pinch | Touch thumb tip to index tip | **Zoom mode** |
| ⬆️ Pinch Up | Pinch + move hand upward | Zoom in |
| ⬇️ Pinch Down | Pinch + move hand downward | Zoom out |
| ☝️ Point | Extend only index finger | **Tilt mode** — move up/down to tilt |
| ✊ Fist | Close all fingers into a fist | **Lock** — freezes the model |
| 👌 OK Sign | Touch thumb + index, others open | **Reset** — back to default view |

> 💡 **Tip:** OK and Fist switch **instantly** — no 2.5s wait needed.

---

## ⌨️ Keyboard Shortcuts

| Key | Action |
|---|---|
| `S` | Toggle auto-spin (model spins on its own) |
| `R` | Reset — return to default position and zoom |
| `ESC` | Quit Stark Lab |

---

## 📂 Loading STL Files

You have 3 ways to load a model:

**Option 1 — Command line (recommended)**
```bash
python3 starklab.py /home/yourname/Downloads/model.stl
```

**Option 2 — Drag and drop**
1. Run `python3 starklab.py` (no file argument)
2. Drag any `.stl` file from your file manager onto the Stark Lab window
3. The model loads instantly with a green flash

**Option 3 — Auto-spin test**
Once a model is loaded, press `S` to auto-spin it and check it looks right before using gestures.

---

## 🔍 What You See On Screen

```
┌─ Gesture Panel (top-left) ──────────────────┐
│  Coloured bar shows current active gesture   │
│  Progress bar fills during 2.5s countdown   │
└──────────────────────────────────────────────┘

┌─ Camera Preview (bottom-right) ─────────────┐
│  Live webcam feed                            │
│  Green/white dots = hand landmarks           │
│  Lines = finger connections                  │
└──────────────────────────────────────────────┘

┌─ Title Bar ─────────────────────────────────┐
│  STARK LAB // gesture // filename // fps     │
└──────────────────────────────────────────────┘

┌─ Blue Grid (floor) ─────────────────────────┐
│  Holographic floor grid for depth reference  │
└──────────────────────────────────────────────┘
```

---

## ⚠️ Troubleshooting

### ❌ `ModuleNotFoundError: No module named 'glfw'`
```bash
pip3 install glfw pyopengl pyopengl-accelerate
```

### ❌ `mediapipe has no attribute 'solutions'`
```bash
pip3 uninstall mediapipe -y
pip3 install mediapipe==0.10.9
```

### ❌ `Cannot open webcam`
Check if your webcam is detected:
```bash
v4l2-ctl --list-devices
```
If your camera is at `/dev/video1` instead of `/dev/video0`, run:
```bash
python3 starklab.py /path/to/model.stl 1
```
(The `1` at the end sets the camera index)

### ❌ STL file not loading / "no model" in title bar
Make sure the file path is correct and the file actually exists:
```bash
ls -lh /path/to/your/file.stl
```
Note: Linux filenames are **case-sensitive** — `MK1.STL` and `mk1.stl` are different!

### ❌ Hand not being detected
- Make sure your hand is clearly visible to the camera
- Use in a well-lit room — avoid backlighting
- Keep your hand 30–60 cm from the camera
- Check the camera preview box (bottom-right) to see what the camera sees

### ❌ Gestures feel laggy or jittery
- Close other applications to free up CPU
- Make sure you're running Python 3.8+
- Reduce background light noise

---

## 📁 Project Structure

```
~/starklab/
│
├── starklab.py          ← Main application (this is all you need)
├── requirements.txt     ← Package list
└── README.md            ← This file
```

---

## 🧠 How It Works (Simple Explanation)

```
Your Hand
   ↓
Webcam captures video frames
   ↓
MediaPipe AI detects 21 landmarks on your hand
   ↓
Stark Lab classifies the landmark positions into gestures
   ↓
Gestures are translated into 3D transforms (rotate / scale / tilt)
   ↓
PyOpenGL renders the STL model with the new transform
   ↓
You see the model move in real time!
```

**The 21 hand landmarks MediaPipe tracks:**
```
        4
        |
    3   8   12  16  20
    |   |   |   |   |
    2   7   11  15  19
    |   |   |   |   |
    1   6   10  14  18
     \  |   |   |   |
      \ 5   9   13  17
       \|___|___|___|
            0  (wrist)
```
Stark Lab checks whether fingertips (4,8,12,16,20) are above or below their knuckles to decide if each finger is up or down — that's how it tells your gestures apart.

---

## 🛠️ Tech Stack

| Tool | Purpose |
|---|---|
| **Python 3** | Programming language |
| **MediaPipe** | AI hand landmark detection (Google) |
| **OpenCV** | Webcam capture + camera preview |
| **PyOpenGL** | 3D rendering engine |
| **GLFW** | Window creation and input handling |
| **NumPy** | Fast math for 3D geometry |

---

## 💡 Tips for Best Experience

1. **Good lighting** is the most important factor — sit facing a window or lamp
2. **Plain background** behind your hand helps detection accuracy
3. **Hold gestures steady** — wait for the countdown bar to fill before moving
4. **Start with auto-spin** (`S` key) to verify your model loaded correctly
5. **Use pinch zoom first** — it's the most satisfying gesture to try!

---

*Built with ❤️ — Inspired by Tony Stark*
