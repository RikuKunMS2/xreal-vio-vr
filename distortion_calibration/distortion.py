import cv2
major_version = int(cv2.__version__.split('.')[0])
assert major_version >= 3, 'The fisheye module requires opencv version >= 3.0.0'
import numpy as np
import os
import glob

# --- CONFIGURATION ---
CHECKERBOARD = (6,9) # Number of internal corners (e.g., (cols-1, rows-1) squares)
IMAGE_PATH_PATTERN = '*.jpg' # Or your specific path and pattern

# --- CALIBRATION PARAMETERS ---
subpix_criteria = (cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER, 30, 0.1)
subpix_window_size = (11,11) # Using a slightly larger window often helps
calibration_flags = cv2.fisheye.CALIB_RECOMPUTE_EXTRINSIC+cv2.fisheye.CALIB_CHECK_COND+cv2.fisheye.CALIB_FIX_SKEW

# --- PREPARE OBJECT POINTS ---
objp = np.zeros((1, CHECKERBOARD[0]*CHECKERBOARD[1], 3), np.float32)
objp[0,:,:2] = np.mgrid[0:CHECKERBOARD[0], 0:CHECKERBOARD[1]].T.reshape(-1, 2)

_img_shape = None
objpoints = [] # 3d point in real world space
imgpoints = [] # 2d points in image plane.

images = glob.glob(IMAGE_PATH_PATTERN)
print(f"Found {len(images)} images matching pattern: {IMAGE_PATH_PATTERN}")
if not images:
    print(f"Error: No images found. Check your IMAGE_PATH_PATTERN: '{IMAGE_PATH_PATTERN}'")
    exit()

for fname in images:
    img = cv2.imread(fname)
    if img is None:
        print(f"Failed to load image: {fname}. Skipping.")
        continue

    if _img_shape is None:
        _img_shape = img.shape[:2] # (height, width)
    else:
        if _img_shape != img.shape[:2]:
            print(f"Image {fname} has different size {img.shape[:2]} than expected {_img_shape}. Skipping.")
            continue

    gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    find_corners_flags = cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE # Removed FAST_CHECK for better detection
    ret, corners = cv2.findChessboardCorners(gray, CHECKERBOARD, find_corners_flags)
    print(f"Processing {fname}: Found corners = {ret}")

    if ret == True:
        objpoints.append(objp)
        cv2.cornerSubPix(gray, corners, subpix_window_size, (-1,-1), subpix_criteria)
        imgpoints.append(corners)
        # --- Optional: Draw and display the corners ---
        # drawn_img = cv2.drawChessboardCorners(img.copy(), CHECKERBOARD, corners, ret)
        # cv2.imshow('Corners Found', drawn_img)
        # cv2.waitKey(50)

# if len(images) > 0 and any(cv2.getWindowProperty(winname, 0) >= 0 for winname in ['Corners Found']): # Check if window exists
#     cv2.destroyAllWindows()


N_OK = len(objpoints)
print(f"\nFound {N_OK} valid images for calibration out of {len(images)} processed.")

if N_OK == 0:
    print("Calibration failed: No valid images with detected checkerboards.")
    exit()

if _img_shape is None:
    print("Error: No images were successfully processed to determine image shape.")
    exit()

K = np.zeros((3, 3))
D = np.zeros((4, 1)) # For fisheye, D is (k1, k2, k3, k4)
rvecs = [np.zeros((1, 1, 3), dtype=np.float64) for _ in range(N_OK)]
tvecs = [np.zeros((1, 1, 3), dtype=np.float64) for _ in range(N_OK)]

print(f"\nAttempting calibration with {N_OK} image(s)...")
# Use the shape of the last successfully processed gray image for calibration dimensions
# This assumes all images are the same size, which is checked earlier.
calibration_image_shape_wh = gray.shape[::-1] # (width, height)
print(f"Image shape for calibration: {calibration_image_shape_wh} (width, height)")

try:
    rms, _, _, _, _ = \
        cv2.fisheye.calibrate(
            objpoints,
            imgpoints,
            calibration_image_shape_wh, # (width, height) of images
            K,
            D,
            rvecs,
            tvecs,
            calibration_flags,
            (cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER, 30, 1e-6)
        )

    print("\nCalibration successful!")
    print(f"RMS re-projection error: {rms}")
    print("Image Dimensions (height, width) = " + str(_img_shape))
    print("K (Intrinsic Matrix) = np.array(" + str(K.tolist()) + ")")
    print("D (Distortion Coefficients) = np.array(" + str(D.tolist()) + ")")

    # --- Extract and Print VSLAM Specific Parameters ---
    fx = K[0, 0]
    fy = K[1, 1]
    cx = K[0, 2]
    cy = K[1, 2]
    dist_coeffs = D.flatten().tolist() # D is [k1, k2, k3, k4] for fisheye

    print("\n--- VSLAM Camera Parameters ---")
    print(f"Camera.fx: {fx}")
    print(f"Camera.fy: {fy}")
    print(f"Camera.cx: {cx}")
    print(f"Camera.cy: {cy}")
    print(f"Camera.width: {calibration_image_shape_wh[0]}")
    print(f"Camera.height: {calibration_image_shape_wh[1]}")
    print(f"Camera.fps: 30.0 # (Set your actual FPS if known, otherwise use a placeholder)")
    print(f"\n# Fisheye distortion parameters (k1, k2, k3, k4)")
    print(f"Camera.k1: {dist_coeffs[0] if len(dist_coeffs) > 0 else 'N/A'}")
    print(f"Camera.k2: {dist_coeffs[1] if len(dist_coeffs) > 1 else 'N/A'}")
    print(f"Camera.k3: {dist_coeffs[2] if len(dist_coeffs) > 2 else 'N/A'}")
    print(f"Camera.k4: {dist_coeffs[3] if len(dist_coeffs) > 3 else 'N/A'}")

    print("\n# Example YAML format for some VSLAM systems (like ORB_SLAM3 fisheye):")
    print("%YAML:1.0")
    print("---")
    print("Camera.type: \"FISHEYE\"")
    print(f"Camera.fx: {fx:.6f}")
    print(f"Camera.fy: {fy:.6f}")
    print(f"Camera.cx: {cx:.6f}")
    print(f"Camera.cy: {cy:.6f}")
    print(f"Camera.k1: {dist_coeffs[0]:.6f}")
    print(f"Camera.k2: {dist_coeffs[1]:.6f}")
    print(f"Camera.k3: {dist_coeffs[2]:.6f}")
    print(f"Camera.k4: {dist_coeffs[3]:.6f}")
    print(f"\nCamera.width: {calibration_image_shape_wh[0]}")
    print(f"Camera.height: {calibration_image_shape_wh[1]}")
    print(f"Camera.fps: 30.0 # Adjust as needed")
    print("Camera.RGB: 1 # Set to 0 if images are grayscale, 1 if color (BGR)")
    # --- End VSLAM Specific Parameters ---

except cv2.error as e:
    print(f"\nOpenCV Error during calibration: {e}")
    print("This might happen if input data is still problematic (e.g., insufficient views, poor corner detection).")
except Exception as e:
    print(f"\nAn unexpected error occurred: {e}")