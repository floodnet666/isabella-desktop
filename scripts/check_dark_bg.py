from PIL import Image

transp = Image.open(r"D:\isabella-desktop\benchmarks_avatars\isabella_pngtuber_user\test_transp.png")
W, H = transp.size

bg = Image.new("RGBA", (W, H), (30, 35, 50, 255))
bg.alpha_composite(transp)
bg.save(r"D:\isabella-desktop\benchmarks_avatars\isabella_pngtuber_user\test_dark_bg.png")
print("Salvo sobre fundo escuro!")
