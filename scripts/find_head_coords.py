import bpy
import mathutils

mesh_obj = bpy.data.objects.get("Mesh_0")
verts = mesh_obj.data.vertices

xs = [v.co.x for v in verts]
ys = [v.co.y for v in verts]
zs = [v.co.z for v in verts]

print(f"Total vertices: {len(verts)}")
print(f"X bounds: min={min(xs):.4f}, max={max(xs):.4f}")
print(f"Y bounds: min={min(ys):.4f}, max={max(ys):.4f}")
print(f"Z bounds: min={min(zs):.4f}, max={max(zs):.4f}")

# Checar transformações do objeto (matrix_world, location, rotation, scale)
print(f"Location: {mesh_obj.location}")
print(f"Rotation: {mesh_obj.rotation_euler}")
print(f"Scale: {mesh_obj.scale}")

# Checar os dentes e olhos onde foram colocados
for name in ["Eye_Left", "Eye_Right", "Teeth_Upper", "Teeth_Lower", "Mouth_Cavity_Interior"]:
    o = bpy.data.objects.get(name)
    if o:
        print(f"{name}: loc={o.location}, matrix_world_translation={o.matrix_world.translation}")

# Checar onde está o osso 'head' na Armature
arm = bpy.data.objects.get("Armature_WarriorGirl")
if arm:
    head_bone = arm.data.bones.get("head")
    if head_bone:
        print(f"Head bone head={head_bone.head}, tail={head_bone.tail}")
