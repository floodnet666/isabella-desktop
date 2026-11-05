import struct

def check_tensors(path):
    print(f"\n--- Tensors em {path} ---")
    with open(path, 'rb') as f:
        magic = f.read(4)
        version = struct.unpack('<I', f.read(4))[0]
        tensor_count = struct.unpack('<Q', f.read(8))[0]
        kv_count = struct.unpack('<Q', f.read(8))[0]
        print(f"Total Tensors: {tensor_count}, KV: {kv_count}")
        
        # Ler KV até achar general.architecture ou acabar
        # Como o header GGUF tem KV primeiro e depois os metadados dos tensores:
        # Vamos pular as KVs ou inspecionar os tipos de tensores
check_tensors(r"E:\modelos_ollama\gemma-4-E4B-it-mmproj-BF16.gguf")
