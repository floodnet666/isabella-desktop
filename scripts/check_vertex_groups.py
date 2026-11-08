import bpy

blend_base = r'D:\isabella-desktop\assets\models\warrior_girl_rigged.blend'
bpy.ops.wm.open_mainfile(filepath=blend_base)

mesh_obj = bpy.data.objects.get("Mesh_0")
print("=== MODIFIERS ===")
for m in mesh_obj.modifiers:
    print(f"Mod: {m.name}, Tipo: {m.type}")

print("\n=== VERTEX GROUPS ===")
for vg in mesh_obj.vertex_groups:
    print(f"VG: {vg.name}")

# Checar se os vértices da cabeça têm peso no grupo 'head'
vg_head = mesh_obj.vertex_groups.get("head") or mesh_obj.vertex_groups.get("Head")
if vg_head:
    print(f"Grupo head encontrado: {vg_head.name}")
    # Pegar 5 vértices da cabeça
    for v in mesh_obj.data.vertices:
        if v.co.z > 0.70:
            for g in v.groups:
                if g.group == vg_head.index:
                    print(f"Vert {v.index} (z={v.co.z:.3f}): peso head = {g.weight:.3f}")
            break
else:
    print("NENHUM grupo de vértice head encontrado!")
