"""Unit and integration tests for Personality Profile, HippoRAG Inoculation, and Installer (TDD).

Tests coverage:
1. Personality profile creation, archetypes, and system prompt generation.
2. HippoRAG & Contextual FTS5 inoculation from personality profile.
3. Icon generation (assets/isabella_icon.ico).
4. Native Rust IsabellaSetup.exe headless execution and Desktop shortcut (.lnk) verification.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(r"D:\isabella-desktop")


class TestPersonalityAndInstaller(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="isabella_persona_test_"))
        self.db_path = self.temp_dir / "test_persona_memory.db"
        self.profile_path = self.temp_dir / "personality_profile.json"

    def tearDown(self):
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_personality_loader_and_archetypes(self):
        from scripts.memory.personality_loader import (
            build_personality_profile,
            load_personality_profile,
            save_personality_profile,
        )

        profile = build_personality_profile(
            user_name="Thiago",
            archetype="philosophical",
            response_style="concise",
            proactivity="proactive",
            voice_mode="omnivoice",
        )
        self.assertEqual(profile["user_name"], "Thiago")
        self.assertEqual(profile["archetype"], "philosophical")
        self.assertIn("Thiago", profile["system_prompt"])
        self.assertIn("filosófica", profile["system_prompt"].lower())
        self.assertTrue(0.0 <= profile["base_smile"] <= 0.5)

        save_personality_profile(profile, self.profile_path)
        loaded = load_personality_profile(self.profile_path)
        self.assertEqual(loaded["user_name"], "Thiago")
        self.assertEqual(loaded["archetype"], "philosophical")

    def test_hipporag_personality_inoculation(self):
        from scripts.memory.personality_loader import (
            build_personality_profile,
            inoculate_memory_with_profile,
        )
        from scripts.memory.hipporag_engine import HippoRAGEngine
        from scripts.memory.contextual_fts5 import ContextualFTS5

        profile = build_personality_profile(
            user_name="Thiago",
            archetype="provocative",
            response_style="concise",
            proactivity="proactive",
            voice_mode="omnivoice",
        )

        result = inoculate_memory_with_profile(profile, str(self.db_path))
        self.assertTrue(result["triples_added"] >= 3)

        graph = HippoRAGEngine(str(self.db_path))
        ppr = graph.personalized_pagerank(["Thiago", "prefers_archetype"], top_k=5)
        entities = [n["entity"] for n in ppr]
        self.assertTrue(any("Provocante" in e or "Thiago" in e for e in entities))

        fts = ContextualFTS5(str(self.db_path))
        matches = fts.search("Thiago personalidade", limit=3)
        self.assertTrue(len(matches) >= 1)

    def test_icon_generation_valid_ico(self):
        from scripts.memory.personality_loader import ensure_app_icon

        ico_path = self.temp_dir / "test_icon.ico"
        generated = ensure_app_icon(ico_path)
        self.assertTrue(generated.exists())
        self.assertGreater(generated.stat().st_size, 1024)
        # Check ICO magic header: 00 00 01 00
        with open(generated, "rb") as f:
            header = f.read(4)
        self.assertEqual(header, b"\x00\x00\x01\x00")

    def test_native_rust_setup_exe_and_desktop_shortcut(self):
        root = Path(__file__).resolve().parent.parent
        setup_exe = root / "isabella-core" / "target" / "release" / "IsabellaSetup.exe"
        core_exe = root / "isabella-core" / "target" / "release" / "isabella-core.exe"
        if not setup_exe.exists() or not core_exe.exists():
            self.skipTest("Rust release binaries not pre-built in this environment")

        res = subprocess.run(
            [
                str(setup_exe),
                "--headless",
                "--user-name",
                "Thiago",
                "--archetype",
                "witty",
                "--style",
                "concise",
                "--proactivity",
                "proactive",
                "--voice",
                "omnivoice",
            ],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(res.returncode, 0, msg=res.stderr)

        root_setup = root / "IsabellaSetup.exe"
        self.assertTrue(root_setup.exists())

        # Verify Desktop shortcut points directly to isabella-core.exe (no .bat terminal)
        ps_check = (
            "$ws = New-Object -ComObject WScript.Shell; "
            "$desk = [Environment]::GetFolderPath('Desktop'); "
            "$lnk = $ws.CreateShortcut((Join-Path $desk 'Isabella Companion.lnk')); "
            "Write-Output $lnk.TargetPath"
        )
        lnk_out = subprocess.check_output(
            ["powershell.exe", "-NoProfile", "-Command", ps_check],
            text=True,
        ).strip()
        self.assertTrue(
            lnk_out.lower().endswith("isabella-core.exe"),
            f"Expected shortcut TargetPath to end with isabella-core.exe, got: {lnk_out}",
        )


if __name__ == "__main__":
    unittest.main()
