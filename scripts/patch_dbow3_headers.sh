#!/bin/bash
set -e

echo "📦 Patching DBoW3 headers for missing C++ includes..."

BOWVEC="libs/DBoW3/src/BowVector.h"
FEATUREVEC="libs/DBoW3/src/FeatureVector.h"

# Only insert if not already present
grep -q '<ostream>' "$BOWVEC" || sed -i '/#include "exports.h"/a #include <ostream>' "$BOWVEC"
grep -q '<string>' "$BOWVEC" || sed -i '/#include "exports.h"/a #include <string>' "$BOWVEC"
grep -q '<cstdint>' "$BOWVEC" || sed -i '/#include "exports.h"/a #include <cstdint>' "$BOWVEC"

grep -q '<ostream>' "$FEATUREVEC" || sed -i '/#include "BowVector.h"/a #include <ostream>' "$FEATUREVEC"

echo "✅ Headers patched."
