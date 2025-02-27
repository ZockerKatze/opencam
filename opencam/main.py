import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QPushButton, 
                           QVBoxLayout, QWidget, QComboBox, QMessageBox,
                           QProgressBar, QDialog)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer, Qt
import os
import urllib.request

class DownloadProgressBar(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Downloading YOLO Files")
        self.setFixedSize(400, 100)
        self.setWindowModality(Qt.ApplicationModal)
        
        layout = QVBoxLayout()
        
        self.label = QLabel("Downloading...")
        layout.addWidget(self.label)
        
        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        layout.addWidget(self.progress)
        
        self.setLayout(layout)
    
    def update_progress(self, current, total):
        percentage = int((current / total) * 100)
        self.progress.setValue(percentage)
    
    def set_file_label(self, filename):
        self.label.setText(f"Downloading {filename}...")

class DownloadProgressHandler:
    def __init__(self, progress_dialog):
        self.progress_dialog = progress_dialog
        self.current_size = 0
        self.total_size = 0
    
    def handle_progress(self, count, block_size, total_size):
        self.total_size = total_size
        self.current_size += block_size
        self.progress_dialog.update_progress(self.current_size, self.total_size)

class CameraApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Object Detection Camera Viewer")
        self.setGeometry(100, 100, 800, 600)

        self.camera_index = 0
        self.cap = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.available_cameras = []
        
        # Initialize object detection
        self.net = None
        self.classes = None
        self.output_layers = None
        self.load_yolo()

        self.init_ui()

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout()

        self.video_label = QLabel(self)
        layout.addWidget(self.video_label)

        self.camera_select = QComboBox(self)
        self.detect_cameras()
        layout.addWidget(self.camera_select)
        self.camera_select.currentIndexChanged.connect(self.change_camera)

        self.start_button = QPushButton("Start Camera", self)
        self.start_button.clicked.connect(self.start_camera)
        layout.addWidget(self.start_button)

        self.stop_button = QPushButton("Stop Camera", self)
        self.stop_button.clicked.connect(self.stop_camera)
        layout.addWidget(self.stop_button)

        self.central_widget.setLayout(layout)

    def detect_cameras(self):
        self.camera_select.clear()
        self.available_cameras = []
        
        # Try to get the list of available cameras using DirectShow backend
        for i in range(10):  # Check first 10 indexes
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                # Get camera name
                cap.set(cv2.CAP_PROP_SETTINGS, 1)  # This might show camera properties dialog
                name = f"Camera {i}"
                
                # Try to get camera resolution to verify it's working
                width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                
                if width and height:
                    name = f"{name} ({int(width)}x{int(height)})"
                    self.available_cameras.append(i)
                    self.camera_select.addItem(name, i)
                
                cap.release()
        
        if len(self.available_cameras) == 0:
            QMessageBox.warning(self, "Warning", "No cameras detected!")
            print("Error: No available cameras detected.")
        else:
            print(f"Detected {len(self.available_cameras)} cameras")

    def change_camera(self, index):
        if index >= 0:  # Only change if a valid camera is selected
            self.camera_index = self.camera_select.itemData(index)
            if self.cap is not None and self.cap.isOpened():
                self.stop_camera()
                self.start_camera()

    def start_camera(self):
        if self.cap is not None:
            self.stop_camera()
        
        try:
            self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                QMessageBox.warning(self, "Error", f"Cannot open camera {self.camera_index}")
                print(f"Error: Cannot open camera {self.camera_index}")
                return
            
            # Set camera properties for better performance
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            
            self.timer.start(30)
            print(f"Started camera {self.camera_index}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error starting camera: {str(e)}")
            print(f"Error starting camera: {str(e)}")

    def stop_camera(self):
        if self.cap:
            self.timer.stop()
            self.cap.release()
            self.cap = None
            self.video_label.clear()
            print("Camera stopped")

    def load_yolo(self):
        # Download YOLO files if they don't exist
        weights_path = "yolov3.weights"
        config_path = "yolov3.cfg"
        classes_path = "coco.names"
        
        if not all(os.path.exists(f) for f in [weights_path, config_path, classes_path]):
            QMessageBox.information(self, "Download", "Downloading YOLO model files. This may take a moment...")
            self.download_yolo_files()
        
        try:
            self.net = cv2.dnn.readNet(weights_path, config_path)
            with open(classes_path, "r") as f:
                self.classes = [line.strip() for line in f.readlines()]
            
            layer_names = self.net.getLayerNames()
            self.output_layers = [layer_names[i - 1] for i in self.net.getUnconnectedOutLayers()]
            
            print("YOLO model loaded successfully")
        except Exception as e:
            print(f"Error loading YOLO model: {str(e)}")
            QMessageBox.warning(self, "Error", "Failed to load object detection model")

    def download_yolo_files(self):
        files = {
            "yolov3.weights": "https://pjreddie.com/media/files/yolov3.weights",
            "yolov3.cfg": "https://raw.githubusercontent.com/pjreddie/darknet/master/cfg/yolov3.cfg",
            "coco.names": "https://raw.githubusercontent.com/pjreddie/darknet/master/data/coco.names"
        }
        
        progress_dialog = DownloadProgressBar(self)
        progress_dialog.show()
        
        for file_name, url in files.items():
            if not os.path.exists(file_name):
                print(f"Downloading {file_name}...")
                progress_dialog.set_file_label(file_name)
                try:
                    progress_handler = DownloadProgressHandler(progress_dialog)
                    urllib.request.urlretrieve(
                        url, 
                        file_name,
                        reporthook=progress_handler.handle_progress
                    )
                    print(f"Downloaded {file_name}")
                except Exception as e:
                    print(f"Error downloading {file_name}: {str(e)}")
                    QMessageBox.critical(self, "Error", f"Failed to download {file_name}")
        
        progress_dialog.close()

    def detect_objects(self, frame):
        if self.net is None or self.classes is None:
            return frame
        
        height, width, _ = frame.shape
        blob = cv2.dnn.blobFromImage(frame, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
        
        self.net.setInput(blob)
        outs = self.net.forward(self.output_layers)
        
        # Showing information on the screen
        class_ids = []
        confidences = []
        boxes = []
        
        # Showing information on the screen
        for out in outs:
            for detection in out:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                if confidence > 0.5:
                    # Object detected
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)

                    # Rectangle coordinates
                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)

                    boxes.append([x, y, w, h])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)
        
        indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)
        
        for i in range(len(boxes)):
            if i in indexes:
                x, y, w, h = boxes[i]
                label = str(self.classes[class_ids[i]])
                confidence = confidences[i]
                color = (0, 255, 0)  # Green
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                cv2.putText(frame, f"{label} {confidence:.2f}", (x, y - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        return frame

    def update_frame(self):
        if self.cap is None or not self.cap.isOpened():
            return
        
        ret, frame = self.cap.read()
        if ret:
            # Perform object detection
            frame = self.detect_objects(frame)
            
            # Convert the frame from BGR to RGB
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            
            # Convert the frame to QImage
            q_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            # Scale the image to fit the label while maintaining aspect ratio
            scaled_pixmap = QPixmap.fromImage(q_image).scaled(
                self.video_label.size(), 
                aspectRatioMode=1  # Qt.KeepAspectRatio
            )
            self.video_label.setPixmap(scaled_pixmap)
        else:
            print("Failed to get frame from camera")

    def closeEvent(self, event):
        self.stop_camera()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CameraApp()
    window.show()
    sys.exit(app.exec_())