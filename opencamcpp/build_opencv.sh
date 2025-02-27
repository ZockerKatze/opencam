#!/bin/bash

# Exit on error
set -e

# Function to check CUDA installation
check_cuda() {
    if ! command -v nvcc &> /dev/null; then
        echo "CUDA not found! Please install CUDA toolkit first."
        exit 1
    fi
    echo "Found CUDA installation: $(nvcc --version | head -n1)"
}

# Function to check GPU
check_gpu() {
    if ! command -v nvidia-smi &> /dev/null; then
        echo "No NVIDIA GPU found or drivers not installed!"
        exit 1
    fi
    echo "Found GPU: $(nvidia-smi -L)"
}

# Check CUDA and GPU
check_cuda
check_gpu

# Get CUDA compute capability
CUDA_ARCH=$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader)
echo "GPU Compute Capability: $CUDA_ARCH"

# Create build directory
cd ~/opencv_build/opencv
mkdir -p build
cd build

# Configure OpenCV build
cmake -D CMAKE_BUILD_TYPE=RELEASE \
    -D CMAKE_INSTALL_PREFIX=/usr/local \
    -D OPENCV_EXTRA_MODULES_PATH=../../opencv_contrib/modules \
    -D WITH_CUDA=ON \
    -D WITH_CUDNN=OFF \
    -D OPENCV_DNN_CUDA=ON \
    -D ENABLE_FAST_MATH=1 \
    -D CUDA_FAST_MATH=1 \
    -D CUDA_ARCH_BIN=$CUDA_ARCH \
    -D WITH_CUBLAS=1 \
    -D WITH_TBB=ON \
    -D WITH_V4L=ON \
    -D WITH_QT=ON \
    -D WITH_OPENGL=ON \
    -D WITH_GSTREAMER=ON \
    -D OPENCV_GENERATE_PKGCONFIG=ON \
    -D OPENCV_PC_FILE_NAME=opencv.pc \
    -D OPENCV_ENABLE_NONFREE=ON \
    -D INSTALL_PYTHON_EXAMPLES=OFF \
    -D INSTALL_C_EXAMPLES=OFF \
    -D BUILD_EXAMPLES=OFF \
    -D BUILD_opencv_cudacodec=OFF \
    -D OPENCV_ENABLE_MEMALIGN=ON \
    -D WITH_OPENEXR=ON \
    -D OPENCV_ENABLE_MEMALIGN=ON \
    -D WITH_EIGEN=ON \
    -D ENABLE_PRECOMPILED_HEADERS=OFF \
    ..

# Build using all available CPU cores
make -j$(nproc)

# Install
sudo make install
sudo ldconfig

# Print OpenCV installation information
echo "OpenCV installation completed!"
echo "OpenCV version: $(pkg-config --modversion opencv4)"
echo "Installation location: $(pkg-config --variable=prefix opencv4)"

# Create a pkg-config path file
sudo sh -c 'echo "/usr/local/lib/pkgconfig" > /etc/ld.so.conf.d/opencv.conf'
sudo ldconfig

echo "Setup complete! You can now use OpenCV with CUDA support." 