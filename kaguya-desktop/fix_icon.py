from PIL import Image
import os

# Create a simple icon
img = Image.new('RGBA', (256, 256), (10, 10, 30, 255))

# Draw a simple "K" shape
from PIL import ImageDraw
draw = ImageDraw.Draw(img)

# Background gradient effect
for y in range(256):
    r = int(10 + (y / 256) * 20)
    g = int(10 + (y / 256) * 15)
    b = int(30 + (y / 256) * 40)
    draw.line([(0, y), (256, y)], fill=(r, g, b, 255))

# Draw K
# Vertical line
draw.rectangle([60, 40, 100, 216], fill=(100, 200, 255, 255))
# Upper diagonal
draw.polygon([(100, 40), (196, 40), (196, 80), (100, 120)], fill=(100, 200, 255, 255))
# Lower diagonal
draw.polygon([(100, 216), (196, 216), (196, 176), (100, 136)], fill=(100, 200, 255, 255))

# Save as ICO with multiple sizes
sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
imgs = []
for size in sizes:
    imgs.append(img.resize(size, Image.LANCZOS))

ico_path = r'c:\Users\林智涵\.conda\kaguya-desktop\assets\kaguya.ico'
imgs[0].save(ico_path, format='ICO', sizes=[(s[0], s[1]) for s in sizes], append_images=imgs[1:])

print(f"Icon saved: {ico_path}, size: {os.path.getsize(ico_path)} bytes")

# Also save PNG
png_path = r'c:\Users\林智涵\.conda\kaguya-desktop\assets\kaguya.png'
img.save(png_path, format='PNG')
print(f"PNG saved: {png_path}, size: {os.path.getsize(png_path)} bytes")
