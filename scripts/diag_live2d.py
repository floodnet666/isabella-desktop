import traceback
import sys

try:
    import live2d
    print("live2d imported")
    live2d.init()
    print("live2d.init() OK")
    import pygame
    from pygame.locals import *
    from OpenGL.GL import *
    pygame.init()
    screen = pygame.display.set_mode((200, 200), DOUBLEBUF | OPENGL)
    print("OpenGL context OK")
    live2d.glInit()
    print("live2d.glInit() OK")
    m = live2d.Model()
    print("live2d.Model() OK")
    m.LoadModelJson(r"D:\isabella-desktop\benchmarks_avatars\live2d\Hiyori\Hiyori.model3.json")
    print("LoadModelJson OK!")
except Exception as e:
    traceback.print_exc()
    sys.exit(1)
