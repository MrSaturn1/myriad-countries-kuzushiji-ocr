#!/bin/sh
# Set up NDL古典籍OCR-Lite (a git submodule, pinned to the version this project
# used) in a local virtualenv at tools/venv.
#
# Usage:  sh scripts/setup_tools.sh
# Then:   cd tools/ndlkotenocr-lite/src
#         ../../venv/bin/python ocr.py --sourcedir "<scan folder>/vol1" --output <out folder>/vol1
set -eu
cd "$(dirname "$0")/.."
git submodule update --init tools/ndlkotenocr-lite
python3 -m venv tools/venv
tools/venv/bin/pip install -q --upgrade pip
tools/venv/bin/pip install -q -r tools/ndlkotenocr-lite/requirements.txt -r requirements.txt
echo "Ready: tools/venv/bin/python, NDL OCR Lite in tools/ndlkotenocr-lite/src"
