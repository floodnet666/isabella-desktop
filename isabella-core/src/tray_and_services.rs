use crate::personality::PersonalityProfile;
use std::fs::OpenOptions;
use std::net::TcpStream;
#[cfg(windows)]
use std::os::windows::process::CommandExt;
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::{Arc, Mutex};
use std::time::Duration;

#[cfg(windows)]
const CREATE_NO_WINDOW: u32 = 0x0800_0000;

#[derive(Clone, Debug)]
pub enum TrayAction {
    ToggleVisibility,
    SelectArchetype(String),
    OpenPersonalityWizard,
    RestartServices,
    OpenLogsFolder,
    ExitApp,
}

pub struct BackgroundServices {
    project_root: PathBuf,
    children: Vec<(&'static str, Child)>,
}

impl BackgroundServices {
    pub fn new(project_root: PathBuf) -> Self {
        Self {
            project_root,
            children: Vec::new(),
        }
    }

    fn is_port_listening(port: u16) -> bool {
        let addr = format!("127.0.0.1:{}", port);
        if let Ok(sock_addr) = addr.parse() {
            TcpStream::connect_timeout(&sock_addr, Duration::from_millis(250)).is_ok()
        } else {
            false
        }
    }

    pub fn start_all(&mut self, profile: &PersonalityProfile) {
        let logs_dir = self.project_root.join("logs");
        let _ = std::fs::create_dir_all(&logs_dir);

        // 1. Colibri CUDA v2.1.0 (Port 8000)
        if !Self::is_port_listening(8000) {
            let coli_cmd = PathBuf::from(
                std::env::var("LOCALAPPDATA")
                    .unwrap_or_else(|_| r"C:\Users\thiag\AppData\Local".to_string()),
            )
            .join(r"colibri\runtime\colibri-v2.1.0\coli.cmd");
            let colibri_model = self
                .project_root
                .join(r"assets\models\LFM3-Audio-2B-Q4_K_M.colibri");

            if coli_cmd.exists() && colibri_model.exists() {
                let log_out = OpenOptions::new()
                    .create(true)
                    .append(true)
                    .open(logs_dir.join("colibri_bg.log"))
                    .map(Stdio::from)
                    .unwrap_or_else(|_| Stdio::null());
                let log_err = OpenOptions::new()
                    .create(true)
                    .append(true)
                    .open(logs_dir.join("colibri_bg.log"))
                    .map(Stdio::from)
                    .unwrap_or_else(|_| Stdio::null());

                let mut cmd = Command::new("cmd.exe");
                cmd.args([
                    "/C",
                    &coli_cmd.to_string_lossy(),
                    "serve",
                    "--model",
                    &colibri_model.to_string_lossy(),
                    "--port",
                    "8000",
                    "--ctx",
                    "2048",
                    "--policy",
                    "experimental-fast",
                    "--no-think",
                ])
                .env("COLI_CUDA", "1")
                .env("COLI_LOOKUP", "1")
                .env("COLI_SPEC_GATE", "1")
                .env("COLI_CUDA_CHAIN_ROWS", "4096")
                .env("Q36_KV", "f16")
                .current_dir(&self.project_root)
                .stdin(Stdio::null())
                .stdout(log_out)
                .stderr(log_err);

                #[cfg(windows)]
                cmd.creation_flags(CREATE_NO_WINDOW);

                if let Ok(child) = cmd.spawn() {
                    self.children.push(("colibri", child));
                }
            }
        }

        // 2. llama-server CUDA (Port 8080)
        if !Self::is_port_listening(8080) {
            let llama_exe = self.project_root.join(r"tools\llama-cpp\llama-server.exe");
            let mut gguf_model = self
                .project_root
                .join(r"assets\models\LFM3-Audio-2B-Q4_K_M.gguf");
            let mut mmproj_model = self
                .project_root
                .join(r"assets\models\mmproj-LFM3-Audio-2B-Q8_0.gguf");

            if !gguf_model.exists() {
                gguf_model = PathBuf::from(r"E:\modelos_ollama\LFM3-Omni-2B-F16.gguf");
                mmproj_model = PathBuf::from(r"E:\modelos_ollama\mmproj-LFM3-Omni-2B-F16.gguf");
            }

            if llama_exe.exists() && gguf_model.exists() {
                let log_out = OpenOptions::new()
                    .create(true)
                    .append(true)
                    .open(logs_dir.join("llama_server_bg.log"))
                    .map(Stdio::from)
                    .unwrap_or_else(|_| Stdio::null());
                let log_err = OpenOptions::new()
                    .create(true)
                    .append(true)
                    .open(logs_dir.join("llama_server_bg.log"))
                    .map(Stdio::from)
                    .unwrap_or_else(|_| Stdio::null());

                let mut cmd = Command::new(&llama_exe);
                cmd.args([
                    "-m",
                    &gguf_model.to_string_lossy(),
                    "--mmproj",
                    &mmproj_model.to_string_lossy(),
                    "-ngl",
                    "99",
                    "-fa",
                    "auto",
                    "-np",
                    "1",
                    "-c",
                    "2048",
                    "--jinja",
                    "--reasoning",
                    "off",
                    "--no-reasoning-preserve",
                    "--port",
                    "8080",
                ])
                .current_dir(&self.project_root)
                .stdin(Stdio::null())
                .stdout(log_out)
                .stderr(log_err);

                #[cfg(windows)]
                cmd.creation_flags(CREATE_NO_WINDOW);

                if let Ok(child) = cmd.spawn() {
                    self.children.push(("llama-server", child));
                }
            }
        }

        // 3. Voice Bridge (OmniVoice ou Liquid) sem abrir terminal
        let script_rel = if profile.voice_engine == "liquid" {
            r"scripts\voice_bridge.py"
        } else {
            r"scripts\voice_bridge_omnivoice.py"
        };
        let script_path = self.project_root.join(script_rel);
        if script_path.exists() {
            let venv_python = self.project_root.join(r".venv\Scripts\python.exe");
            let log_out = OpenOptions::new()
                .create(true)
                .append(true)
                .open(logs_dir.join("voice_bridge_daemon.log"))
                .map(Stdio::from)
                .unwrap_or_else(|_| Stdio::null());
            let log_err = OpenOptions::new()
                .create(true)
                .append(true)
                .open(logs_dir.join("voice_bridge_daemon.log"))
                .map(Stdio::from)
                .unwrap_or_else(|_| Stdio::null());

            let mut cmd = if venv_python.exists() {
                let mut c = Command::new(venv_python);
                c.arg(&script_path);
                c
            } else {
                let mut c = Command::new("uv");
                c.args(["run", "python", &script_path.to_string_lossy()]);
                c
            };

            cmd.current_dir(&self.project_root)
                .stdin(Stdio::null())
                .stdout(log_out)
                .stderr(log_err);

            #[cfg(windows)]
            cmd.creation_flags(CREATE_NO_WINDOW);

            if let Ok(child) = cmd.spawn() {
                self.children.push(("voice-bridge", child));
            }
        }
    }

