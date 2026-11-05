use std::fs::File;
use std::io::{BufRead, BufReader};
use bytemuck::{Pod, Zeroable};
use byteorder::{LittleEndian, ReadBytesExt};

const SH_C0: f32 = 0.28209479177387814;

#[repr(C)]
#[derive(Clone, Copy, Debug, Pod, Zeroable)]
pub struct SplatGpu {
    pub position: [f32; 4], // x, y, z, pad
    pub color: [f32; 4],    // r, g, b, alpha
    pub scale: [f32; 4],    // sx, sy, sz, pad
    pub rotation: [f32; 4], // w, x, y, z (unit quaternion)
}

fn quat_mul(a: [f32; 4], b: [f32; 4]) -> [f32; 4] {
    let [aw, ax, ay, az] = a;
    let [bw, bx, by, bz] = b;
    let w = aw * bw - ax * bx - ay * by - az * bz;
    let x = aw * bx + ax * bw + ay * bz - az * by;
    let y = aw * by - ax * bz + ay * bw + az * bx;
    let z = aw * bz + ax * by - ay * bx + az * bw;
    let norm = (w * w + x * x + y * y + z * z).sqrt().max(1e-8);
    [w / norm, x / norm, y / norm, z / norm]
}

pub fn load_splat_ply(path: &str) -> Result<Vec<SplatGpu>, Box<dyn std::error::Error>> {
    let file = File::open(path)?;
    let mut reader = BufReader::new(file);

    let mut line = String::new();
    let mut vertex_count: usize = 0;

    // 1. Ler cabeçalho PLY
    loop {
        line.clear();
        let bytes_read = reader.read_line(&mut line)?;
        if bytes_read == 0 {
            return Err("Fim de arquivo inesperado no cabeçalho PLY".into());
        }
        let trimmed = line.trim();
        if trimmed.starts_with("element vertex") {
            let parts: Vec<&str> = trimmed.split_whitespace().collect();
            if parts.len() >= 3 {
                vertex_count = parts[2].parse()?;
            }
        }
        if trimmed == "end_header" {
            break;
        }
    }

    if vertex_count == 0 {
        return Err("Nenhum vértice encontrado no arquivo PLY".into());
    }

    println!("[PLY Loader] Carregando {} gaussianas de: {}", vertex_count, path);

    let mut splats = Vec::with_capacity(vertex_count);
    
    let mut min_pos = [f32::MAX, f32::MAX, f32::MAX];
    let mut max_pos = [f32::MIN, f32::MIN, f32::MIN];

    for _ in 0..vertex_count {
        let raw_x = reader.read_f32::<LittleEndian>()?;
        let raw_y = reader.read_f32::<LittleEndian>()?;
        let raw_z = reader.read_f32::<LittleEndian>()?;
        
        let _nx = reader.read_f32::<LittleEndian>()?;
        let _ny = reader.read_f32::<LittleEndian>()?;
        let _nz = reader.read_f32::<LittleEndian>()?;

        let f_dc_0 = reader.read_f32::<LittleEndian>()?;
        let f_dc_1 = reader.read_f32::<LittleEndian>()?;
        let f_dc_2 = reader.read_f32::<LittleEndian>()?;

        let opacity = reader.read_f32::<LittleEndian>()?;

        let scale_0 = reader.read_f32::<LittleEndian>()?;
        let scale_1 = reader.read_f32::<LittleEndian>()?;
        let scale_2 = reader.read_f32::<LittleEndian>()?;

        let rot_0 = reader.read_f32::<LittleEndian>()?;
        let rot_1 = reader.read_f32::<LittleEndian>()?;
        let rot_2 = reader.read_f32::<LittleEndian>()?;
        let rot_3 = reader.read_f32::<LittleEndian>()?;

        // Rotação própria de 180 graus (det = +1) em torno de (1, 0, 1)/sqrt(2) para alinhar (+raw_x) para a câmera (+Z) sem espelhamento horizontal:
        // Frontal (+raw_x) -> +z (voltado para a câmera)
        // Cabeça (-raw_y)  -> +y (topo da tela)
        // Lado direito da imagem (+raw_z) -> +x (lado direito da tela do espectador, idêntico à foto de referência e ao Blender)
        let x = raw_z;
        let y = -raw_y;
        let z = raw_x;

        min_pos[0] = min_pos[0].min(x);
        min_pos[1] = min_pos[1].min(y);
        min_pos[2] = min_pos[2].min(z);
        max_pos[0] = max_pos[0].max(x);
        max_pos[1] = max_pos[1].max(y);
        max_pos[2] = max_pos[2].max(z);

        // Cor de harmônicos esféricos (SH0 -> RGB).
        // Garantir piso mínimo de 0.008 (~2/255) para que pixels escuros do cabelo
        // mantenham preto profundo sem coincidir com o ColorKey RGB(0,0,0) de transparência
        let r = (0.5 + SH_C0 * f_dc_0).clamp(0.008, 1.0);
        let g = (0.5 + SH_C0 * f_dc_1).clamp(0.008, 1.0);
        let b = (0.5 + SH_C0 * f_dc_2).clamp(0.008, 1.0);

        // Opacidade
        let alpha = (1.0 / (1.0 + (-opacity).exp())).clamp(0.0, 1.0);

        // Escala
        let sx = scale_0.exp();
        let sy = scale_1.exp();
        let sz = scale_2.exp();

        // Transformar o quatérnion de rotação exatamente pela rotação própria de 180 graus em torno do eixo (1, 0, 1) / sqrt(2)
        let s2 = std::f32::consts::FRAC_1_SQRT_2;
        let q_axis = [0.0, s2, 0.0, s2];
        let q_rot = quat_mul(q_axis, [rot_0, rot_1, rot_2, rot_3]);

        splats.push(SplatGpu {
            position: [x, y, z, 1.0],
            color: [r, g, b, alpha],
            scale: [sx, sy, sz, 0.0],
            rotation: q_rot,
        });
    }

    println!("[PLY Loader] Bounding box frontal: X[{:.2}, {:.2}], Y[{:.2}, {:.2}], Z[{:.2}, {:.2}]",
        min_pos[0], max_pos[0], min_pos[1], max_pos[1], min_pos[2], max_pos[2]);

    // Centralizar modelo na origem
    let center = [
        (min_pos[0] + max_pos[0]) * 0.5,
        (min_pos[1] + max_pos[1]) * 0.5,
        (min_pos[2] + max_pos[2]) * 0.5,
    ];

    for s in &mut splats {
        s.position[0] -= center[0];
        s.position[1] -= center[1];
        s.position[2] -= center[2];
    }

    Ok(splats)
}
