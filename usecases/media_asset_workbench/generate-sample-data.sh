#!/usr/bin/env bash
# ────────────────────────────────────────────────────────────────────────────
# Generate sample media packs for the Media Asset Workbench demo.
# Requires: ImageMagick (convert/magick), ffmpeg
# Usage: ./generate-sample-data.sh
# ────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUT="${SCRIPT_DIR}/sample-data"

# Detect ImageMagick command
if command -v magick &>/dev/null; then
  IM="magick"
elif command -v convert &>/dev/null; then
  IM="convert"
else
  echo "ERROR: ImageMagick not found. Install it first." >&2; exit 1
fi
command -v ffmpeg &>/dev/null || { echo "ERROR: ffmpeg not found." >&2; exit 1; }

rand_color() { printf "rgb(%d,%d,%d)" $((RANDOM%256)) $((RANDOM%256)) $((RANDOM%256)); }

# Find a usable font
FONT=""
for f in /System/Library/Fonts/Helvetica.ttc /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf /usr/share/fonts/TTF/DejaVuSans.ttf; do
  [ -f "$f" ] && FONT="$f" && break
done
[ -z "$FONT" ] && FONT=$(fc-list -f '%{file}\n' 2>/dev/null | head -1)
FONT_FLAG=()
[ -n "$FONT" ] && FONT_FLAG=(-font "$FONT")

# Marketing images (30 files - JPG + PNG, mixed resolutions)

IMG_DIR="${OUT}/marketing-images"
rm -rf "${IMG_DIR}" && mkdir -p "${IMG_DIR}"
echo "--- Generating marketing-images (30 files)"

RESOLUTIONS=("1920x1080" "3840x2160" "1280x720" "2560x1440" "1080x1080")
LABELS=("Hero Banner" "Product Shot" "Lifestyle" "Campaign" "Social Post"
        "Landing Page" "Email Header" "Promo Card" "Feature" "Seasonal")

for i in $(seq -w 1 30); do
  res=${RESOLUTIONS[$((RANDOM % ${#RESOLUTIONS[@]}))]}
  label="${LABELS[$((RANDOM % ${#LABELS[@]}))]}"
  # Alternate JPG and PNG
  if (( 10#$i % 5 == 0 )); then ext="png"; else ext="jpg"; fi
  $IM -size "$res" "xc:$(rand_color)" \
    "${FONT_FLAG[@]}" -gravity center -pointsize 64 -fill white \
    -annotate 0 "${label} ${i}" \
    "${IMG_DIR}/marketing_${i}.${ext}"
done
echo "    Created $(ls "${IMG_DIR}" | wc -l | tr -d ' ') files"

# Video clips (8 files - MP4, HD + 4K, 5-30s)

VID_DIR="${OUT}/video-clips"
rm -rf "${VID_DIR}" && mkdir -p "${VID_DIR}"
echo "--- Generating video-clips (8 files)"

VID_SPECS=(
  "1920:1080:5"  "3840:2160:8"  "1920:1080:15" "3840:2160:10"
  "1920:1080:30" "1280:720:12"  "3840:2160:20" "1920:1080:7"
)

for i in $(seq 0 7); do
  IFS=: read -r w h dur <<< "${VID_SPECS[$i]}"
  idx=$(printf "%02d" $((i+1)))
  ffmpeg -y -loglevel error \
    -f lavfi -i "testsrc2=s=${w}x${h}:d=${dur}:rate=24" \
    -f lavfi -i "sine=frequency=440:duration=${dur}" \
    -c:v libx264 -preset ultrafast -crf 28 -pix_fmt yuv420p \
    -c:a aac -b:a 64k -shortest \
    "${VID_DIR}/clip_${idx}.mp4"
done
echo "    Created $(ls "${VID_DIR}" | wc -l | tr -d ' ') files"

# Mixed media (20 files - 15 images + 5 videos)

MIX_DIR="${OUT}/mixed-media"
rm -rf "${MIX_DIR}" && mkdir -p "${MIX_DIR}"
echo "--- Generating mixed-media (20 files)"

# 15 images
for i in $(seq -w 1 15); do
  res=${RESOLUTIONS[$((RANDOM % ${#RESOLUTIONS[@]}))]}
  if (( 10#$i % 3 == 0 )); then ext="png"; else ext="jpg"; fi
  $IM -size "$res" "xc:$(rand_color)" \
    "${FONT_FLAG[@]}" -gravity center -pointsize 48 -fill white \
    -annotate 0 "Mixed ${i}" \
    "${MIX_DIR}/photo_${i}.${ext}"
done

# 5 videos
MIX_VID_SPECS=("1920:1080:6" "3840:2160:10" "1280:720:8" "1920:1080:15" "3840:2160:5")
for i in $(seq 0 4); do
  IFS=: read -r w h dur <<< "${MIX_VID_SPECS[$i]}"
  idx=$(printf "%02d" $((i+1)))
  ffmpeg -y -loglevel error \
    -f lavfi -i "testsrc2=s=${w}x${h}:d=${dur}:rate=24" \
    -f lavfi -i "sine=frequency=330:duration=${dur}" \
    -c:v libx264 -preset ultrafast -crf 28 -pix_fmt yuv420p \
    -c:a aac -b:a 64k -shortest \
    "${MIX_DIR}/video_${idx}.mp4"
done

echo "    Created $(ls "${MIX_DIR}" | wc -l | tr -d ' ') files"

# ── Summary ──────────────────────────────────────────────────────────────────

echo ""
echo "  Sample data generated in: ${OUT}"
echo ""
echo "  marketing-images/  $(ls "${IMG_DIR}" | wc -l | tr -d ' ') files"
echo "  video-clips/       $(ls "${VID_DIR}" | wc -l | tr -d ' ') files"
echo "  mixed-media/       $(ls "${MIX_DIR}" | wc -l | tr -d ' ') files"
echo "  See README Step 3 to upload to S3."
