"""
Teste de Integração de 1 Turno Conversacional Completo com OmniVoice
Verifica:
1. Conexão com llama-server (porta 8080).
2. Carregamento do OmniVoice e do prompt da Isabella.
3. Geração do raciocínio conversacional pelo LLM.
4. Síntese neural de fala com a voz clonada do ElevenLabs via OmniVoice.
5. Extração de visemes FFT e envio de pacotes UDP (127.0.0.1:9888).
6. Reprodução do áudio clonado no alto-falante.
"""

import os
import sys
import time

sys.path.insert(0, r"D:\isabella-desktop")
sys.path.insert(0, r"D:\isabella-desktop\scripts")

import requests
import soundfile as sf
import sounddevice as sd
import torch
import numpy as np

from voice_bridge_omnivoice import (
    ensure_llama_server,
    init_omnivoice,
    think_and_respond,
    speak_with_interruption_and_visemes,
    clean_text_for_speech,
    split_into_thought_chunks
)
import queue

def main():
    print("=" * 65)
    print("  TESTE DE CONVERSA EM TEMPO REAL: ISABELLA + OMNIVOICE CLONE")
    print("=" * 65)
    
    # 1. Servidor
    print("\n>> 1. Verificando llama-server na porta 8080...")
    if not ensure_llama_server():
        print("[ERRO]: Não foi possível conectar ao llama-server.")
        return
    print(">> llama-server online!")
    
    # 2. Inicializar OmniVoice
    print("\n>> 2. Carregando OmniVoice na GPU...")
    init_omnivoice()
    
    # 3. Simular entrada do usuário
    user_prompt = "Oi Isabella! Como você está se sentindo hoje com essa sua nova voz?"
    print(f"\n>> 3. Entrada do Usuário: \"{user_prompt}\"")
    
    # 4. Geração do LLM
    print("\n>> 4. Gerando resposta com o modelo de linguagem...")
    t0 = time.time()
    reply = think_and_respond(user_prompt)
    print(f">> Resposta ({time.time() - t0:.2f}s): \"{reply}\"")
    
    if not reply:
        print("[ERRO]: Nenhuma resposta gerada pelo LLM.")
        return
        
    # 5. Síntese e reprodução com OmniVoice + Visemes UDP
    print("\n>> 5. Sintetizando com OmniVoice e reproduzindo nos alto-falantes com visemes 3D...")
    q = queue.Queue()
    speak_with_interruption_and_visemes(reply, q, threshold=0.005)
    
    print("\n>> Teste conversacional de 1 turno concluído com sucesso!")

if __name__ == "__main__":
    main()
