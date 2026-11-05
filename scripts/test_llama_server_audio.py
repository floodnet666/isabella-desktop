import urllib.request
import json
import base64

AUDIO_PATH = r"D:\isabella-desktop\assets\audio\test_user_voice.wav"
with open(AUDIO_PATH, "rb") as f:
    audio_bytes = f.read()
audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

payload = {
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Você é Isabela: 18 anos, mente aberta e safada. O usuário te perguntou algo no áudio abaixo. Responda em português com voz provocante e sedutora (sem tags de pensamento, fale direto com o usuário):"
                },
                {
                    "type": "input_audio",
                    "input_audio": {
                        "data": audio_b64,
                        "format": "wav"
                    }
                }
            ]
        }
    ],
    "max_tokens": 512,
    "temperature": 0.8
}

req = urllib.request.Request(
    "http://127.0.0.1:8080/v1/chat/completions",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)

with urllib.request.urlopen(req, timeout=40) as resp:
    data = json.loads(resp.read().decode("utf-8"))
    msg = data["choices"][0]["message"]
    print("CONTENT:\n", msg.get("content"))
