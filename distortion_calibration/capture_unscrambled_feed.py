import gi
import struct
import time
import sys
import numpy as np
import os # Added for path joining
from PIL import Image # Added for image saving

gi.require_version('Gst', '1.0')
gi.require_version('Gtk', '4.0')
from gi.repository import Gst, GLib, Gtk

Gst.init(None)

# --- Configuration ---
CAMERA_NATIVE_FORMAT = "YUY2"
CAMERA_NATIVE_WIDTH = 640
CAMERA_NATIVE_HEIGHT = 241
CAMERA_NATIVE_FRAMERATE_NUM = 60
CAMERA_NATIVE_FRAMERATE_DEN = 1

APPSINK_EXPECTED_BLOCKSIZE = CAMERA_NATIVE_WIDTH * CAMERA_NATIVE_HEIGHT * 2

OUT_WIDTH = 480
OUT_HEIGHT = 640
OUT_FORMAT = "GRAY8"

# --- Global variables for photo capture ---
last_photo_time = 0.0  # Initialize to 0.0, will be set on first frame processed
photo_capture_interval = 5  # seconds
photo_counter = 0
# Output folder for calibration images (current directory)
output_folder = "."
# If you wanted a subfolder, you could do:
# output_folder = "calibration_images"
# if not os.path.exists(output_folder):
#     os.makedirs(output_folder)

# --- Build Input Pipeline: avfvideosrc ! caps_cam_native ! queue ! appsink ---
pipeline = Gst.Pipeline()

source = Gst.ElementFactory.make("avfvideosrc", "source")
if not source: print("ERROR: Failed to create avfvideosrc"); sys.exit(1)
source.props.device_index = 0

caps_cam_native_filter = Gst.ElementFactory.make("capsfilter", "caps_cam_native_filter")
if not caps_cam_native_filter: print("ERROR: Failed to create caps_cam_native_filter"); sys.exit(1)
caps_cam_native_str = (
    f"video/x-raw,format={CAMERA_NATIVE_FORMAT},width={CAMERA_NATIVE_WIDTH},"
    f"height={CAMERA_NATIVE_HEIGHT},framerate={CAMERA_NATIVE_FRAMERATE_NUM}/{CAMERA_NATIVE_FRAMERATE_DEN}"
)
caps_cam_native_filter.props.caps = Gst.Caps.from_string(caps_cam_native_str)

queue_in = Gst.ElementFactory.make("queue", "queue_in")
if not queue_in: print("ERROR: Failed to create queue_in"); sys.exit(1)
queue_in.set_property("max-size-buffers", 5)
queue_in.set_property("max-size-bytes", 0)
queue_in.set_property("max-size-time", 0)

appsink = Gst.ElementFactory.make("appsink", "sink")
if not appsink: print("ERROR: Failed to create appsink"); sys.exit(1)
appsink.props.emit_signals = True
appsink.props.max_buffers = 5
appsink.props.drop = True

pipeline.add(source)
pipeline.add(caps_cam_native_filter)
pipeline.add(queue_in)
pipeline.add(appsink)

if not source.link(caps_cam_native_filter):
    print("ERROR: Could not link source to caps_cam_native_filter.")
    sys.exit(1)
if not caps_cam_native_filter.link(queue_in):
    print("ERROR: Could not link caps_cam_native_filter to queue_in.")
    sys.exit(1)
if not queue_in.link(appsink):
    print("ERROR: Could not link queue_in to appsink.")
    sys.exit(1)

# --- Output Pipeline for Displaying Unscrambled Data ---
outpipe = Gst.Pipeline()
outsrc = Gst.ElementFactory.make('appsrc', 'outsource')
if not outsrc: print("ERROR: Failed to create outsrc for outpipe"); sys.exit(1)

outsrc.props.caps = Gst.Caps.from_string(
    f'video/x-raw,format={OUT_FORMAT},width={OUT_WIDTH},height={OUT_HEIGHT},framerate=30/1'
)
outsrc.props.is_live = True
outsrc.props.block = True
outsrc.props.format = Gst.Format.TIME

queue_out = Gst.ElementFactory.make("queue", "queue_out")
if not queue_out: print("ERROR: Failed to create queue_out"); sys.exit(1)
queue_out.set_property("max-size-buffers", 5)
queue_out.set_property("max-size-bytes", 0)
queue_out.set_property("max-size-time", 0)

