import os
import torch
from omnivoice import OmniVoice

def main():
    print(">> Carregando OmniVoice...")
    model = OmniVoice.from_pretrained(
        "k2-fsa/OmniVoice",
        device_map="cuda:0",
        dtype=torch.float16,
    )
    
    ref_audio = r"D:\isabella-desktop\assets\voices\isabella_elevenlabs_ref_12s.wav"
    out_prompt = r"D:\isabella-desktop\assets\voices\isabella_omnivoice_prompt.pt"
    
    print(f">> Criando prompt a partir de: {ref_audio}")
    prompt = model.create_voice_clone_prompt(ref_audio=ref_audio)
    
    print(f">> Texto transcrito da referência: \"{prompt.ref_text}\"")
    print(f">> RMS da referência: {prompt.ref_rms}")
    print(f">> Tokens de áudio: shape={prompt.ref_audio_tokens.shape}")
    
    prompt.save(out_prompt)
    print(f">> VoiceClonePrompt salvo com sucesso em: {out_prompt}")

if __name__ == "__main__":
    main()
