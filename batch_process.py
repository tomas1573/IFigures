"""
Batch processing wrapper for IFigure.py with interactive parameter preview
"""

from ij import IJ
from ij.io import Opener, FileSaver, DirectoryChooser
from ij.gui import GenericDialog, WaitForUserDialog, NonBlockingGenericDialog
from ij.plugin import ChannelSplitter
import os

# Store selected folders and dialog reference
selected_input = [None]
selected_output = [None]
gd_reference = [None]

def browse_input_folder(event):
    """Open directory chooser for input folder"""
    dc = DirectoryChooser("Select INPUT folder containing images")
    folder = dc.getDirectory()
    if folder:
        selected_input[0] = folder
        # Update the text field in the dialog
        if gd_reference[0]:
            gd_reference[0].getStringFields()[0].setText(folder)
        IJ.log("Input folder selected: {}".format(folder))

def browse_output_folder(event):
    """Open directory chooser for output folder"""
    dc = DirectoryChooser("Select OUTPUT folder for processed images")
    folder = dc.getDirectory()
    if folder:
        selected_output[0] = folder
        # Update the text field in the dialog
        if gd_reference[0]:
            gd_reference[0].getStringFields()[1].setText(folder)
        IJ.log("Output folder selected: {}".format(folder))

#----------- Selecting input and output folders
gd_intro = GenericDialog("Batch Processing - Folder Setup")
gd_intro.addMessage(" ")
gd_intro.addMessage("Select folders for batch processing:")
gd_intro.addMessage(" ")
gd_intro.addStringField("Input folder:", "", 50)
gd_intro.addButton("Browse Input Folder", browse_input_folder)
gd_intro.addMessage(" ")
gd_intro.addStringField("Output folder:", "", 50)
gd_intro.addButton("Browse Output Folder", browse_output_folder)
gd_intro.addMessage(" ")

# Store reference to dialog for button callbacks
gd_reference[0] = gd_intro

gd_intro.showDialog()

if gd_intro.wasCanceled():
    exit()

# Get the folders - first try the text fields, then fallback to button selections
input_dir = gd_intro.getNextString().strip()
output_dir = gd_intro.getNextString().strip()

# Use button selections if text fields are empty
if not input_dir:
    input_dir = selected_input[0]
if not output_dir:
    output_dir = selected_output[0]

if input_dir is None or input_dir == "":
    IJ.log("Input folder not selected. Cancelled.")
    exit()

if output_dir is None or output_dir == "":
    IJ.log("Output folder not selected. Cancelled.")
    exit()

IJ.log("Input folder: {}".format(input_dir))
IJ.log("Output folder: {}".format(output_dir))

#----------- file format
gd_setup = GenericDialog("Batch Process - File Format")
gd_setup.addMessage("Select file format to process:")
gd_setup.addChoice("File format:", ["czi", "tif", "tiff", "lsm", "nd2"], "czi")
gd_setup.showDialog()

if gd_setup.wasCanceled():
    exit()

file_ext = gd_setup.getNextChoice()

# Validate directories
if not os.path.exists(input_dir):
    IJ.error("Input folder does not exist: {}".format(input_dir))
    raise SystemExit

# Create output directory if it doesn't exist
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Get list of files matching pattern
files = []
for f in os.listdir(input_dir):
    if f.lower().endswith("." + file_ext):
        files.append(os.path.join(input_dir, f))

if len(files) == 0:
    IJ.error("No files found with extension .{} in {}".format(file_ext, input_dir))
    raise SystemExit

IJ.log("Found {} files to process".format(len(files)))

#----------- BATCH processing
processed = 0
failed = 0
skip_all = False

# default labels corresponding to previously used channels on airyscan, might need to be reordered in the future
last_label_ch1 = "Cyan"
last_label_ch2 = "Far red"
last_label_ch3 = "Red"
last_label_merged = "Merged"

