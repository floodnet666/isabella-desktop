import time
import torch
import soundfile as sf
import sounddevice as sd
from omnivoice import OmniVoice
from omnivoice.models.omnivoice import VoiceClonePrompt, OmniVoiceGenerationConfig

def main():
    print(">> Carregando OmniVoice na GPU...")
    model = OmniVoice.from_pretrained(
        "k2-fsa/OmniVoice",
        device_map="cuda:0",
        dtype=torch.float16,
    )
    prompt_path = r"D:\isabella-desktop\assets\voices\isabella_omnivoice_prompt.pt"
    prompt = VoiceClonePrompt.load(prompt_path, map_location="cuda:0")
    
    test_phrase = "Oi amor! Que bom falar com você."
    
    for steps in [32, 20, 16, 12]:
        cfg = OmniVoiceGenerationConfig(num_step=steps)
        t0 = time.time()
        results = model.generate(
            text=test_phrase,
            language="pt",
            voice_clone_prompt=prompt,
            speed=1.05,
            generation_config=cfg
        )
        dt = time.time() - t0
        audio = results[0]
        dur = len(audio) / 24000.0
        out_f = f"D:\\isabella-desktop\\assets\\renders\\voice_comparison\\test_step_{steps}.wav"
        sf.write(out_f, audio, 24000)
        print(f">> Steps={steps:2d} | Tempo={dt:.2f}s | Audio={dur:.2f}s | RTF={dt/dur:.2f}x | Salvo em: test_step_{steps}.wav")

if __name__ == "__main__":
    main()
