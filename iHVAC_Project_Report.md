# SVKM’s NMIMS · School of Technology Management & Engineering (STME)
### Department of Computer Engineering, Mumbai
**Course:** Image and Video Processing (IVP) · Mini-Project Report

---

# **iHVAC: Intelligent HVAC Occupancy Mapping & Room Automation**
### *Vision-Based Zonal Lighting and Dynamic Multi-Tier Thermostat Control*

| **Student Details** | **Academic & Institutional Details** |
| :--- | :--- |
| **Anupam Kanoongo** (Roll No: F044, SAP ID: 70022400311)<br/>**Arjun Borkar** (Roll No: F005, SAP ID: 70022400057)<br/>**Asmit Baldi** (Roll No: F042, SAP ID: 70022400309) | **Programme / Division:** B.Tech. CE, Section A<br/>**Faculty Mentor:** Dr. Raj Gaurav Mishra<br/>**Academic Year:** 2026 – 2027<br/>**Submission Date:** October 13, 2026 |

---

## **Abstract**
Lighting and heating, ventilation, and air conditioning (HVAC) systems in educational and commercial facilities typically operate on static schedules or manual overrides, generating severe energy waste in vacant or partially occupied rooms. This project introduces **iHVAC**, an intelligent computer vision system that detects occupants in real time using overhead monocular video and dynamically regulates zonal illumination and climate setpoints. The video stream is processed by a deep convolutional YOLO person detector paired with the ByteTrack multi-object tracking algorithm. Bounding boxes are projected onto an 8×6 perspective-calibrated room grid using polygon intersection tests (`cv2.intersectConvexConvex`) to identify active zones. To eliminate disruptive relay chatter, a 10-second temporal settling hysteresis debounces lighting actuation. Climate control employs a multi-tiered comfort engine that automatically transitions setpoints across 26°C (vacant / AC OFF), 23°C (standard occupancy), and 21°C (high occupancy). Experimental evaluation over 355 operational logging snapshots and 1,345 historical transitions demonstrated reliable detection (mean confidence: 0.77), stable debounce behavior, and responsive thermal adjustments, managed through an interactive real-time Tkinter monitoring dashboard.

---

## **1. Introduction**

### **1.1 Background of the Problem**
Commercial and institutional buildings account for approximately 40% of global electricity consumption, with HVAC and artificial lighting representing over 65% of total facility energy usage. Traditional building automation systems (BAS) rely heavily on fixed timetable clocks or rudimentary wall-mounted sensors. In academic institutions, lecture halls and seminar rooms frequently experience erratic attendance patterns, intermittent usage, and extended vacancies. Leaving cooling compressors and high-wattage ceiling luminaires powered continuously during low-occupancy windows incurs substantial financial costs and unnecessary carbon emissions.

### **1.2 Why the Problem is Relevant**
Modern energy conservation standards (such as ASHRAE Standard 90.1 and ISO 50001) mandate demand-controlled ventilation and occupancy-responsive building services. Furthermore, contemporary hybrid work and flexible academic schedules make predetermined operational calendars obsolete. Dynamic, real-time sensing of occupant presence is essential to balance human thermal comfort against aggressive electrical efficiency targets.

### **1.3 Role of Image and Video Processing**
Conventional occupancy sensors, such as Passive Infrared (PIR) and ultrasonic detectors, suffer from fundamental physical shortcomings: they fail to detect stationary occupants (e.g., individuals reading or typing), provide zero spatial coordinate data, and cannot report headcount density. Carbon dioxide ($CO_2$) sensors exhibit multi-minute latency due to air dispersal delays. In contrast, video processing captures rich spatial context. A single optical sensor can simultaneously identify occupant count, precise spatial coordinates, motion vectors, and zone occupancy without requiring intrusive wearable badges or specialized hardware.

### **1.4 Motivation for Selecting the Project**
The motivation behind iHVAC is to bridge theoretical image and video processing algorithms with tangible cyber-physical automation. By synthesizing real-time deep neural object detection, multi-frame object association, perspective projection geometry, and temporal debouncing into an operational IoT control loop, the project delivers an end-to-end practical solution for smart campus environments.

