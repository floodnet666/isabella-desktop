import sys
import os
import site
import bpy

# Adicionar site-packages do usuário para módulos como opencc
user_site = site.getusersitepackages()
if user_site not in sys.path:
    sys.path.append(user_site)

# Adicionar mmd_tools ao sys.path
mmd_tools_dir = r"D:\isabella-desktop\tools\blender_mmd_tools"
if mmd_tools_dir not in sys.path:
    sys.path.insert(0, mmd_tools_dir)

import mmd_tools
mmd_tools.register()

print("mmd_tools registrado com sucesso!")
print("Operadores mmd:", [x for x in dir(bpy.ops.mmd_tools)])

# Limpar cena
bpy.ops.wm.read_homefile(use_empty=True)

# Importar miku_v2.pmd
pmd_path = r"D:\isabella-desktop\benchmarks_avatars\mmd\miku_v2.pmd"
bpy.ops.mmd_tools.import_model(filepath=pmd_path)

print("Objetos na cena apos importacao MMD:")
for obj in bpy.data.objects:
    print(f" - {obj.name} (tipo: {obj.type})")
    if obj.data and hasattr(obj.data, 'shape_keys') and obj.data.shape_keys:
        print(f"   Shape keys ({len(obj.data.shape_keys.key_blocks)}): {[kb.name for kb in obj.data.shape_keys.key_blocks[:10]]}...")