for idx, file_path in enumerate(files, 1):
    filename = os.path.basename(file_path)
    IJ.log(" ")
    IJ.log("[{}/{}] Processing: {}".format(idx, len(files), filename))
    
    if skip_all:
        IJ.log("Skipped (user selected skip all)")
        continue
    
    try:
        # Open image
        opener = Opener()
        imp = opener.openImage(file_path)
        imp.show()
        
        channels = imp.getNChannels()
        slices_img = imp.getNSlices()
        roi = imp.getRoi()
        
        # Get the middle z slice as starting position
        middle_slice = (slices_img + 1) // 2
        
        # Create non-blocking dialog with parameters
        gd_params = NonBlockingGenericDialog("Image {}/{} - {}".format(idx, len(files), filename))
        gd_params.addMessage("Set parameters for processing:")
        gd_params.addMessage(" ")
        gd_params.addSlider("Gaussian Blur Sigma:", 0.0, 5.0, 0.0)
        gd_params.addSlider("Z-slice to use:", 1, slices_img, middle_slice)
        gd_params.addMessage(" ")
        gd_params.addMessage("Z-Projection range (for bottom row):")
        gd_params.addSlider("Start slice:", 1, slices_img, 1)
        gd_params.addSlider("End slice:", 1, slices_img, slices_img)
        gd_params.addMessage(" ")
        gd_params.addMessage("Channel labels (top row panels):")
        gd_params.addStringField("Channel 1 (Cyan):", last_label_ch1, 20)
        gd_params.addStringField("Channel 2 (Far red):", last_label_ch2, 20)
        gd_params.addStringField("Channel 3 (Red):", last_label_ch3, 20)
        gd_params.addStringField("Merged:", last_label_merged, 20)
        gd_params.addMessage(" ")
        gd_params.addChoice("Action:", ["Process", "Skip this", "Skip all remaining"], "Process")
        gd_params.showDialog()
        
        if gd_params.wasCanceled():
            IJ.run("Close All", "")
            IJ.log("Batch processing cancelled by user")
            exit()
        
        blur_sigma = gd_params.getNextNumber()
        z_slice = int(gd_params.getNextNumber())
        z_start = int(gd_params.getNextNumber())
        z_end = int(gd_params.getNextNumber())
        label_ch1 = gd_params.getNextString()
        label_ch2 = gd_params.getNextString()
        label_ch3 = gd_params.getNextString()
        label_merged = gd_params.getNextString()
        action = gd_params.getNextChoice()
        
        # Handle skip options
        if action == "Skip this":
            IJ.run("Close All", "")
            IJ.log("Skipped by user")
            continue
        elif action == "Skip all remaining":
            skip_all = True
            IJ.run("Close All", "")
            IJ.log("Skipped (skip all selected)")
            continue
        
        # Handle skip options
        if action == "Skip this":
            IJ.run("Close All", "")
            IJ.log("Skipped by user")
            continue
        elif action == "Skip all remaining":
            skip_all = True
            IJ.run("Close All", "")
            IJ.log("Skipped (skip all selected)")
            continue
        
        # Validate ranges
        z_slice = max(1, min(z_slice, slices_img))
        z_start = max(1, min(z_start, slices_img))
        z_end = max(z_start, min(z_end, slices_img))
        
        IJ.log("Parameters - Blur: {}, Z-slice: {}, Z-range: {}-{}".format(blur_sigma, z_slice, z_start, z_end))
        
        # Save labels for next image
        last_label_ch1 = label_ch1
        last_label_ch2 = label_ch2
        last_label_ch3 = label_ch3
        last_label_merged = label_merged
        
        # Create execution context with parameters
        exec_context = {
            'IJ': IJ,
            'Opener': Opener,
            'FileSaver': FileSaver,
            'ChannelSplitter': ChannelSplitter,
            'imp': imp,
            'roi': roi,
            'channels': channels,
            'slices': slices_img,
            'blur_sigma': blur_sigma,
            'zslice': z_slice,
            'z_start': z_start,
            'z_end': z_end,
            'panel_labels': [label_ch1, label_ch2, label_ch3, label_merged],
            '__name__': '__main__',
            'exit': exit,
        }
        
        # Search in the same directory as this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        ifigure_path = os.path.join(script_dir, "IFigure_batch.py")
        
        if not os.path.exists(ifigure_path):
            IJ.error("IFigure_batch.py not found in: {}".format(script_dir))
            raise SystemExit
        
        with open(ifigure_path, 'r') as f:
            ifigure_code = f.read()
        
        exec(ifigure_code, exec_context)
        
        # Get the result image (fig_combined)
        result_img = IJ.getImage()
        
        # Save the combined figure
        output_name = filename.split('.')[0] + "_figure.jpeg"
        output_path = os.path.join(output_dir, output_name)
        
        fs = FileSaver(result_img)
        fs.saveAsJpeg(output_path)
        
        IJ.log("Saved: {}".format(output_path))
        processed += 1
        
        # Close all windows for this image
        IJ.run("Close All", "")
        
    except Exception as e:
        IJ.log("ERROR: {}".format(str(e)))
        failed += 1
        try:
            IJ.run("Close All", "")
        except:
            pass
        continue

# ===== STEP 6: Summary =====
IJ.log(" ")
IJ.log("="*60)
IJ.log("Batch processing complete!")
IJ.log("="*60)
IJ.log("Processed: {} files".format(processed))
IJ.log("Failed:    {} files".format(failed))
IJ.log("Output:    {}".format(output_dir))
IJ.log("="*60)