    pub fn restart_all(&mut self, profile: &PersonalityProfile) {
        self.stop_all();
        self.start_all(profile);
    }

    pub fn stop_all(&mut self) {
        for (_name, mut child) in self.children.drain(..) {
            let pid = child.id();
            #[cfg(windows)]
            {
                let mut tk = Command::new("taskkill");
                tk.args(["/F", "/T", "/PID", &pid.to_string()])
                    .stdin(Stdio::null())
                    .stdout(Stdio::null())
                    .stderr(Stdio::null())
                    .creation_flags(CREATE_NO_WINDOW);
                let _ = tk.status();
            }
            let _ = child.kill();
            let _ = child.wait();
        }
    }
}

impl Drop for BackgroundServices {
    fn drop(&mut self) {
        self.stop_all();
    }
}

// ============================================================================
// WINDOWS SYSTEM TRAY ICON (Shell_NotifyIconW)
// ============================================================================

#[cfg(windows)]
const WM_TRAYICON: u32 = windows::Win32::UI::WindowsAndMessaging::WM_USER + 101;

#[cfg(windows)]
const IDM_TOGGLE_VISIBILITY: usize = 1001;
#[cfg(windows)]
const IDM_ARCH_SWEET: usize = 1010;
#[cfg(windows)]
const IDM_ARCH_PHILOSOPHICAL: usize = 1011;
#[cfg(windows)]
const IDM_ARCH_WITTY: usize = 1012;
#[cfg(windows)]
const IDM_ARCH_FOCUSED: usize = 1013;
#[cfg(windows)]
const IDM_OPEN_WIZARD: usize = 1020;
#[cfg(windows)]
const IDM_RESTART_SERVICES: usize = 1030;
#[cfg(windows)]
const IDM_OPEN_LOGS: usize = 1040;
#[cfg(windows)]
const IDM_EXIT: usize = 1099;

pub struct SystemTray {
    pub actions: Arc<Mutex<Vec<TrayAction>>>,
    #[cfg(windows)]
    hwnd: windows::Win32::Foundation::HWND,
}

#[cfg(windows)]
type TrayStatePair = (Arc<Mutex<Vec<TrayAction>>>, Arc<Mutex<String>>);

#[cfg(windows)]
static mut GLOBAL_TRAY_STATE: Option<TrayStatePair> = None;

#[cfg(windows)]
fn wide_null(s: &str) -> Vec<u16> {
    s.encode_utf16().chain(std::iter::once(0)).collect()
}

#[cfg(windows)]
unsafe extern "system" fn tray_wnd_proc(
    hwnd: windows::Win32::Foundation::HWND,
    msg: u32,
    wparam: windows::Win32::Foundation::WPARAM,
    lparam: windows::Win32::Foundation::LPARAM,
) -> windows::Win32::Foundation::LRESULT {
    use windows::core::PCWSTR;
    use windows::Win32::Foundation::{LRESULT, POINT};
    use windows::Win32::UI::WindowsAndMessaging::{
        AppendMenuW, CreatePopupMenu, DefWindowProcW, DestroyMenu, GetCursorPos,
        SetForegroundWindow, TrackPopupMenu, MF_CHECKED, MF_SEPARATOR, MF_STRING, MF_UNCHECKED,
        TPM_BOTTOMALIGN, TPM_LEFTALIGN, TPM_RIGHTBUTTON, WM_COMMAND, WM_LBUTTONDBLCLK,
        WM_RBUTTONUP,
    };

    if msg == WM_TRAYICON {
        let mouse_msg = (lparam.0 & 0xFFFF) as u32;
        if mouse_msg == WM_LBUTTONDBLCLK {
            if let Some((ref q, _)) = GLOBAL_TRAY_STATE {
                if let Ok(mut guard) = q.lock() {
                    guard.push(TrayAction::ToggleVisibility);
                }
            }
            return LRESULT(0);
        } else if mouse_msg == WM_RBUTTONUP {
            if let Ok(hmenu) = CreatePopupMenu() {
                let cur_arch = if let Some((_, ref arch_lock)) = GLOBAL_TRAY_STATE {
                    arch_lock
                        .lock()
                        .map(|g| g.clone())
                        .unwrap_or_else(|_| "sweet".to_string())
                } else {
                    "sweet".to_string()
                };

                let t_toggle = wide_null("Mostrar / Ocultar Isabella no Desktop");
                let _ = AppendMenuW(
                    hmenu,
                    MF_STRING,
                    IDM_TOGGLE_VISIBILITY,
                    PCWSTR(t_toggle.as_ptr()),
                );
                let _ = AppendMenuW(hmenu, MF_SEPARATOR, 0, PCWSTR::null());

                let arch_items = [
                    (IDM_ARCH_SWEET, "sweet", "Personalidade: Doce & Acolhedora"),
                    (
                        IDM_ARCH_PHILOSOPHICAL,
                        "philosophical",
                        "Personalidade: Filosófica & Reflexiva",
                    ),
                    (
                        IDM_ARCH_WITTY,
                        "witty",
                        "Personalidade: Espirituosa & Provocante",
                    ),
                    (
                        IDM_ARCH_FOCUSED,
                        "focused",
                        "Personalidade: Focada & Eficiente",
                    ),
                ];

                for (id, key, label) in arch_items {
                    let flag = if cur_arch == key {
                        MF_STRING | MF_CHECKED
                    } else {
                        MF_STRING | MF_UNCHECKED
                    };
                    let w = wide_null(label);
                    let _ = AppendMenuW(hmenu, flag, id, PCWSTR(w.as_ptr()));
                }

                let _ = AppendMenuW(hmenu, MF_SEPARATOR, 0, PCWSTR::null());
                let t_wiz = wide_null("Configurar Personalidade (Assistente)...");
                let _ = AppendMenuW(hmenu, MF_STRING, IDM_OPEN_WIZARD, PCWSTR(t_wiz.as_ptr()));

                let t_res = wide_null("Reiniciar Motores de Voz em Background");
                let _ = AppendMenuW(
                    hmenu,
                    MF_STRING,
                    IDM_RESTART_SERVICES,
                    PCWSTR(t_res.as_ptr()),
                );

                let t_logs = wide_null("Abrir Pasta de Logs");
                let _ = AppendMenuW(hmenu, MF_STRING, IDM_OPEN_LOGS, PCWSTR(t_logs.as_ptr()));

                let _ = AppendMenuW(hmenu, MF_SEPARATOR, 0, PCWSTR::null());
                let t_exit = wide_null("Encerrar Isabella Companion");
                let _ = AppendMenuW(hmenu, MF_STRING, IDM_EXIT, PCWSTR(t_exit.as_ptr()));

                let mut pt = POINT { x: 0, y: 0 };
                let _ = GetCursorPos(&mut pt);
                let _ = SetForegroundWindow(hwnd);
                let _ = TrackPopupMenu(
                    hmenu,
                    TPM_LEFTALIGN | TPM_BOTTOMALIGN | TPM_RIGHTBUTTON,
                    pt.x,
                    pt.y,
                    0,
                    hwnd,
                    None,
                );
                let _ = DestroyMenu(hmenu);
            }
            return LRESULT(0);
        }
    } else if msg == WM_COMMAND {
        let cmd_id = wparam.0 & 0xFFFF;
        if let Some((ref q, ref arch_lock)) = GLOBAL_TRAY_STATE {
            if let Ok(mut guard) = q.lock() {
                match cmd_id {
                    IDM_TOGGLE_VISIBILITY => guard.push(TrayAction::ToggleVisibility),
                    IDM_ARCH_SWEET => {
                        if let Ok(mut a) = arch_lock.lock() {
                            *a = "sweet".to_string();
                        }
                        guard.push(TrayAction::SelectArchetype("sweet".to_string()));
                    }
                    IDM_ARCH_PHILOSOPHICAL => {
                        if let Ok(mut a) = arch_lock.lock() {
                            *a = "philosophical".to_string();
                        }
                        guard.push(TrayAction::SelectArchetype("philosophical".to_string()));
                    }
                    IDM_ARCH_WITTY => {
                        if let Ok(mut a) = arch_lock.lock() {
                            *a = "witty".to_string();
                        }
                        guard.push(TrayAction::SelectArchetype("witty".to_string()));
                    }
                    IDM_ARCH_FOCUSED => {
                        if let Ok(mut a) = arch_lock.lock() {
                            *a = "focused".to_string();
                        }
                        guard.push(TrayAction::SelectArchetype("focused".to_string()));
                    }
                    IDM_OPEN_WIZARD => guard.push(TrayAction::OpenPersonalityWizard),
                    IDM_RESTART_SERVICES => guard.push(TrayAction::RestartServices),
                    IDM_OPEN_LOGS => guard.push(TrayAction::OpenLogsFolder),
                    IDM_EXIT => guard.push(TrayAction::ExitApp),
                    _ => {}
                }
            }
        }
        return LRESULT(0);
    }

    DefWindowProcW(hwnd, msg, wparam, lparam)
}

impl SystemTray {
    #[cfg(windows)]
    pub fn new(project_root: &std::path::Path, initial_archetype: &str) -> Option<Self> {
        use windows::core::PCWSTR;
        use windows::Win32::Foundation::HWND;
        use windows::Win32::System::LibraryLoader::GetModuleHandleW;
        use windows::Win32::UI::Shell::{
            Shell_NotifyIconW, NIF_ICON, NIF_MESSAGE, NIF_TIP, NIM_ADD, NOTIFYICONDATAW,
        };
        use windows::Win32::UI::WindowsAndMessaging::{
            CreateWindowExW, LoadIconW, LoadImageW, RegisterClassW, HICON, IDI_APPLICATION,
            IMAGE_ICON, LR_DEFAULTSIZE, LR_LOADFROMFILE, WINDOW_EX_STYLE, WINDOW_STYLE, WNDCLASSW,
        };

        let actions = Arc::new(Mutex::new(Vec::new()));
        let active_archetype = Arc::new(Mutex::new(initial_archetype.to_string()));

        unsafe {
            GLOBAL_TRAY_STATE = Some((actions.clone(), active_archetype.clone()));

            let hinstance = GetModuleHandleW(None).ok()?;
            let class_name = wide_null("IsabellaTrayHiddenWindowClass");

            let wc = WNDCLASSW {
                lpfnWndProc: Some(tray_wnd_proc),
                hInstance: hinstance.into(),
                lpszClassName: PCWSTR(class_name.as_ptr()),
                ..Default::default()
            };
            let _ = RegisterClassW(&wc);

            let hwnd = CreateWindowExW(
                WINDOW_EX_STYLE(0),
                PCWSTR(class_name.as_ptr()),
                PCWSTR(wide_null("IsabellaTrayMsgWnd").as_ptr()),
                WINDOW_STYLE(0),
                0,
                0,
                0,
                0,
                HWND(0),
                None,
                hinstance,
                None,
            );
            if hwnd.0 == 0 {
                return None;
            }

            let ico_path = project_root.join(r"assets\isabella_icon.ico");
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

            let mut nid = NOTIFYICONDATAW {
                cbSize: std::mem::size_of::<NOTIFYICONDATAW>() as u32,
                hWnd: hwnd,
                uID: 1,
                uFlags: NIF_ICON | NIF_MESSAGE | NIF_TIP,
                uCallbackMessage: WM_TRAYICON,
                hIcon: hicon,
                ..Default::default()
            };

            let tip = wide_null("Isabella Companion — Ativa em Background (Clique Direito)");
            for (dst, src) in nid.szTip.iter_mut().zip(tip.iter()) {
                *dst = *src;
            }

            let _ = Shell_NotifyIconW(NIM_ADD, &nid);

            Some(Self { actions, hwnd })
        }
    }

    #[cfg(not(windows))]
    pub fn new(_project_root: &std::path::Path, _initial_archetype: &str) -> Option<Self> {
        Some(Self {
            actions: Arc::new(Mutex::new(Vec::new())),
        })
    }

    pub fn drain_actions(&self) -> Vec<TrayAction> {
        if let Ok(mut guard) = self.actions.lock() {
            guard.drain(..).collect()
        } else {
            Vec::new()
        }
    }
}

impl Drop for SystemTray {
    fn drop(&mut self) {
        #[cfg(windows)]
        unsafe {
            use windows::Win32::UI::Shell::{Shell_NotifyIconW, NIM_DELETE, NOTIFYICONDATAW};
            use windows::Win32::UI::WindowsAndMessaging::DestroyWindow;

            let nid = NOTIFYICONDATAW {
                cbSize: std::mem::size_of::<NOTIFYICONDATAW>() as u32,
                hWnd: self.hwnd,
                uID: 1,
                ..Default::default()
            };
            let _ = Shell_NotifyIconW(NIM_DELETE, &nid);
            let _ = DestroyWindow(self.hwnd);
        }
    }
}
