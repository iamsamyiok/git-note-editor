from PIL import Image
img = Image.open("icon.png")
img.save("icon.ico", format="ICO", sizes=[(48, 48), (32, 32), (16, 16)])
print("icon.ico created")