videoconvert_out = Gst.ElementFactory.make('videoconvert', 'videoconvert_out')
if not videoconvert_out: print("ERROR: Failed to create videoconvert_out for outpipe"); sys.exit(1)
outsink = Gst.ElementFactory.make('autovideosink', 'outsink')
if not outsink: print("ERROR: Failed to create autovideosink for outpipe"); sys.exit(1)

outpipe.add(outsrc)
outpipe.add(queue_out)
outpipe.add(videoconvert_out)
outpipe.add(outsink)

if not outsrc.link(queue_out):
    print("ERROR: Could not link outsrc to queue_out.")
    sys.exit(1)
if not queue_out.link(videoconvert_out):
    print("ERROR: Could not link queue_out to videoconvert_out.")
    sys.exit(1)
if not videoconvert_out.link(outsink):
    print("ERROR: Could not link videoconvert_out to outsink.")
    sys.exit(1)

frame_count_unscrambled = 0

def on_bus_message(bus, message, pipeline_name):
    t = message.type
    if t == Gst.MessageType.EOS:
        print(f"[{pipeline_name}] End-of-stream")
    elif t == Gst.MessageType.ERROR:
        err, debug = message.parse_error()
        print(f"[{pipeline_name}] Error: {err}, {debug}")
        if mainloop.is_running(): mainloop.quit()
    elif t == Gst.MessageType.WARNING:
        err, debug = message.parse_warning()
        print(f"[{pipeline_name}] Warning: {err}, {debug}")
    return True

bus_in = pipeline.get_bus()
bus_in.add_signal_watch()
bus_in.connect("message", on_bus_message, "InputPipe")

bus_out = outpipe.get_bus()
bus_out.add_signal_watch()
bus_out.connect("message", on_bus_message, "OutputPipe")