---

## **2. Problem Statement and Objectives**

### **Problem Statement**
Commercial and educational indoor spaces suffer from persistent energy waste due to static, unmonitored HVAC and lighting operation. Existing presence sensors lack spatial resolution and stationary human detection capability. The challenge is to design an automated vision-based system that accurately counts occupants, localizes them to physical room sub-zones in real time from a fixed downward-angled camera, and issues robust, flicker-free control signals to building electrical loads.

### **Specific Objectives**
1. **Real-Time Human Detection & Multi-Object Tracking:** Ingest monocular video streams at $\ge 30$ FPS and perform robust person detection (COCO class 0) with persistent cross-frame tracking via ByteTrack.
2. **Geometric Perspective Modeling & Spatial Discretization:** Mathematically project 2D camera coordinates onto an 8×6 perspective grid compensating for downward pitch angle (30°), mapping people to discrete room cells.
3. **Flicker-Free Zonal Lighting Automation:** Implement a 10-second temporal hysteresis debouncing state machine to ensure lighting relays switch only upon verified, stable state transitions.
4. **Headcount-Driven HVAC Temperature Modulation:** Dynamically adjust air conditioning power and target temperature setpoints across customized thermal comfort profiles (26°C empty, 23°C occupied, 21°C busy).
5. **Interactive Dashboard, Historical Replay & Hardware Bridge:** Develop a full-featured graphical monitoring interface with live heatmap overlays, historical scrub playback, sensor telemetry ingestion, and optional Arduino relay interfacing.

---

## **3. Scope of the Project**

### **3.1 What the Project Covers**
- End-to-end monocular video pipeline from camera capture to physical relay actuation.
- Real-time person detection, multi-person tracking, and perspective-corrected 2D spatial grid partitioning.
- Multi-tier automated thermostat regulation based on instantaneous visible occupancy.
- Temporal state settling (10s debounce) to guard hardware relays against mechanical wear and rapid switching.
- Real-time Tkinter monitoring dashboard, telemetry persistence (JSON/CSV), and interactive timeline playback.
- Microcontroller interfacing via pyFirmata over USB/serial for real-world relay driving.

### **3.2 What the Project Does Not Cover**
- Facial recognition, individual biometric tracking, or identity logging (strict privacy preservation; video frames are processed transiently and not stored on disk).
- Multi-camera spatial stitching across multiple interconnected halls or PTZ camera tracking.
- Thermodynamic computational fluid dynamic (CFD) modeling of room airflow distribution.
- Thermal infrared night vision (relies on ambient visible indoor illumination).

### **3.3 Type of Videos & Application Domain**
- **Video Characteristics:** Continuous RGB monocular video feeds (640×480 to 1920×1080 resolution) captured from fixed ceiling or wall-mounted perspectives.
- **Application Domain:** Smart university classrooms, enterprise boardrooms, co-working facilities, and commercial building energy management systems (BEMS).

---

## **4. Dataset / Input Description**

- **Source of Input:** Real-time optical video captured from standard USB webcams (OpenCV video source index `0`), RTSP IP camera network streams, or pre-recorded test video files (`.mp4`, `.avi`).
- **Pretrained Weights:** Deep neural model inference utilizes Ultralytics YOLO checkpoints (`yolo26n.pt`, `yolo11n.pt`, `yolo11m.pt`) pretrained on the Microsoft Common Objects in Context (MS COCO) benchmark dataset, filtered exclusively for Category 0 (Person).
- **Operational Test Sessions:** Continuous real-world monitoring sessions recorded inside university laboratory and meeting rooms. The project log archive incorporates 355 persistent time-series snapshots and 1,345 granular event logs reflecting diverse human motion, room entries, exits, stationary meetings, and full vacancies.
- **Image Formatting:** Captured frames are standard 3-channel BGR numpy arrays converted into RGB tensors scaled to 640×640 pixels during convolutional inference.

---

## **5. Methodology / Proposed Approach**

