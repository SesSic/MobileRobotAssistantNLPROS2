# Mobile Robot Assistant for Autonomous Navigation Using NLP and ROS2

> ROS2-based mobile assistant robot for educational environments, integrating offline NLP in Spanish, YOLOv8n object detection, and reactive navigation on Raspberry Pi 4B.

📄 **Paper:** *Mobile Robot Assistant for Autonomous Navigation in Controlled Environments Using Natural Language Processing and ROS2* — Submitted to [Robotics (MDPI)](https://www.mdpi.com/journal/robotics), 2026.  
👥 **Authors:** Sebastián Alexis Aucapiña, Nataly Cecilia Benalcázar, Ramiro Isa-Jara  
🏛️ **Institution:** Universidad Tecnológica Indoamérica / ESPOCH — Ecuador

---

## Overview

This project presents a low-cost educational mobile robot that combines autonomous reactive navigation with offline natural language processing in Spanish. The system runs entirely on a **Raspberry Pi 4B** using **ROS2 Humble** as middleware, making it accessible for resource-constrained educational environments such as public schools or universities in Latin America.

The robot operates in two modes:
- **Education Mode** — answers academic questions via voice interaction using a hybrid NLP architecture
- **Navigation Mode** — navigates autonomously using visual and ultrasonic perception

Total hardware cost: **under $250 USD**.

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

| Node | Function |
|------|----------|
| `usb_camera_node` | Real-time image acquisition |
| `object_detector_node` | YOLOv8n-based object detection |
| `object_follower_node` | Motion command generation |
| `ultrasonic_node` | Obstacle distance measurement |
| `imu_node` | Orientation estimation (MPU6050) |
| `motor_controller_node` | PWM motor control (TB6612FNG) |
| `voice_node` | Speech recognition + TTS + NLP orchestration |

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
| Local LLM | Qwen (quantized) |
| Cloud LLM | Trinity (online) |
| Semantic cache | Embedding-based similarity matching |

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
│  Local Model    │  Qwen (offline, quantized)
│  (Qwen)         │
└────────┬────────┘
         │ Complex query / no connectivity
         ▼
┌─────────────────┐
│  Cloud Model    │  Trinity API (online)
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

### Clone the repository

```bash
git clone https://github.com/SesSic/MobileRobotAssistantNLPROS2.git
cd MobileRobotAssistantNLPROS2
```

### Install dependencies

```bash
pip install ultralytics vosk --break-system-packages
sudo apt install ros-humble-cv-bridge ros-humble-sensor-msgs
```

### Build the ROS2 workspace

```bash
colcon build
source install/setup.bash
```

### Launch

```bash
# Education mode
ros2 launch robot_assistant education.launch.py

# Navigation mode
ros2 launch robot_assistant navigation.launch.py
```

---

## Dataset

Door detection model trained using transfer learning on the [Door Dataset](https://universe.roboflow.com/coins-j8vwp/door-p28ku) from Roboflow Universe (accessed March 2026).

---

## Data Availability

The experimental data supporting the results of this study are available upon reasonable request from the corresponding author: saucapina2@indoamerica.edu.ec / sebaaucaaa@gmail.com

---

## Citation

If you use this work, please cite:

```bibtex
@article{aucapina2026mobile,
  title={Mobile Robot Assistant for Autonomous Navigation in Controlled Environments Using Natural Language Processing and ROS2},
  author={Aucapi{\~n}a, Sebasti{\'a}n Alexis and Benalc{\'a}zar, Nataly Cecilia and Isa-Jara, Ramiro},
  journal={Robotics},
  publisher={MDPI},
  year={2026}
}
```

> ⚠️ DOI will be added upon acceptance.

---

## License

This project is licensed under the [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/) license, consistent with MDPI open access policy.

---

## Acknowledgments

The authors acknowledge the support of the Facultad de Ingenierías, Maestría en Robótica y Automatización Industrial, Universidad Tecnológica Indoamérica, Ambato, Ecuador.
