# ROS2-Based Low-Cost Mobile Robot for Educational Assistance with Reactive Navigation and Semantic-Cached Language Processing

> ROS2-based mobile assistant robot for educational environments, integrating offline NLP in Spanish, YOLOv8n object detection, and reactive navigation on Raspberry Pi 4B.

📄 **Paper:** *ROS2-Based Low-Cost Mobile Robot for Educational Assistance with Reactive Navigation and Semantic-Cached Language Processing* — Submitted to [Robotics (MDPI)](https://www.mdpi.com/journal/robotics), 2026.  
👥 **Authors:** Sebastián Alexis Aucapiña, Nataly Cecilia Benalcázar, José Varela-Aldás and Ramiro Isa-Jara  
🏛️ **Institution:** Universidad Tecnológica Indoamérica / ESPOCH — Ecuador

---

## Overview

This project presents a low-cost educational mobile robot that combines autonomous reactive navigation with offline natural language processing in Spanish. The system runs entirely on a **Raspberry Pi 4B** using **ROS2 Humble** as middleware, making it accessible for resource-constrained educational environments such as public schools or universities in Latin America.

The robot operates in two modes:
- **Education Mode** — answers academic questions via voice interaction using a hybrid NLP architecture
- **Navigation Mode** — navigates autonomously using visual and ultrasonic perception

Total hardware cost: **under $250 USD**.

<img width="1481" height="2509 alt="FrontalView2_1" src="https://github.com/user-attachments/assets/ec48239a-2f64-4a2d-8a29-7236c9ddf8cf" />


---

## System Architecture

The system is organized into four functional layers:

```
┌─────────────────────────────────────────┐
│         Application Layer               │
│     (Mode Orchestrator - ROS2 Node)     │
├─────────────────────────────────────────┤
│         Processing Layer                │
│  Vision | Speech/NLP | Navigation       │
├─────────────────────────────────────────┤
│         Abstraction Layer               │
│     (ROS2 Interface Nodes)              │
├─────────────────────────────────────────┤
│         Physical Layer                  │
│  Raspberry Pi 4B | Sensors | Actuators  │
└─────────────────────────────────────────┘
```

### ROS2 Nodes

| Node | Package | Function |
|------|---------|----------|
| `usb_camera_node` | `robot_vision` | Real-time image acquisition |
| `object_detector_node` | `robot_vision` | YOLOv8n-based object detection |
| `object_follower_node` | `robot_vision` | Motion command generation |
| `ultrasonic_node` | `robot_navigation` | Obstacle distance measurement |
| `imu_odometry_node` | `robot_navigation` | Orientation estimation (MPU6050) |
| `motor_controller_node` | `robot_navigation` | PWM motor control (TB6612FNG) |
| `voice_node` | `robot_voice` | Speech recognition + TTS + NLP orchestration |

---

## Hardware

| Component | Specification |
|-----------|--------------|
| Computing unit | Raspberry Pi 4B — 4GB RAM |
| OS | Ubuntu 22.04 Server (ARM64) |
| Motors | N20 DC motors — differential drive |
| Motor driver | TB6612FNG |
| IMU | MPU6050 |
| Camera | USB Camera (Logitech C270) |
| Ultrasonic sensor | HC-SR04 |
| Audio amplifier | PAM8403 + 8Ω speaker |
| Battery | 7.4V LiPo 2200mAh |
| Voltage regulator | LM2596 DC-DC step-down |

---

## Software Stack

| Component | Technology |
|-----------|-----------|
| Middleware | ROS2 Humble |
| Object detection | YOLOv8n (Ultralytics) |
| Speech recognition | VOSK (offline, Latin American Spanish) |
| TTS Online | Edge TTS |
| TTS Offline | Piper TTS |
| Local LLM | Qwen2.5-1.5B Q4_K_M (quantized) |
| Cloud LLM | Trinity via OpenRouter API |
| Semantic cache | all-MiniLM-L6-v2 (sentence-transformers) |

---

## Key Results

| Metric | Value |
|--------|-------|
| Speech recognition accuracy (quiet) | 98% |
| Speech recognition accuracy (noisy) | 98% |
| YOLOv8n F1-score | 0.975 |
| Door detection recall | 100% |
| Semantic cache accuracy | 100% |
| Semantic cache avg. latency | 3.8 s |
| Battery life — Education mode | 96 min (1.46 A) |
| Battery life — Navigation mode | 75.6 min (1.85 A) |
| Total hardware cost | < $250 USD |

---

## NLP Architecture

The NLP module uses a three-tier hybrid architecture to balance accuracy, latency, and energy consumption:

```
User Query (voice)
       │
       ▼
┌─────────────────┐     HIT      ┌──────────────────┐
│  Semantic Cache │─────────────▶│  Instant Response│
│  (embeddings)   │              └──────────────────┘
└────────┬────────┘
         │ MISS
         ▼
┌─────────────────┐
│  Local Model    │  Qwen2.5-1.5B Q4_K_M (offline)
│  (Qwen)         │
└────────┬────────┘
         │ Complex query / no connectivity
         ▼
┌─────────────────┐
│  Cloud Model    │  Trinity via OpenRouter (online)
│  (Trinity)      │
└─────────────────┘
```

The semantic cache resolved **33.3% of queries** without invoking any LLM, significantly reducing energy consumption and latency.

---

## Installation

### Prerequisites

- Raspberry Pi 4B with Ubuntu 22.04 Server (ARM64)
- ROS2 Humble installed
- Python 3.10+

### 1. Clone the repository

```bash
git clone https://github.com/SesSic/MobileRobotAssistantNLPROS2.git
cd MobileRobotAssistantNLPROS2
```

### 2. Install ROS2 dependencies

```bash
sudo apt install ros-humble-usb-cam ros-humble-cv-bridge ros-humble-sensor-msgs
```

### 3. Install Python dependencies

```bash
pip install ultralytics vosk sentence-transformers openai --break-system-packages
```

### 4. Download models (not included — large files)

| Model | Destination | Source |
|-------|------------|--------|
| VOSK Spanish small | `model-vosk-es-small/` | [alphacephei.com/vosk/models](https://alphacephei.com/vosk/models) — `vosk-model-small-es-0.42` |
| YOLOv8n | workspace root | auto-downloaded on first run via Ultralytics |
| Door detector | `src/robot_vision/models/` | see Dataset section below |
| Piper TTS | `/home/<user>/piper/` | [github.com/rhasspy/piper](https://github.com/rhasspy/piper) |

> **Note:** After downloading Piper, update the `piper_path` parameter in `src/robot_educativo/launch/robot_completo_launch.py` to match your installation path.

### 5. Configure audio devices

Edit `src/robot_educativo/launch/robot_completo_launch.py` and set your actual ALSA device IDs:

```python
'mic_device': 'hw:1,0',       # your microphone
'speaker_device': 'plughw:2,0' # your speaker
```

Run `arecord -l` and `aplay -l` on the Pi to find your device numbers.

### 6. Add your OpenRouter API key

Edit `src/robot_voice/robot_voice/unified_processor.py` and replace:

```python
'openrouter_api_key': "YOUR_OPENROUTER_API_KEY_HERE"
```

### 7. Build and launch

```bash
colcon build
source install/setup.bash
ros2 launch robot_educativo robot_completo_launch.py
```

---

## Repository Structure

```
MobileRobotAssistantNLPROS2/
├── src/
│   ├── robot_educativo/        # Main package: orchestrator + launch
│   ├── robot_navigation/       # Motor, ultrasonic, IMU nodes
│   ├── robot_vision/           # Camera, YOLO, follower nodes
│   └── robot_voice/            # Voice recognition, TTS, NLP nodes
├── scripts/                    # Utility and test scripts
├── start_robot.sh              # Convenience startup script
├── test_openrouter.py          # API connectivity test
├── test_embeddings.py          # Semantic cache test
├── test_vosk_integrado.py      # Speech recognition test
└── .gitignore
```

> `build/`, `install/`, `log/`, and model files are excluded from the repository. Run `colcon build` to generate them locally.

---

## Dataset

Door detection model trained using transfer learning on the [Door Dataset](https://universe.roboflow.com/coins-j8vwp/door-p28ku) from Roboflow Universe (accessed March 2026).

---

## Data Availability

The experimental data supporting the results of this study are available upon reasonable request: saucapina2@indoamerica.edu.ec

---

## Citation

If you use this work, please cite:

```bibtex
@article{aucapina2026mobile,
  title={ROS2-Based Low-Cost Mobile Robot for Educational Assistance with Reactive Navigation and Semantic-Cached Language Processing},
  author={Aucapi{\~n}a, Sebasti{\'a}n Alexis and Benalc{\'a}zar, Nataly Cecilia and Varela-Ald{\'a}s, Jos{\'e} and Isa-Jara, Ramiro},
  journal={Robotics},
  publisher={MDPI},
  year={2026}
}
```

> DOI will be added upon acceptance.

---

## License

This project is licensed under the [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/) license, consistent with MDPI open access policy.

---

## Acknowledgments

The authors acknowledge the support of the Facultad de Ingenierías, Maestría en Robótica y Automatización Industrial, Universidad Tecnológica Indoamérica, Ambato, Ecuador.
