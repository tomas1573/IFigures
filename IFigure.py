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


blur_sigma = 1.0 # jačina gaussian blura

#--------- ROI selection
imp = IJ.getImage()
roi = imp.getRoi()

if roi is None:
    IJ.error("Please draw a selection (ROI) before running this script.")
    raise SystemExit

channels = imp.getNChannels()
slices   = imp.getNSlices()

#--------- Z slice selection
zslice = IJ.getNumber("Select Z slice:".format(slices), slices//2)
zslice = int(max(1, min(zslice, slices)))

#--------- Z slice extraction - zadržava sve kanale
IJ.run(imp, "Make Substack...", "slices={} keep".format(zslice))
sub = IJ.getImage()

#--------- crop na prethodno odabran ROI
sub.setRoi(roi)
IJ.run(sub, "Crop", "")
cropped = IJ.getImage()

#--------- splittanje kanala
chs = ChannelSplitter.split(cropped)

processed = []

for ch in chs:
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
processed[0] = normalize_channel(processed[0])
processed[1] = normalize_channel(processed[1]) 
processed[2] = normalize_channel(processed[2])

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
ci.show()

#--------- Layout panela - mijenjanje poretka
panels = [processed[2], processed[0], processed[1], ci]

#--------- podešavanje izgleda crne pozadine i teksta
padding = 60  
label_space = 30  
num_panels = len(panels)
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

fig.updateAndDraw()
fig.show()