struct Uniforms {
    view_proj: mat4x4<f32>,
    view: mat4x4<f32>,
    viewport: vec4<f32>,  // width, height, focal_x, focal_y
    params: vec4<f32>,    // jaw_open, time, mouse_x, mouse_y
    expr: vec4<f32>,      // blink, smile, lip_round, lip_spread
    emotion_a: vec4<f32>, // joy, anger, disgust, fear
    emotion_b: vec4<f32>, // sadness, surprise, smirk, brow_raise
};

@group(0) @binding(0)
var<uniform> uniforms: Uniforms;

struct VertexInput {
    @location(0) quad_pos: vec2<f32>,
    @location(1) splat_pos: vec4<f32>,
    @location(2) splat_color: vec4<f32>,
    @location(3) splat_scale: vec4<f32>,
    @location(4) splat_rot: vec4<f32>, // w, x, y, z (unit quaternion)
};

struct VertexOutput {
    @builtin(position) clip_pos: vec4<f32>,
    @location(0) uv: vec2<f32>,
    @location(1) color: vec4<f32>,
};

fn rotate_head_vec(v: vec3<f32>, yaw: f32, pitch: f32, roll: f32) -> vec3<f32> {
    let cr = cos(roll);
    let sr = sin(roll);
    let v_r = vec3<f32>(v.x * cr - v.y * sr, v.x * sr + v.y * cr, v.z);

    let cp = cos(pitch);
    let sp = sin(pitch);
    let v_p = vec3<f32>(v_r.x, v_r.y * cp - v_r.z * sp, v_r.y * sp + v_r.z * cp);

    let cy = cos(yaw);
    let sy = sin(yaw);
    return vec3<f32>(v_p.x * cy + v_p.z * sy, v_p.y, -v_p.x * sy + v_p.z * cy);
}

