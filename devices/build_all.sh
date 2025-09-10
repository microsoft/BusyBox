#!/bin/bash
set -e

SRC_DIR="/home/busybox/BusyBox/devices"
MAP_FILE="$SRC_DIR/device_build_targets.yaml"

# Extract board from YAML
BOARD=$(grep '^board:' "$MAP_FILE" | awk '{print $2}')

for sketch in "$SRC_DIR"/*; do
    if [ -d "$sketch" ]; then
        name=$(basename "$sketch")
        build_dir="$sketch/build"
        mkdir -p "$build_dir"

        echo "=== Compiling $name with $BOARD ==="
        arduino-cli compile --fqbn "$BOARD" "$sketch" --output-dir "$build_dir"
    fi
done

echo "✅ All sketches compiled successfully. Build artifacts are in each sketch's build/ folder."
