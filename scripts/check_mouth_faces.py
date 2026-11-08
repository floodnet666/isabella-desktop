import bpy
import bmesh

blend_base = r'D:\isabella-desktop\assets\models\warrior_girl_rigged.blend'
bpy.ops.wm.open_mainfile(filepath=blend_base)

mesh_obj = bpy.data.objects.get("Mesh_0")
bm = bmesh.new()
bm.from_mesh(mesh_obj.data)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()

# A boca está entre z=0.640 e z=0.665, y em torno de -0.09, |x| < 0.04
mouth_faces = [f for f in bm.faces if all(0.63 <= v.co.z <= 0.67 and v.co.y < -0.06 and abs(v.co.x) < 0.045 for v in f.verts)]
print(f"Total mouth faces: {len(mouth_faces)}")

for f in mouth_faces:
    center = f.calc_center_median()
    print(f"Face {f.index}: center=({center.x:.4f}, {center.y:.4f}, {center.z:.4f}), num_verts={len(f.verts)}")
