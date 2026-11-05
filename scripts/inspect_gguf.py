import struct

def inspect_gguf(path):
    print(f"\n--- Inspecionando {path} ---")
    with open(path, 'rb') as f:
        magic = f.read(4)
        if magic != b'GGUF':
            print("Não é GGUF!")
            return
        version = struct.unpack('<I', f.read(4))[0]
        tensor_count = struct.unpack('<Q', f.read(8))[0]
        kv_count = struct.unpack('<Q', f.read(8))[0]
        print(f"GGUF v{version}, Tensors: {tensor_count}, KV Metadata: {kv_count}")
        
        # Ler algumas KVs
        for i in range(min(kv_count, 30)):
            key_len = struct.unpack('<Q', f.read(8))[0]
            key = f.read(key_len).decode('utf-8', errors='replace')
            val_type = struct.unpack('<I', f.read(4))[0]
            
            # GGUF_TYPE_STRING = 8
            if val_type == 8:
                str_len = struct.unpack('<Q', f.read(8))[0]
                val = f.read(str_len).decode('utf-8', errors='replace')
                print(f"  {key} = '{val}'")
            elif val_type in (0, 1, 2, 3, 4, 5, 6, 7): # uint8..int64, float32, bool
                size = [1, 1, 2, 2, 4, 4, 8, 8, 0, 4, 8, 1][val_type]
                raw = f.read(size)
                print(f"  {key} (type {val_type})")
            elif val_type == 9: # Array
                arr_type = struct.unpack('<I', f.read(4))[0]
                arr_len = struct.unpack('<Q', f.read(8))[0]
                print(f"  {key} (Array of type {arr_type}, len {arr_len})")
                # pular ou parar
                break
            else:
                print(f"  {key} (val_type {val_type})")
                break

inspect_gguf(r"D:\isabella-desktop\assets\models\llm_multimodal\gemma-4-E4B-it-mmproj-BF16.gguf")
inspect_gguf(r"D:\isabella-desktop\assets\models\llm_multimodal\gemma-4-E4B-it-ultra-uncensored-heretic-Q4_K_M.gguf")