### **5.1 Processing Pipeline**
The iHVAC processing pipeline follows a highly modular, decoupled architecture where perception, spatial mapping, device policy logic, hardware actuation, and graphical presentation interact synchronously:

```
[ Video Input Feed ]
         │ (OpenCV VideoCapture)
         ▼
[ YOLO Person Detection (640x640, Conf >= 0.45) ]
         │
         ▼
[ ByteTrack Multi-Object Tracking ]
         │
         ├───► Visible Headcount (N)
         │           │
         │           ▼
         │     [ Multi-Tier Climate Engine (Comfort Profiles) ]
         │           │
         │           ▼
         │     [ AC Relay Actuation (Pin 8) & Setpoint Target ]
         │
         └───► Bounding Box Polygons
                     │
                     ▼
         [ Perspective Room Grid (8x6 Cells, Tilt=30°) ]
                     │
                     ▼
         [ Polygon-Polygon Convex Intersection (intersectConvexConvex) ]
                     │
                     ▼
         [ Temporal Debounce State Machine (10.0s Hysteresis) ]
                     │
                     ▼
         [ Zonal Lighting Relay Actuation & Status ]
                     │
                     ▼
         [ Atomic JSON State & CSV Telemetry Logs ]
                     │
                     ▼
         [ Desktop Tkinter Dashboard & Replay System ]
```

### **5.2 Core Control Loop Pseudocode**
```python
# Main iHVAC Control Loop
for each frame F from VideoSource:
    # 1. Detection and Tracking
    detections, mean_conf = YOLO_Track(F, class=0, conf>=0.45, tracker="bytetrack.yaml")
    headcount = len(detections)
    
    # 2. Spatial Perspective Grid Intersection
    occupied_cells = set()
    for box in detections:
        poly_person = FormPolygon(box)
        for (r, c), poly_cell in grid.cell_polygons():
            if cv2.intersectConvexConvex(poly_person, poly_cell)[0] > 1.0:
                occupied_cells.add((r, c))
                
    # 3. Temporal Debounce (10.0 Seconds Hysteresis)
    light_states = light_controller.update(occupied_cells, now=time.monotonic())
    
    # 4. Multi-Tier Climate Regulation
    ac_on, ac_temp, profile = ac_settings(headcount, config)
    
    # 5. Hardware Actuation & Logging
    write_relay(board, ac_pin, ac_on)
    store.set_device_status(light_states, ac_on, ac_temp, profile)
    store.persist_snapshot()
```

---

## **6. Techniques / Algorithms Used**

### **6.1 Image Processing Techniques**
- **Geometric Perspective Modeling:** Unlike orthogonal 2D bounding boxes that distort when cameras point downwards at an angle, `PerspectiveRoomGrid` computes depth geometry using the downward tilt angle $\theta = 30^\circ$. Row boundary positions follow an exponential curve:
  $$y_r = H \cdot \left(\frac{r}{N_{\text{rows}}}\right)^k \quad \text{where } k = \frac{1}{\tan(\theta)}$$
  Column convergence toward the vanishing point is modeled with sinusoidal edge falloff:
  $$x_c = \text{base}_x + \text{convergence} \cdot \sin(\pi \cdot c_{\text{norm}}) \cdot (\text{vanishing}_x - \text{base}_x)$$
- **Convex Polygon Intersection:** Overlap evaluation uses `cv2.intersectConvexConvex` between 4-vertex quadrilateral grid cells and rectangular bounding boxes, evaluating the exact area of geometric overlap.
- **Alpha-Channel Blending:** Renders translucent overlays onto preview frames using linear alpha blending: $I_{\text{out}} = \alpha \cdot I_{\text{overlay}} + (1 - \alpha) \cdot I_{\text{frame}}$ ($\alpha = 0.30$) via `cv2.addWeighted`.

