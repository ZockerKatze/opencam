#!/bin/bash

# Exit on error
set -e

# Function to copy library and its dependencies
copy_dependencies() {
    local binary="$1"
    local target_dir="$2"
    
    # Create target directory if it doesn't exist
    mkdir -p "$target_dir"
    
    # Get all dependencies
    ldd "$binary" | while read -r line; do
        # Extract the library path
        if [[ $line =~ '=>' ]]; then
            lib_path=$(echo "$line" | awk '{print $3}')
        else
            lib_path=$(echo "$line" | awk '{print $1}')
        fi
        
        # Skip system libraries and non-existent files
        if [[ -f "$lib_path" && ! "$lib_path" =~ ^/lib && ! "$lib_path" =~ ^/usr/lib ]]; then
            cp -L "$lib_path" "$target_dir/"
        fi
    done
}

# Create AppDir structure
mkdir -p AppDir/usr/{bin,lib,share/applications,share/icons/hicolor/256x256/apps}

# Build the application
mkdir -p build
cd build
cmake .. -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)

# Install to AppDir
make DESTDIR=../AppDir install
cd ..

# Copy desktop file and icon
cp opencam.desktop AppDir/usr/share/applications/
cp icon.png AppDir/usr/share/icons/hicolor/256x256/apps/opencam.png

# Copy Qt plugins
mkdir -p AppDir/usr/plugins
for plugin_dir in platforms imageformats xcbglintegrations; do
    if [ -d "/usr/lib/x86_64-linux-gnu/qt5/plugins/$plugin_dir" ]; then
        cp -r "/usr/lib/x86_64-linux-gnu/qt5/plugins/$plugin_dir" AppDir/usr/plugins/
    fi
done

# Copy dependencies for the main executable
copy_dependencies "AppDir/usr/bin/opencam" "AppDir/usr/lib"

# Copy dependencies for Qt plugins
find AppDir/usr/plugins -type f -name "*.so" | while read plugin; do
    copy_dependencies "$plugin" "AppDir/usr/lib"
done

# Create AppRun script
cat > AppDir/AppRun << 'EOF'
#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"
export LD_LIBRARY_PATH="${HERE}/usr/lib:${LD_LIBRARY_PATH}"
export QT_PLUGIN_PATH="${HERE}/usr/plugins"
export QT_QPA_PLATFORM_PLUGIN_PATH="${HERE}/usr/plugins/platforms"
exec "${HERE}/usr/bin/opencam" "$@"
EOF

chmod +x AppDir/AppRun

# Download linuxdeploy if not present
if [ ! -f linuxdeploy-x86_64.AppImage ]; then
    wget https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage
    chmod +x linuxdeploy-x86_64.AppImage
fi

if [ ! -f linuxdeploy-plugin-qt-x86_64.AppImage ]; then
    wget https://github.com/linuxdeploy/linuxdeploy-plugin-qt/releases/download/continuous/linuxdeploy-plugin-qt-x86_64.AppImage
    chmod +x linuxdeploy-plugin-qt-x86_64.AppImage
fi

# Create the AppImage
export OUTPUT="OpenCam-x86_64.AppImage"
./linuxdeploy-x86_64.AppImage --appdir AppDir --plugin qt --output appimage

echo "AppImage created successfully: $OUTPUT" 