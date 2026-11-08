import bpy
import math

blend_base = r'D:\isabella-desktop\assets\models\warrior_girl_rigged.blend'
bpy.ops.wm.open_mainfile(filepath=blend_base)

scene = bpy.context.scene

# Configurar render
scene.render.engine = 'BLENDER_EEVEE_NEXT' if hasattr(bpy.types, 'RenderSettings') and 'BLENDER_EEVEE_NEXT' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
scene.render.resolution_x = 512
scene.render.resolution_y = 512
scene.display_settings.display_device = 'sRGB'
scene.view_settings.view_transform = 'Standard'

# Configurar World
scene.world.use_nodes = True
bg = scene.world.node_tree.nodes.get('Background')
if bg:
    bg.inputs['Color'].default_value = (0.85, 0.85, 0.85, 1.0)
    bg.inputs['Strength'].default_value = 1.0

# Camera close-up frontal
cam_obj = bpy.data.objects.get('Camera')
if not cam_obj:
    cam_data = bpy.data.cameras.new('Camera')
    cam_obj = bpy.data.objects.new('Camera', cam_data)
    scene.collection.objects.link(cam_obj)

cam_obj.location = (0.0, -0.55, 0.73)
cam_obj.rotation_euler = (math.radians(90), 0, 0)
cam_obj.data.lens = 75 # lente teleobjetiva para evitar distorção de perspectiva

# Luz principal suave frontal/topo
light = bpy.data.objects.get('KeyLight')
if not light:
    light_data = bpy.data.lights.new('KeyLight', type='SUN')
    light = bpy.data.objects.new('KeyLight', light_data)
    scene.collection.objects.link(light)
light.location = (0.2, -0.5, 1.2)
light.rotation_euler = (math.radians(45), math.radians(15), 0)
light.data.energy = 2.5

scene.camera = cam_obj
out_path = r'D:\isabella-desktop\assets\renders\warrior_girl\face_closeup_base.png'
scene.render.filepath = out_path
bpy.ops.render.render(write_still=True)
print(f"Render salvo em {out_path}")
