import struct
import sys

sys.stdout.reconfigure(encoding='utf-8')


pmd_path = r"D:\isabella-desktop\benchmarks_avatars\mmd\miku_v2.pmd"

with open(pmd_path, "rb") as f:
    magic = f.read(3)
    version = struct.unpack("<f", f.read(4))[0]
    name = f.read(20).split(b'\x00')[0].decode('shift_jis', errors='ignore')
    comment = f.read(256).split(b'\x00')[0].decode('shift_jis', errors='ignore')
    
    print(f"PMD Magic: {magic}, Version: {version}, Name: {name}")
    print(f"Comment: {comment[:60]}...")
    
    # Vertices
    num_verts = struct.unpack("<I", f.read(4))[0]
    print(f"Vertices: {num_verts}")
    # Pular vertices (38 bytes cada)
    f.seek(num_verts * 38, 1)
    
    # Faces
    num_indices = struct.unpack("<I", f.read(4))[0]
    print(f"Indices: {num_indices} (Triangulos: {num_indices // 3})")
    f.seek(num_indices * 2, 1)
    
    # Materials
    num_mats = struct.unpack("<I", f.read(4))[0]
    print(f"Materials: {num_mats}")
    f.seek(num_mats * 70, 1)
    
    # Bones
    num_bones = struct.unpack("<H", f.read(2))[0]
    print(f"Bones: {num_bones}")
    f.seek(num_bones * 39, 1)
    
    # IK
    num_ik = struct.unpack("<H", f.read(2))[0]
    print(f"IK: {num_ik}")
    for _ in range(num_ik):
        f.seek(2 + 2, 1) # bone_idx, target_idx
        chain_len = struct.unpack("<B", f.read(1))[0]
        f.seek(2 + 4, 1) # iterations, weight
        f.seek(chain_len * 2, 1) # child bones
        
    # Morphs (Expressões faciais)
    num_morphs = struct.unpack("<H", f.read(2))[0]
    print(f"Morphs (Blendshapes): {num_morphs}")
    for i in range(num_morphs):
        m_name = f.read(20).split(b'\x00')[0].decode('shift_jis', errors='ignore')
        m_verts = struct.unpack("<I", f.read(4))[0]
        m_type = struct.unpack("<B", f.read(1))[0]
        print(f"  Morph {i}: '{m_name}' (Tipo: {m_type}, Verts: {m_verts})")
        f.seek(m_verts * (4 + 12), 1)
