import bpy
import bmesh
import numpy as np

# Inspecionar objetos na cena
print("=== OBJETOS NA CENA ===")
for obj in bpy.data.objects:
    print(f"Objeto: {obj.name}, Tipo: {obj.type}, Parent: {obj.parent.name if obj.parent else None}")

mesh_obj = bpy.data.objects.get("Mesh_0")
if mesh_obj:
    print("\n=== MESH_0 SHAPE KEYS ===")
    if mesh_obj.data.shape_keys:
        for kb in mesh_obj.data.shape_keys.key_blocks:
            print(f"KeyBlock: {kb.name}, Value: {kb.value}")
    else:
        print("Nenhuma shape key encontrada!")

    # Inspecionar vértices na região da face (Z entre 1.45 e 1.75, Y > 0.0)
    verts = mesh_obj.data.vertices
    face_verts = [v for v in verts if 1.45 <= v.co.z <= 1.75 and v.co.y > 0.0]
    print(f"\nTotal vertices em Mesh_0: {len(verts)}")
    print(f"Vertices na regiao da face: {len(face_verts)}")
    
    # Boca: z ~ 1.51 - 1.56, y ~ 0.06 - 0.12, |x| < 0.05
    mouth_verts = [v for v in face_verts if 1.50 <= v.co.z <= 1.56 and abs(v.co.x) < 0.04 and v.co.y > 0.05]
    print(f"Vertices na regiao da boca: {len(mouth_verts)}")
    
    # Olhos: z ~ 1.60 - 1.66, y ~ 0.05 - 0.11, |x| entre 0.015 e 0.055
    eye_l = [v for v in face_verts if 1.60 <= v.co.z <= 1.66 and 0.015 <= v.co.x <= 0.055 and v.co.y > 0.05]
    eye_r = [v for v in face_verts if 1.60 <= v.co.z <= 1.66 and -0.055 <= v.co.x <= -0.015 and v.co.y > 0.05]
    print(f"Vertices Olho Esquerdo: {len(eye_l)}, Olho Direito: {len(eye_r)}")

    # Sobrancelhas: z ~ 1.65 - 1.71, y ~ 0.05 - 0.12, |x| < 0.06
    brows = [v for v in face_verts if 1.65 <= v.co.z <= 1.71 and abs(v.co.x) < 0.06 and v.co.y > 0.05]
    print(f"Vertices Sobrancelhas: {len(brows)}")
