
from ij import IJ, ImagePlus
from ij.plugin import ChannelSplitter
from ij.gui import NewImage
from ij.process import LUT
from ij import CompositeImage, ImageStack
from java.awt import Color
from ij.process import FloatProcessor
from java.awt import Font

def normalize_channel(img):
    stats = img.getStatistics()
    ip = img.getProcessor().convertToFloatProcessor()
    ip.multiply(255.0 / (stats.max - stats.min)) # skalira 0 - 255
    ip.subtract(stats.min * 255.0 / (stats.max - stats.min))
    img.setProcessor(ip)
    return img


# Use provided parameters (from batch_process.py) instead of dialogs
# blur_sigma, zslice, z_start, z_end are passed from batch wrapper
# If not defined, use defaults
try:
    blur_sigma
except NameError:
    blur_sigma = 0.0

try:
    zslice
except NameError:
    zslice = None

try:
    z_start
except NameError:
    z_start = None

try:
    z_end
except NameError:
    z_end = None

#--------- ROI selection (optional - use whole image if no ROI)
imp = IJ.getImage()
roi = imp.getRoi()

channels = imp.getNChannels()
slices   = imp.getNSlices()

# If zslice not provided, use middle slice
if zslice is None:
    zslice = slices // 2

# If z_start/z_end not provided, use full range
if z_start is None:
    z_start = 1
if z_end is None:
    z_end = slices

#--------- Crop ROI first (keeping all slices and channels), or use whole image
if roi is not None:
    imp.setRoi(roi)
    IJ.run(imp, "Duplicate...", "duplicate")
    cropped_stack = IJ.getImage()
    cropped_stack.hide()
else:
    IJ.run(imp, "Duplicate...", "duplicate")
    cropped_stack = IJ.getImage()
    cropped_stack.hide()

#--------- Z slice extraction from cropped stack
zslice = int(max(1, min(zslice, slices)))
IJ.run(cropped_stack, "Make Substack...", "slices={} keep".format(zslice))
cropped = IJ.getImage()
cropped.hide()

#--------- splittanje kanala
chs = ChannelSplitter.split(cropped)

processed = []

for ch in chs:
    ch.hide()
    IJ.run(ch, "Gaussian Blur...", "sigma={}".format(blur_sigma))
    processed.append(ch)

# processed[0] = kanal 1/3
# processed[1] = kanal 2/3
# processed[2] = kanal 3/3

#--------- sastavljanje composita
w = processed[0].getWidth()
h = processed[0].getHeight()

stack = ImageStack(w, h)

#--------- normalizacija svih kanala, nastavak sastavljanja
# trenutno po mom shvaćanju normalizacija nije potrebna ukoliko je 
# tijekom mikroskopiranja sve dobro postimano, tako da za sad nista od ovog
##processed[0] = normalize_channel(processed[0])
##processed[1] = normalize_channel(processed[1]) 
##processed[2] = normalize_channel(processed[2])

stack.addSlice("FarRed", processed[0].getProcessor())
stack.addSlice("GrayCh1", processed[1].getProcessor())

imp_merge = ImagePlus("Merged", stack)

#--------- prebacivanje u CompositeImage
ci = CompositeImage(imp_merge, CompositeImage.COMPOSITE)

#--------- LUT - tu se mogu boje promijeniti
ci.setChannelLut(LUT.createLutFromColor(Color.red), 1)
ci.setChannelLut(LUT.createLutFromColor(Color.white), 2)

#--------- display ranges
ci.setDisplayRange(0, 255, 1)
ci.setDisplayRange(0, 255, 2)

ci.setActiveChannels("11")
ci.setMode(CompositeImage.COMPOSITE)
ci.hide()

#--------- Layout panela - mijenjanje poretka
panels = [processed[2], processed[0], processed[1], ci]

#--------- podešavanje izgleda crne pozadine i teksta
padding = 60  
label_space = 30  
num_panels = len(panels)

#---------- korištenje labela iz dijaloga
try:
    panel_labels
except NameError:
    panel_labels = ["Cyan", "Far red", "Red", "Merged"]  

#--------- fig size
fig_width = w * num_panels + padding * (num_panels + 1)
fig_height = h + 2 * padding + label_space  # extra space for labels


fig = NewImage.createRGBImage("Figure", fig_width, fig_height, 1, NewImage.FILL_BLACK)
fig_ip = fig.getProcessor()

#--------- font
fig_ip.setFont(Font("SansSerif", Font.BOLD, 16))
fig_ip.setColor(Color.white)

