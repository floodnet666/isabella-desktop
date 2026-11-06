import time
import torch
import soundfile as sf
from omnivoice import OmniVoice
from omnivoice.models.omnivoice import VoiceClonePrompt

def main():
    print(">> Carregando OmniVoice...")
    t0 = time.time()
    model = OmniVoice.from_pretrained(
        "k2-fsa/OmniVoice",
        device_map="cuda:0",
        dtype=torch.float16,
    )
    print(f">> Modelo carregado em {(time.time() - t0):.2f}s")
    
    prompt_path = r"D:\isabella-desktop\assets\voices\isabella_omnivoice_prompt.pt"
    print(f">> Carregando prompt salvo: {prompt_path}")
    prompt = VoiceClonePrompt.load(prompt_path, map_location="cuda:0")
    
    test_phrase = "Oi amor! Estou te ouvindo perfeitamente agora."
    print(f">> Gerando áudio para: \"{test_phrase}\"")
    
    t_gen0 = time.time()
    results = model.generate(
        text=test_phrase,
        language="pt",
        voice_clone_prompt=prompt,
        speed=1.05,
    )
    gen_time = time.time() - t_gen0
    audio_np = results[0]
    audio_dur = len(audio_np) / 24000.0
    rtf = gen_time / audio_dur if audio_dur > 0 else 0
    print(f">> Resultado: {audio_dur:.2f}s de áudio gerados em {gen_time:.2f}s (RTF: {rtf:.2f}x)")

if __name__ == "__main__":
    main()