### **6.2 Video Processing Techniques**
- **Deep Convolutional Detection (YOLO):** Real-time single-stage feature extraction via CSPDarknet backbone and Path Aggregation Network (PANet).
- **Multi-Object Tracking (ByteTrack):** Solves data association across video frames using Kalman filter motion state vectors ($[x, y, a, h, \dot{x}, \dot{y}, \dot{a}, \dot{h}]$) and bipartite Hungarian matching. Retains low-confidence detections to prevent ID switches during momentary partial occlusions.
- **Temporal Debouncing (Hysteresis Filter):** Prevents mechanical wear and relay chatter by requiring light state switches to remain stable for 10.0 continuous seconds before triggering physical hardware.

### **6.3 Comparison with Classical Approaches**
| Approach | Mechanism | Limitation in Indoor Automation |
| :--- | :--- | :--- |
| **Background Subtraction (MOG2)** | Pixel color differencing | Fails when occupants sit still; light switching creates huge false motion masks. |
| **Optical Flow (Lucas-Kanade)** | Spatial intensity gradients | Cannot detect stationary seated occupants; high computational load. |
| **iHVAC (YOLO + ByteTrack)** | Deep semantic features + Kalman tracking | Accurately tracks moving and stationary occupants; completely immune to illumination shifts. |

---

## **7. Implementation Details**

- **Programming Language:** Python 3.11+
- **Computer Vision & Math:** OpenCV (`opencv-python` $\ge 4.7.0$), NumPy
- **Deep Learning:** Ultralytics YOLO ($\ge 8.4.0$), PyTorch ($\ge 2.0.0$)
- **Microcontroller Driver:** pyFirmata (v1.1.0) communicating over USB serial
- **GUI & Visualization:** Tkinter, ttk (Clam theme engine)
- **Persistence:** Atomic JSON serialization (`occupancy_state.json`), append-only CSV logs (`occupancy_events.csv`, `room_history.csv`)

### **Thermal Comfort Profiles**
| Profile | AC On Threshold | Busy Threshold | Empty Setpoint | Occupied Setpoint | Busy Setpoint |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Balanced (Default)** | $\ge 1$ | $\ge 5$ | 26°C (OFF) | 23°C (ON) | 21°C (ON) |
| **Focus** | $\ge 1$ | $\ge 6$ | 26°C (OFF) | 24°C (ON) | 22°C (ON) |
| **Meeting** | $\ge 1$ | $\ge 5$ | 26°C (OFF) | 22°C (ON) | 20°C (ON) |
| **Eco** | $\ge 2$ | $\ge 6$ | 27°C (OFF) | 25°C (ON) | 23°C (ON) |

---

## **8. Results and Discussion**

### **8.1 Operational Headcount Distribution**
During live system trials, room occupancy fluctuated between 0 and 6 occupants across 355 recorded operational snapshots:

| Headcount | Snapshots | Percentage | AC State | Target Temperature | Mean Lit Zones (of 48) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **0 (Vacant)** | 24 | 6.8% | **OFF** | 26°C | 0.0 |
| **1 Person** | 70 | 19.7% | **ON** | 23°C | 39.8 |
| **2 People** | 83 | 23.4% | **ON** | 23°C | 39.6 |
| **3 People** | 75 | 21.1% | **ON** | 23°C | 34.8 |
| **4 People** | 57 | 16.1% | **ON** | 23°C | 27.3 |
| **5 People (Busy)** | 39 | 11.0% | **ON** | 21°C | 26.0 |
| **6 People (Busy)** | 7 | 2.0% | **ON** | 21°C | 21.7 |
| **Overall** | **355** | **100.0%** | — | — | **33.2** |

### **8.2 Detection Confidence & Stability**
- Evaluated across 331 non-empty frames, the detection model achieved a **mean confidence of 0.77 (77.1%)**, ranging from 0.45 to 0.94.
- Tracking persistence via ByteTrack successfully maintained track continuity across 1,345 logged entry, exit, and steady-state events.
- Zero false human detections were recorded from desks, chairs, or presentation projections.

### **8.3 Zonal Lighting Spatial Dynamics**
- A single person walking across the room spans multiple grid cells due to camera perspective pitch, illuminating an average of 39.8 cells.
- As multiple people sit around centralized conference desks, their bounding footprints overlap into shared clusters rather than activating new zones.
- The 10-second hysteresis filter completely eliminated relay chatter during temporary occupant movement.

