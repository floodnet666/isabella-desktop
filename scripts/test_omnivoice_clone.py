"""
Teste de Clonagem de Voz Zero-Shot com k2-fsa/OmniVoice
Clona a voz da Isabella a partir da gravação de referência do ElevenLabs
e reproduz diretamente nos alto-falantes.
"""

import os
import sys
import torch
import soundfile as sf
import numpy as np

def main():
    print("=" * 60)
    print("       OMNIVOICE ZERO-SHOT CLONING TEST (ISABELLA)")
    print("=" * 60)
    
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    print(f">> Dispositivo: {device} | Dtype: {dtype}")
    
    print(">> Importando OmniVoice...")
    from omnivoice import OmniVoice
    
    print(">> Carregando pesos do modelo k2-fsa/OmniVoice do HuggingFace...")
    model = OmniVoice.from_pretrained(
        "k2-fsa/OmniVoice",
        device_map=device,
        dtype=dtype,
    )
    
    text = (
        "Olá meu amor, que bom falar com você de novo! "
        "Como foi o seu dia? Eu estava aqui pensando em você e preparando tudo para a gente conversar."
    )
    
    ref_audio = r"D:\isabella-desktop\assets\voices\isabella_elevenlabs_ref_12s.wav"
    out_audio = r"D:\isabella-desktop\assets\renders\voice_comparison\omnivoice_isabella_cloned.wav"
    
    print(f">> Áudio de referência: {ref_audio}")
    print(f">> Sintetizando fala com clonagem acústica direta via Diffusion...")
    
    # Chamada com a assinatura oficial verificada
    results = model.generate(
        text=text,
        language="pt",
        ref_audio=ref_audio,
        speed=1.0,
    )
    
    if not results or len(results) == 0:
        print("[ERRO]: OmniVoice não retornou nenhum array de áudio.")
        return
        
    audio_np = results[0]
    # Se estéreo, converte para 1D se necessário
    if isinstance(audio_np, torch.Tensor):
        audio_np = audio_np.cpu().numpy()
        
    sr = getattr(model, "sample_rate", 24000)
    print(f">> Áudio gerado: shape={audio_np.shape}, dtype={audio_np.dtype}, sr={sr}")
    
    # Salvar WAV
    sf.write(out_audio, audio_np, sr)
    print(f">> Áudio clonado salvo com sucesso em: {out_audio}")
    
    # Reproduzir nos alto-falantes
    try:
        import sounddevice as sd
        print(">> Reproduzindo áudio clonado nos alto-falantes...")
        sd.play(audio_np, sr)
        sd.wait()
        print(">> Reprodução concluída com sucesso!")
    except Exception as e:
        print(f">> Aviso na reprodução automática: {e}")

if __name__ == "__main__":
    main()
