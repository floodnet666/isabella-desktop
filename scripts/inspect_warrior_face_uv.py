import bpy
import bmesh
from mathutils import Vector

# Carregar o modelo original limpo warrior_girl_rigged.blend
blend_base = r'D:\isabella-desktop\assets\models\warrior_girl_rigged.blend'
bpy.ops.wm.open_mainfile(filepath=blend_base)

mesh_obj = bpy.data.objects.get("Mesh_0")
verts = mesh_obj.data.vertices

print("=== INSPECAO DE VERTICES DE MESH_0 ===")
print(f"Total verts: {len(verts)}")

# Pegar vértices do topo (z > 0.6) e frente (y < 0)
head_verts = [v for v in verts if v.co.z > 0.55]
print(f"Total head verts (z > 0.55): {len(head_verts)}")

min_x = min(v.co.x for v in head_verts)
max_x = max(v.co.x for v in head_verts)
min_y = min(v.co.y for v in head_verts)
max_y = max(v.co.y for v in head_verts)
min_z = min(v.co.z for v in head_verts)
max_z = max(v.co.z for v in head_verts)
print(f"Head bounds: X=[{min_x:.4f}, {max_x:.4f}], Y=[{min_y:.4f}, {max_y:.4f}], Z=[{min_z:.4f}, {max_z:.4f}]")

# Vamos encontrar os vértices mais proeminentes na frente do rosto (menor Y)
front_verts = sorted(head_verts, key=lambda v: v.co.y)[:50]
print("\nTop 10 vertices mais frontais (menor Y):")
for v in front_verts[:10]:
    print(f"Index {v.index}: co=({v.co.x:.4f}, {v.co.y:.4f}, {v.co.z:.4f})")

# Vamos inspecionar materiais e texturas do mesh_obj
print("\n=== MATERIAIS ===")
for i, m in enumerate(mesh_obj.data.materials):
    print(f"Mat {i}: {m.name}")
    if m.use_nodes:
        for node in m.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                print(f"  TexImage: {node.image.name}, size={node.image.size}, filepath={node.image.filepath}")
