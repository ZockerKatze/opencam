# OpenCam

Real-time object detection application using OpenCV and YOLO, with both Python and C++ implementations.

## Features

- Real-time object detection using YOLOv3
- Support for multiple camera inputs
- GPU acceleration with CUDA (optional)
- Cross-platform support (Windows, Linux)
- Modern Qt-based user interface
- Portable Linux AppImage build support

## Prerequisites

### For C++ Version

- CMake 3.16 or higher
- C++17 compatible compiler
- Qt 5.12 or higher
- OpenCV 4.x with CUDA support (optional)
- CUDA Toolkit 10.0 or higher (optional)

### For Python Version

- Python 3.8 or higher
- OpenCV-Python
- PyQt5
- NumPy

## Installation

### Building from Source (C++)

1. Clone the repository:
```bash
git clone https://github.com/ZockerKatze/opencam.git
cd opencam/opencamcpp
```

2. Build OpenCV with CUDA (optional):
```bash
chmod +x build_opencv.sh
./build_opencv.sh
```

3. Build the application:
```bash
mkdir build && cd build
cmake ..
make -j$(nproc)
```

### Creating AppImage (Linux)

1. Ensure all dependencies are installed:
```bash
sudo apt-get install cmake build-essential qt5-default libopencv-dev librsvg2-bin
```

2. Build the AppImage:
```bash
chmod +x build_appimage.sh
./build_appimage.sh
```

### Python Version Setup

1. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # Linux
# or
.venv\Scripts\activate     # Windows
```

2. Install dependencies:
```bash
pip install opencv-python pyqt5 numpy
```

## Usage

### Running the C++ Version

```bash
./opencam
```

### Running the Python Version

```bash
python main.py
```

## Model Files

The application requires YOLOv3 model files:
- `yolov3.weights`
- `yolov3.cfg`
- `coco.names`

Download the weights file from: https://pjreddie.com/media/files/yolov3.weights

## License

[Your chosen license]

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request 
