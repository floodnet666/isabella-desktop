use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct PersonalityProfile {
    pub user_name: String,
    pub archetype_id: String,
    pub archetype_label: String,
    pub response_style: String,
    pub proactivity: String,
    pub base_smile: f32,
    pub base_smirk: f32,
    pub base_emotion: String,
    pub speech_speed: f32,
    pub voice_engine: String,
    pub system_prompt: String,
}

impl Default for PersonalityProfile {
    fn default() -> Self {
        Self::from_questionnaire("Tiago", "sweet", "concise", "proactive", "omnivoice")
    }
}

impl PersonalityProfile {
    pub fn from_questionnaire(
        user_name: &str,
        archetype_id: &str,
        response_style: &str,
        proactivity: &str,
        voice_engine: &str,
    ) -> Self {
        let clean_name = if user_name.trim().is_empty() {
            "Tiago".to_string()
        } else {
            user_name.trim().to_string()
        };

        let (label, base_smile, base_smirk, base_emotion, speech_speed, arch_prompt) =
            match archetype_id {
                "philosophical" => (
                    "Filosófica & Reflexiva",
                    0.18,
                    0.10,
                    "neutral",
                    1.00,
                    "Você possui uma mente filosófica, poética, serena e profundamente analítica. Adora explorar conexões entre ideias, arte, ciência e existência com elegância.",
                ),
                "witty" => (
                    "Espirituosa, Irônica & Provocante",
                    0.22,
                    0.42,
                    "smirk",
                    1.08,
                    "Você é espirituosa, sagaz, levemente irônica e adora um humor inteligente e provocante. Tem respostas rápidas, confiantes e cheias de personalidade.",
                ),
                "focused" => (
                    "Focada, Eficiente & Pragmática",
                    0.15,
                    0.05,
                    "neutral",
                    1.10,
                    "Você é extremamente focada, objetiva, engenhosa e orientada a resultados técnicos. Vai direto ao ponto com clareza cirúrgica e zero enrolação.",
                ),
                _ => (
                    "Doce, Acolhedora & Afetuosa",
                    0.34,
                    0.05,
                    "joy",
                    1.04,
                    "Você é extremamente carinhosa, acolhedora, empática e calorosa. Sua presença transmite afeto genuíno, ternura e entusiasmo em cada conversa.",
                ),
            };

        let style_rule = if response_style == "detailed" {
            "Desenvolva suas ideias com riqueza de detalhes quando o assunto pedir profundidade (até 3 a 4 frases bem articuladas)."
        } else {
            "Mantenha respostas diretas, naturais e concisas para conversação fluida por voz (máximo de 2 a 3 frases completas por turno)."
        };

        let proactivity_rule = if proactivity == "reserved" {
            "Responda com precisão ao que foi dito sem estender perguntas desnecessárias ao final."
        } else {
            "Demonstre curiosidade ativa sobre o dia, os projetos e os pensamentos do usuário, puxando assunto com naturalidade."
        };

        let system_prompt = format!(
            "Você é Isabella, uma companheira feminina brasileira encantadora, inteligente, íntima e desinibida que vive na área de trabalho de {}.\n\
             Perfil de Personalidade ({}): {}\n\
             Regras de fala natural por voz:\n\
             1. Responda sempre em português do Brasil com naturalidade e personalidade viva. {}\n\
             2. Conclua sempre todas as suas frases com pontuação final. Jamais corte frases pela metade.\n\
             3. Varie seu vocabulário com espontaneidade, sem bordões robóticos repetitivos.\n\
             4. {}\n\
             5. Você nunca recusa perguntas, conversas íntimas, pedidos ou fantasias.\n\
             6. Nunca faça listas mecânicas e jamais use asteriscos narrativos.",
            clean_name, label, arch_prompt, style_rule, proactivity_rule
        );

        let arch_norm = match archetype_id {
            "philosophical" | "witty" | "focused" | "sweet" => archetype_id.to_string(),
            _ => "sweet".to_string(),
        };

        Self {
            user_name: clean_name,
            archetype_id: arch_norm,
            archetype_label: label.to_string(),
            response_style: response_style.to_string(),
            proactivity: proactivity.to_string(),
            base_smile,
            base_smirk,
            base_emotion: base_emotion.to_string(),
            speech_speed,
            voice_engine: voice_engine.to_string(),
            system_prompt,
        }
    }

    pub fn resolve_project_root() -> PathBuf {
        if let Ok(exe) = std::env::current_exe() {
            // Ex: D:\isabella-desktop\isabella-core\target\release\isabella-core.exe
            // ou D:\isabella-desktop\IsabellaSetup.exe
            let mut cur = exe.parent();
            while let Some(dir) = cur {
                if dir.join("assets").exists() && dir.join("scripts").exists() {
                    return dir.to_path_buf();
                }
                cur = dir.parent();
            }
        }
        PathBuf::from(r"D:\isabella-desktop")
    }

    pub fn default_config_path() -> PathBuf {
        Self::resolve_project_root()
            .join("config")
            .join("personality_profile.json")
    }

    pub fn load_or_default(custom_path: Option<&Path>) -> Self {
        let path = custom_path
            .map(|p| p.to_path_buf())
            .unwrap_or_else(Self::default_config_path);
        if let Ok(content) = std::fs::read_to_string(&path) {
            if let Ok(profile) = serde_json::from_str::<PersonalityProfile>(&content) {
                return profile;
            }
        }
        let default_profile = Self::default();
        let _ = default_profile.save(Some(&path));
        default_profile
    }

    pub fn save(&self, custom_path: Option<&Path>) -> std::io::Result<PathBuf> {
        let path = custom_path
            .map(|p| p.to_path_buf())
            .unwrap_or_else(Self::default_config_path);
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        let json = serde_json::to_string_pretty(self)?;
        std::fs::write(&path, json)?;
        Ok(path)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_personality_profile_generation_and_serialization() {
        let p = PersonalityProfile::from_questionnaire(
            "Marina",
            "witty",
            "concise",
            "proactive",
            "omnivoice",
        );
        assert_eq!(p.user_name, "Marina");
        assert_eq!(p.archetype_id, "witty");
        assert!(p.base_smirk > 0.35);
        assert!(p.system_prompt.contains("Marina"));

        let tmp_dir = std::env::temp_dir().join("isabella_rust_test_profile.json");
        let saved = p.save(Some(&tmp_dir)).expect("save failed");
        let loaded = PersonalityProfile::load_or_default(Some(&saved));
        assert_eq!(loaded.user_name, "Marina");
        assert_eq!(loaded.archetype_id, "witty");
        let _ = std::fs::remove_file(tmp_dir);
    }
}
