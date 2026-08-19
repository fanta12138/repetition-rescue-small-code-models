#!/usr/bin/env bash
# Try to fetch official ICLR style files; report what worked.
set -uo pipefail
for y in 2026 2025; do
    url="https://media.iclr.cc/Conferences/ICLR${y}/Styles.zip"
    out="/tmp/styles_${y}.zip"
    curl -sL --max-time 25 -o "$out" "$url"
    echo "ICLR${y}: $(file -b "$out") $(stat -c%s "$out" 2>/dev/null) bytes"
done
# extract the first real zip found
for y in 2026 2025; do
    if file -b "/tmp/styles_${y}.zip" | grep -qi zip; then
        mkdir -p /tmp/iclr_styles
        unzip -o "/tmp/styles_${y}.zip" -d /tmp/iclr_styles
        ls -R /tmp/iclr_styles
        break
    fi
done
