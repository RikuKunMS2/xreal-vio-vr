#!/bin/bash
echo "📦 Installing system dependencies..."

sudo apt update
sudo apt install -y \
  cmake g++ libopencv-dev libeigen3-dev libboost-dev \
  libglew-dev libglfw3-dev libsuitesparse-dev

echo "✅ Done."
