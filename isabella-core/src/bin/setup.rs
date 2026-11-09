#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

#[path = "../personality.rs"]
mod personality;

use personality::PersonalityProfile;
#[cfg(windows)]
use std::os::windows::process::CommandExt;
use std::path::Path;
use std::process::{Command, Stdio};

#[cfg(windows)]
const CREATE_NO_WINDOW: u32 = 0x0800_0000;

fn apply_installation_and_inoculation(
    project_root: &Path,
    profile: &PersonalityProfile,
    launch_after: bool,
) -> Result<String, String> {
    // 1. Salvar config/personality_profile.json
    let cfg_path = project_root.join("config").join("personality_profile.json");
    profile
        .save(Some(&cfg_path))
        .map_err(|e| format!("Falha ao salvar perfil: {}", e))?;

    // 2. Inocular o banco HippoRAG 2 + Contextual FTS5 via script Python sem abrir terminal
    let venv_py = project_root.join(r".venv\Scripts\python.exe");
    let py_code = "from scripts.memory.personality_loader import load_personality_profile, inoculate_memory_with_profile; p = load_personality_profile(); inoculate_memory_with_profile(p)";
    let mut cmd = if venv_py.exists() {
        let mut c = Command::new(venv_py);
        c.args(["-c", py_code]);
        c
    } else {
        let mut c = Command::new("uv");
        c.args(["run", "python", "-c", py_code]);
        c
    };
    cmd.current_dir(project_root)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null());
    #[cfg(windows)]
    cmd.creation_flags(CREATE_NO_WINDOW);
    let _ = cmd.status();

    // 3. Copiar IsabellaSetup.exe para a raiz D:\isabella-desktop\IsabellaSetup.exe
    let release_setup = project_root.join(r"isabella-core\target\release\IsabellaSetup.exe");
    let root_setup = project_root.join("IsabellaSetup.exe");
    if release_setup.exists() && release_setup != root_setup {
        let _ = std::fs::copy(&release_setup, &root_setup);
    }

    // 4. Criar / Atualizar atalho na Área de Trabalho ("Isabella Companion.lnk") apontando direto para isabella-core.exe (WindowStyle=1 sem console)
    let core_exe = project_root.join(r"isabella-core\target\release\isabella-core.exe");
    let icon_ico = project_root.join(r"assets\isabella_icon.ico");
    let ps_script = format!(
        "$ws = New-Object -ComObject WScript.Shell; \
         $desk = [Environment]::GetFolderPath('Desktop'); \
         $lnk = $ws.CreateShortcut((Join-Path $desk 'Isabella Companion.lnk')); \
         $lnk.TargetPath = '{}'; \
         $lnk.WorkingDirectory = '{}'; \
         $lnk.IconLocation = '{},0'; \
         $lnk.Description = 'Isabella Desktop Companion 3DGS (Background System Tray)'; \
         $lnk.Save()",
        core_exe.to_string_lossy(),
        project_root.to_string_lossy(),
        icon_ico.to_string_lossy()
    );
    let mut ps_cmd = Command::new("powershell.exe");
    ps_cmd
        .args([
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            &ps_script,
        ])
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null());
    #[cfg(windows)]
    ps_cmd.creation_flags(CREATE_NO_WINDOW);
    let _ = ps_cmd.status();

    // 5. Se solicitado, iniciar Isabella Companion imediatamente em background
    if launch_after && core_exe.exists() {
        let mut launch_cmd = Command::new(&core_exe);
        launch_cmd
            .current_dir(project_root)
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null());
        #[cfg(windows)]
        launch_cmd.creation_flags(CREATE_NO_WINDOW);
        let _ = launch_cmd.spawn();
    }

    Ok(format!(
        "Perfil '{}' para {} salvo em:\n{}\n\nAtalho 'Isabella Companion' configurado para rodar 100% em segundo plano (System Tray) sem janelas de terminal!",
        profile.archetype_label,
        profile.user_name,
        cfg_path.display()
    ))
}

