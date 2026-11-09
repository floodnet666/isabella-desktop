import os
import time
import psutil
import pygame
from pygame.locals import *
from OpenGL.GL import *
try:
    import live2d.v3 as live2d
except ImportError:
    import live2d

print("Live2D SDK version:", live2d.__version__)
print("Csm version:", live2d.__csm_version__)
