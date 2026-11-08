import bpy
import math

blend_base = r'D:\isabella-desktop\assets\models\warrior_girl_rigged.blend'
bpy.ops.wm.open_mainfile(filepath=blend_base)

scene = bpy.context.scene

# Configurações do motor
scene.render.engine = 'BLENDER_EEVEE_NEXT' if hasattr(bpy.types, 'RenderSettings') and 'BLENDER_EEVEE_NEXT' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
scene.render.resolution_x = 512
scene.render.resolution_y = 512
scene.display_settings.display_device = 'sRGB'
scene.view_settings.view_transform = 'Standard'

# World com cinza estúdio neutro
scene.world.use_nodes = True
nodes = scene.world.node_tree.nodes
nodes.clear()
node_out = nodes.new('ShaderNodeOutputWorld')
node_bg = nodes.new('ShaderNodeBackground')
node_bg.inputs['Color'].default_value = (0.82, 0.83, 0.83, 1.0) # Tom cinza exato da referência
node_bg.inputs['Strength'].default_value = 0.8
scene.world.node_tree.links.new(node_bg.outputs['Background'], node_out.inputs['Surface'])

# Remover luzes antigas
for obj in list(bpy.data.objects):
    if obj.type == 'LIGHT':
        bpy.data.objects.remove(obj, do_unlink=True)

# Key Light (Area light suave do topo direito)
key_data = bpy.data.lights.new('KeyArea', type='AREA')
key_data.energy = 8.0
key_data.size = 0.5
key_data.color = (1.0, 0.98, 0.95)
key_obj = bpy.data.objects.new('KeyArea', key_data)
scene.collection.objects.link(key_obj)
key_obj.location = (0.25, -0.65, 1.05)
key_obj.rotation_euler = (math.radians(50), math.radians(10), math.radians(15))

# Fill Light (Area light suave da esquerda para preenchimento)
fill_data = bpy.data.lights.new('FillArea', type='AREA')
fill_data.energy = 4.0
fill_data.size = 0.8
fill_data.color = (0.95, 0.98, 1.0)
fill_obj = bpy.data.objects.new('FillArea', fill_data)
scene.collection.objects.link(fill_obj)
fill_obj.location = (-0.35, -0.60, 0.85)
fill_obj.rotation_euler = (math.radians(50), math.radians(-15), math.radians(-25))

# Câmera calibrada
cam = bpy.data.objects.get('Camera')
if not cam:
    cam_data = bpy.data.cameras.new('Camera')
    cam = bpy.data.objects.new('Camera', cam_data)
    scene.collection.objects.link(cam)

scene.camera = cam
cam.data.lens = 85
# Enquadrar do topo da cabeça (z=0.95) até a clavícula (z=0.50)
cam.location = (-0.01, -0.85, 0.72)
cam.rotation_euler = (math.radians(90), 0, 0)

out_path = r'D:\isabella-desktop\assets\renders\warrior_girl\face_calibrated_lighting.png'
scene.render.filepath = out_path
bpy.ops.render.render(write_still=True)
print(f"Render teste salvo em {out_path}")