#[cfg(windows)]
mod win32_wizard {
    use super::*;
    use windows::core::PCWSTR;
    use windows::Win32::Foundation::{HWND, LPARAM, LRESULT, WPARAM};
    use windows::Win32::Graphics::Gdi::{
        CreateFontW, GetStockObject, CLEARTYPE_QUALITY, DEFAULT_CHARSET, DEFAULT_GUI_FONT, FW_BOLD,
        FW_NORMAL, HBRUSH, OUT_DEFAULT_PRECIS, VARIABLE_PITCH, WHITE_BRUSH,
    };
    use windows::Win32::System::LibraryLoader::GetModuleHandleW;
    use windows::Win32::UI::WindowsAndMessaging::{
        CreateWindowExW, DefWindowProcW, DestroyWindow, DispatchMessageW, GetMessageW,
        GetWindowTextLengthW, GetWindowTextW, LoadCursorW, LoadIconW, LoadImageW, MessageBoxW,
        PostQuitMessage, RegisterClassW, SendMessageW, ShowWindow, TranslateMessage, BM_GETCHECK,
        BM_SETCHECK, BS_AUTORADIOBUTTON, BS_DEFPUSHBUTTON, BS_GROUPBOX, CW_USEDEFAULT, HICON,
        HMENU, IDC_ARROW, IDI_APPLICATION, IMAGE_ICON, LR_DEFAULTSIZE, LR_LOADFROMFILE,
        MB_ICONINFORMATION, MB_OK, MSG, SW_SHOW, WINDOW_EX_STYLE, WINDOW_STYLE, WM_CLOSE,
        WM_COMMAND, WM_CREATE, WM_DESTROY, WM_SETFONT, WNDCLASSW, WS_BORDER, WS_CAPTION, WS_CHILD,
        WS_GROUP, WS_OVERLAPPED, WS_SYSMENU, WS_TABSTOP, WS_VISIBLE,
    };

    const IDC_EDIT_NAME: usize = 2001;
    const IDC_ARCH_SWEET: usize = 2010;
    const IDC_ARCH_PHILO: usize = 2011;
    const IDC_ARCH_WITTY: usize = 2012;
    const IDC_ARCH_FOCUSED: usize = 2013;

    const IDC_STYLE_CONCISE: usize = 2020;
    const IDC_STYLE_DETAILED: usize = 2021;

    const IDC_PROACT_ACTIVE: usize = 2030;
    const IDC_PROACT_RESERVED: usize = 2031;

    const IDC_VOICE_OMNIVOICE: usize = 2040;
    const IDC_VOICE_LIQUID: usize = 2041;

    const IDC_BTN_INSTALL_LAUNCH: usize = 2090;
    const IDC_BTN_SAVE_ONLY: usize = 2091;

    fn wide_null(s: &str) -> Vec<u16> {
        s.encode_utf16().chain(std::iter::once(0)).collect()
    }

    unsafe fn get_control_text(hwnd_parent: HWND, id: usize) -> String {
        use windows::Win32::UI::WindowsAndMessaging::GetDlgItem;
        let hctrl = GetDlgItem(hwnd_parent, id as i32);
        if hctrl.0 == 0 {
            return String::new();
        }
        let len = GetWindowTextLengthW(hctrl);
        if len <= 0 {
            return String::new();
        }
        let mut buf = vec![0u16; (len + 1) as usize];
        let read = GetWindowTextW(hctrl, &mut buf);
        String::from_utf16_lossy(&buf[..read as usize])
    }

    unsafe fn is_checked(hwnd_parent: HWND, id: usize) -> bool {
        use windows::Win32::UI::WindowsAndMessaging::GetDlgItem;
        let hctrl = GetDlgItem(hwnd_parent, id as i32);
        if hctrl.0 == 0 {
            return false;
        }
        SendMessageW(hctrl, BM_GETCHECK, WPARAM(0), LPARAM(0)).0 == 1
    }

    #[allow(clippy::too_many_arguments)]
    unsafe fn create_ctrl(
        class: &str,
        text: &str,
        style: WINDOW_STYLE,
        x: i32,
        y: i32,
        w: i32,
        h: i32,
        parent: HWND,
        id: usize,
        font: isize,
    ) -> HWND {
        let c_w = wide_null(class);
        let t_w = wide_null(text);
        let hwnd = CreateWindowExW(
            WINDOW_EX_STYLE(0),
            PCWSTR(c_w.as_ptr()),
            PCWSTR(t_w.as_ptr()),
            style,
            x,
            y,
            w,
            h,
            parent,
            HMENU(id as isize),
            GetModuleHandleW(None).unwrap_or_default(),
            None,
        );
        if hwnd.0 != 0 && font != 0 {
            SendMessageW(hwnd, WM_SETFONT, WPARAM(font as usize), LPARAM(1));
        }
        hwnd
    }

