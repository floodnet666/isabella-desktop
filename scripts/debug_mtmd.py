import subprocess

cmd = [
    r"D:\isabella-desktop\tools\llama-cpp\llama-mtmd-cli.exe",
    "-m", r"E:\modelos_ollama\gemma-4-E4B-it-ultra-uncensored-heretic-Q4_K_M.gguf",
    "--mmproj", r"E:\modelos_ollama\gemma-4-E4B-it-mmproj-BF16.gguf",
    "-p", "Diga oi",
    "-v"
]

proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="replace")
stdout, stderr = proc.communicate(timeout=30)
print("Returncode:", proc.returncode)
print("STDERR:\n", stderr)
print("STDOUT:\n", stdout)
