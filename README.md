# ⚡ STARK LAB v5 – Real-Time Gesture 3D Model Viewer

A powerful real-time 3D model viewer that responds to hand gestures captured via webcam. Control 3D models (STL format) using intuitive hand movements powered by **MediaPipe**, **PyOpenGL**, and **GLFW**.

![Stark Lab](https://img.shields.io/badge/Version-5.0-blue)
![Python](https://img.shields.io/badge/Python-3.8%2B-brightgreen)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 🎯 Features

- **Real-time Hand Gesture Recognition** – Webcam-based hand tracking via MediaPipe
- **Smooth Gesture Controls** – Rotate, zoom, and tilt 3D models with natural hand movements
- **STL Model Support** – Load binary and ASCII STL files
- **Hardware-Accelerated 3D** – PyOpenGL with VBO rendering
- **Fallback Mouse Mode** – Works without webcam using mouse input
- **Auto-Spin** – Continuous model rotation for presentations
- **Cross-Platform** – Linux, macOS, Windows support

---

## 🎮 Gesture Controls

| Gesture | Movement | Action |
|---------|----------|--------|
| ✋ **Open Hand** | Wave RIGHT | Rotate clockwise (smooth) |
| ✋ **Open Hand** | Wave LEFT | Rotate counter-clockwise (smooth) |
| 🤏 **Pinch** | Move UP | Zoom in (smooth) |
| 🤏 **Pinch** | Move DOWN | Zoom out (smooth) |
| ☝️ **Point** | Move UP/DOWN | Tilt on X-axis |
| ✊ **Fist** | (static) | Lock/freeze model position |
| 👌 **OK Sign** | (static) | Reset all transforms |

**Note:** 2.5 second hold required before switching gestures (prevents accidents). Fist & OK switch instantly.

### ⌨️ Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `S` | Toggle auto-spin |
| `R` | Reset transforms |
| `O` | Open STL file dialog |
| `ESC` | Quit |

---

## ⚙️ Requirements

### System Dependencies

- **Python 3.8+**
- **OpenGL** support (most modern GPUs)
- **Webcam** (optional – falls back to mouse mode)

### Python Packages

```bash
pip install -r requirements.txt
```

**Core dependencies:**
- `glfw` – Window management
- `PyOpenGL` – 3D rendering
- `numpy` – Numerical operations
- `opencv-python` – Video capture
- `mediapipe` – Hand gesture recognition

---

## 🚀 Quick Start

### 1️⃣ Install Dependencies

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

### 2️⃣ Run the App

```bash
# Launch with file dialog
python3 starklab.py

# Or load an STL file directly
python3 starklab.py /path/to/model.stl

# Example
python3 starklab.py MK1.stl
```

### 3️⃣ Use Hand Gestures

- Position your hand ~30-50cm from webcam
- Perform gestures to control the model
- Use keyboard shortcuts as needed

---

## 📦 Project Structure

```
starklab/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── starklab.py              # Main application (v5)
├── files2/
│   ├── stark_lab.py         # Alternate version
│   └── venv/                # Virtual environment
└── stark3d/
    ├── models/              # STL model files
    └── requirements.txt
```

---

## 🔧 Development

### Code Architecture

**STLMesh** – Loads and normalizes binary/ASCII STL files
```python
mesh = STLMesh()
mesh.load("model.stl")
```

**HandTracker** – Captures webcam frames and detects hand landmarks via MediaPipe
```python
tracker = HandTracker()
tracker.start()  # Runs in background thread
```

**StarkLabRenderer** – Manages OpenGL rendering and gesture processing
```python
renderer = StarkLabRenderer()
renderer.run(stl_path)
```

### Performance Tips

- Use **binary STL** files (faster loading than ASCII)
- Smaller models (<100k triangles) for smooth 60 FPS
- Ensure adequate lighting for hand detection
- Use `S` to enable auto-spin when hands aren't visible

---

## 🎓 Sample Models

Free STL models to test with:

- **Thingiverse** – https://www.thingiverse.com (search "head", "helmet", "gear")
- **Printables** – https://www.printables.com
- **Free3D** – https://free3d.com (filter by STL)

**Recommended models:**
- Iron Man helmet
- Mechanical gears
- Anatomical models
- Architectural components

---

## 🐛 Troubleshooting

### MediaPipe not found
```bash
pip install mediapipe==0.10.14
```

### No webcam detected
- Falls back to **mouse mode** automatically
- Left-click drag to rotate
- Right-click drag to scale

### Slow performance
- Reduce model complexity (decimate in Blender)
- Lower camera resolution in code (change `cv2.resize()` params)
- Disable auto-spin when not needed

### Hand not detected
- Ensure good lighting
- Keep hand 30-50cm from camera
- Make clear, distinct gestures

---

## 🔐 Optional: Intel RealSense Support

For depth-aware hand tracking (advanced):

```bash
sudo apt install librealsense2 librealsense2-dev  # Ubuntu
pip install pyrealsense2
```

Then uncomment RealSense code in `starklab.py` (see comments in source).

---

## 📜 License

MIT License – See LICENSE file for details

---

## 🤝 Contributing

Contributions welcome! Areas for improvement:

- [ ] Support for GLTF/GLB models
- [ ] Multi-hand gesture combos
- [ ] Haptic feedback integration
- [ ] WebGL export
- [ ] Real-time model assembly/disassembly

---

## 👤 Author

**Knight** – Stark Gesture Lab Project

---

## 📞 Support

For issues, questions, or feature requests:
1. Check [Troubleshooting](#-troubleshooting) section
2. Verify all dependencies are installed
3. Test with sample models first
4. Open an issue on GitHub

---

## 🎬 Quick Reference

### Launch Examples

```bash
# Interactive file picker
python3 starklab.py

# Load specific model
python3 starklab.py iron_man_helmet.stl

# With activated venv
source venv/bin/activate && python3 starklab.py

# Run tests (if available)
python3 -m pytest tests/
```

### Performance Metrics

- **Typical FPS:** 30-60 (depending on model complexity)
- **Hand Detection Latency:** ~100-150ms
- **Memory Usage:** ~200-500 MB (for large models)

---

**Made with ⚡ for real-time gesture control of 3D models**