def new_frame_unscramble(sink):
    global frame_count_unscrambled
    global last_photo_time, photo_counter # Declare globals for photo capture

    sample = sink.emit("pull-sample")
    if sample is None:
        return Gst.FlowReturn.OK

    gst_buffer = sample.get_buffer()
    if gst_buffer is None:
        print("Unscramble: get_buffer returned None from sample")
        return Gst.FlowReturn.ERROR

    success, map_info = gst_buffer.map(Gst.MapFlags.READ)
    if not success:
        print("Unscramble: Failed to map buffer for reading")
        return Gst.FlowReturn.ERROR
    
    buffer_data_bytes = map_info.data
    
    if len(buffer_data_bytes) != APPSINK_EXPECTED_BLOCKSIZE:
        print(f"Unscramble: Unexpected buffer size. Expected {APPSINK_EXPECTED_BLOCKSIZE}, Got {len(buffer_data_bytes)}")
        gst_buffer.unmap(map_info)
        return Gst.FlowReturn.OK

    img_bytes_slice_data = buffer_data_bytes[:0x0004B000]
    hdr_bytes_slice_data = buffer_data_bytes[0x0004B000:]
    gst_buffer.unmap(map_info)

    img_np_view = np.frombuffer(img_bytes_slice_data, dtype=np.uint8)

    try:
        if len(hdr_bytes_slice_data) < (0x30 + 12):
            return Gst.FlowReturn.OK
        if hdr_bytes_slice_data[0x30 + 11] == 1: # Skip based on header byte
            return Gst.FlowReturn.OK
    except (struct.error, IndexError) as e:
        return Gst.FlowReturn.OK # Or handle error

    img_new_unscrambled_pre_rotation_rows = 480
    img_new_unscrambled_pre_rotation_cols = 640
    # Initialize with zeros, will be filled by unscrambling logic
    img_new_unscrambled = np.zeros(img_new_unscrambled_pre_rotation_rows * img_new_unscrambled_pre_rotation_cols, dtype=np.uint8)
    
    bmap = []
    first_frame_debug = (frame_count_unscrambled == 0)

    try:
        num_blocks_expected = 0x0004B000 // 2400
        if len(img_np_view) != num_blocks_expected * 2400:
            if first_frame_debug: print(f"Unscramble: img_np_view size mismatch for unscrambling.")
            # Don't return yet, let it go to the black image fallback for final_image_np
        else: # Only proceed with unscrambling if size is correct
            marker = b'\0' * 128
            from_block_idx = 0
            try:
                start_byte_offset = img_bytes_slice_data.index(marker)
                from_block_idx = start_byte_offset // 2400
                if first_frame_debug: print(f"  Found marker at byte {start_byte_offset}, starting from_block_idx = {from_block_idx}")
            except ValueError:
                if first_frame_debug: print("  Marker b'\\0'*128 not found, starting from_block_idx = 0")
            
            if not (0 <= from_block_idx < num_blocks_expected):
                if first_frame_debug: print(f"  Calculated from_block_idx {from_block_idx} is out of range. Defaulting to 0.")
                from_block_idx = 0

            edge_pixels = []
            chain_options = [[] for _ in range(num_blocks_expected)]

            for b_idx in range(num_blocks_expected):
                top_line = img_np_view[b_idx*2400 : b_idx*2400+640]
                bottom_line = img_np_view[b_idx*2400+2400-640 : b_idx*2400+2400]
                if len(top_line) != 640 or len(bottom_line) != 640:
                    if first_frame_debug: print(f"Unscramble: Invalid line slice for block {b_idx}")
                    continue # Skip this block if lines are not extractable

                for other_b_idx, (ot, ob) in enumerate(edge_pixels):
                    dt = np.abs(ot.astype(np.int16) - bottom_line.astype(np.int16)).sum()
                    db = np.abs(ob.astype(np.int16) - top_line.astype(np.int16)).sum()
                    chain_options[b_idx].append((dt, other_b_idx))
                    chain_options[other_b_idx].append((db, b_idx))
                edge_pixels.append((top_line, bottom_line))
            
            for options in chain_options:
                options.sort()
            
            for _ in range(num_blocks_expected):
                if not (0 <= from_block_idx < len(chain_options)) or not chain_options[from_block_idx]:
                    if first_frame_debug: print(f"  Bmap build: 'from_block_idx' {from_block_idx} invalid. Filling.")
                    remaining_indices = [idx for idx in range(num_blocks_expected) if idx not in bmap]
                    bmap.extend(remaining_indices)
                    break
                
                current_options = chain_options[from_block_idx]
                bmap.append(from_block_idx)

                found_next = False
                for _quality, next_candidate_idx in current_options:
                    if next_candidate_idx not in bmap:
                        from_block_idx = next_candidate_idx
                        found_next = True
                        break
                
                if not found_next:
                    if first_frame_debug: print(f"  Bmap build: No unique next block. Filling.")
                    remaining_indices = [idx for idx in range(num_blocks_expected) if idx not in bmap]
                    bmap.extend(remaining_indices)
                    break
            
            if len(bmap) < num_blocks_expected:
                if first_frame_debug: print(f"  Bmap build: Post-loop bmap has {len(bmap)}. Filling.")
                missing_indices = [idx for idx in range(num_blocks_expected) if idx not in bmap]
                bmap.extend(missing_indices)

            if first_frame_debug:
                is_permutation = len(set(bmap)) == num_blocks_expected and len(bmap) == num_blocks_expected
                print(f"Unscramble Frame {frame_count_unscrambled}: bmap is full permutation: {is_permutation}, len(set): {len(set(bmap))}, len: {len(bmap)}")
                if not is_permutation or len(bmap) < 20 : print(f"Unscramble Frame {frame_count_unscrambled}: Generated bmap (first 20): {bmap[:20]}")

            for target_block_idx in range(num_blocks_expected):
                if target_block_idx >= len(bmap): continue # Should not happen if bmap filled
                source_block_idx = bmap[target_block_idx]
                # Ensure source_block_idx is valid, default to target_block_idx (identity map for this block)
                if not (0 <= source_block_idx < num_blocks_expected):
                    source_block_idx = target_block_idx 

                src_start = source_block_idx * 2400
                tgt_start = target_block_idx * 2400
                
                if (src_start + 2400 <= len(img_np_view)) and \
                   (tgt_start + 2400 <= len(img_new_unscrambled)):
                    img_new_unscrambled[tgt_start : tgt_start+2400] = img_np_view[src_start : src_start+2400]

    except Exception as e:
        print(f"Unscramble: Error during unscrambling algorithm: {e}")
        import traceback
        traceback.print_exc()
        # img_new_unscrambled will remain zeros or partially filled

    # --- Prepare final image (rotation, fallback to black if issues) ---
    final_image_np = None # This will hold the np array of the final image (OUT_HEIGHT, OUT_WIDTH)

    # Check if unscrambled data seems valid enough for rotation
    if img_new_unscrambled.size == img_new_unscrambled_pre_rotation_rows * img_new_unscrambled_pre_rotation_cols:
        try:
            image_2d = img_new_unscrambled.reshape((img_new_unscrambled_pre_rotation_rows, img_new_unscrambled_pre_rotation_cols))
            rotated_image_2d = np.rot90(image_2d, k=1) # k=1 for counter-clockwise
            
            # Sanity check dimensions after rotation
            if rotated_image_2d.shape[0] == OUT_HEIGHT and rotated_image_2d.shape[1] == OUT_WIDTH:
                final_image_np = rotated_image_2d
            else: # Shape mismatch after rotation
                if first_frame_debug: print(f"WARNING: Rotated image shape {rotated_image_2d.shape} != OUT_HEIGHT/OUT_WIDTH ({OUT_HEIGHT},{OUT_WIDTH}). Using black image.")
                final_image_np = np.zeros((OUT_HEIGHT, OUT_WIDTH), dtype=np.uint8)
        except Exception as rot_ex: # Error during rotation
            if first_frame_debug: print(f"Unscramble: Error during rotation: {rot_ex}. Using black image.")
            final_image_np = np.zeros((OUT_HEIGHT, OUT_WIDTH), dtype=np.uint8)
    else: # img_new_unscrambled was not of expected size (e.g., unscrambling failed catastrophically)
        if first_frame_debug: print("Unscramble: Size mismatch of pre-rotation data. Using black image.")
        final_image_np = np.zeros((OUT_HEIGHT, OUT_WIDTH), dtype=np.uint8)

    # Safeguard: ensure final_image_np is always a valid array
    if final_image_np is None:
        print("CRITICAL: final_image_np ended up as None. Defaulting to black image.")
        final_image_np = np.zeros((OUT_HEIGHT, OUT_WIDTH), dtype=np.uint8)

    # Convert the final NumPy array to bytes for GStreamer
    final_buffer_data_bytes = final_image_np.tobytes()

    # --- Photo Capture Logic ---
    current_time = time.time()
    # Initialize last_photo_time on the very first successfully processed frame
    if last_photo_time == 0.0: 
        last_photo_time = current_time # Start timer from the first frame

    if (current_time - last_photo_time) >= photo_capture_interval:
        photo_counter += 1
        filename = os.path.join(output_folder, f"calibr_{photo_counter}.jpg")
        try:
            # final_image_np is a NumPy array with shape (OUT_HEIGHT, OUT_WIDTH)
            # OUT_FORMAT is GRAY8, so it's a grayscale image.
            pil_image = Image.fromarray(final_image_np, mode='L') # 'L' for 8-bit grayscale
            pil_image.save(filename, "JPEG")
            print(f"Saved photo: {filename}")
            last_photo_time = current_time # Reset timer for the next interval
        except Exception as e:
            print(f"Error saving photo {filename}: {e}")
    # --- End Photo Capture Logic ---

    out_g_buf = Gst.Buffer.new_wrapped(final_buffer_data_bytes)
    ret = outsrc.emit("push-buffer", out_g_buf)

    frame_count_unscrambled += 1
    return Gst.FlowReturn.OK

