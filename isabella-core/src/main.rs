mod ply_loader;
mod renderer;

use renderer::ExpressionParams;
use std::sync::{Arc, Mutex};
use tokio::net::UdpSocket;
use winit::{
    dpi::{LogicalSize, PhysicalPosition},
    event::{ElementState, Event, MouseButton, WindowEvent},
    event_loop::{ControlFlow, EventLoop},
    window::{WindowBuilder, WindowLevel},
};

#[derive(Clone, Debug, Default)]
struct EmotionState {
    pub joy: f32,
    pub anger: f32,
    pub disgust: f32,
    pub fear: f32,
    pub sadness: f32,
    pub surprise: f32,
    pub smirk: f32,
    pub brow_raise: f32,
}

#[derive(Default)]
struct SharedState {
    pub jaw_open: f32,
    pub lip_round: f32,
    pub lip_spread: f32,
    pub smile: f32,
    pub avatar_state: String,
    pub emotion: EmotionState,
}

#[cfg(windows)]
fn query_global_cursor_norm(window: &winit::window::Window) -> Option<(f32, f32)> {
    use windows::Win32::Foundation::POINT;
    use windows::Win32::UI::WindowsAndMessaging::GetCursorPos;

    let mut pt = POINT { x: 0, y: 0 };
    let ok = unsafe { GetCursorPos(&mut pt) };
    if ok.is_err() {
        return None;
    }

    let win_pos = window.outer_position().ok()?;
    let win_size = window.outer_size();
    let head_center_x = win_pos.x as f32 + (win_size.width as f32) * 0.50;
    let head_center_y = win_pos.y as f32 + (win_size.height as f32) * 0.34;

    let dx = (pt.x as f32 - head_center_x) / 680.0;
    let dy = (pt.y as f32 - head_center_y) / 480.0;
    Some((dx.tanh(), dy.tanh()))
}

#[cfg(not(windows))]
fn query_global_cursor_norm(_window: &winit::window::Window) -> Option<(f32, f32)> {
    None
}

