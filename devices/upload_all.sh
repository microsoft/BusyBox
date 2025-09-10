#!/bin/bash
set -e

SRC_DIR="/home/busybox/BusyBox/devices"
MAP_FILE="$SRC_DIR/device_build_targets.yaml"

# Extract board from YAML
BOARD=$(grep '^board:' "$MAP_FILE" | awk '{print $2}')

# Parse mapping under "devices:"
awk '/devices:/ {flag=1; next} /^$/ {flag=0} flag' "$MAP_FILE" | while IFS=":" read -r port sketch; do
    port=$(echo "$port" | xargs)
    sketch=$(echo "$sketch" | xargs)

    build_dir="$SRC_DIR/$sketch/build"
    hex_file=$(find "$build_dir" -name "*.hex" | head -n 1)

    if [ -z "$hex_file" ]; then
        echo "❌ No hex file found for $sketch (expected in $build_dir)"
        continue
    fi

    echo "=== Uploading $sketch to $port with $BOARD ==="
    arduino-cli upload -p "$port" --fqbn "$BOARD" "$SRC_DIR/$sketch" || {
        echo "❌ Upload failed for $sketch on $port"
    }
done

echo "✅ Upload process finished."