appsink.connect('new-sample', new_frame_unscramble)

print("Setting pipelines to PLAYING state...")
if pipeline.set_state(Gst.State.PLAYING) == Gst.StateChangeReturn.FAILURE:
    print("ERROR: Input pipeline failed to go to PLAYING state."); sys.exit(1)
if outpipe.set_state(Gst.State.PLAYING) == Gst.StateChangeReturn.FAILURE:
    print("ERROR: Output pipeline failed to go to PLAYING state."); pipeline.set_state(Gst.State.NULL); sys.exit(1)

print(f"Input pipeline delivering: {caps_cam_native_str} (size: {APPSINK_EXPECTED_BLOCKSIZE} bytes) -> appsink")
print(f"Unscrambling, then rotating. Outputting as: {OUT_FORMAT}, {OUT_WIDTH}x{OUT_HEIGHT} (size: {OUT_WIDTH*OUT_HEIGHT} bytes)")
print(f"Output pipeline displaying this via appsrc.")
print(f"Photos will be saved as calibr_X.jpg every {photo_capture_interval} seconds in '{os.path.abspath(output_folder)}'.")
print("Starting main loop. Press Ctrl+C to exit.")

mainloop = GLib.MainLoop()
try:
    mainloop.run()
except KeyboardInterrupt:
    print("\nCtrl+C pressed, exiting.")
except Exception as e:
    print(f"An unexpected error occurred in mainloop: {e}")
    import traceback
    traceback.print_exc()
finally:
    print("Setting pipelines to NULL state.")
    if pipeline: pipeline.set_state(Gst.State.NULL)
    if outpipe: outpipe.set_state(Gst.State.NULL)
    print("Exited.")