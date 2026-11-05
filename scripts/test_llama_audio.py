import subprocess
import time
import sys

EXE = r"D:\isabella-desktop\tools\llama-cpp\llama-mtmd-cli.exe"
MODEL = r"E:\modelos_ollama\gemma-4-E4B-it-ultra-uncensored-heretic-Q4_K_M.gguf"
MMPROJ = r"E:\modelos_ollama\gemma-4-E4B-it-mmproj-BF16.gguf"
AUDIO = r"D:\isabella-desktop\assets\audio\test_user_voice.wav"

cmd = [
    EXE,
    "-m", MODEL,
    "--mmproj", MMPROJ,
    "--audio", AUDIO,
    "-p", "<bos><|turn>user\nO que você ouviu no áudio? Responda em português:<turn|>\n<|turn>model\n",
    "-ngl", "24",
    "-c", "4096",
    "-n", "128",
    "--temp", "0.7"
]

print("Executando llama-mtmd-cli com áudio direto (SEM WHISPER)...")
t0 = time.time()
proc = subprocess.Popen(
    cmd,
    stdin=subprocess.DEVNULL,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    encoding="utf-8",
    errors="replace"
)

stdout, stderr = proc.communicate(timeout=60)
elapsed = time.time() - t0

print(f"\nConcluído em {elapsed:.2f}s (Exit code: {proc.returncode})")
print("\n--- STDOUT ---")
print(stdout)
if stderr:
    print("\n--- STDERR (últimas 10 linhas) ---")
    print("\n".join(stderr.strip().splitlines()[-10:]))
