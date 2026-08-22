from PIL import Image, ImageDraw

S = 256
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle([8, 8, S - 8, S - 8], radius=52, fill=(13, 16, 24, 255))

cx, cy = S / 2, S / 2
minx, maxx = cx - 28, cx + 40
for x in range(int(minx), int(maxx) + 1):
    t = (x - minx) / (maxx - minx)
    col = (int(139 + (77 - 139) * t), int(124 + (214 - 124) * t), 255, 255)
    yt = cy - 42 * (1 - t)
    yb = cy + 42 * (1 - t)
    d.line([(x, yt), (x, yb)], fill=col)

img.save("icon.ico", sizes=[(256, 256), (128, 128), (64, 64),
                            (48, 48), (32, 32), (16, 16)])
print("icon OK")
