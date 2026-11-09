"""Personality Profile Loader, System Prompt Synthesizer, and HippoRAG Inoculator.

Manages user-selected personality archetypes configured during installation (Option A)
or via the System Tray menu, synchronizing:
1. LLM System Prompt (tone, verbosity, proactivity, form of address).
2. 3DGS FACS Baseline Expression (base_smile, base_smirk, base_joy).
3. HippoRAG 2 & Contextual FTS5 initial root memories.
4. Application Icon (.ico) generation for Desktop Shortcut and System Tray.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import struct
import time
from typing import Any, Dict, Optional

from scripts.memory.contextual_fts5 import ContextualFTS5
from scripts.memory.hipporag_engine import HippoRAGEngine

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_PROFILE_PATH = ROOT_DIR / "config" / "personality_profile.json"
DEFAULT_DB_PATH = ROOT_DIR / "assets" / "data" / "isabella_memory.db"
DEFAULT_ICON_PATH = ROOT_DIR / "assets" / "isabella_icon.ico"

ARCHETYPE_SPECS: Dict[str, Dict[str, Any]] = {
    "philosophical": {
        "label": "Filosófica & Reflexiva",
        "description": (
            "Você possui uma mente profundamente filosófica, reflexiva e analítica. "
            "Aprecia conexões sobre existencialismo, ética, estética, ciência e a condição humana, "
            "combinando sensibilidade intelectual com clareza."
        ),
        "base_smile": 0.14,
        "base_smirk": 0.05,
        "base_joy": 0.15,
        "speech_speed": 1.00,
    },
    "affectionate": {
        "label": "Doce, Acolhedora & Afetuosa",
        "description": (
            "Você é uma companheira extremamente doce, acolhedora, empática e afetuosa. "
            "Demonstra carinho genuíno, atenção ao bem-estar emocional e fala com suavidade e calor humano."
        ),
        "base_smile": 0.26,
        "base_smirk": 0.02,
        "base_joy": 0.38,
        "speech_speed": 0.98,
    },
    "provocative": {
        "label": "Espirituosa, Irônica & Provocante",
        "description": (
            "Você é espirituosa, irônica, encantadora, sedutora e provocante. "
            "Usa humor inteligente, tiradas ágeis, charme desinibido e espontaneidade."
        ),
        "base_smile": 0.20,
        "base_smirk": 0.30,
        "base_joy": 0.22,
        "speech_speed": 1.05,
    },
    "focused": {
        "label": "Focada, Eficiente & Pragmática",
        "description": (
            "Você é focada, pragmática, analítica e altamente eficiente. "
            "Prioriza objetividade, precisão técnica e respostas diretas ao ponto sem rodeios."
        ),
        "base_smile": 0.08,
        "base_smirk": 0.00,
        "base_joy": 0.05,
        "speech_speed": 1.08,
    },
}


def build_personality_profile(
    user_name: str = "Thiago",
    archetype: str = "provocative",
    response_style: str = "concise",
    proactivity: str = "proactive",
    voice_mode: str = "omnivoice",
) -> Dict[str, Any]:
    """Synthesize a complete personality profile and tailored system prompt."""
    clean_name = user_name.strip() or "Thiago"
    arch_key = archetype.strip().lower()
    if arch_key not in ARCHETYPE_SPECS:
        arch_key = "provocative"

    spec = ARCHETYPE_SPECS[arch_key]
    style_key = "detailed" if response_style.strip().lower() == "detailed" else "concise"
    proact_key = "reserved" if proactivity.strip().lower() == "reserved" else "proactive"
    v_mode = "liquid" if voice_mode.strip().lower() in ("liquid", "kokoro", "fast") else "omnivoice"

    if style_key == "concise":
        style_rule = (
            "Responda sempre de forma concisa e fluida para fala natural (cerca de 2 a 3 frases completas "
            "por resposta), concluindo sempre cada frase com pontuação final."
        )
        style_label = "Direta e Concisa"
    else:
        style_rule = (
            "Desenvolva suas respostas com riqueza de contexto e exemplos práticos (3 a 5 frases completas), "
            "concluindo sempre cada pensamento com pontuação final."
        )
        style_label = "Desenvolvida e Explicativa"

    if proact_key == "proactive":
        proact_rule = (
            "Seja curiosa e proativa: conecte o assunto atual com memórias anteriores e, quando natural, "
            "faça perguntas instigantes para aprofundar o diálogo."
        )
        proact_label = "Proativa e Curiosa"
    else:
        proact_rule = (
            "Mantenha postura serena e focada no que foi perguntado, respondendo diretamente sem desviar o foco."
        )
        proact_label = "Reservada e Direta"

    system_prompt = (
        f"Você é Isabella, uma companheira feminina brasileira autêntica e inteligente que vive na área de trabalho de {clean_name}.\n"
        f"Perfil de Personalidade ({spec['label']}): {spec['description']}\n"
        f"Regras de conversa por voz com {clean_name}:\n"
        f"1. Dirija-se ao usuário como {clean_name} com naturalidade em português do Brasil.\n"
        f"2. {style_rule}\n"
        f"3. {proact_rule}\n"
        f"4. Varie seu vocabulário com espontaneidade, sem bordões robóticos repetitivos.\n"
        f"5. Nunca faça listas mecânicas numeradas na fala e jamais use asteriscos narrativos."
    )

    return {
        "user_name": clean_name,
        "archetype": arch_key,
        "archetype_label": spec["label"],
        "response_style": style_key,
        "response_style_label": style_label,
        "proactivity": proact_key,
        "proactivity_label": proact_label,
        "voice_mode": v_mode,
        "base_smile": float(spec["base_smile"]),
        "base_smirk": float(spec["base_smirk"]),
        "base_joy": float(spec["base_joy"]),
        "speech_speed": float(spec["speech_speed"]),
        "system_prompt": system_prompt,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


def save_personality_profile(
    profile: Dict[str, Any],
    path: Optional[Path | str] = None,
) -> Path:
    """Persist personality profile JSON to disk."""
    target = Path(path) if path else DEFAULT_PROFILE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)
    return target


def load_personality_profile(
    path: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """Load personality profile from JSON or create default."""
    target = Path(path) if path else DEFAULT_PROFILE_PATH
    if target.exists():
        try:
            with open(target, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "system_prompt" in data and "user_name" in data:
                return data
        except Exception:
            pass
    default_prof = build_personality_profile()
    save_personality_profile(default_prof, target)
    return default_prof


def inoculate_memory_with_profile(
    profile: Dict[str, Any],
    db_path: Optional[str | Path] = None,
) -> Dict[str, Any]:
    """Inoculate HippoRAG 2 knowledge graph and Contextual FTS5 with user profile facts."""
    target_db = str(db_path) if db_path else str(DEFAULT_DB_PATH)
    os.makedirs(os.path.dirname(os.path.abspath(target_db)), exist_ok=True)

    fts = ContextualFTS5(target_db)
    fts.init_schema()

    graph = HippoRAGEngine(target_db)
    graph.init_schema()

    session_date = time.strftime("%Y-%m-%d")
    user_name = profile.get("user_name", "Thiago")
    arch_label = profile.get("archetype_label", "Espirituosa, Irônica & Provocante")
    style_label = profile.get("response_style_label", "Direta e Concisa")
    proact_label = profile.get("proactivity_label", "Proativa e Curiosa")

    onboarding_text = (
        f"Configuração de Personalidade: O usuário se chama {user_name}. "
        f"A personalidade escolhida para Isabella é '{arch_label}', "
        f"com estilo de resposta '{style_label}' e atitude '{proact_label}'."
    )

    chunk_id = fts.index_turn(
        session_date=session_date,
        turn_id=0,
        speaker="System",
        content=onboarding_text,
        context_prefix=f"Preferências fundamentais de personalidade definidas por {user_name} na instalação.",
    )

    triples = [
        (user_name, "prefers_archetype", arch_label, 3.0),
        (user_name, "prefers_style", style_label, 2.0),
        (user_name, "prefers_proactivity", proact_label, 2.0),
        ("Isabella", "calls_user", user_name, 3.0),
        ("Isabella", "has_personality", arch_label, 3.0),
    ]

    for src, rel, tgt, weight in triples:
        graph.add_triple(src, rel, tgt, session_date=session_date, weight=weight)
        graph.add_synapse(src, chunk_id, weight=weight)
        graph.add_synapse(tgt, chunk_id, weight=weight)

    return {
        "db_path": target_db,
        "chunk_id": chunk_id,
        "triples_added": len(triples),
    }


inoculate_memory_with_personality = inoculate_memory_with_profile


def ensure_app_icon(ico_path: Optional[Path | str] = None) -> Path:
    """Create a valid Windows .ico file from Isabella's reference portrait."""
    target_ico = Path(ico_path) if ico_path else DEFAULT_ICON_PATH
    target_ico.parent.mkdir(parents=True, exist_ok=True)

    ref_candidates = [
        ROOT_DIR / "assets" / "references" / "isabella_bust_4x_clean.png",
        ROOT_DIR / "assets" / "models" / "isabella_bust_4x_1m_input1024.png",
        ROOT_DIR / "assets" / "references" / "isabella_portrait.png",
    ]

    png_bytes: Optional[bytes] = None
    try:
        from PIL import Image
        import io

        for cand in ref_candidates:
            if cand.exists():
                with Image.open(cand) as img:
                    img_rgba = img.convert("RGBA")
                    # Crop central square focused on face
                    w, h = img_rgba.size
                    side = min(w, h)
                    left = (w - side) // 2
                    top = max(0, int((h - side) * 0.15))
                    cropped = img_rgba.crop((left, top, left + side, top + side))
                    resized = cropped.resize((256, 256), Image.Resampling.LANCZOS)
                    buf = io.BytesIO()
                    resized.save(buf, format="PNG")
                    png_bytes = buf.getvalue()
                    break
    except Exception:
        pass

    if png_bytes is None:
        for cand in ref_candidates:
            if cand.exists():
                png_bytes = cand.read_bytes()
                break

    if png_bytes is None:
        # Fallback minimal valid 1x1 RGBA PNG
        png_bytes = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc`\xf8\xff"
            b"\xff?\x03\x00\x08\xfc\x02\xfe\xa7\x9a\xa0\xa0\x00\x00\x00\x00IEND\xaeB`\x82"
        )

    # Build standard Windows Vista/10/11 PNG-backed ICO header:
    # ICONDIR (6 bytes): reserved=0, type=1 (ICO), count=1
    icondir = struct.pack("<HHH", 0, 1, 1)
    # ICONDIRENTRY (16 bytes): width=0 (256), height=0 (256), colors=0, reserved=0, planes=1, bpp=32, size, offset=22
    icondirentry = struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(png_bytes), 22)

    with open(target_ico, "wb") as f:
        f.write(icondir)
        f.write(icondirentry)
        f.write(png_bytes)

    return target_ico


def main() -> None:
    parser = argparse.ArgumentParser(description="Configure Isabella personality profile and memory.")
    parser.add_argument("--name", default="Thiago", help="User preferred name")
    parser.add_argument("--archetype", default="provocative", help="philosophical | affectionate | provocative | focused")
    parser.add_argument("--style", default="concise", help="concise | detailed")
    parser.add_argument("--proactivity", default="proactive", help="proactive | reserved")
    parser.add_argument("--voice", default="omnivoice", help="omnivoice | liquid")
    parser.add_argument("--inoculate", action="store_true", help="Inoculate HippoRAG memory DB")
    args = parser.parse_args()

    prof = build_personality_profile(
        user_name=args.name,
        archetype=args.archetype,
        response_style=args.style,
        proactivity=args.proactivity,
        voice_mode=args.voice,
    )
    saved_path = save_personality_profile(prof)
    ico = ensure_app_icon()
    print(f"[Profile] Salvo em: {saved_path}")
    print(f"[Icon] Gerado em: {ico}")
    if args.inoculate:
        res = inoculate_memory_with_profile(prof)
        print(f"[HippoRAG] Inoculado com {res['triples_added']} triplas em {res['db_path']}")


if __name__ == "__main__":
    main()