fn apply_avatar_scale(new_scale: f32, current_scale: &mut f32, window: &winit::window::Window) {
    let clamped = new_scale.clamp(0.40, 2.50);
    if (*current_scale - clamped).abs() < 0.005 {
        return;
    }

    let cur_pos = window
        .outer_position()
        .unwrap_or(PhysicalPosition::new(0, 0));
    let cur_size = window.outer_size();
    let bottom_y = cur_pos.y + cur_size.height as i32;
    let center_x = cur_pos.x + (cur_size.width as i32) / 2;

    *current_scale = clamped;
    let new_w = (380.0 * clamped).round() as u32;
    let new_h = (580.0 * clamped).round() as u32;

    let new_x = center_x - (new_w as i32) / 2;
    let new_y = bottom_y - (new_h as i32);

    #[cfg(windows)]
    {
        use windows::Win32::UI::WindowsAndMessaging::{SetWindowPos, SWP_NOACTIVATE, SWP_NOZORDER};
        use winit::raw_window_handle::{HasWindowHandle, RawWindowHandle};
        if let Ok(handle) = window.window_handle() {
            if let RawWindowHandle::Win32(win32_handle) = handle.as_raw() {
                let hwnd = windows::Win32::Foundation::HWND(win32_handle.hwnd.get());
                unsafe {
                    let _ = SetWindowPos(
                        hwnd,
                        windows::Win32::Foundation::HWND(0),
                        new_x,
                        new_y,
                        new_w as i32,
                        new_h as i32,
                        SWP_NOACTIVATE | SWP_NOZORDER,
                    );
                }
            }
        }
    }
    #[cfg(not(windows))]
    {
        let _ = window.request_inner_size(LogicalSize::new(new_w, new_h));
        window.set_outer_position(PhysicalPosition::new(new_x, new_y));
    }
    println!(
        "[Avatar Scale] Escala ajustada para: {:.2}x ({}x{} px)",
        clamped, new_w, new_h
    );
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("=======================================================");
    println!("       ISABELLA — DESKTOP COMPANION (HD 1M)           ");
    println!("=======================================================");

    let args: Vec<String> = std::env::args().collect();
    let ply_path = if let Some(pos) = args.iter().position(|a| a == "--ply") {
        args.get(pos + 1)
            .map(|s| s.as_str())
            .unwrap_or(r"D:\isabella-desktop\assets\models\isabella_bust_4x_1m.ply")
    } else {
        r"D:\isabella-desktop\assets\models\isabella_bust_4x_1m.ply"
    };

    println!("[Main] Carregando modelo 3DGS HD de: {}...", ply_path);
    let splats = ply_loader::load_splat_ply(ply_path)?;
    println!("[Main] {} gaussianas prontas para GPU.", splats.len());

    let event_loop = EventLoop::new()?;

    // Janela sem bordas, 100% transparente (DWM glass) e sem redirection bitmap
    #[cfg(windows)]
    use winit::platform::windows::WindowBuilderExtWindows;

    #[cfg(windows)]
    let builder = WindowBuilder::new()
        .with_title("Isabella Desktop Companion")
        .with_inner_size(LogicalSize::new(380.0, 580.0))
        .with_decorations(false)
        .with_transparent(true)
        .with_no_redirection_bitmap(true)
        .with_undecorated_shadow(false)
        .with_window_level(WindowLevel::AlwaysOnTop);

    #[cfg(not(windows))]
    let builder = WindowBuilder::new()
        .with_title("Isabella Desktop Companion")
        .with_inner_size(LogicalSize::new(380.0, 580.0))
        .with_decorations(false)
        .with_transparent(true)
        .with_window_level(WindowLevel::AlwaysOnTop);

    let window = Arc::new(builder.build(&event_loop)?);

    // Configuração Win32 rigorosa: erradicar bordas do app, botões (minimizar, maximizar, fechar) e estender DWM glass
    #[cfg(windows)]
    {
        use windows::Win32::Graphics::Dwm::DwmExtendFrameIntoClientArea;
        use windows::Win32::UI::Controls::MARGINS;
        use windows::Win32::UI::WindowsAndMessaging::{
            GetWindowLongPtrW, SetWindowLongPtrW, SetWindowPos, GWL_STYLE, SWP_FRAMECHANGED,
            SWP_NOACTIVATE, SWP_NOMOVE, SWP_NOSIZE, SWP_NOZORDER, WS_CAPTION, WS_MAXIMIZEBOX,
            WS_MINIMIZEBOX, WS_POPUP, WS_SYSMENU, WS_THICKFRAME, WS_VISIBLE,
        };
        use winit::raw_window_handle::{HasWindowHandle, RawWindowHandle};

        if let Ok(handle) = window.window_handle() {
            if let RawWindowHandle::Win32(win32_handle) = handle.as_raw() {
                let hwnd = windows::Win32::Foundation::HWND(win32_handle.hwnd.get());

                // 1. Remover estilos de janela com barra de título, bordas e botões de controle do Windows
                let mut style = unsafe { GetWindowLongPtrW(hwnd, GWL_STYLE) } as u32;
                style &= !(WS_CAPTION.0
                    | WS_SYSMENU.0
                    | WS_THICKFRAME.0
                    | WS_MINIMIZEBOX.0
                    | WS_MAXIMIZEBOX.0);
                style |= WS_POPUP.0 | WS_VISIBLE.0;
                unsafe { SetWindowLongPtrW(hwnd, GWL_STYLE, style as isize) };

                // 2. Notificar o compositor do Windows para recalcular e descartar a moldura e botões imediatamente
                unsafe {
                    let _ = SetWindowPos(
                        hwnd,
                        windows::Win32::Foundation::HWND(0),
                        0,
                        0,
                        0,
                        0,
                        SWP_FRAMECHANGED | SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE,
                    );
                }

                // 3. Estender o quadro DWM com margem -1 sobre toda a janela para transparência total
                let margins = MARGINS {
                    cxLeftWidth: -1,
                    cxRightWidth: -1,
                    cyTopHeight: -1,
                    cyBottomHeight: -1,
                };
                let hr = unsafe { DwmExtendFrameIntoClientArea(hwnd, &margins) };
                println!(
                    "[Main] DWM glass frame estendido (margem -1, bordas e botoes removidos): {:?}",
                    hr
                );
            }
        }
    }

    // Obter a área útil de trabalho do monitor (descontando a barra de tarefas do Windows)
    // para assentar a modelo perfeitamente acima da barra iniciar
    #[cfg(windows)]
    let mut initial_pos = (50i32, 50i32);
    #[cfg(windows)]
    {
        use windows::Win32::Graphics::Gdi::{
            GetMonitorInfoW, MonitorFromWindow, MONITORINFO, MONITOR_DEFAULTTONEAREST,
        };
        use winit::raw_window_handle::{HasWindowHandle, RawWindowHandle};

        let win_size = window.outer_size();
        let mut positioned = false;

        if let Ok(handle) = window.window_handle() {
            if let RawWindowHandle::Win32(win32_handle) = handle.as_raw() {
                let hwnd = windows::Win32::Foundation::HWND(win32_handle.hwnd.get());
                let mut mi = MONITORINFO {
                    cbSize: std::mem::size_of::<MONITORINFO>() as u32,
                    ..Default::default()
                };
                let hmonitor = unsafe { MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST) };
                if unsafe { GetMonitorInfoW(hmonitor, &mut mi) }.as_bool() {
                    let target_x = (mi.rcWork.right - win_size.width as i32 - 15).max(0);
                    let target_y = (mi.rcWork.bottom - win_size.height as i32).max(0);
                    println!("[Main] Monitor work area: [{:?}, {:?}], posicionando acima da barra de tarefas: X={}, Y={}",
                        mi.rcWork.right, mi.rcWork.bottom, target_x, target_y);
                    window.set_outer_position(PhysicalPosition::new(target_x, target_y));
                    initial_pos = (target_x, target_y);
                    positioned = true;
                }
            }
        }

        if !positioned {
            if let Some(monitor) = window.current_monitor() {
                let screen_size = monitor.size();
                let target_x = (screen_size.width as i32 - win_size.width as i32 - 15).max(50);
                let target_y = (screen_size.height as i32 - 48 - win_size.height as i32).max(50);
                println!(
                    "[Main] Fallback posicionando em: X={}, Y={}",
                    target_x, target_y
                );
                window.set_outer_position(PhysicalPosition::new(target_x, target_y));
                initial_pos = (target_x, target_y);
            }
        }
    }

    let mut renderer = renderer::SplatRenderer::new(window.clone(), splats).await?;

    if let Some(pos) = args.iter().position(|a| a == "--snapshot") {
        if let Some(out_path) = args.get(pos + 1) {
            println!("[Main] Modo snapshot detectado: gerando {}...", out_path);
            renderer.render_to_image(760, 1160, out_path).await?;
            println!("[Main] Snapshot salvo com sucesso. Encerrando.");
            return Ok(());
        }
    }

    if let Some(pos) = args.iter().position(|a| a == "--multiview") {
        if let Some(out_dir) = args.get(pos + 1) {
            std::fs::create_dir_all(out_dir)?;
            println!("[Main] Gerando multiview 360 e close-up em: {}...", out_dir);

            let p_front = format!("{}/isabella_frontal.png", out_dir);
            renderer
                .render_view(
                    760,
                    1160,
                    glam::Vec3::new(0.0, -0.02, 1.45),
                    glam::Vec3::new(0.0, -0.02, 0.0),
                    wgpu::Color {
                        r: 1.0,
                        g: 1.0,
                        b: 1.0,
                        a: 1.0,
                    },
                    &p_front,
                )
                .await?;
            println!("[Main] [1/4] Frontal concluída.");

            let p_lat = format!("{}/isabella_lateral.png", out_dir);
            renderer
                .render_view(
                    760,
                    1160,
                    glam::Vec3::new(1.35, -0.02, 0.0),
                    glam::Vec3::new(0.0, -0.02, 0.0),
                    wgpu::Color {
                        r: 1.0,
                        g: 1.0,
                        b: 1.0,
                        a: 1.0,
                    },
                    &p_lat,
                )
                .await?;
            println!("[Main] [2/4] Lateral concluída.");

            let p_costas = format!("{}/isabella_costas.png", out_dir);
            renderer
                .render_view(
                    760,
                    1160,
                    glam::Vec3::new(0.0, -0.02, -1.45),
                    glam::Vec3::new(0.0, -0.02, 0.0),
                    wgpu::Color {
                        r: 1.0,
                        g: 1.0,
                        b: 1.0,
                        a: 1.0,
                    },
                    &p_costas,
                )
                .await?;
            println!("[Main] [3/4] Costas concluída.");

            let p_rosto = format!("{}/isabella_rosto.png", out_dir);
            renderer
                .render_view(
                    760,
                    1160,
                    glam::Vec3::new(0.0, 0.14, 0.82),
                    glam::Vec3::new(0.0, 0.14, 0.0),
                    wgpu::Color {
                        r: 1.0,
                        g: 1.0,
                        b: 1.0,
                        a: 1.0,
                    },
                    &p_rosto,
                )
                .await?;
            println!("[Main] [4/4] Foco no Rosto concluída.");

            println!("[Main] Todas as 4 visualizações foram renderizadas com sucesso.");
            return Ok(());
        }
    }

    if let Some(pos) = args.iter().position(|a| a == "--test-emotions") {
        if let Some(out_dir) = args.get(pos + 1) {
            std::fs::create_dir_all(out_dir)?;
            println!(
                "[Main] Renderizando bateria completa de expressões emocionais FACS em: {}...",
                out_dir
            );
            let white = wgpu::Color {
                r: 1.0,
                g: 1.0,
                b: 1.0,
                a: 1.0,
            };
            let eye_close = glam::Vec3::new(0.0, 0.14, 0.82);
            let target_close = glam::Vec3::new(0.0, 0.14, 0.0);

            let emotions: Vec<(&str, &str, ExpressionParams)> = vec![
                (
                    "01_neutro",
                    "Neutro / Atento",
                    ExpressionParams {
                        jaw_open: 0.0,
                        blink: 0.0,
                        smile: 0.08,
                        lip_round: 0.0,
                        lip_spread: 0.0,
                        joy: 0.0,
                        anger: 0.0,
                        disgust: 0.0,
                        fear: 0.0,
                        sadness: 0.0,
                        surprise: 0.0,
                        smirk: 0.0,
                        brow_raise: 0.0,
                    },
                ),
                (
                    "02_alegria_joy",
                    "Alegria / Sedutora",
                    ExpressionParams {
                        jaw_open: 0.0,
                        blink: 0.0,
                        smile: 0.55,
                        lip_round: 0.0,
                        lip_spread: 0.18,
                        joy: 0.75,
                        anger: 0.0,
                        disgust: 0.0,
                        fear: 0.0,
                        sadness: 0.0,
                        surprise: 0.0,
                        smirk: 0.0,
                        brow_raise: 0.10,
                    },
                ),
                (
                    "03_raiva_anger",
                    "Raiva / Tensa (AU4+AU7)",
                    ExpressionParams {
                        jaw_open: 0.0,
                        blink: 0.0,
                        smile: 0.0,
                        lip_round: 0.0,
                        lip_spread: 0.10,
                        joy: 0.0,
                        anger: 0.70,
                        disgust: 0.0,
                        fear: 0.0,
                        sadness: 0.0,
                        surprise: 0.0,
                        smirk: 0.0,
                        brow_raise: 0.0,
                    },
                ),
                (
                    "04_desdem_disgust",
                    "Nojo / Desdém (AU9+AU10)",
                    ExpressionParams {
                        jaw_open: 0.0,
                        blink: 0.0,
                        smile: 0.0,
                        lip_round: 0.0,
                        lip_spread: 0.08,
                        joy: 0.0,
                        anger: 0.10,
                        disgust: 0.65,
                        fear: 0.0,
                        sadness: 0.0,
                        surprise: 0.0,
                        smirk: 0.0,
                        brow_raise: 0.0,
                    },
                ),
                (
                    "05_medo_fear",
                    "Medo / Chocada (AU1+AU2)",
                    ExpressionParams {
                        jaw_open: 0.04,
                        blink: 0.0,
                        smile: 0.0,
                        lip_round: 0.0,
                        lip_spread: 0.15,
                        joy: 0.0,
                        anger: 0.0,
                        disgust: 0.0,
                        fear: 0.65,
                        sadness: 0.0,
                        surprise: 0.15,
                        smirk: 0.0,
                        brow_raise: 0.25,
                    },
                ),
                (
                    "06_tristeza_sadness",
                    "Tristeza / Dengo (AU1+AU15)",
                    ExpressionParams {
                        jaw_open: 0.0,
                        blink: 0.0,
                        smile: 0.0,
                        lip_round: 0.0,
                        lip_spread: 0.0,
                        joy: 0.0,
                        anger: 0.0,
                        disgust: 0.0,
                        fear: 0.0,
                        sadness: 0.75,
                        surprise: 0.0,
                        smirk: 0.0,
                        brow_raise: 0.0,
                    },
                ),
                (
                    "07_surpresa_surprise",
                    "Surpresa / Curiosa (AU1+AU2+AU26)",
                    ExpressionParams {
                        jaw_open: 0.06,
                        blink: 0.0,
                        smile: 0.12,
                        lip_round: 0.20,
                        lip_spread: 0.0,
                        joy: 0.0,
                        anger: 0.0,
                        disgust: 0.0,
                        fear: 0.0,
                        sadness: 0.0,
                        surprise: 0.70,
                        smirk: 0.0,
                        brow_raise: 0.50,
                    },
                ),
                (
                    "08_smirk_flirty",
                    "Smirk / Irônica (AU12 unilat + AU2)",
                    ExpressionParams {
                        jaw_open: 0.0,
                        blink: 0.0,
                        smile: 0.20,
                        lip_round: 0.0,
                        lip_spread: 0.12,
                        joy: 0.15,
                        anger: 0.0,
                        disgust: 0.0,
                        fear: 0.0,
                        sadness: 0.0,
                        surprise: 0.0,
                        smirk: 0.85,
                        brow_raise: 0.0,
                    },
                ),
            ];

            for (idx, (fname, label, ep)) in emotions.iter().enumerate() {
                let out_file = format!("{}/emo_{}.png", out_dir, fname);
                renderer
                    .render_expression_view(
                        760,
                        1160,
                        eye_close,
                        target_close,
                        white,
                        (0.0, 0.0),
                        0.0,
                        *ep,
                        &out_file,
                    )
                    .await?;
                println!(
                    "[Main] [{}/{}] Expressão '{}' concluída: {}",
                    idx + 1,
                    emotions.len(),
                    label,
                    out_file
                );
            }

            println!("[Main] Bateria completa de expressões renderizada com sucesso.");
            return Ok(());
        }
    }

    let shared_state = Arc::new(Mutex::new(SharedState {
        jaw_open: 0.0,
        lip_round: 0.0,
        lip_spread: 0.0,
        smile: 0.18,
        avatar_state: "idle".to_string(),
        emotion: EmotionState::default(),
    }));

    // Iniciar escuta UDP de áudio/visemas/emoções na porta 9888
    let state_clone = shared_state.clone();
    tokio::spawn(async move {
        let socket = match UdpSocket::bind("127.0.0.1:9888").await {
            Ok(s) => s,
            Err(e) => {
                eprintln!("[Audio Bridge] Falha ao abrir porta UDP 9888: {}", e);
                return;
            }
        };
        println!("[Audio Bridge] Escutando visemas e emoções do Voice Bridge em 127.0.0.1:9888");

        let mut buf = [0u8; 2048];
        loop {
            if let Ok((len, _)) = socket.recv_from(&mut buf).await {
                if let Ok(msg) = std::str::from_utf8(&buf[..len]) {
                    if let Ok(val) = serde_json::from_str::<serde_json::Value>(msg) {
                        let mut st = state_clone.lock().unwrap();
                        if let Some(en) = val.get("energy").and_then(|v| v.as_f64()) {
                            st.jaw_open = en as f32;
                        }
                        if let Some(lr) = val.get("lip_round").and_then(|v| v.as_f64()) {
                            st.lip_round = lr as f32;
                        }
                        if let Some(ls) = val.get("lip_spread").and_then(|v| v.as_f64()) {
                            st.lip_spread = ls as f32;
                        }
                        if let Some(sm) = val.get("smile").and_then(|v| v.as_f64()) {
                            st.smile = sm as f32;
                        }
                        if let Some(s) = val.get("state").and_then(|v| v.as_str()) {
                            st.avatar_state = s.to_string();
                        }

                        // Mapear emoção categórica
                        if let Some(emo_name) = val.get("emotion").and_then(|v| v.as_str()) {
                            let intensity = val
                                .get("intensity")
                                .and_then(|v| v.as_f64())
                                .unwrap_or(0.85) as f32;
                            st.emotion = EmotionState::default();
                            match emo_name {
                                "joy" | "happy" => st.emotion.joy = intensity,
                                "anger" | "mad" => st.emotion.anger = intensity,
                                "disgust" => st.emotion.disgust = intensity,
                                "fear" | "shock" => st.emotion.fear = intensity,
                                "sadness" | "sad" => st.emotion.sadness = intensity,
                                "surprise" => {
                                    st.emotion.surprise = intensity;
                                    st.emotion.brow_raise = intensity * 0.8;
                                }
                                "smirk" | "flirt" => st.emotion.smirk = intensity,
                                _ => {}
                            }
                        }
                    }
                }
            }
        }
    });

    let mut fallback_cursor = (0.0f32, 0.0f32);
    let mut smooth_mouse = (0.0f32, 0.0f32);
    let mut cur_expr = ExpressionParams {
        smile: 0.18,
        ..Default::default()
    };

    let mut current_scale: f32 = 1.0;
    let mut is_dragging = false;
    let mut drag_offset = (0i32, 0i32);

    let start_instant = std::time::Instant::now();
    let mut last_frame = start_instant;
    let mut next_blink_time = 2.4f32;
    let mut blink_counter: u32 = 0;

    println!("\n=======================================================");
    println!("       ISABELLA — DESKTOP COMPANION INTERATIVO         ");
    println!("=======================================================");
    println!("  🖱️  Arrastar: Clique e segure com botão esquerdo (Drag-and-Drop)");
    println!("  🔍 Redimensionar: Role a roda do mouse (Scroll Up/Down) ou teclas '+' / '-'");
    println!("  🏠 Resetar tamanho/posição: Pressione '0' ou 'Home'");
    println!("  🎭 Emoções (F1-F7): F1: Neutro | F2: Alegria | F3: Raiva | F4: Nojo");
    println!("                      F5: Medo   | F6: Tristeza | F7: Smirk");
    println!("  ❌ Fechar: Pressione ESC");
    println!("=======================================================\n");

    let hotkey_emotion = Arc::new(Mutex::new(Option::<EmotionState>::None));
    let hotkey_emo_clone = hotkey_emotion.clone();

    event_loop.run(move |event, elwt| {
        elwt.set_control_flow(ControlFlow::Poll);

        match event {
            Event::WindowEvent { event, window_id } if window_id == window.id() => match event {
                WindowEvent::CloseRequested => elwt.exit(),
                WindowEvent::Resized(physical_size) => {
                    renderer.resize(physical_size);
                }
                WindowEvent::CursorMoved { position, .. } => {
                    let win_size = window.inner_size();
                    if win_size.width > 0 && win_size.height > 0 {
                        fallback_cursor.0 =
                            ((position.x as f32 / win_size.width as f32) - 0.5) * 2.0;
                        fallback_cursor.1 =
                            ((position.y as f32 / win_size.height as f32) - 0.5) * 2.0;
                    }
                }
                WindowEvent::MouseInput { state, button, .. } => {
                    if button == MouseButton::Left {
                        match state {
                            ElementState::Pressed => {
                                #[cfg(windows)]
                                {
                                    use windows::Win32::Foundation::POINT;
                                    use windows::Win32::UI::WindowsAndMessaging::GetCursorPos;
                                    let mut pt = POINT { x: 0, y: 0 };
                                    if unsafe { GetCursorPos(&mut pt) }.is_ok() {
                                        if let Ok(win_pos) = window.outer_position() {
                                            is_dragging = true;
                                            drag_offset = (pt.x - win_pos.x, pt.y - win_pos.y);
                                        }
                                    }
                                }
                            }
                            ElementState::Released => {
                                is_dragging = false;
                            }
                        }
                    }
                }
                WindowEvent::MouseWheel { delta, .. } => {
                    let dy = match delta {
                        winit::event::MouseScrollDelta::LineDelta(_x, y) => y,
                        winit::event::MouseScrollDelta::PixelDelta(pos) => (pos.y as f32) / 40.0,
                    };
                    if dy.abs() > 0.05 {
                        let step = if dy > 0.0 { 1.05 } else { 0.95 };
                        apply_avatar_scale(current_scale * step, &mut current_scale, &window);
                    }
                }
                WindowEvent::KeyboardInput { event, .. } => {
                    use winit::keyboard::{Key, NamedKey};
                    if event.state == ElementState::Pressed {
                        match event.logical_key {
                            Key::Named(NamedKey::Escape) => elwt.exit(),
                            Key::Character(ref ch) if ch == "+" || ch == "=" => {
                                apply_avatar_scale(
                                    current_scale * 1.08,
                                    &mut current_scale,
                                    &window,
                                );
                            }
                            Key::Character(ref ch) if ch == "-" || ch == "_" => {
                                apply_avatar_scale(
                                    current_scale * 0.92,
                                    &mut current_scale,
                                    &window,
                                );
                            }
                            Key::Character(ref ch) if ch == "0" => {
                                apply_avatar_scale(1.0, &mut current_scale, &window);
                            }
                            Key::Named(NamedKey::PageUp) => {
                                apply_avatar_scale(
                                    current_scale * 1.10,
                                    &mut current_scale,
                                    &window,
                                );
                            }
                            Key::Named(NamedKey::PageDown) => {
                                apply_avatar_scale(
                                    current_scale * 0.90,
                                    &mut current_scale,
                                    &window,
                                );
                            }
                            Key::Named(NamedKey::Home) => {
                                apply_avatar_scale(1.0, &mut current_scale, &window);
                                #[cfg(windows)]
                                window.set_outer_position(PhysicalPosition::new(
                                    initial_pos.0,
                                    initial_pos.1,
                                ));
                            }
                            Key::Named(NamedKey::F1) => {
                                println!("[Hotkey] Emoção selecionada: NEUTRO");
                                *hotkey_emo_clone.lock().unwrap() = Some(EmotionState::default());
                            }
                            Key::Named(NamedKey::F2) => {
                                println!("[Hotkey] Emoção selecionada: ALEGRIA / SEDUTORA (Joy)");
                                *hotkey_emo_clone.lock().unwrap() = Some(EmotionState {
                                    joy: 0.90,
                                    ..Default::default()
                                });
                            }
                            Key::Named(NamedKey::F3) => {
                                println!("[Hotkey] Emoção selecionada: RAIVA / TENSA (Anger)");
                                *hotkey_emo_clone.lock().unwrap() = Some(EmotionState {
                                    anger: 0.95,
                                    ..Default::default()
                                });
                            }
                            Key::Named(NamedKey::F4) => {
                                println!("[Hotkey] Emoção selecionada: NOJO / DESDÉM (Disgust)");
                                *hotkey_emo_clone.lock().unwrap() = Some(EmotionState {
                                    disgust: 0.92,
                                    ..Default::default()
                                });
                            }
                            Key::Named(NamedKey::F5) => {
                                println!("[Hotkey] Emoção selecionada: MEDO / CHOCADA (Fear)");
                                *hotkey_emo_clone.lock().unwrap() = Some(EmotionState {
                                    fear: 0.90,
                                    brow_raise: 0.45,
                                    ..Default::default()
                                });
                            }
                            Key::Named(NamedKey::F6) => {
                                println!("[Hotkey] Emoção selecionada: TRISTEZA / DENGO (Sadness)");
                                *hotkey_emo_clone.lock().unwrap() = Some(EmotionState {
                                    sadness: 0.92,
                                    ..Default::default()
                                });
                            }
                            Key::Named(NamedKey::F7) => {
                                println!("[Hotkey] Emoção selecionada: SMIRK / IRÔNICA (Flirt)");
                                *hotkey_emo_clone.lock().unwrap() = Some(EmotionState {
                                    smirk: 0.95,
                                    ..Default::default()
                                });
                            }
                            _ => {}
                        }
                    }
                }
                WindowEvent::RedrawRequested => {
                    let now = std::time::Instant::now();
                    let dt = now
                        .duration_since(last_frame)
                        .as_secs_f32()
                        .clamp(0.001, 0.10);
                    last_frame = now;
                    let elapsed = now.duration_since(start_instant).as_secs_f32();

                    // 0. Atualizar posição de arrasto contínuo da janela (Drag-and-Drop a 60 FPS)
                    if is_dragging {
                        #[cfg(windows)]
                        {
                            use windows::Win32::Foundation::POINT;
                            use windows::Win32::UI::Input::KeyboardAndMouse::{
                                GetAsyncKeyState, VK_LBUTTON,
                            };
                            use windows::Win32::UI::WindowsAndMessaging::GetCursorPos;

                            let lmb_down = unsafe { GetAsyncKeyState(VK_LBUTTON.0 as i32) } < 0;
                            if !lmb_down {
                                is_dragging = false;
                            } else {
                                let mut pt = POINT { x: 0, y: 0 };
                                if unsafe { GetCursorPos(&mut pt) }.is_ok() {
                                    let target_x = pt.x - drag_offset.0;
                                    let target_y = pt.y - drag_offset.1;
                                    window.set_outer_position(PhysicalPosition::new(
                                        target_x, target_y,
                                    ));
                                }
                            }
                        }
                    }

                    // 1. Rastreamento global do cursor no desktop (tau = 0.14s)
                    let target_cursor =
                        query_global_cursor_norm(&window).unwrap_or(fallback_cursor);
                    let alpha_mouse = 1.0 - (-dt / 0.14).exp();
                    smooth_mouse.0 += (target_cursor.0 - smooth_mouse.0) * alpha_mouse;
                    smooth_mouse.1 += (target_cursor.1 - smooth_mouse.1) * alpha_mouse;

                    // 2. Ler visemas e estado emocional
                    let (
                        target_jaw,
                        target_round,
                        target_spread,
                        target_smile,
                        is_speaking,
                        target_emo,
                    ) = {
                        let st = shared_state.lock().unwrap();
                        let active_emo = if let Some(ref hk) = *hotkey_emotion.lock().unwrap() {
                            hk.clone()
                        } else {
                            st.emotion.clone()
                        };
                        (
                            st.jaw_open,
                            st.lip_round,
                            st.lip_spread,
                            st.smile,
                            st.avatar_state == "speaking",
                            active_emo,
                        )
                    };

                    let tau_jaw = if target_jaw > cur_expr.jaw_open {
                        0.028
                    } else {
                        0.055
                    };
                    let alpha_jaw = 1.0 - (-dt / tau_jaw).exp();
                    cur_expr.jaw_open += (target_jaw - cur_expr.jaw_open) * alpha_jaw;
                    cur_expr.lip_round += (target_round - cur_expr.lip_round) * alpha_jaw;
                    cur_expr.lip_spread += (target_spread - cur_expr.lip_spread) * alpha_jaw;

                    let idle_smile_wave = 0.16 + 0.10 * (elapsed * 0.38).sin().max(0.0);
                    let desired_smile = if is_speaking {
                        target_smile.max(0.32)
                    } else {
                        target_smile.max(idle_smile_wave)
                    };
                    let alpha_smile = 1.0 - (-dt / 0.18).exp();
                    cur_expr.smile += (desired_smile - cur_expr.smile) * alpha_smile;

                    // Interpolação suave de emoções (tau = 0.22s)
                    let alpha_emo = 1.0 - (-dt / 0.22).exp();
                    cur_expr.joy += (target_emo.joy - cur_expr.joy) * alpha_emo;
                    cur_expr.anger += (target_emo.anger - cur_expr.anger) * alpha_emo;
                    cur_expr.disgust += (target_emo.disgust - cur_expr.disgust) * alpha_emo;
                    cur_expr.fear += (target_emo.fear - cur_expr.fear) * alpha_emo;
                    cur_expr.sadness += (target_emo.sadness - cur_expr.sadness) * alpha_emo;
                    cur_expr.surprise += (target_emo.surprise - cur_expr.surprise) * alpha_emo;
                    cur_expr.smirk += (target_emo.smirk - cur_expr.smirk) * alpha_emo;
                    cur_expr.brow_raise +=
                        (target_emo.brow_raise - cur_expr.brow_raise) * alpha_emo;

                    // 3. Máquina de estados procedural de piscar de olhos
                    let blink_duration = 0.19f32;
                    if elapsed >= next_blink_time {
                        let t_in_blink = elapsed - next_blink_time;
                        if t_in_blink <= blink_duration {
                            if t_in_blink < 0.065 {
                                let u = t_in_blink / 0.065;
                                cur_expr.blink = u * u * (3.0 - 2.0 * u);
                            } else {
                                let u = 1.0 - (t_in_blink - 0.065) / (blink_duration - 0.065);
                                cur_expr.blink = (u * u * (3.0 - 2.0 * u)).clamp(0.0, 1.0);
                            }
                        } else {
                            cur_expr.blink = 0.0;
                            blink_counter = blink_counter.wrapping_add(1);
                            if blink_counter.is_multiple_of(5) {
                                next_blink_time = elapsed + 0.22;
                            } else {
                                let pseudo_rand =
                                    ((blink_counter as f32 * 1.6180339).fract() * 2.8) + 2.8;
                                next_blink_time = elapsed + pseudo_rand;
                            }
                        }
                    } else {
                        cur_expr.blink = 0.0;
                    }

                    match renderer.render(smooth_mouse, cur_expr) {
                        Ok(_) => {}
                        Err(wgpu::SurfaceError::Lost) => {
                            renderer.resize(window.inner_size());
                        }
                        Err(wgpu::SurfaceError::OutOfMemory) => elwt.exit(),
                        Err(e) => eprintln!("[Render Error]: {:?}", e),
                    }
                }
                _ => {}
            },
            Event::AboutToWait => {
                window.request_redraw();
            }
            _ => {}
        }
    })?;

    Ok(())
}
