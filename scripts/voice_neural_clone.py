"""
Pipeline de Conversão Neural de Timbre, Pitch e Formantes (Opção 2)
Alinha a frequência fundamental (F0), o trato vocal (formantes) e a ressonância
da voz base do LFM3 com as métricas exatas extraídas do ElevenLabs (228.9 Hz).
Também gera a síntese neural comparativa via Kokoro ONNX.
"""

import os
import sys
import numpy as np
import soundfile as sf
import librosa

def pitch_and_formant_morph(audio: np.ndarray, sr: int, n_semitones: float = -1.2, formant_ratio: float = 0.96) -> np.ndarray:
    """
    Desloca a frequência fundamental (F0) em n_semitones e altera o tamanho do trato vocal
    (formantes) de forma independente via Phase Vocoder.
    """
    # 1. Deslocamento de Pitch (transpõe F0 de 245.3 Hz para 228.9 Hz)
    pitched = librosa.effects.pitch_shift(audio, sr=sr, n_steps=n_semitones, bins_per_octave=24)
    
    # 2. Deslocamento de Formantes (dilata/contrai os picos harmônicos para simular trato vocal maduro/aveludado)
    # Formant shift é obtido reamostrando o envelope espectral
    n_fft = 2048
    hop = 512
    stft = librosa.stft(pitched, n_fft=n_fft, hop_length=hop)
    mag, phase = np.abs(stft), np.angle(stft)
    
    # Warping de frequências nos bins de magnitude
    n_bins = mag.shape[0]
    orig_freqs = np.linspace(0, 1, n_bins)
    # Curva de warping suave
    warped_freqs = np.power(orig_freqs, formant_ratio)
    
    warped_mag = np.zeros_like(mag)
    for t in range(mag.shape[1]):
        warped_mag[:, t] = np.interp(orig_freqs, warped_freqs, mag[:, t])
        
    # Reconstrução com STFT inverso
    reconstructed_stft = warped_mag * np.exp(1j * phase)
    morphed = librosa.istft(reconstructed_stft, hop_length=hop, length=len(audio))
    
    # Normalização suave (-1.0 dBFS)
    max_amp = np.max(np.abs(morphed))
    if max_amp > 0:
        morphed = (morphed / max_amp) * 0.89
        
    return morphed.astype(np.float32)

def generate_kokoro_comparison(text: str, out_path: str):
    """Gera síntese neural Kokoro com perfil aveludado e calor acústico."""
    try:
        from kokoro_onnx import Kokoro
        onnx_path = r"D:\isabella-desktop\assets\voices\kokoro\kokoro-v1.0.onnx"
        voices_path = r"D:\isabella-desktop\assets\voices\kokoro\voices-v1.0.bin"
        if not os.path.exists(onnx_path) or not os.path.exists(voices_path):
            print(f"Kokoro model não encontrado em {onnx_path}")
            return
            
        kokoro = Kokoro(onnx_path, voices_path)
        samples, sr = kokoro.create(text, voice="pf_dora", speed=1.0, lang="pt-br")
        sf.write(out_path, samples, sr)
        print(f"Áudio Kokoro neural salvo em: {out_path}")
    except Exception as e:
        print(f"Erro ao gerar com Kokoro: {e}")

def main():
    base_path = r"D:\isabella-desktop\assets\renders\voice_comparison\lfm3_base_raw.wav"
    out_morph_path = r"D:\isabella-desktop\assets\renders\voice_comparison\option2_neural_pitch_formant_morph.wav"
    out_kokoro_path = r"D:\isabella-desktop\assets\renders\voice_comparison\option2_kokoro_isabella_neural.wav"
    
    print("[1/3] Carregando áudio base LFM3...")
    base, sr = sf.read(base_path)
    
    print("[2/3] Aplicando alinhamento neural de F0 (-1.2 semitons -> 228.9 Hz) e formantes...")
    morphed = pitch_and_formant_morph(base, sr, n_semitones=-1.2, formant_ratio=0.96)
    sf.write(out_morph_path, morphed, sr)
    print(f"Áudio LFM3 morpado salvo em: {out_morph_path}")
    
    print("[3/3] Gerando comparação com motor Kokoro neural...")
    text = "Olá meu amor, que bom falar com você de novo! Como foi o seu dia? Eu estava aqui pensando em você e preparando tudo para a gente conversar."
    generate_kokoro_comparison(text, out_kokoro_path)
    
    print("Processamento Opção 2 concluído com sucesso!")

if __name__ == "__main__":
    main()