    unsafe extern "system" fn setup_wnd_proc(
        hwnd: HWND,
        msg: u32,
        wparam: WPARAM,
        lparam: LPARAM,
    ) -> LRESULT {
        match msg {
            WM_CREATE => {
                let current = PersonalityProfile::load_or_default(None);

                let hfont_title = CreateFontW(
                    22,
                    0,
                    0,
                    0,
                    FW_BOLD.0 as i32,
                    0,
                    0,
                    0,
                    DEFAULT_CHARSET.0 as u32,
                    OUT_DEFAULT_PRECIS.0 as u32,
                    0,
                    CLEARTYPE_QUALITY.0 as u32,
                    VARIABLE_PITCH.0 as u32,
                    PCWSTR(wide_null("Segoe UI").as_ptr()),
                );
                let hfont_body = CreateFontW(
                    16,
                    0,
                    0,
                    0,
                    FW_NORMAL.0 as i32,
                    0,
                    0,
                    0,
                    DEFAULT_CHARSET.0 as u32,
                    OUT_DEFAULT_PRECIS.0 as u32,
                    0,
                    CLEARTYPE_QUALITY.0 as u32,
                    VARIABLE_PITCH.0 as u32,
                    PCWSTR(wide_null("Segoe UI").as_ptr()),
                );
                let font_b = if hfont_body.0 != 0 {
                    hfont_body.0
                } else {
                    GetStockObject(DEFAULT_GUI_FONT).0
                };
                let font_t = if hfont_title.0 != 0 {
                    hfont_title.0
                } else {
                    font_b
                };

                create_ctrl(
                    "STATIC",
                    "Isabella Companion — Assistente de Instalação & Personalidade",
                    WS_CHILD | WS_VISIBLE,
                    24,
                    16,
                    590,
                    28,
                    hwnd,
                    0,
                    font_t,
                );
                create_ctrl(
                    "STATIC",
                    "Personalize o temperamento, a voz neural e a memória de longo prazo (HippoRAG 2) da sua Isabella:",
                    WS_CHILD | WS_VISIBLE,
                    24,
                    46,
                    590,
                    22,
                    hwnd,
                    0,
                    font_b,
                );

                // 1. Nome do Usuário
                create_ctrl(
                    "STATIC",
                    "1. Como você gostaria que a Isabella te chamasse?",
                    WS_CHILD | WS_VISIBLE,
                    24,
                    80,
                    380,
                    22,
                    hwnd,
                    0,
                    font_b,
                );
                create_ctrl(
                    "EDIT",
                    &current.user_name,
                    WS_CHILD | WS_VISIBLE | WS_BORDER | WS_TABSTOP,
                    410,
                    78,
                    195,
                    26,
                    hwnd,
                    IDC_EDIT_NAME,
                    font_b,
                );

                // 2. Arquétipo de Personalidade
                create_ctrl(
                    "BUTTON",
                    "2. Arquétipo de Personalidade e Expressão 3DGS (FACS)",
                    WS_CHILD | WS_VISIBLE | WINDOW_STYLE(BS_GROUPBOX as u32),
                    24,
                    116,
                    582,
                    136,
                    hwnd,
                    0,
                    font_b,
                );
                let h_sweet = create_ctrl(
                    "BUTTON",
                    "Doce, Acolhedora & Afetuosa (Carinhosa, calorosa e sorriso suave)",
                    WS_CHILD | WS_VISIBLE | WS_GROUP | WINDOW_STYLE(BS_AUTORADIOBUTTON as u32),
                    40,
                    142,
                    545,
                    24,
                    hwnd,
                    IDC_ARCH_SWEET,
                    font_b,
                );
                let h_philo = create_ctrl(
                    "BUTTON",
                    "Filosófica & Reflexiva (Poética, serena, analítica e profunda)",
                    WS_CHILD | WS_VISIBLE | WINDOW_STYLE(BS_AUTORADIOBUTTON as u32),
                    40,
                    168,
                    545,
                    24,
                    hwnd,
                    IDC_ARCH_PHILO,
                    font_b,
                );
                let h_witty = create_ctrl(
                    "BUTTON",
                    "Espirituosa, Irônica & Provocante (Humor rápido, sagaz e olhar smirk)",
                    WS_CHILD | WS_VISIBLE | WINDOW_STYLE(BS_AUTORADIOBUTTON as u32),
                    40,
                    194,
                    545,
                    24,
                    hwnd,
                    IDC_ARCH_WITTY,
                    font_b,
                );
                let h_focus = create_ctrl(
                    "BUTTON",
                    "Focada, Eficiente & Pragmática (Direta ao ponto, técnica e objetiva)",
                    WS_CHILD | WS_VISIBLE | WINDOW_STYLE(BS_AUTORADIOBUTTON as u32),
                    40,
                    220,
                    545,
                    24,
                    hwnd,
                    IDC_ARCH_FOCUSED,
                    font_b,
                );

                let sel_arch = match current.archetype_id.as_str() {
                    "philosophical" => h_philo,
                    "witty" => h_witty,
                    "focused" => h_focus,
                    _ => h_sweet,
                };
                SendMessageW(sel_arch, BM_SETCHECK, WPARAM(1), LPARAM(0));

                // 3. Estilo de Resposta
                create_ctrl(
                    "BUTTON",
                    "3. Ritmo e Extensão das Respostas por Voz",
                    WS_CHILD | WS_VISIBLE | WINDOW_STYLE(BS_GROUPBOX as u32),
                    24,
                    264,
                    582,
                    82,
                    hwnd,
                    0,
                    font_b,
                );
                let h_concise = create_ctrl(
                    "BUTTON",
                    "Direta e Concisa (2 a 3 frases ágeis, ideal para diálogo rápido)",
                    WS_CHILD | WS_VISIBLE | WS_GROUP | WINDOW_STYLE(BS_AUTORADIOBUTTON as u32),
                    40,
                    288,
                    545,
                    24,
                    hwnd,
                    IDC_STYLE_CONCISE,
                    font_b,
                );
                let h_detailed = create_ctrl(
                    "BUTTON",
                    "Desenvolvida e Explicativa (3 a 4 frases articuladas para temas profundos)",
                    WS_CHILD | WS_VISIBLE | WINDOW_STYLE(BS_AUTORADIOBUTTON as u32),
                    40,
                    314,
                    545,
                    24,
                    hwnd,
                    IDC_STYLE_DETAILED,
                    font_b,
                );
                let sel_style = if current.response_style == "detailed" {
                    h_detailed
                } else {
                    h_concise
                };
                SendMessageW(sel_style, BM_SETCHECK, WPARAM(1), LPARAM(0));

                // 4. Iniciativa / Proatividade
                create_ctrl(
                    "BUTTON",
                    "4. Iniciativa Conversacional",
                    WS_CHILD | WS_VISIBLE | WINDOW_STYLE(BS_GROUPBOX as u32),
                    24,
                    356,
                    582,
                    82,
                    hwnd,
                    0,
                    font_b,
                );
                let h_proact = create_ctrl(
                    "BUTTON",
                    "Proativa e Curiosa (Demonstra interesse ativo e puxa assunto naturalmente)",
                    WS_CHILD | WS_VISIBLE | WS_GROUP | WINDOW_STYLE(BS_AUTORADIOBUTTON as u32),
                    40,
                    380,
                    545,
                    24,
                    hwnd,
                    IDC_PROACT_ACTIVE,
                    font_b,
                );
                let h_reserv = create_ctrl(
                    "BUTTON",
                    "Reservada e Direta (Responde apenas ao que foi perguntado com precisão)",
                    WS_CHILD | WS_VISIBLE | WINDOW_STYLE(BS_AUTORADIOBUTTON as u32),
                    40,
                    406,
                    545,
                    24,
                    hwnd,
                    IDC_PROACT_RESERVED,
                    font_b,
                );
                let sel_proact = if current.proactivity == "reserved" {
                    h_reserv
                } else {
                    h_proact
                };
                SendMessageW(sel_proact, BM_SETCHECK, WPARAM(1), LPARAM(0));

                // 5. Motor de Síntese de Voz
                create_ctrl(
                    "BUTTON",
                    "5. Motor Neural de Voz (GPU)",
                    WS_CHILD | WS_VISIBLE | WINDOW_STYLE(BS_GROUPBOX as u32),
                    24,
                    448,
                    582,
                    82,
                    hwnd,
                    0,
                    font_b,
                );
                let h_omni = create_ctrl(
                    "BUTTON",
                    "OmniVoice 24kHz Diffusion (Voz Clonada de Alta Fidelidade na GPU)",
                    WS_CHILD | WS_VISIBLE | WS_GROUP | WINDOW_STYLE(BS_AUTORADIOBUTTON as u32),
                    40,
                    472,
                    545,
                    24,
                    hwnd,
                    IDC_VOICE_OMNIVOICE,
                    font_b,
                );
                let h_liq = create_ctrl(
                    "BUTTON",
                    "LFM3 LiquidCodec 24kHz (Baixíssimo uso de VRAM via llama-server)",
                    WS_CHILD | WS_VISIBLE | WINDOW_STYLE(BS_AUTORADIOBUTTON as u32),
                    40,
                    498,
                    545,
                    24,
                    hwnd,
                    IDC_VOICE_LIQUID,
                    font_b,
                );
                let sel_voice = if current.voice_engine == "liquid" {
                    h_liq
                } else {
                    h_omni
                };
                SendMessageW(sel_voice, BM_SETCHECK, WPARAM(1), LPARAM(0));

                // Botões de Ação
                create_ctrl(
                    "BUTTON",
                    "Apenas Salvar Perfil",
                    WS_CHILD | WS_VISIBLE | WS_TABSTOP,
                    196,
                    546,
                    180,
                    36,
                    hwnd,
                    IDC_BTN_SAVE_ONLY,
                    font_b,
                );
                create_ctrl(
                    "BUTTON",
                    "Concluir & Iniciar Isabella (Tray)",
                    WS_CHILD | WS_VISIBLE | WS_TABSTOP | WINDOW_STYLE(BS_DEFPUSHBUTTON as u32),
                    390,
                    546,
                    216,
                    36,
                    hwnd,
                    IDC_BTN_INSTALL_LAUNCH,
                    font_t,
                );

                LRESULT(0)
            }
            WM_COMMAND => {
                let cmd_id = wparam.0 & 0xFFFF;
                if cmd_id == IDC_BTN_INSTALL_LAUNCH || cmd_id == IDC_BTN_SAVE_ONLY {
                    let user_name = get_control_text(hwnd, IDC_EDIT_NAME);
                    let arch = if is_checked(hwnd, IDC_ARCH_PHILO) {
                        "philosophical"
                    } else if is_checked(hwnd, IDC_ARCH_WITTY) {
                        "witty"
                    } else if is_checked(hwnd, IDC_ARCH_FOCUSED) {
                        "focused"
                    } else {
                        "sweet"
                    };
                    let style = if is_checked(hwnd, IDC_STYLE_DETAILED) {
                        "detailed"
                    } else {
                        "concise"
                    };
                    let proact = if is_checked(hwnd, IDC_PROACT_RESERVED) {
                        "reserved"
                    } else {
                        "proactive"
                    };
                    let voice = if is_checked(hwnd, IDC_VOICE_LIQUID) {
                        "liquid"
                    } else {
                        "omnivoice"
                    };

                    let profile = PersonalityProfile::from_questionnaire(
                        &user_name, arch, style, proact, voice,
                    );
                    let root = PersonalityProfile::resolve_project_root();
                    let launch = cmd_id == IDC_BTN_INSTALL_LAUNCH;

                    match apply_installation_and_inoculation(&root, &profile, launch) {
                        Ok(summary) => {
                            let title = wide_null("Isabella Companion — Configuração Concluída");
                            let body = wide_null(&summary);
                            MessageBoxW(
                                hwnd,
                                PCWSTR(body.as_ptr()),
                                PCWSTR(title.as_ptr()),
                                MB_OK | MB_ICONINFORMATION,
                            );
                            let _ = DestroyWindow(hwnd);
                        }
                        Err(err) => {
                            let title = wide_null("Erro na Configuração");
                            let body = wide_null(&err);
                            MessageBoxW(hwnd, PCWSTR(body.as_ptr()), PCWSTR(title.as_ptr()), MB_OK);
                        }
                    }
                    return LRESULT(0);
                }
                DefWindowProcW(hwnd, msg, wparam, lparam)
            }
            WM_CLOSE => {
                let _ = DestroyWindow(hwnd);
                LRESULT(0)
            }
            WM_DESTROY => {
                PostQuitMessage(0);
                LRESULT(0)
            }
            _ => DefWindowProcW(hwnd, msg, wparam, lparam),
        }
    }

