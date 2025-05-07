#!/bin/bash
set -e

echo "🔧 Building DBoW3..."
./scripts/patch_dbow3_headers.sh
cd libs/DBoW3
mkdir -p build && cd build
cmake ..
make -j$(nproc)
sudo make install

# go back to root before next lib
cd ../../../

echo "🔧 Building Pangolin..."
cd libs/Pangolin
mkdir -p build && cd build
cmake ..
make -j$(nproc)
sudo make install
cd ../../..

echo "✅ All libraries built and installed."
