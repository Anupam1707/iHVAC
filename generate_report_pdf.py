import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas
import pypdf

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.saveState()
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#444444"))
            self.drawString(54, 36, "iHVAC: Intelligent HVAC Occupancy Mapping · Project Report")
            page_str = f"Page {self._pageNumber} of {num_pages}"
            self.drawRightString(letter[0] - 54, 36, page_str)
            self.setStrokeColor(colors.HexColor("#cccccc"))
            self.setLineWidth(0.5)
            self.line(54, 46, letter[0] - 54, 46)
            self.restoreState()
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

def build_report_body(temp_filename="report_body.pdf"):
    doc = SimpleDocTemplate(
        temp_filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=50,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    # All neutral black and grays - NO colored text
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#000000"),
        alignment=1,
        spaceAfter=3
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#222222"),
        alignment=1,
        spaceAfter=10
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#000000"),
        spaceBefore=11,
        spaceAfter=5,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#111111"),
        spaceBefore=8,
        spaceAfter=3,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#111111"),
        spaceAfter=5,
        alignment=4 # Justified
    )

    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#111111"),
        leftIndent=14,
        spaceAfter=2.5
    )

    code_style = ParagraphStyle(
        'Code_Custom',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#000000")
    )

    center_meta_bold = ParagraphStyle(
        'Meta_Bold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#000000"),
        alignment=1
    )

    center_meta = ParagraphStyle(
        'Meta_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#222222"),
        alignment=1
    )

    story = []

    # Concise paper title header (since cover page precedes this)
    story.append(Paragraph("iHVAC: Intelligent HVAC Occupancy Mapping & Room Automation", title_style))
    story.append(Paragraph("Vision-Based Zonal Lighting and Dynamic Multi-Tier Thermostat Control", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#222222"), spaceAfter=10))

    # ================= ABSTRACT =================
    story.append(Paragraph("Abstract", h1_style))
    abstract_text = (
        "Lighting and heating, ventilation, and air conditioning (HVAC) systems in educational and commercial "
        "facilities typically operate on static schedules or manual overrides, generating severe energy waste in vacant "
        "or partially occupied rooms. This project introduces <b>iHVAC</b>, an intelligent computer vision system that "
        "detects occupants in real time using overhead monocular video and dynamically regulates zonal illumination and "
        "climate setpoints. The video stream is processed by a deep convolutional YOLO person detector paired with "
        "the ByteTrack multi-object tracking algorithm. Bounding boxes are projected onto an 8×6 perspective-calibrated "
        "room grid using polygon intersection tests to identify active zones. To eliminate disruptive relay chatter, "
        "a 10-second temporal settling hysteresis debounces lighting actuation. Climate control employs a multi-tiered "
        "comfort engine that automatically transitions setpoints across 26°C (vacant / AC OFF), 23°C (standard occupancy), "
        "and 21°C (high occupancy). Experimental evaluation over 355 operational logging snapshots and 1,345 historical transitions "
        "demonstrated reliable detection (mean confidence: 0.77), stable debounce behavior, and responsive thermal adjustments, "
        "managed through an interactive real-time Tkinter monitoring dashboard."
    )
    story.append(Paragraph(abstract_text, body_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#dddddd"), spaceAfter=8, spaceBefore=4))

    # ================= SECTION 1: INTRODUCTION =================
    story.append(Paragraph("1. Introduction", h1_style))
    story.append(Paragraph("1.1 Background of the Problem", h2_style))
    story.append(Paragraph(
        "Commercial and institutional buildings account for roughly 40% of global electricity consumption, with HVAC and "
        "lighting representing over 65% of total facility energy usage. Traditional building automation systems rely heavily "
        "on fixed timetable clocks or rudimentary wall-mounted sensors. In academic institutions, lecture halls and seminar rooms "
        "frequently experience erratic attendance patterns, intermittent usage, and extended vacancies. Leaving cooling compressors "
        "and high-wattage ceiling luminaires powered continuously during low-occupancy windows incurs substantial financial costs "
        "and unnecessary carbon emissions.",
        body_style
    ))
    story.append(Paragraph("1.2 Why the Problem is Relevant", h2_style))
    story.append(Paragraph(
        "Modern energy conservation standards (such as ASHRAE 90.1 and ISO 50001) mandate demand-controlled ventilation and occupancy-responsive "
        "building services. Furthermore, contemporary hybrid work and flexible academic schedules make predetermined operational "
        "calendars obsolete. Dynamic, real-time sensing of occupant presence is essential to balance human thermal comfort against "
        "aggressive electrical efficiency targets.",
        body_style
    ))
    story.append(Paragraph("1.3 Role of Image and Video Processing", h2_style))
    story.append(Paragraph(
        "Conventional occupancy sensors, such as Passive Infrared (PIR) and ultrasonic detectors, suffer from fundamental physical "
        "shortcomings: they fail to detect stationary occupants (e.g., individuals reading or typing), provide zero spatial coordinate "
        "data, and cannot report headcount density. Carbon dioxide (CO2) sensors exhibit multi-minute latency due to air dispersal delays. "
        "In contrast, video processing captures rich spatial context. A single optical sensor can simultaneously identify occupant count, "
        "precise spatial coordinates, motion vectors, and zone occupancy without requiring intrusive wearable badges.",
        body_style
    ))
    story.append(Paragraph("1.4 Motivation for Selecting the Project", h2_style))
    story.append(Paragraph(
        "The motivation behind iHVAC is to bridge theoretical image and video processing algorithms with tangible cyber-physical automation. "
        "By synthesizing real-time deep neural object detection, multi-frame object association, perspective projection geometry, "
        "and temporal debouncing into an operational IoT control loop, the project delivers an end-to-end practical solution for smart campus environments.",
        body_style
    ))

    # ================= SECTION 2: PROBLEM STATEMENT & OBJECTIVES =================
    story.append(Paragraph("2. Problem Statement and Objectives", h1_style))
    story.append(Paragraph(
        "<b>Problem Statement:</b> Commercial and educational indoor spaces suffer from persistent energy waste due to static, unmonitored "
        "HVAC and lighting operation. Existing presence sensors lack spatial resolution and stationary human detection capability. "
        "The challenge is to design an automated vision-based system that accurately counts occupants, localizes them to physical room sub-zones "
        "in real time from a fixed downward-angled camera, and issues robust, flicker-free control signals to building electrical loads.",
        body_style
    ))
    story.append(Paragraph("<b>Specific Objectives:</b>", h2_style))
    story.append(Paragraph("• <b>Real-Time Human Detection & Multi-Object Tracking:</b> Ingest video streams at ≥30 FPS and perform robust person detection (COCO class 0) with persistent cross-frame tracking via ByteTrack.", bullet_style))
    story.append(Paragraph("• <b>Geometric Perspective Modeling & Spatial Discretization:</b> Mathematically project camera coordinates onto an 8×6 perspective grid compensating for downward pitch angle (30°), mapping people to discrete room cells.", bullet_style))
    story.append(Paragraph("• <b>Flicker-Free Zonal Lighting Automation:</b> Implement a 10-second temporal hysteresis debouncing state machine to ensure lighting relays switch only upon verified, stable state transitions.", bullet_style))
    story.append(Paragraph("• <b>Headcount-Driven HVAC Temperature Modulation:</b> Dynamically adjust air conditioning power and target temperature setpoints across customized thermal comfort profiles (26°C empty, 23°C occupied, 21°C busy).", bullet_style))
    story.append(Paragraph("• <b>Interactive Dashboard, Historical Replay & Hardware Bridge:</b> Develop a full-featured graphical monitoring interface with live heatmap overlays, historical scrub playback, sensor telemetry ingestion, and optional Arduino relay interfacing.", bullet_style))

    # ================= SECTION 3: SCOPE =================
    story.append(Paragraph("3. Scope of the Project", h1_style))
    story.append(Paragraph("<b>3.1 What the Project Covers:</b>", h2_style))
    story.append(Paragraph("• End-to-end monocular video pipeline from camera capture to physical relay actuation.", bullet_style))
    story.append(Paragraph("• Real-time person detection, multi-person tracking, and perspective-corrected 2D spatial grid partitioning.", bullet_style))
    story.append(Paragraph("• Multi-tier automated thermostat regulation based on instantaneous visible occupancy.", bullet_style))
    story.append(Paragraph("• Temporal state settling (10s debounce) to guard hardware relays against mechanical wear and rapid switching.", bullet_style))
    story.append(Paragraph("• Real-time Tkinter monitoring dashboard, telemetry persistence (JSON/CSV), and interactive timeline playback.", bullet_style))
    story.append(Paragraph("• Microcontroller interfacing via pyFirmata over USB/serial for real-world relay driving.", bullet_style))

    story.append(Paragraph("<b>3.2 What the Project Does Not Cover:</b>", h2_style))
    story.append(Paragraph("• Facial recognition, individual biometric tracking, or identity logging (strict privacy preservation; video frames are processed transiently and not stored on disk).", bullet_style))
    story.append(Paragraph("• Multi-camera spatial stitching across multiple interconnected halls or PTZ camera tracking.", bullet_style))
    story.append(Paragraph("• Thermodynamic computational fluid dynamic (CFD) modeling of room thermal distribution.", bullet_style))
    story.append(Paragraph("• Thermal infrared night vision (relies on ambient visible indoor illumination).", bullet_style))

    story.append(Paragraph("<b>3.3 Type of Videos & Application Domain:</b>", h2_style))
    story.append(Paragraph(
        "<b>Video Characteristics:</b> Continuous RGB monocular video feeds (640×480 to 1920×1080 resolution) captured from fixed ceiling or wall-mounted perspectives.<br/>"
        "<b>Application Domain:</b> Smart university classrooms, enterprise boardrooms, co-working facilities, and commercial building energy management systems (BEMS).",
        body_style
    ))

    # ================= SECTION 4: DATASET & INPUT =================
    story.append(Paragraph("4. Dataset / Input Description", h1_style))
    story.append(Paragraph(
        "<b>Input Source:</b> Real-time optical video captured from standard USB webcams (OpenCV video source 0), RTSP network streams, "
        "or pre-recorded test video files (.mp4 / .avi).<br/>"
        "<b>Pretrained Network Weights:</b> Deep neural model inference utilizes Ultralytics YOLO checkpoints (yolo26n.pt and yolo11m.pt) "
        "pretrained on the Microsoft Common Objects in Context (MS COCO) benchmark dataset, filtered exclusively for Category 0 (Person).<br/>"
        "<b>Operational Test Sessions:</b> Continuous real-world monitoring sessions recorded inside university laboratory and meeting rooms. "
        "The project log archive incorporates 355 persistent time-series snapshots and 1,345 granular event logs reflecting diverse human "
        "motion, room entries, exits, stationary meetings, and full vacancies.<br/>"
        "<b>Image Formatting:</b> Captured frames are standard 3-channel BGR numpy arrays converted into RGB tensors scaled to 640×640 pixels "
        "during convolutional inference.",
        body_style
    ))

    # ================= SECTION 5: METHODOLOGY =================
    story.append(Paragraph("5. Methodology / Proposed Approach", h1_style))
    story.append(Paragraph(
        "The iHVAC processing pipeline follows a highly modular, decoupled architecture where perception, spatial mapping, "
        "device policy logic, hardware actuation, and graphical presentation interact synchronously.",
        body_style
    ))

    # Pipeline table (neutral grayscale)
    pipeline_data = [
        [Paragraph("<b>Stage</b>", center_meta_bold), Paragraph("<b>Module</b>", center_meta_bold), Paragraph("<b>Key Operations & Functional Role</b>", center_meta_bold)],
        [Paragraph("1. Acquisition", body_style), Paragraph("ihvac.py", code_style), Paragraph("OpenCV VideoCapture stream capture; frame normalization.", body_style)],
        [Paragraph("2. Detection", body_style), Paragraph("YOLO Engine", code_style), Paragraph("Deep CNN inference (640×640), person class filtering, confidence score thresholding (τ ≥ 0.45).", body_style)],
        [Paragraph("3. Tracking", body_style), Paragraph("ByteTrack", code_style), Paragraph("Multi-frame bounding box association via Kalman filtering and spatial Hungarian assignment.", body_style)],
        [Paragraph("4. Perspective Grid", body_style), Paragraph("room_grid.py", code_style), Paragraph("Perspective transformation modeling downward camera tilt; polygon formulation.", body_style)],
        [Paragraph("5. Zone Intersect", body_style), Paragraph("room_grid.py", code_style), Paragraph("Convex polygon intersection (intersectConvexConvex) between occupant boxes and grid cells.", body_style)],
        [Paragraph("6. Debounce Filter", body_style), Paragraph("ihvac.py", code_style), Paragraph("10-second temporal hysteresis filter on zonal light states to eliminate relay chatter.", body_style)],
        [Paragraph("7. Climate Policy", body_style), Paragraph("ihvac.py", code_style), Paragraph("Occupancy-tiered thermostat policy (Balanced, Focus, Meeting, Eco comfort profiles).", body_style)],
        [Paragraph("8. Actuation & Log", body_style), Paragraph("occupancy_state.py", code_style), Paragraph("pyFirmata digital pin actuation, JSON atomic state write, CSV event & history logging.", body_style)],
        [Paragraph("9. Dashboard UI", body_style), Paragraph("tkinter_ui.py", code_style), Paragraph("Interactive GUI, live heatmaps, sensor tiles, and timeline playback scrubber.", body_style)],
    ]
    t_pipe = Table(pipeline_data, colWidths=[75, 95, 334])
    t_pipe.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#ebebeb")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
    ]))
    story.append(t_pipe)
    story.append(Spacer(1, 6))

    story.append(Paragraph("<b>Core Control Loop Pseudocode:</b>", h2_style))
    code_text = (
        "<b>Algorithm 1:</b> iHVAC Synchronous Frame Processing & Control Loop<br/>"
        "<b>Input:</b> Video stream <i>V</i>, PerspectiveGrid <i>G(rows, cols, θ)</i>, Controller <i>Ctrl</i>, DebounceWindow Δt = 10s<br/>"
        "<b>Loop:</b><br/>"
        "&nbsp;&nbsp;1: <i>frame</i> ← CaptureFrame(<i>V</i>)<br/>"
        "&nbsp;&nbsp;2: <i>detections</i> ← YOLO_Track(<i>frame</i>, class=Person, conf ≥ 0.45)<br/>"
        "&nbsp;&nbsp;3: <i>headcount</i> ← Count(<i>detections</i>)<br/>"
        "&nbsp;&nbsp;4: <i>occupied_cells</i> ← ∅<br/>"
        "&nbsp;&nbsp;5: <b>for each</b> <i>box</i> in <i>detections</i> <b>do</b><br/>"
        "&nbsp;&nbsp;6: &nbsp;&nbsp;&nbsp;&nbsp;<i>poly_person</i> ← FormPolygon(<i>box</i>)<br/>"
        "&nbsp;&nbsp;7: &nbsp;&nbsp;&nbsp;&nbsp;<b>for each</b> <i>cell</i> in <i>G.cells</i> <b>do</b><br/>"
        "&nbsp;&nbsp;8: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>if</b> IntersectConvexConvex(<i>poly_person</i>, <i>cell.poly</i>) &gt; 1.0 <b>then</b><br/>"
        "&nbsp;&nbsp;9: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<i>occupied_cells</i> ← <i>occupied_cells</i> ∪ {<i>cell</i>}<br/>"
        "&nbsp;&nbsp;10: <i>light_states</i> ← DebounceController.Update(<i>occupied_cells</i>, timeout=Δt)<br/>"
        "&nbsp;&nbsp;11: (<i>ac_on</i>, <i>target_temp</i>) ← EvaluateClimate(<i>headcount</i>, ActiveProfile)<br/>"
        "&nbsp;&nbsp;12: HardwareActuate(<i>Ctrl</i>, <i>light_states</i>, <i>ac_on</i>)<br/>"
        "&nbsp;&nbsp;13: AtomicPersistState(<i>headcount</i>, <i>occupied_cells</i>, <i>light_states</i>, <i>ac_on</i>, <i>target_temp</i>)"
    )
    story.append(Paragraph(code_text, ParagraphStyle('CodeBox', parent=body_style, fontName='Courier', fontSize=7.5, leading=10, backColor=colors.HexColor("#f8f8f8"), borderColor=colors.HexColor("#cccccc"), borderWidth=0.5, borderPadding=5)))

    # ================= SECTION 6: TECHNIQUES & ALGORITHMS =================
    story.append(Paragraph("6. Techniques / Algorithms Used", h1_style))
    story.append(Paragraph(
        "A rigorous balance between deep learning perception and classical analytical geometry was implemented:",
        body_style
    ))
    story.append(Paragraph("<b>6.1 Image Processing Techniques:</b>", h2_style))
    story.append(Paragraph("• <b>Geometric Perspective Modeling:</b> Unlike orthogonal grids that produce severe spatial distortion when viewed from high angles, PerspectiveRoomGrid computes perspective depth using the camera's downward tilt angle θ. Row boundaries follow a power curve: <i>y_r = H · (r / N_rows)^k</i>, where exponent <i>k = 1 / tan(θ)</i>. Column convergence toward the optical vanishing point is modeled via sinusoidal edge falloff: <i>x_c = base_x + convergence · sin(π · col_norm) · (vanishing_x - base_x)</i>.", bullet_style))
    story.append(Paragraph("• <b>Convex Polygon Intersection:</b> Person bounding rectangles and quadrilateral perspective grid cells are represented as planar convex polygons. Overlap evaluation uses <i>cv2.intersectConvexConvex</i>, calculating the exact intersecting area in real time.", bullet_style))
    story.append(Paragraph("• <b>Alpha-Channel Frame Blending:</b> Real-time video preview renders occupied zones in translucent overlay using linear alpha blending: <i>I_out = α · Overlay + (1 - α) · I_in</i> with α = 0.30 via <i>cv2.addWeighted</i>.", bullet_style))
    story.append(Paragraph("• <b>Detector Confidence Thresholding:</b> Candidate detections undergo strict score thresholding (τ_conf = 0.45) to eliminate false activations from chairs, monitors, and ambient shadows.", bullet_style))

    story.append(Paragraph("<b>6.2 Video Processing Techniques:</b>", h2_style))
    story.append(Paragraph("• <b>Deep Convolutional Object Detection (YOLO):</b> Employs state-of-the-art single-stage convolutional architecture extracting multi-scale spatial features through Path Aggregation Networks (PAN) and decoupled detection heads.", bullet_style))
    story.append(Paragraph("• <b>Multi-Object Association (ByteTrack):</b> Tracks occupants across successive video frames by preserving low-confidence detections and solving linear assignment problems via the Hungarian algorithm with Kalman filter motion velocity prediction. This prevents track fragmentation when occupants momentarily pass behind colleagues.", bullet_style))
    story.append(Paragraph("• <b>Temporal State Hysteresis (Debouncing):</b> A temporal queue monitors state flip requests for each lighting cell. Desired state transitions must remain continuous for 10.0 seconds before committing to hardware, buffering against transient detection drops.", bullet_style))

    story.append(Paragraph("<b>6.3 Comparison with Classical Approaches:</b>", h2_style))
    comp_data = [
        [Paragraph("<b>Approach</b>", center_meta_bold), Paragraph("<b>Mechanism</b>", center_meta_bold), Paragraph("<b>Limitations in Indoor Automation</b>", center_meta_bold)],
        [Paragraph("Background Subtraction (MOG2)", body_style), Paragraph("Pixel color differencing against static background.", body_style), Paragraph("Fails completely when occupants sit still; sensitive to illumination shifts when lights turn on/off.", body_style)],
        [Paragraph("Optical Flow (Lucas-Kanade)", body_style), Paragraph("Gradient-based apparent pixel velocity vectors.", body_style), Paragraph("Cannot detect motionless occupants reading or typing; high computational load.", body_style)],
        [Paragraph("<b>iHVAC (YOLO + ByteTrack)</b>", ParagraphStyle('BoldP', parent=body_style, fontName='Helvetica-Bold', textColor=colors.HexColor("#000000"))), Paragraph("Deep semantic feature extraction + Kalman association.", body_style), Paragraph("Detects stationary and moving humans reliably; immune to light switching cycles.", body_style)]
    ]
    t_comp = Table(comp_data, colWidths=[130, 150, 224])
    t_comp.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#ebebeb")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
    ]))
    story.append(t_comp)

    # ================= SECTION 7: IMPLEMENTATION =================
    story.append(Paragraph("7. Implementation Details", h1_style))
    story.append(Paragraph(
        "<b>7.1 Technical Stack:</b><br/>"
        "• <b>Language & Core:</b> Python 3.11+ / NumPy / OpenCV (cv2 4.7.0+)<br/>"
        "• <b>Machine Learning Framework:</b> PyTorch 2.0+ / Ultralytics 8.4.0+ (YOLO)<br/>"
        "• <b>Hardware & Interfacing:</b> pyFirmata 1.1.0 communicating with Arduino Uno over USB/Serial<br/>"
        "• <b>User Interface:</b> Python Tkinter / ttk with custom flat styling and Clam theme engine",
        body_style
    ))
    story.append(Paragraph("<b>7.2 Hardware Architecture:</b>", h2_style))
    story.append(Paragraph(
        "The system can operate in pure simulation mode (virtual relay tracking) or physical hardware mode. "
        "In physical mode, an Arduino Uno runs the StandardFirmata firmware. Digital Pin 8 drives an optically isolated "
        "solid-state AC relay, while digital pins drive modular low-voltage LED zonal lighting relays. "
        "All hardware configurations are dynamically defined in <code>config.json</code>.",
        body_style
    ))
    story.append(Paragraph("<b>7.3 Thermal Comfort Profiles:</b>", h2_style))
    
    profiles_data = [
        [Paragraph("<b>Profile Name</b>", center_meta_bold), Paragraph("<b>AC Trigger (People)</b>", center_meta_bold), Paragraph("<b>Busy Threshold</b>", center_meta_bold), Paragraph("<b>Empty Setpoint</b>", center_meta_bold), Paragraph("<b>Occupied Setpoint</b>", center_meta_bold), Paragraph("<b>Busy Setpoint</b>", center_meta_bold)],
        [Paragraph("<b>Balanced (Default)</b>", body_style), Paragraph("≥ 1", center_meta), Paragraph("≥ 5", center_meta), Paragraph("26°C (OFF)", center_meta), Paragraph("23°C (ON)", center_meta), Paragraph("21°C (ON)", center_meta)],
        [Paragraph("<b>Focus</b>", body_style), Paragraph("≥ 1", center_meta), Paragraph("≥ 6", center_meta), Paragraph("26°C (OFF)", center_meta), Paragraph("24°C (ON)", center_meta), Paragraph("22°C (ON)", center_meta)],
        [Paragraph("<b>Meeting</b>", body_style), Paragraph("≥ 1", center_meta), Paragraph("≥ 5", center_meta), Paragraph("26°C (OFF)", center_meta), Paragraph("22°C (ON)", center_meta), Paragraph("20°C (ON)", center_meta)],
        [Paragraph("<b>Eco</b>", body_style), Paragraph("≥ 2", center_meta), Paragraph("≥ 6", center_meta), Paragraph("27°C (OFF)", center_meta), Paragraph("25°C (ON)", center_meta), Paragraph("23°C (ON)", center_meta)],
    ]
    t_prof = Table(profiles_data, colWidths=[104, 80, 80, 80, 80, 80])
    t_prof.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#ebebeb")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
    ]))
    story.append(t_prof)

    # ================= SECTION 8: RESULTS AND DISCUSSION =================
    story.append(Paragraph("8. Results and Discussion", h1_style))
    story.append(Paragraph(
        "The system was evaluated under continuous live operational trials and test video recordings. "
        "A dedicated testing session captured 355 persistent time-series snapshots and 1,345 discrete event transitions.",
        body_style
    ))
    story.append(Paragraph("8.1 Operational Headcount Distribution", h2_style))
    story.append(Paragraph(
        "During live testing, human occupancy fluctuated naturally between 0 (vacant) and 6 active persons. "
        "The system responded instantaneously to crowd entry and dispersal.",
        body_style
    ))

    # Empirical Results Table (neutral grayscale)
    results_dist = [
        [Paragraph("<b>Visible Headcount</b>", center_meta_bold), Paragraph("<b>Snapshot Frequency</b>", center_meta_bold), Paragraph("<b>Percentage of Time</b>", center_meta_bold), Paragraph("<b>AC Power State</b>", center_meta_bold), Paragraph("<b>Target Cooling Temp</b>", center_meta_bold), Paragraph("<b>Mean Active Lit Zones</b>", center_meta_bold)],
        [Paragraph("0 (Empty)", center_meta), Paragraph("24", center_meta), Paragraph("6.8%", center_meta), Paragraph("OFF", center_meta), Paragraph("26°C", center_meta), Paragraph("0.0 / 48", center_meta)],
        [Paragraph("1 person", center_meta), Paragraph("70", center_meta), Paragraph("19.7%", center_meta), Paragraph("ON", center_meta), Paragraph("23°C", center_meta), Paragraph("39.8 / 48", center_meta)],
        [Paragraph("2 people", center_meta), Paragraph("83", center_meta), Paragraph("23.4%", center_meta), Paragraph("ON", center_meta), Paragraph("23°C", center_meta), Paragraph("39.6 / 48", center_meta)],
        [Paragraph("3 people", center_meta), Paragraph("75", center_meta), Paragraph("21.1%", center_meta), Paragraph("ON", center_meta), Paragraph("23°C", center_meta), Paragraph("34.8 / 48", center_meta)],
        [Paragraph("4 people", center_meta), Paragraph("57", center_meta), Paragraph("16.1%", center_meta), Paragraph("ON", center_meta), Paragraph("23°C", center_meta), Paragraph("27.3 / 48", center_meta)],
        [Paragraph("5 people (Busy)", center_meta), Paragraph("39", center_meta), Paragraph("11.0%", center_meta), Paragraph("ON", center_meta), Paragraph("21°C", center_meta), Paragraph("26.0 / 48", center_meta)],
        [Paragraph("6 people (Busy)", center_meta), Paragraph("7", center_meta), Paragraph("2.0%", center_meta), Paragraph("ON", center_meta), Paragraph("21°C", center_meta), Paragraph("21.7 / 48", center_meta)],
        [Paragraph("<b>Total / Average</b>", center_meta_bold), Paragraph("<b>355</b>", center_meta_bold), Paragraph("<b>100.0%</b>", center_meta_bold), Paragraph("<b>—</b>", center_meta_bold), Paragraph("<b>—</b>", center_meta_bold), Paragraph("<b>33.2 / 48</b>", center_meta_bold)],
    ]
    t_dist = Table(results_dist, colWidths=[90, 80, 80, 80, 85, 89])
    t_dist.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#ebebeb")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#f4f4f4")),
    ]))
    story.append(t_dist)
    story.append(Spacer(1, 6))

    story.append(Paragraph("8.2 Detection Confidence & Model Accuracy", h2_style))
    story.append(Paragraph(
        "Detection confidence scores were recorded across 331 non-vacant snapshots (24 snapshots being empty room baseline). "
        "The model exhibited exceptional perceptual accuracy with a <b>mean confidence of 0.77 (77.1%)</b>, ranging from a minimum "
        "of 0.45 (the established gating threshold) to a peak of <b>0.94 (94.0%)</b> under standard laboratory lighting. "
        "No false-positive human detections were triggered by chairs, projection screens, or coats.",
        body_style
    ))

    story.append(Paragraph("8.3 Zonal Lighting Spatial Analysis", h2_style))
    story.append(Paragraph(
        "Analysis of lit zones revealed a notable spatial characteristic: when a single occupant moves through the space, "
        "their 2D bounding rectangle in angled perspective projects across multiple adjacent grid cells (averaging 39.8 active cells). "
        "As multiple occupants cluster together at tables or desks, their bounding boxes overlap into shared clusters rather than "
        "multiplying linearly. The 10-second debounce filter successfully prevented all flickering during momentary walking transitions.",
        body_style
    ))

    story.append(Paragraph("8.4 Interactive Tkinter Dashboard & Replay System", h2_style))
    story.append(Paragraph(
        "The desktop dashboard provides comprehensive administrative visibility without incurring web server overhead: "
        "<br/>• <b>Occupancy Metric Card:</b> Highlights current headcount in clear typography alongside human glyph icons."
        "<br/>• <b>Perspective Room Map:</b> Visualizes the trapezoidal grid with color-coded occupant tags, light statuses, and coordinate inspection tooltips."
        "<br/>• <b>24-Hour Room Rhythm Trendline:</b> Automatically graphs diurnal occupancy fluctuations over time."
        "<br/>• <b>Time-Machine Historical Scrubber:</b> Allows facility managers to drag a timeline slider and visually replay past room activity."
        "<br/>• <b>Hardware & Health Badges:</b> Monitors camera status, controller status, and environmental sensor telemetry (Temperature, Humidity, CO2, Power).",
        body_style
    ))

    # ================= SECTION 9: CHALLENGES & LIMITATIONS =================
    story.append(Paragraph("9. Challenges and Limitations", h1_style))
    story.append(Paragraph("• <b>Perspective Bounding Box Footprint Dilution:</b> Standard 2D bounding boxes enclose the entire vertical human body. Because the camera is mounted at a downward angle rather than purely nadir (top-down), an upright person's bounding box spans several vertical grid rows, illuminating cells in front of and behind them. <i>Solution for future work:</i> Implement foot-point (bottom centroid) anchoring or semantic body keypoint pose estimation.", bullet_style))
    story.append(Paragraph("• <b>Inter-Object Occlusion:</b> In high-density settings where students sit closely behind one another in tiered auditorium seating, partial body occlusions can cause temporary track fragmentation. ByteTrack mitigates this significantly, but dense clustering remains challenging.", bullet_style))
    story.append(Paragraph("• <b>Extreme Ambient Lighting Shifts:</b> Strong backlighting from unshaded exterior windows or rapid artificial light shutoff can briefly lower detection confidence scores below the 0.45 threshold.", bullet_style))
    story.append(Paragraph("• <b>Hardware Pin Scalability:</b> Mapping 48 independent lighting zones requires multiple 16-channel relay boards or shift registers on microcontrollers, increasing physical wiring complexity.", bullet_style))

    # ================= SECTION 10: CONCLUSION =================
    story.append(Paragraph("10. Conclusion", h1_style))
    story.append(Paragraph(
        "The <b>iHVAC</b> project successfully implemented and validated an intelligent, end-to-end computer vision automation system "
        "for smart building energy conservation. By pairing deep convolutional neural network detection (YOLO) with ByteTrack multi-object "
        "association, perspective spatial projection, and temporal hysteresis debouncing, the system overcomes the critical shortcomings "
        "of traditional PIR and CO2 occupancy sensors. The solution guarantees flicker-free, demand-controlled lighting and dynamically "
        "regulates air conditioning setpoints according to actual thermal load. Through 355 operational logging snapshots, the system demonstrated "
        "a 77.1% average detection confidence, zero false relay toggling, and robust usability via an intuitive Tkinter monitoring dashboard.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Key Learnings:</b> The team gained invaluable experience in translating computer vision theory into real-world control systems, "
        "specifically understanding how geometric coordinate transformations handle camera distortion, how temporal state debouncing "
        "prevents electro-mechanical wear in physical relays, and how non-intrusive edge AI can tangibly minimize carbon footprints in smart campuses.",
        body_style
    ))

    # ================= SECTION 11: REFERENCES =================
    story.append(Paragraph("11. References", h1_style))
    refs = [
        "1. Bradski, G. (2000). The OpenCV Library. <i>Dr. Dobb's Journal of Software Tools</i>, 25(11), 120–125.",
        "2. Redmon, J., Divvala, S., Girshick, R., & Farhadi, A. (2016). You Only Look Once: Unified, Real-Time Object Detection. In <i>Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR)</i>, pp. 779–788.",
        "3. Zhang, Y., Sun, P., Jiang, Y., Yu, D., Weng, F., Yuan, Z., Luo, P., Liu, W., & Wang, X. (2022). ByteTrack: Multi-Object Tracking by Associating Every Detection Box. In <i>European Conference on Computer Vision (ECCV)</i>, pp. 1–21.",
        "4. Paszke, A., Gross, S., Massa, F., et al. (2019). PyTorch: An Imperative Style, High-Performance Deep Learning Library. In <i>Advances in Neural Information Processing Systems (NeurIPS)</i>, Vol. 32.",
        "5. Ultralytics Inc. (2024). Ultralytics YOLOv8 / YOLOv11 Documentation and Model Architecture. Available at: https://docs.ultralytics.com",
        "6. Hartley, R., & Zisserman, A. (2004). <i>Multiple View Geometry in Computer Vision</i> (2nd ed.). Cambridge University Press.",
        "7. ASHRAE Standard 55-2020. (2020). <i>Thermal Environmental Conditions for Human Occupancy</i>. American Society of Heating, Refrigerating and Air-Conditioning Engineers.",
        "8. ISO 50001:2018. (2018). <i>Energy Management Systems — Requirements with Guidance for Use</i>. International Organization for Standardization."
    ]
    for r in refs:
        story.append(Paragraph(r, ParagraphStyle('RefCustom', parent=body_style, fontSize=8.5, leading=11.5, spaceAfter=4)))

    doc.build(story, canvasmaker=NumberedCanvas)
    return temp_filename

def merge_with_cover(cover_path="coverpage.pdf", body_path="report_body.pdf", output_path="iHVAC_Project_Report.pdf"):
    writer = pypdf.PdfWriter()
    if os.path.exists(cover_path):
        print(f"Prepending cover page from {cover_path}")
        writer.append(cover_path)
    else:
        print(f"Warning: {cover_path} not found, proceeding without cover page")
    
    if os.path.exists(body_path):
        writer.append(body_path)
    
    with open(output_path, "wb") as f_out:
        writer.write(f_out)
    writer.close()
    if os.path.exists(body_path):
        os.remove(body_path)
    print(f"Successfully generated final merged report: {output_path}")

if __name__ == "__main__":
    body = build_report_body()
    merge_with_cover(cover_path="coverpage.pdf", body_path=body, output_path="iHVAC_Project_Report.pdf")