@vertex
fn vs_main(in: VertexInput) -> VertexOutput {
    var out: VertexOutput;
    out.uv = in.quad_pos;

    let jaw_open = clamp(uniforms.params.x, 0.0, 1.0);
    let time = uniforms.params.y;
    let mouse_x = clamp(uniforms.params.z, -1.0, 1.0);
    let mouse_y = clamp(uniforms.params.w, -1.0, 1.0);

    let blink = clamp(uniforms.expr.x, 0.0, 1.0);
    let base_smile = clamp(uniforms.expr.y, 0.0, 1.0);
    let lip_round = clamp(uniforms.expr.z, 0.0, 1.0);
    let lip_spread = clamp(uniforms.expr.w, 0.0, 1.0);

    // Canais Emocionais FACS
    let emo_joy      = clamp(uniforms.emotion_a.x, 0.0, 1.0);
    let emo_anger    = clamp(uniforms.emotion_a.y, 0.0, 1.0);
    let emo_disgust  = clamp(uniforms.emotion_a.z, 0.0, 1.0);
    let emo_fear     = clamp(uniforms.emotion_a.w, 0.0, 1.0);
    let emo_sadness  = clamp(uniforms.emotion_b.x, 0.0, 1.0);
    let emo_surprise = clamp(uniforms.emotion_b.y, 0.0, 1.0);
    let emo_smirk    = clamp(uniforms.emotion_b.z, 0.0, 1.0);
    let brow_raise   = clamp(uniforms.emotion_b.w, 0.0, 1.0);

    let smile = clamp(base_smile + emo_joy * 0.75, 0.0, 1.0);

    var pos = in.splat_pos.xyz;
    let s = in.splat_scale.xyz;
    var col = in.splat_color;
    var world_y_stretch = 1.0;

    // Centros anatômicos verificados dos olhos esquerdo e direito
    let le_cx = -0.1165;
    let le_cy = 0.2905 + 0.10 * (pos.x - le_cx);
    let re_cx = -0.0215;
    let re_cy = 0.3035 + 0.12 * (pos.x - re_cx);

    let dl_x = (pos.x - le_cx) / 0.033;
    let dl_y = (pos.y - le_cy) / 0.021;
    let dist2_l = dl_x * dl_x + dl_y * dl_y;

    let dr_x = (pos.x - re_cx) / 0.033;
    let dr_y = (pos.y - re_cy) / 0.021;
    let dist2_r = dr_x * dr_x + dr_y * dr_y;

    let is_left = dist2_l < dist2_r;
    let dist2 = select(dist2_r, dist2_l, is_left);
    let eye_cy = select(re_cy, le_cy, is_left);
    let lower_lash_y = eye_cy - 0.0110;

    // =========================================================================
    // 1. SOBRANCELHAS & GLABELA (AU1, AU2, AU4 - Alegria, Raiva, Nojo, Medo, Tristeza, Surpresa, Smirk)
    // Microdeformações sutis e perfeitamente contínuas (C1/C-infinito) sem cortes rígidos
    // =========================================================================
    if (pos.z > 0.115 && pos.y > 0.250 && pos.y < 0.420 && pos.x > -0.190 && pos.x < 0.070) {
        let w_brow_y = smoothstep(0.250, 0.300, pos.y) * smoothstep(0.420, 0.360, pos.y);
        let w_brow_x = smoothstep(-0.190, -0.140, pos.x) * smoothstep(0.070, 0.020, pos.x);
        let w_brow_z = smoothstep(0.115, 0.145, pos.z);
        let w_brow = w_brow_y * w_brow_x * w_brow_z;

        let glabella_cx = -0.068;
        let dx_g = pos.x - glabella_cx;
        let inner_factor = smoothstep(0.040, -0.005, abs(dx_g));
        let outer_factor = 1.0 - inner_factor;

        // 1a. RAIVA / ANGER (AU4 - Brow Lowerer): Sobrancelhas descem sutilmente e convergem para o centro
        if (emo_anger > 0.001) {
            let dy_anger = -0.0030 * emo_anger * w_brow;
            let center_pull = clamp(dx_g / 0.025, -1.0, 1.0);
            let dx_anger = -center_pull * 0.0015 * emo_anger * w_brow;
            pos.y += dy_anger;
            pos.x += dx_anger;
        }

        // 1b. NOJO / DISGUST (AU9): Sutil rebaixamento medial
        if (emo_disgust > 0.001) {
            let dy_disgust = -0.0020 * emo_disgust * w_brow * inner_factor;
            pos.y += dy_disgust;
        }

        // 1c. SURPRESA (AU1+AU2) & BROW RAISE: Elevação suave de toda a sobrancelha/fronte
        let high_brow = emo_surprise * 0.0038 + brow_raise * 0.0032;
        if (high_brow > 0.001) {
            pos.y += high_brow * w_brow;
        }

        // 1d. MEDO / FEAR (AU1): Sobrancelhas sobem sutilmente no centro
        if (emo_fear > 0.001) {
            let dy_fear = 0.0028 * emo_fear * w_brow * inner_factor;
            pos.y += dy_fear;
        }

        // 1e. TRISTEZA / SADNESS (AU1 inner up + AU4 outer down): Arco suave de dengo/empatia
        if (emo_sadness > 0.001) {
            let dy_inner_up = 0.0032 * emo_sadness * w_brow * inner_factor;
            let dy_outer_down = -0.0015 * emo_sadness * w_brow * outer_factor;
            pos.y += (dy_inner_up + dy_outer_down);
        }

        // 1f. SMIRK / DESAFIADORA (AU2 unilateral): Sobrancelha direita (espectador) sobe suavemente
        if (emo_smirk > 0.001 && !is_left) {
            pos.y += 0.0032 * emo_smirk * w_brow;
        }
    }

    // =========================================================================
    // 2. PÁLPEBRAS & OLHOS (AU7 - Lid Tightener, Eye Blink)
    // Semicerrar de olhos sutil e piscar natural (zero estrias escuras ou rasgos)
    // =========================================================================
    let eye_tighten = clamp(emo_anger * 0.35 + emo_disgust * 0.30 + emo_smirk * 0.20, 0.0, 0.50);
    let eff_blink = clamp(blink + smile * 0.08 + eye_tighten, 0.0, 1.0);

    if (pos.z > 0.135 && pos.y > 0.255 && pos.y < 0.348 && dist2 < 1.70) {
        let w_eye = exp(-1.45 * dist2) * smoothstep(0.135, 0.158, pos.z);
        let orig_y = pos.y;

        // Piscar e squint suave
        if (eff_blink > 0.001) {
            if (orig_y > lower_lash_y) {
                let dy = -(orig_y - lower_lash_y) * 0.85 * eff_blink * w_eye;
                pos.y += dy;
                pos.z += 0.0020 * eff_blink * w_eye;
                world_y_stretch += 0.55 * eff_blink * w_eye;
            } else {
                pos.y += 0.0015 * (eff_blink + smile * 0.3) * w_eye;
            }

            if (blink > 0.10 && dist2 < 1.05 && pos.z > 0.145) {
                let close_factor = smoothstep(0.10, 0.72, blink) * exp(-1.25 * dist2);
                let lash_band = smoothstep(lower_lash_y + 0.0065, lower_lash_y + 0.0018, pos.y);
                let crease_band = smoothstep(eye_cy + 0.003, eye_cy + 0.012, orig_y);
                let lid_skin = mix(vec3<f32>(0.72, 0.48, 0.35), vec3<f32>(0.56, 0.36, 0.26), crease_band * 0.55);
                let lash_dark = vec3<f32>(0.05, 0.035, 0.028);
                let target_lid_rgb = mix(lid_skin, lash_dark, lash_band);
                col = vec4<f32>(mix(col.rgb, target_lid_rgb, clamp(close_factor * 1.15, 0.0, 0.99)), col.a);
            }
        }
    }

    // =========================================================================
    // 3. BOCA, LÁBIOS & MANDÍBULA (Alegria, Raiva, Nojo, Medo, Tristeza, Surpresa, Smirk, Visemas)
    // Microdeformações expressivas e orgânicas
    // =========================================================================
    if (pos.z > 0.110 && pos.y > 0.080 && pos.y < 0.268 && pos.x > -0.155 && pos.x < 0.035) {
        let mouth_cx = -0.0615;
        let part_y = 0.1846 + 0.125 * (pos.x - mouth_cx);
        let dx_m = pos.x - mouth_cx;
        let dy_m = pos.y - part_y;

        let w_mouth_x = exp(-0.5 * (dx_m / 0.035) * (dx_m / 0.035));
        let w_front_m = smoothstep(0.125, 0.168, pos.z);
        let w_depth_all = smoothstep(0.02, 0.11, pos.z);

        // Abertura mandibular sutil (apenas para fala ou surpresa suave)
        let eff_jaw = clamp(jaw_open + emo_surprise * 0.12, 0.0, 1.0);
        if (eff_jaw > 0.001) {
            let norm_x = clamp(dx_m / 0.027, -1.0, 1.0);
            let oval_aperture = pow(max(0.0, 1.0 - norm_x * norm_x), 1.6);

            let w_jaw_global = exp(-0.5 * (dx_m / 0.045) * (dx_m / 0.045)) * smoothstep(0.080, 0.145, pos.y) * smoothstep(part_y + 0.015, part_y - 0.010, pos.y) * w_depth_all;
            pos.y -= 0.0045 * eff_jaw * w_jaw_global;
            pos.z -= 0.0015 * eff_jaw * w_jaw_global;

            if (dy_m < -0.0005) {
                let w_llip_y = smoothstep(0.115, 0.165, pos.y);
                let w_llip = oval_aperture * w_llip_y * w_depth_all;
                pos.y -= 0.0060 * eff_jaw * w_llip;
                pos.z -= 0.0012 * eff_jaw * w_llip;
            } else if (dy_m >= -0.0005 && dy_m < 0.020) {
                let w_ulip = oval_aperture * smoothstep(0.020, 0.001, dy_m) * w_depth_all;
                pos.y += 0.0018 * eff_jaw * w_ulip;
            }

            if (eff_jaw > 0.15 && abs(dy_m) <= 0.0030 && abs(dx_m) < 0.022 && pos.z > 0.168) {
                let w_seam = oval_aperture * (1.0 - abs(dy_m) / 0.0030);
                world_y_stretch += 1.40 * eff_jaw * w_seam;
                pos.y -= 0.0020 * eff_jaw * w_seam;

                let is_upper_teeth = smoothstep(0.0002, 0.0020, dy_m) * smoothstep(0.25, 0.55, eff_jaw) * oval_aperture;
                let oral_dark = vec3<f32>(0.18, 0.065, 0.075);
                let teeth_tint = vec3<f32>(0.82, 0.77, 0.75);
                let inner_rgb = mix(oral_dark, teeth_tint, is_upper_teeth * 0.50);
                let shade_w = clamp((eff_jaw - 0.10) * 1.05 * w_seam, 0.0, 0.82);
                col = vec4<f32>(mix(col.rgb, inner_rgb, shade_w), col.a);
            }
        }

        let w_lip_zone = exp(-0.5 * ((dx_m / 0.045) * (dx_m / 0.045) + (dy_m / 0.022) * (dy_m / 0.022))) * w_front_m;

        // Arredondamento labial
        let eff_round = clamp(lip_round + emo_surprise * 0.25, 0.0, 1.0);
        if (eff_round > 0.001) {
            pos.x -= dx_m * 0.15 * eff_round * w_lip_zone;
            pos.z += 0.0030 * eff_round * w_lip_zone;
        }

        // Lábios largos / Sorriso / Fricativa
        let eff_wide = smile * 0.15 + lip_spread * 0.10;
        if (eff_wide > 0.001) {
            pos.x += dx_m * eff_wide * w_lip_zone;
            let corner_factor = smoothstep(0.012, 0.038, abs(dx_m)) * w_lip_zone;
            pos.y += (0.0090 * smile + 0.0030 * lip_spread) * corner_factor;
            pos.z -= 0.0015 * smile * corner_factor;
        }

        // TRISTEZA (AU15 - Lip Corner Depressor): Cantos caem suavemente + dengo
        if (emo_sadness > 0.001) {
            let corner_sad = smoothstep(0.012, 0.038, abs(dx_m)) * w_lip_zone;
            pos.y -= 0.0045 * emo_sadness * corner_sad;
            if (abs(dx_m) < 0.018 && dy_m < 0.0) {
                pos.y += 0.0025 * emo_sadness * (1.0 - abs(dx_m) / 0.018) * w_front_m;
                pos.z += 0.0015 * emo_sadness * w_front_m;
            }
        }

        // SMIRK (AU12 unilateral): Canto direito do espectador sobe de forma provocante e charmosa
        if (emo_smirk > 0.001 && dx_m > 0.006) {
            let corner_smirk = smoothstep(0.006, 0.036, dx_m) * w_lip_zone;
            pos.y += 0.0065 * emo_smirk * corner_smirk;
            pos.x += 0.0025 * emo_smirk * corner_smirk;
            pos.z += 0.0012 * emo_smirk * corner_smirk;
        }

        // Elevação zigomática (maçãs do rosto) no sorriso
        if (smile > 0.01 && pos.y > 0.195 && pos.y < 0.268) {
            let dc_l = vec2<f32>((pos.x - (-0.118)) / 0.036, (pos.y - 0.232) / 0.028);
            let dc_r = vec2<f32>((pos.x - (-0.008)) / 0.036, (pos.y - 0.244) / 0.028);
            let w_cheek = (exp(-dot(dc_l, dc_l)) + exp(-dot(dc_r, dc_r))) * w_front_m;
            pos.y += 0.0035 * smile * w_cheek;
            pos.z += 0.0020 * smile * w_cheek;
        }
    }

    // =========================================================================
    // 5. CICLO DE RESPIRAÇÃO TORÁCICA ORGÂNICA (IDLE BREATHING)
    // =========================================================================
    let breath_raw = 0.5 + 0.5 * sin(time * 1.45);
    let breath_wave = pow(breath_raw, 1.6);
    if (pos.y > -0.45 && pos.y < 0.05 && pos.z > -0.02) {
        let w_chest_y = smoothstep(-0.44, -0.22, pos.y) * smoothstep(0.05, -0.06, pos.y);
        let w_chest_z = smoothstep(-0.02, 0.08, pos.z);
        let w_chest = w_chest_y * w_chest_z;
        pos.z += 0.0048 * breath_wave * w_chest;
        pos.y += 0.0026 * breath_wave * w_chest;
    }

    pos.y += breath_wave * 0.0016;

    // =========================================================================
    // 6. CINEMÁTICA CERVICAL DA CABEÇA + MODULAÇÃO POSTURAL EMOCIONAL
    // =========================================================================
    let neck_pivot = vec3<f32>(-0.055, 0.045, 0.040);
    let w_head = smoothstep(-0.045, 0.095, pos.y);

    let idle_yaw   = 0.024 * sin(time * 0.67) + 0.011 * sin(time * 1.51);
    let idle_pitch = 0.016 * sin(time * 0.53 + 1.1) + 0.010 * breath_wave;
    let idle_roll  = 0.019 * sin(time * 0.41 + 2.3) + 0.028 * smile;

    // Postura da cabeça calibrada com referências anatômicas (emtions grid.jpg / ref faces.jpg):
    // Tristeza: queixo abaixa (-pitch) e cabeça inclina dengosa (+roll)
    // Smirk: cabeça charmosa e inclinada de lado (+roll, +yaw)
    // Surpresa: cabeça levanta em curiosidade (+pitch)
    // Raiva: queixo recolhido para frente (-pitch)
    // Nojo: cabeça recua (+pitch, -yaw)
    let emo_pitch_offset = -0.075 * emo_sadness + 0.045 * emo_surprise - 0.050 * emo_anger + 0.035 * emo_disgust + 0.020 * emo_joy;
    let emo_roll_offset  = 0.075 * emo_smirk + 0.045 * emo_sadness + 0.035 * emo_joy - 0.025 * emo_fear;
    let emo_yaw_offset   = 0.055 * emo_smirk - 0.060 * emo_disgust;

    let head_yaw   = (mouse_x * 0.22 + idle_yaw + emo_yaw_offset) * w_head;
    let head_pitch = (-mouse_y * 0.14 + idle_pitch + jaw_open * 0.015 + emo_pitch_offset) * w_head;
    let head_roll  = (-mouse_x * 0.055 + idle_roll + emo_roll_offset) * w_head;

    if (w_head > 0.001) {
        pos = neck_pivot + rotate_head_vec(pos - neck_pivot, head_yaw, head_pitch, head_roll);
    }

    if (pos.y < 0.08 && (pos.x < -0.11 || pos.z < -0.02)) {
        let w_hair = smoothstep(0.08, -0.25, pos.y);
        let hair_sway = sin(time * 1.35 - pos.y * 6.0) * 0.0032 + mouse_x * 0.006;
        pos.x += hair_sway * w_hair;
    }

    out.color = col;

    let cam_pos4 = uniforms.view * vec4<f32>(pos, 1.0);
    let center_clip = uniforms.view_proj * vec4<f32>(pos, 1.0);

    if (cam_pos4.z > -0.05 || center_clip.w <= 0.05) {
        out.clip_pos = vec4<f32>(0.0, 0.0, 2.0, 1.0);
        return out;
    }

    let w = in.splat_rot.x;
    let x = in.splat_rot.y;
    let y = in.splat_rot.z;
    let z = in.splat_rot.w;

    var col0 = vec3<f32>(
        1.0 - 2.0 * (y * y + z * z),
        2.0 * (x * y + w * z),
        2.0 * (x * z - w * y)
    ) * s.x;

    var col1 = vec3<f32>(
        2.0 * (x * y - w * z),
        1.0 - 2.0 * (x * x + z * z),
        2.0 * (y * z + w * x)
    ) * s.y;

    var col2 = vec3<f32>(
        2.0 * (x * z + w * y),
        2.0 * (y * z - w * x),
        1.0 - 2.0 * (x * x + y * y)
    ) * s.z;

    if (world_y_stretch > 1.001) {
        col0.y *= world_y_stretch;
        col1.y *= world_y_stretch;
        col2.y *= world_y_stretch;
    }

    if (w_head > 0.001) {
        col0 = rotate_head_vec(col0, head_yaw, head_pitch, head_roll);
        col1 = rotate_head_vec(col1, head_yaw, head_pitch, head_roll);
        col2 = rotate_head_vec(col2, head_yaw, head_pitch, head_roll);
    }

    let w0 = (uniforms.view * vec4<f32>(col0, 0.0)).xyz;
    let w1 = (uniforms.view * vec4<f32>(col1, 0.0)).xyz;
    let w2 = (uniforms.view * vec4<f32>(col2, 0.0)).xyz;

    let fx = uniforms.viewport.z;
    let fy = uniforms.viewport.w;
    let tz = min(cam_pos4.z, -0.1);
    let inv_z = -1.0 / tz;

    let lim_x = 1.3 * (0.5 * uniforms.viewport.x / fx);
    let lim_y = 1.3 * (0.5 * uniforms.viewport.y / fy);
    let tx_z = clamp(cam_pos4.x * inv_z, -lim_x, lim_x);
    let ty_z = clamp(cam_pos4.y * inv_z, -lim_y, lim_y);

    let u0 = vec2<f32>(
        fx * (w0.x * inv_z - tx_z * w0.z * inv_z),
        fy * (w0.y * inv_z - ty_z * w0.z * inv_z)
    );
    let u1 = vec2<f32>(
        fx * (w1.x * inv_z - tx_z * w1.z * inv_z),
        fy * (w1.y * inv_z - ty_z * w1.z * inv_z)
    );
    let u2 = vec2<f32>(
        fx * (w2.x * inv_z - tx_z * w2.z * inv_z),
        fy * (w2.y * inv_z - ty_z * w2.z * inv_z)
    );

    let cov_a = u0.x * u0.x + u1.x * u1.x + u2.x * u2.x + 0.3;
    let cov_b = u0.x * u0.y + u1.x * u1.y + u2.x * u2.y;
    let cov_c = u0.y * u0.y + u1.y * u1.y + u2.y * u2.y + 0.3;

    let mid = 0.5 * (cov_a + cov_c);
    let half_diff = 0.5 * (cov_a - cov_c);
    let disc = sqrt(max(0.01, half_diff * half_diff + cov_b * cov_b));
    let lambda1 = max(0.1, mid + disc);
    let lambda2 = max(0.1, mid - disc);

    let r1 = min(sqrt(lambda1) * 3.0, 256.0);
    let r2 = min(sqrt(lambda2) * 3.0, 256.0);

    var v1 = vec2<f32>(cov_b, lambda1 - cov_a);
    let v1_len = length(v1);
    if (v1_len < 1e-5) {
        if (cov_a >= cov_c) {
            v1 = vec2<f32>(1.0, 0.0);
        } else {
            v1 = vec2<f32>(0.0, 1.0);
        }
    } else {
        v1 = v1 / v1_len;
    }
    let v2 = vec2<f32>(-v1.y, v1.x);

    let offset_px = in.quad_pos.x * r1 * v1 + in.quad_pos.y * r2 * v2;
    let offset_ndc = offset_px * 2.0 / uniforms.viewport.xy;

    out.clip_pos = center_clip + vec4<f32>(offset_ndc * center_clip.w, 0.0, 0.0);
    return out;
}

@fragment
fn fs_main(in: VertexOutput) -> @location(0) vec4<f32> {
    let dist_sq = dot(in.uv, in.uv);
    if (dist_sq > 1.0) {
        discard;
    }

    let gauss_weight = exp(-4.5 * dist_sq);
    let final_alpha = min(0.99, in.color.a * gauss_weight);

    if (final_alpha < 0.004) {
        discard;
    }

    let srgb = clamp(in.color.rgb, vec3<f32>(0.0), vec3<f32>(1.0));
    let linear_rgb = max(pow(srgb, vec3<f32>(2.2)), vec3<f32>(0.008));
    let rgb = linear_rgb * final_alpha;
    return vec4<f32>(rgb, final_alpha);
}