    pub fn run_gui_wizard() -> Result<(), String> {
        unsafe {
            let hinstance = GetModuleHandleW(None).map_err(|e| e.to_string())?;
            let class_name = wide_null("IsabellaSetupWizardClass");
            let root = PersonalityProfile::resolve_project_root();
            let ico_path = root.join(r"assets\isabella_icon.ico");
            let ico_w = wide_null(&ico_path.to_string_lossy());

            let hicon = if let Ok(handle) = LoadImageW(
                None,
                PCWSTR(ico_w.as_ptr()),
                IMAGE_ICON,
                0,
                0,
                LR_LOADFROMFILE | LR_DEFAULTSIZE,
            ) {
                HICON(handle.0)
            } else {
                LoadIconW(None, IDI_APPLICATION).unwrap_or(HICON(0))
            };

            let wc = WNDCLASSW {
                lpfnWndProc: Some(setup_wnd_proc),
                hInstance: hinstance.into(),
                hIcon: hicon,
                hCursor: LoadCursorW(None, IDC_ARROW).unwrap_or_default(),
                hbrBackground: HBRUSH(GetStockObject(WHITE_BRUSH).0),
                lpszClassName: PCWSTR(class_name.as_ptr()),
                ..Default::default()
            };
            let _ = RegisterClassW(&wc);

            let title = wide_null("Isabella Companion — Assistente de Instalação e Personalidade");
            let hwnd = CreateWindowExW(
                WINDOW_EX_STYLE(0),
                PCWSTR(class_name.as_ptr()),
                PCWSTR(title.as_ptr()),
                WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_VISIBLE,
                CW_USEDEFAULT,
                CW_USEDEFAULT,
                640,
                635,
                HWND(0),
                None,
                hinstance,
                None,
            );
            if hwnd.0 == 0 {
                return Err("Falha ao criar janela Win32 do instalador".to_string());
            }

            let _ = ShowWindow(hwnd, SW_SHOW);

            let mut msg = MSG::default();
            while GetMessageW(&mut msg, HWND(0), 0, 0).as_bool() {
                let _ = TranslateMessage(&msg);
                DispatchMessageW(&msg);
            }
        }
        Ok(())
    }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let root = PersonalityProfile::resolve_project_root();

