#!/bin/bash

# Install basic development tools
sudo dnf groupinstall -y "Development Tools"
sudo dnf install -y cmake git pkg-config

# Install Qt5
sudo dnf install -y qt5-qtbase-devel qt5-qtmultimedia-devel

# Install CUDA (if not already installed)
# First, add NVIDIA repository
sudo dnf config-manager --add-repo https://developer.download.nvidia.com/compute/cuda/repos/fedora37/x86_64/cuda-fedora37.repo
sudo dnf clean all
# Install CUDA
sudo dnf module disable -y nvidia-driver
sudo dnf install -y cuda

# Install OpenCV dependencies
sudo dnf install -y \
    ffmpeg-devel \
    libavcodec-devel \
    libavformat-devel \
    libswscale-devel \
    libv4l-devel \
    xvidcore-devel \
    x264-devel \
    libjpeg-turbo-devel \
    libpng-devel \
    libtiff-devel \
    gtk3-devel \
    atlas-devel \
    gcc-gfortran \
    python3-devel \
    python3-numpy \
    openblas-devel

# Optional: Install additional multimedia codecs
sudo dnf install -y \
    https://download1.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm \
    https://download1.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm

sudo dnf install -y \
    ffmpeg \
    ffmpeg-devel
