import bpy
import bmesh
from mathutils import Vector

blend_base = r'D:\isabella-desktop\assets\models\warrior_girl_rigged.blend'
bpy.ops.wm.open_mainfile(filepath=blend_base)

mesh_obj = bpy.data.objects.get("Mesh_0")
verts = mesh_obj.data.vertices

# Vamos analisar a curvatura frontal (Y < -0.05, Z entre 0.60 e 0.85, |X| < 0.12)
face_verts = [v for v in verts if v.co.y < -0.05 and 0.60 <= v.co.z <= 0.85 and abs(v.co.x) < 0.12]
print(f"Total face_verts: {len(face_verts)}")

# Vamos agrupar por faixas de Z para identificar:
# Nariz (onde Y é o mais negativo perto do centro X~0)
# Boca (logo abaixo do nariz)
# Queixo (abaixo da boca)
# Olhos (acima do nariz)
# Sobrancelhas (acima dos olhos)

# Encontrar o vértice mais pontudo para frente perto do centro (|x| < 0.03):
nose_candidates = [v for v in face_verts if abs(v.co.x) < 0.02]
nose_tip = min(nose_candidates, key=lambda v: v.co.y)
print(f"Ponta do Nariz provavel: idx={nose_tip.index}, co=({nose_tip.co.x:.4f}, {nose_tip.co.y:.4f}, {nose_tip.co.z:.4f})")

# Vértices abaixo do nariz:
chin_candidates = [v for v in nose_candidates if v.co.z < nose_tip.co.z - 0.08]
chin_tip = min(chin_candidates, key=lambda v: v.co.y)
print(f"Ponta do Queixo provavel: idx={chin_tip.index}, co=({chin_tip.co.x:.4f}, {chin_tip.co.y:.4f}, {chin_tip.co.z:.4f})")

# Boca deve estar entre o nariz e o queixo:
mouth_z_min = chin_tip.co.z + 0.02
mouth_z_max = nose_tip.co.z - 0.02
print(f"Faixa de Boca esperada Z: [{mouth_z_min:.4f}, {mouth_z_max:.4f}]")

mouth_verts = [v for v in face_verts if mouth_z_min <= v.co.z <= mouth_z_max and abs(v.co.x) < 0.05]
print(f"Vertices na regiao da boca: {len(mouth_verts)}")
for v in sorted(mouth_verts, key=lambda v: (v.co.z, v.co.x))[:15]:
    print(f"  Mouth v {v.index}: ({v.co.x:.4f}, {v.co.y:.4f}, {v.co.z:.4f})")

# Olhos devem estar acima do nariz:
eye_z_min = nose_tip.co.z + 0.01
eye_z_max = nose_tip.co.z + 0.06
print(f"Faixa de Olhos esperada Z: [{eye_z_min:.4f}, {eye_z_max:.4f}]")
eye_verts = [v for v in face_verts if eye_z_min <= v.co.z <= eye_z_max and abs(v.co.x) > 0.015 and abs(v.co.x) < 0.07]
print(f"Vertices na regiao dos olhos: {len(eye_verts)}")

# Sobrancelhas:
brow_z_min = eye_z_max
brow_z_max = eye_z_max + 0.05
print(f"Faixa de Sobrancelhas Z: [{brow_z_min:.4f}, {brow_z_max:.4f}]")
brow_verts = [v for v in face_verts if brow_z_min <= v.co.z <= brow_z_max and abs(v.co.x) < 0.08]
print(f"Vertices na regiao das sobrancelhas: {len(brow_verts)}")