for i, p in enumerate(panels):
    tmp = p.duplicate()
    IJ.run(tmp, "8-bit", "")
    IJ.run(tmp, "RGB Color", "")
    
    #--------- centriranje slika
    x_pos = padding + i * (w + padding)  # horizontalno
    y_pos = padding + (fig_height - 2 * padding - h)//2  # vertikalno
    
    fig_ip.insert(tmp.getProcessor(), x_pos, y_pos)
    
    #--------- label iznad
    label = panel_labels[i]
    label_width = fig_ip.getStringWidth(label)
    fig_ip.drawString(label, x_pos + (w - label_width)//2, padding//2)

#--------- Max Z projekcija
from ij.plugin import ZProjector

z_start = int(max(1, min(z_start, slices)))
z_end = int(max(z_start, min(z_end, slices)))

IJ.run(cropped_stack, "Make Substack...", "slices={}-{} keep".format(z_start, z_end))
sub_z = IJ.getImage()
sub_z.hide()

chs_z_stack = ChannelSplitter.split(sub_z)

proc_z = []
for ch_z_stack in chs_z_stack:
    ch_z_stack.hide()
    # Z-project this channel
    zproj = ZProjector(ch_z_stack)
    zproj.setMethod(ZProjector.MAX_METHOD)
    zproj.doProjection()
    proj_ch = zproj.getProjection()
    proj_ch.hide()
    
    IJ.run(proj_ch, "Gaussian Blur...", "sigma={}".format(blur_sigma))
    proc_z.append(proj_ch)
    
    # Clean up
    ch_z_stack.close()

#--------- sastavljanje composita za projection (bez normalizacije)
if len(proc_z) < 2:
    IJ.error("Image has {} channels, but 2 channels are required for Z-projection.\nOriginal image channels: {}".format(len(proc_z), channels))
    raise SystemExit

w_z = proc_z[0].getWidth()
h_z = proc_z[0].getHeight()

stack_z = ImageStack(w_z, h_z)
stack_z.addSlice("Ch0_z", proc_z[0].getProcessor())  # Channel 0
stack_z.addSlice("Ch1_z", proc_z[1].getProcessor())  # Channel 1

imp_merge_z = ImagePlus("Merged_Z", stack_z)

#--------- prebacivanje u CompositeImage za projection
ci_z = CompositeImage(imp_merge_z, CompositeImage.COMPOSITE)

#--------- LUT za projection - iste boje kao gore (only set for channels that exist)
num_channels_z = stack_z.getSize()
if num_channels_z >= 1:
    ci_z.setChannelLut(LUT.createLutFromColor(Color.red), 1)  # Channel 0
    ci_z.setDisplayRange(0, 255, 1)
if num_channels_z >= 2:
    ci_z.setChannelLut(LUT.createLutFromColor(Color.white), 2)  # Channel 1
    ci_z.setDisplayRange(0, 255, 2)

ci_z.setActiveChannels("11")
ci_z.setMode(CompositeImage.COMPOSITE)
ci_z.hide() 

cropped_stack.close()

#--------- Combined Figure - single slice top row, z-projection bottom row
# Build panels_z with channel 0, channel 1, and merged (0+1)
panels_z = []
if len(proc_z) > 0:
    panels_z.append(proc_z[0])  # Channel 0
if len(proc_z) > 1:
    panels_z.append(proc_z[1])  # Channel 1
panels_z.append(ci_z)  # Merged (Ch0 + Ch1)

row_label_space = 30
fig_combined_width = w * num_panels + padding * (num_panels + 1)
fig_combined_height = h + h_z + 3 * padding + 2 * row_label_space

fig_combined = NewImage.createRGBImage("Combined Figure", fig_combined_width, fig_combined_height, 1, NewImage.FILL_BLACK)
fig_combined_ip = fig_combined.getProcessor()

#--------- font
fig_combined_ip.setFont(Font("SansSerif", Font.BOLD, 16))
fig_combined_ip.setColor(Color.white)

#--------- Top row - single slice
for i, p in enumerate(panels):
    tmp = p.duplicate()
    IJ.run(tmp, "8-bit", "")
    IJ.run(tmp, "RGB Color", "")
    
    x_pos = padding + i * (w + padding)
    y_pos = padding + row_label_space
    
    fig_combined_ip.insert(tmp.getProcessor(), x_pos, y_pos)
    
    #--------- label above
    label = panel_labels[i]
    label_width = fig_combined_ip.getStringWidth(label)
    fig_combined_ip.drawString(label, x_pos + (w - label_width)//2, padding + row_label_space - 10)

#--------- Bottom row - z projection
for i, p in enumerate(panels_z):
    tmp = p.duplicate()
    IJ.run(tmp, "8-bit", "")
    IJ.run(tmp, "RGB Color", "")
    
    # Offset by one panel width to the right
    x_pos = padding + (i + 1) * (w_z + padding)
    y_pos = padding + row_label_space + h + padding + row_label_space
    
    fig_combined_ip.insert(tmp.getProcessor(), x_pos, y_pos)
    
    #--------- label above - use custom labels for first two channels, then "Merged"
    if i == 0:
        label = panel_labels[1] + " (Max Z)"  # Channel 2 / Far red
    elif i == 1:
        label = panel_labels[2] + " (Max Z)"  # Channel 3 / Red
    else:
        label = panel_labels[3] + " (Max Z)"  # Merged
    label_width = fig_combined_ip.getStringWidth(label)
    fig_combined_ip.drawString(label, x_pos + (w_z - label_width)//2, y_pos - 10)

fig_combined.updateAndDraw()
fig_combined.show()
