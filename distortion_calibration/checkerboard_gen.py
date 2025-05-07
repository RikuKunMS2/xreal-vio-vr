import cv2
import numpy as np
import os

# --- Parameters for the Checkerboard Pattern ---
# These should match what cv2.findChessboardCorners expects
# It's the number of INNER corners.
# So, for a 7x10 grid of squares, you'll have 6x9 inner corners.
PATTERN_SIZE_INTERNAL_CORNERS = (6, 9)  # (cols-1, rows-1) or (width-1, height-1)

# Number of squares along width and height
NUM_SQUARES_WIDTH = PATTERN_SIZE_INTERNAL_CORNERS[0] + 1
NUM_SQUARES_HEIGHT = PATTERN_SIZE_INTERNAL_CORNERS[1] + 1

# Size of each square in pixels in the output image
SQUARE_SIZE_PIXELS = 100  # Adjust this for your desired output image size

# Add a white border/margin around the checkerboard (in pixels)
# This helps with corner detection, especially near the edges.
MARGIN_PIXELS = SQUARE_SIZE_PIXELS // 2 # Or a fixed value like 50

# Output image filename
OUTPUT_FILENAME = "checkerboard_pattern.png"

# --- Generate the Checkerboard Image ---

# Calculate image dimensions
img_width = NUM_SQUARES_WIDTH * SQUARE_SIZE_PIXELS + 2 * MARGIN_PIXELS
img_height = NUM_SQUARES_HEIGHT * SQUARE_SIZE_PIXELS + 2 * MARGIN_PIXELS

# Create a white image (255)
# Use a grayscale image (1 channel) as color is not necessary for the pattern itself
checkerboard_img = np.ones((img_height, img_width), dtype=np.uint8) * 255

# Iterate over the squares and color them black or white
for r_sq in range(NUM_SQUARES_HEIGHT):  # Row index of the square
    for c_sq in range(NUM_SQUARES_WIDTH):  # Column index of the square
        # Determine color: if (row_idx + col_idx) is even, it's one color, if odd, the other.
        # Let's make (0,0) a black square for consistency (optional choice)
        if (r_sq + c_sq) % 2 == 0:
            color = 0  # Black
        else:
            color = 255 # White (already set, but explicit for black squares)

        if color == 0: # Only draw black squares
            # Calculate top-left corner of the current square
            x1 = MARGIN_PIXELS + c_sq * SQUARE_SIZE_PIXELS
            y1 = MARGIN_PIXELS + r_sq * SQUARE_SIZE_PIXELS

            # Calculate bottom-right corner of the current square
            x2 = x1 + SQUARE_SIZE_PIXELS
            y2 = y1 + SQUARE_SIZE_PIXELS

            # Draw the filled rectangle
            cv2.rectangle(checkerboard_img, (x1, y1), (x2, y2), color, thickness=cv2.FILLED)

# --- Save and Display ---
cv2.imwrite(OUTPUT_FILENAME, checkerboard_img)
print(f"Checkerboard pattern saved as {OUTPUT_FILENAME}")
print(f"Pattern details:")
print(f"  - Internal corners: {PATTERN_SIZE_INTERNAL_CORNERS}")
print(f"  - Number of squares: ({NUM_SQUARES_WIDTH}W x {NUM_SQUARES_HEIGHT}H)")
print(f"  - Square size in image: {SQUARE_SIZE_PIXELS}x{SQUARE_SIZE_PIXELS} pixels")
print(f"  - Image dimensions: {img_width}x{img_height} pixels")

# Display the generated pattern (optional)
cv2.imshow("Generated Checkerboard", checkerboard_img)
cv2.waitKey(0)
cv2.destroyAllWindows()

print("\n--- Instructions for Use ---")
print(f"1. Print '{OUTPUT_FILENAME}' on a flat, rigid surface. Ensure high contrast and sharp edges.")
print(f"   Alternatively, display it on a *flat* monitor (ensure no glare, full screen).")
print(f"2. When printing, measure the *actual physical size* of one square (e.g., in mm or inches).")
print(f"   This 'square_real_world_size' will be used to define 'objp' in your calibration script.")
print(f"   For example, if your printed square is 2.5cm, then square_real_world_size = 25 (if using mm).")
print(f"   Your 'objp' setup in the calibration script assumes a unit square size (e.g., 1.0).")
print(f"   If you use that, the units of your rvecs/tvecs will be in 'square units'.")
print(f"   To get real-world units, modify objp: ")
print(f"     `objp[0,:,:2] = np.mgrid[0:CHECKERBOARD[0], 0:CHECKERBOARD[1]].T.reshape(-1, 2) * square_real_world_size`")
print(f"3. Take multiple pictures of this checkerboard with your fisheye camera from various angles and distances,")
print(f"   ensuring the entire board is visible and fills a good portion of the frame.")
print(f"4. Save these images (e.g., as 'calibration_image_01.jpg', 'calibration_image_02.jpg', etc.) in the")
print(f"   same directory as your calibration script, or update the `glob.glob('*.jpg')` path.")
print(f"5. Run your calibration script (the one you provided in the question).")