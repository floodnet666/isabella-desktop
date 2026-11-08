import time
import torch
from omnivoice import OmniVoice
from omnivoice.models.omnivoice import VoiceClonePrompt, OmniVoiceGenerationConfig

def main():
    print(">> Testando OmniVoice na CPU com num_step reduzido...")
    model = OmniVoice.from_pretrained(
        "k2-fsa/OmniVoice",
        device_map="cpu",
        dtype=torch.float32,
    )
    prompt_path = r"D:\isabella-desktop\assets\voices\isabella_omnivoice_prompt.pt"
    prompt = VoiceClonePrompt.load(prompt_path, map_location="cpu")
    
    cfg = OmniVoiceGenerationConfig(num_step=8)
    
    t0 = time.time()
    results = model.generate(
        text="Olá meu amor!",
        language="pt",
        voice_clone_prompt=prompt,
        generation_config=cfg
    )
    dt = time.time() - t0
    audio_dur = len(results[0]) / 24000.0
    print(f">> CPU (num_step=8): {audio_dur:.2f}s de áudio em {dt:.2f}s (RTF: {dt/audio_dur:.2f}x)")

if __name__ == "__main__":
    main()
