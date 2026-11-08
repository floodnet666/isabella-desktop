import os
import time
import psutil
import pygame
from pygame.locals import *
from OpenGL.GL import *
import live2d.v3 as live2d if hasattr(live2d, 'v3') else None
import live2d

print("Live2D SDK version:", live2d.__version__)
print("Csm version:", live2d.__csm_version__)
