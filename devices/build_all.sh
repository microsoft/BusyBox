#!/bin/bash
set -e

SRC_DIR="/home/busybox/BusyBox/devices"
MAP_FILE="$SRC_DIR/device_build_targets.yaml"

# Extract board from YAML
BOARD=$(grep '^board:' "$MAP_FILE" | awk '{print $2}')

EXTRA_INC="-I$SRC_DIR/include"

for sketch in "$SRC_DIR"/*; do
    [ -d "$sketch" ] || continue
    # Skip directories without any .ino files (e.g., include)
    if ! ls "$sketch"/*.ino >/dev/null 2>&1; then
        continue
    fi
    name=$(basename "$sketch")
    build_dir="$sketch/build"
    mkdir -p "$build_dir"

    echo "=== Compiling $name with $BOARD ==="
    arduino-cli compile --fqbn "$BOARD" \
      --build-property compiler.c.extra_flags="$EXTRA_INC" \
      --build-property compiler.cpp.extra_flags="$EXTRA_INC" \
      "$sketch" --output-dir "$build_dir"
done

echo "✅ All sketches compiled successfully. Build artifacts are in each sketch's build/ folder."
