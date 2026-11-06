"""
Motor DSP de Casamento Espectral e Morfologia de Formantes (Opção 1)
Adapta o timbre e a resposta de frequência da voz base (LFM3) para a identidade
acústica da gravação de referência (ElevenLabs) via análise LTAS e filtro FIR/IIR suave.
"""

import os
import sys
import numpy as np
import soundfile as sf
import scipy.signal as signal
from scipy.ndimage import gaussian_filter1d

def compute_spectral_envelope(audio: np.ndarray, sr: int, n_fft: int = 2048, hop_length: int = 512) -> np.ndarray:
    """Extrai o envelope espectral médio de longo prazo (LTAS) usando liftering cepstral."""
    # Filtro de pré-ênfase
    audio = np.append(audio[0], audio[1:] - 0.95 * audio[:-1])
    
    # STFT
    window = np.hanning(n_fft)
    n_frames = 1 + (len(audio) - n_fft) // hop_length
    if n_frames <= 0:
        return np.ones(n_fft // 2 + 1)
        
    specs = []
    for i in range(n_frames):
        chunk = audio[i * hop_length : i * hop_length + n_fft] * window
        # Magnitude spectrum
        mag = np.abs(np.fft.rfft(chunk))
        # Somente frames com energia vocal
        if np.mean(mag) > 1e-4:
            specs.append(mag)
            
    if not specs:
        return np.ones(n_fft // 2 + 1)
        
    avg_spec = np.mean(specs, axis=0)
    
    # Cepstral liftering para obter o envelope suave do trato vocal (removendo harmônicos F0)
    log_spec = np.log(np.maximum(avg_spec, 1e-7))
    cepstrum = np.fft.irfft(log_spec)
    
    # Manter apenas coeficientes baixos (quefrequências baixas = envelope do trato vocal)
    cutoff = int(n_fft / 32) # ~64 coeficientes
    lifter = np.zeros_like(cepstrum)
    lifter[:cutoff] = 1.0
    lifter[-cutoff:] = 1.0
    
    smoothed_log = np.fft.rfft(cepstrum * lifter).real
    envelope = np.exp(smoothed_log)
    # Suavização gaussiana adicional para transições hiper-orgânicas
    return gaussian_filter1d(envelope, sigma=4.0)

def match_spectral_profile(src_audio: np.ndarray, ref_audio: np.ndarray, sr: int) -> np.ndarray:
    """Calcula a curva de transferência espectral H(f) e filtra o áudio de entrada."""
    n_fft = 2048
    src_env = compute_spectral_envelope(src_audio, sr, n_fft=n_fft)
    ref_env = compute_spectral_envelope(ref_audio, sr, n_fft=n_fft)
    
    # Ganho de transferência H(f) = Ref(f) / Src(f)
    transfer = ref_env / np.maximum(src_env, 1e-6)
    
    # Normalização de energia média
    transfer /= np.mean(transfer)
    
    # Limitação de ganho dinâmico (-12dB a +12dB) para evitar ressonâncias estridentes
    transfer = np.clip(transfer, 0.25, 4.0)
    # Suavização da curva de EQ
    transfer = gaussian_filter1d(transfer, sigma=6.0)
    
    # Converte ganho de frequência em resposta ao impulso FIR via IFFT simétrica
    full_spec = np.concatenate([transfer, transfer[-2:0:-1]])
    fir_coeffs = np.fft.ifft(full_spec).real
    fir_coeffs = np.fft.fftshift(fir_coeffs)
    
    # Janelamento Hanning no filtro FIR (tamanho 513)
    fir_len = 513
    center = len(fir_coeffs) // 2
    fir = fir_coeffs[center - fir_len//2 : center + fir_len//2 + 1] * np.hanning(fir_len)
    fir /= np.sum(fir) # Ganho unitário em DC
    
    # Aplica convolução linear com compensação de fase
    filtered = signal.filtfilt(fir, [1.0], src_audio)
    
    # Saturação aveludada analógica suave (harmônicos quentes de 2ª ordem)
    saturated = filtered + 0.08 * (filtered ** 2) - 0.04 * (filtered ** 3)
    
    # Normalização de pico para -1.0 dBFS
    max_val = np.max(np.abs(saturated))
    if max_val > 0:
        saturated = saturated / max_val * 0.89
        
    return saturated.astype(np.float32)

def main():
    base_path = r"D:\isabella-desktop\assets\renders\voice_comparison\lfm3_base_raw.wav"
    ref_path = r"D:\isabella-desktop\assets\voices\isabella_elevenlabs_ref.wav"
    out_path = r"D:\isabella-desktop\assets\renders\voice_comparison\option1_dsp_spectral_matched.wav"
    
    print("[1/3] Carregando áudios...")
    src, sr1 = sf.read(base_path)
    ref, sr2 = sf.read(ref_path)
    
    if sr1 != sr2:
        print(f"Ajustando sample rate: {sr1} vs {sr2}")
        import librosa
        ref = librosa.resample(ref, orig_sr=sr2, target_sr=sr1)
        sr = sr1
    else:
        sr = sr1
        
    print("[2/3] Calculando casamento de envelopes espectrais LTAS e formantes...")
    matched = match_spectral_profile(src, ref, sr)
    
    print(f"[3/3] Salvando áudio processado em: {out_path}")
    sf.write(out_path, matched, sr)
    print("Processamento concluído com sucesso!")

if __name__ == "__main__":
    main()
