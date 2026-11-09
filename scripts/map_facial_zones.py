import bpy
import bmesh

blend_base = r'D:\isabella-desktop\assets\models\warrior_girl_rigged.blend'
bpy.ops.wm.open_mainfile(filepath=blend_base)

mesh_obj = bpy.data.objects.get("Mesh_0")
bm = bmesh.new()
bm.from_mesh(mesh_obj.data)
bm.verts.ensure_lookup_table()

print("=== DETALHES DA BOCA ===")
mouth_verts = [v for v in bm.verts if 0.61 <= v.co.z <= 0.70 and v.co.y < -0.06 and abs(v.co.x) < 0.05]
print(f"Total mouth verts: {len(mouth_verts)}")

# Separar em lábio superior (z > 0.66), lábio inferior (0.63 <= z <= 0.66), e queixo (z < 0.63)
upper_lip = [v for v in mouth_verts if 0.655 <= v.co.z <= 0.68]
lower_lip = [v for v in mouth_verts if 0.635 <= v.co.z < 0.655]
corners_l = [v for v in mouth_verts if v.co.x > 0.025 and 0.64 <= v.co.z <= 0.67]
corners_r = [v for v in mouth_verts if v.co.x < -0.025 and 0.64 <= v.co.z <= 0.67]

print(f"Upper lip: {len(upper_lip)} verts")
print(f"Lower lip: {len(lower_lip)} verts")
print(f"Corner L: {len(corners_l)} verts, Corner R: {len(corners_r)} verts")

print("\n=== DETALHES DOS OLHOS E SOBRANCELHAS ===")
brows_l = [v for v in bm.verts if 0.80 <= v.co.z <= 0.85 and 0.01 <= v.co.x <= 0.07 and v.co.y < -0.11]
brows_r = [v for v in bm.verts if 0.80 <= v.co.z <= 0.85 and -0.07 <= v.co.x <= -0.01 and v.co.y < -0.11]
brows_mid = [v for v in bm.verts if 0.80 <= v.co.z <= 0.85 and abs(v.co.x) < 0.015 and v.co.y < -0.12]

print(f"Brows L: {len(brows_l)}, Brows R: {len(brows_r)}, Brows Mid: {len(brows_mid)}")

eyes_upper_l = [v for v in bm.verts if 0.77 <= v.co.z <= 0.80 and 0.02 <= v.co.x <= 0.06 and v.co.y < -0.12]
eyes_upper_r = [v for v in bm.verts if 0.77 <= v.co.z <= 0.80 and -0.06 <= v.co.x <= -0.02 and v.co.y < -0.12]

print(f"Eyes Upper L: {len(eyes_upper_l)}, Eyes Upper R: {len(eyes_upper_r)}")
