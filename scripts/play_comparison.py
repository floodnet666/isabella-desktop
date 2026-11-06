"""
Script Interativo de Audição Comparativa de Vozes (Isabella Desktop)
Permite ao usuário ouvir no alto-falante cada uma das abordagens geradas:
1. Áudio de Referência Original (ElevenLabs)
2. Voz Base Pura do LFM3 (Female Raw)
3. Opção 1: Casamento Espectral LTAS + Formantes DSP
4. Opção 2: Alinhamento Neural de Pitch (228.9 Hz) + Warping de Trato Vocal
5. Opção 2 (Bônus): Síntese Neural Kokoro PT-BR
"""

import os
import sys
import time
import soundfile as sf
import sounddevice as sd

FILES = {
    "1": ("Referência Original (ElevenLabs)", r"D:\isabella-desktop\assets\voices\isabella_elevenlabs_ref.wav"),
    "2": ("LFM3 Base Pura (Female Raw)", r"D:\isabella-desktop\assets\renders\voice_comparison\lfm3_base_raw.wav"),
    "3": ("Opção 1: Casamento Espectral DSP (LTAS)", r"D:\isabella-desktop\assets\renders\voice_comparison\option1_dsp_spectral_matched.wav"),
    "4": ("Opção 2: Alinhamento Neural F0 (228.9 Hz) + Formantes", r"D:\isabella-desktop\assets\renders\voice_comparison\option2_neural_pitch_formant_morph.wav"),
    "5": ("Opção 2 (Extra): Síntese Neural Kokoro PT-BR", r"D:\isabella-desktop\assets\renders\voice_comparison\option2_kokoro_isabella_neural.wav"),
}

def play_audio(name: str, path: str):
    if not os.path.exists(path):
        print(f"\n[ERRO]: Arquivo não encontrado: {path}")
        return
    print(f"\n>> REPRODUZINDO: {name}")
    print(f"   Caminho: {path}")
    data, sr = sf.read(path)
    # Se for estéreo, reproduz estéreo; se mono, mono
    sd.play(data, sr)
    sd.wait()
    print(">> Reprodução finalizada.\n")

def main():
    if len(sys.argv) > 1:
        choice = sys.argv[1].strip()
        if choice in FILES:
            name, path = FILES[choice]
            play_audio(name, path)
            return
        elif choice == "all":
            for k in sorted(FILES.keys()):
                name, path = FILES[k]
                play_audio(name, path)
                time.sleep(1.0)
            return

    while True:
        print("="*60)
        print("    ISABELLA DESKTOP — AUDIÇÃO COMPARATIVA DE VOZES")
        print("="*60)
        for k in sorted(FILES.keys()):
            name, path = FILES[k]
            exists = "[OK]" if os.path.exists(path) else "[FALTA]"
            print(f" [{k}] {name} {exists}")
        print(" [A] Ouvir todas sequencialmente")
        print(" [S] Sair")
        print("="*60)
        
        c = input("Escolha uma opção (1-5, A, S): ").strip().upper()
        if c == 'S':
            break
        elif c == 'A':
            for k in sorted(FILES.keys()):
                name, path = FILES[k]
                play_audio(name, path)
                time.sleep(1.0)
        elif c in FILES:
            name, path = FILES[c]
            play_audio(name, path)
        else:
            print("Opção inválida.")

if __name__ == "__main__":
    main()