### **8.4 Interactive Tkinter Dashboard**
The standalone Tkinter desktop interface (`tkinter_ui.py`) delivers:
- **Real-Time Headcount Display:** Live occupant counter with dynamic mood badges.
- **Perspective Room Heatmap:** Color-coded 8×6 grid visualizing occupants and active lighting with hover coordinates.
- **24-Hour Room Rhythm:** Diurnal trend chart plotting occupancy fluctuations.
- **Interactive Historical Timeline:** Scrub slider with play/pause playback to inspect past events.
- **Environmental Sensor Telemetry:** Real-time ingestion of room temperature (°C), humidity (%), $CO_2$ (ppm), and power consumption (W).

---

## **9. Challenges and Limitations**

1. **Perspective Bounding Box Footprint Dilution:** Vertical bounding boxes projected from angled overhead viewpoints cover multiple grid cells along the camera axis. Future work can implement foot-point bottom centroid anchoring or human pose keypoints.
2. **Inter-Object Occlusion:** In dense classroom seating where occupants sit closely in rows, overlapping bodies cause partial occlusion. ByteTrack minimizes track loss, but deep occlusions remain challenging.
3. **Severe Ambient Lighting Shifts:** Extreme backlighting from sunny unshaded windows can temporarily reduce detection confidence scores below 0.45.
4. **Relay Pin Scalability:** Driving 48 discrete lighting zones directly from microcontroller pins requires multiple 16-channel relay boards and shift registers.

---

## **10. Conclusion**

The **iHVAC** project successfully designed, implemented, and validated an intelligent, end-to-end computer vision automation system for smart building energy conservation. By pairing deep convolutional neural network detection (YOLO) with ByteTrack multi-object association, perspective spatial projection, and temporal hysteresis debouncing, the system overcomes the critical shortcomings of traditional PIR and $CO_2$ occupancy sensors. The solution guarantees flicker-free, demand-controlled lighting and dynamically regulates air conditioning setpoints according to actual thermal load. Through 355 operational logging snapshots, the system demonstrated a 77.1% average detection confidence, zero false relay toggling, and robust usability via an intuitive Tkinter monitoring dashboard.

### **Key Learnings**
- Translating computer vision theory into real-world cyber-physical control systems.
- Designing geometric coordinate transformations to compensate for camera perspective distortion.
- Implementing temporal debouncing to protect physical electromechanical relays from chatter.
- Building non-intrusive edge AI systems that preserve occupant privacy while significantly reducing energy footprints.

---

## **11. References**

1. Bradski, G. (2000). The OpenCV Library. *Dr. Dobb's Journal of Software Tools*, 25(11), 120–125.
2. Redmon, J., Divvala, S., Girshick, R., & Farhadi, A. (2016). You Only Look Once: Unified, Real-Time Object Detection. In *Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR)*, pp. 779–788.
3. Zhang, Y., Sun, P., Jiang, Y., Yu, D., Weng, F., Yuan, Z., Luo, P., Liu, W., & Wang, X. (2022). ByteTrack: Multi-Object Tracking by Associating Every Detection Box. In *European Conference on Computer Vision (ECCV)*, pp. 1–21.
4. Paszke, A., Gross, S., Massa, F., et al. (2019). PyTorch: An Imperative Style, High-Performance Deep Learning Library. In *Advances in Neural Information Processing Systems (NeurIPS)*, Vol. 32.
5. Ultralytics Inc. (2024). Ultralytics YOLOv8 / YOLOv11 Documentation and Model Architecture. Available at: [https://docs.ultralytics.com](https://docs.ultralytics.com)
6. Hartley, R., & Zisserman, A. (2004). *Multiple View Geometry in Computer Vision* (2nd ed.). Cambridge University Press.
7. ASHRAE Standard 55-2020. (2020). *Thermal Environmental Conditions for Human Occupancy*. American Society of Heating, Refrigerating and Air-Conditioning Engineers.
8. ISO 50001:2018. (2018). *Energy Management Systems — Requirements with Guidance for Use*. International Organization for Standardization.
