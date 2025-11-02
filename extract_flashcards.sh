#!/bin/bash
set -e

docker images -q typst-flash-cards &>/dev/null || docker build -t typst-flash-cards .

[[ $# -eq 0 ]] && {
    echo "Usage: $0 <pdf-file> [args]"
    exit 1
}

PDF_DIR="$(dirname "$(realpath "$1")")"
PDF_NAME="$(basename "$1")"
OUTPUT_BASE="$(basename "$1" .pdf)"
mkdir -p output

docker run --rm \
    --user "$(id -u):$(id -g)" \
    -v "$PDF_DIR:/data:ro" \
    -v "$(pwd)/output:/output" \
    typst-flash-cards \
    "/data/$PDF_NAME" \
    --output "/output/$OUTPUT_BASE" \
    "${@:2}"