    // Suporte a execução automatizada (--headless) para CI/CD e configuração silenciosa
    if args.iter().any(|a| a == "--headless") {
        let get_arg = |flag: &str, default: &str| -> String {
            if let Some(pos) = args.iter().position(|a| a == flag) {
                if let Some(val) = args.get(pos + 1) {
                    return val.clone();
                }
            }
            default.to_string()
        };

        let existing = PersonalityProfile::load_or_default(None);
        let user_name = get_arg("--user-name", &existing.user_name);
        let archetype = get_arg("--archetype", &existing.archetype_id);
        let style = get_arg("--style", &existing.response_style);
        let proactivity = get_arg("--proactivity", &existing.proactivity);
        let voice = get_arg("--voice", &existing.voice_engine);
        let launch = args.iter().any(|a| a == "--launch");

        let profile = PersonalityProfile::from_questionnaire(
            &user_name,
            &archetype,
            &style,
            &proactivity,
            &voice,
        );
        if let Err(e) = apply_installation_and_inoculation(&root, &profile, launch) {
            eprintln!("[IsabellaSetup Headless Error]: {}", e);
            std::process::exit(1);
        }
        return;
    }

    #[cfg(windows)]
    {
        if let Err(e) = win32_wizard::run_gui_wizard() {
            eprintln!("[IsabellaSetup Error]: {}", e);
            std::process::exit(1);
        }
    }
}
