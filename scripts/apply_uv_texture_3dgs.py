import numpy as np
from PIL import Image, ImageFilter
from plyfile import PlyData, PlyElement
from scipy.ndimage import maximum_filter, minimum_filter, gaussian_filter

ply_path = r"D:\isabella-desktop\assets\models\isabella_bust_4x_1m.ply.bak_20261103_140415"
img_path = r"D:\isabella-desktop\assets\models\isabella_bust_4x_1m_input1024.png"
out_path = r"D:\isabella-desktop\assets\models\isabella_bust_4x_1m.ply"

ply = PlyData.read(ply_path)
v = ply['vertex'].data.copy()
x = v['x'].astype(np.float64)
y = v['y'].astype(np.float64)
z = v['z'].astype(np.float64)

C0 = 0.28209479177387814
r = np.clip(0.5 + C0 * v['f_dc_0'], 0.0, 1.0)
g = np.clip(0.5 + C0 * v['f_dc_1'], 0.0, 1.0)
b = np.clip(0.5 + C0 * v['f_dc_2'], 0.0, 1.0)
op = 1.0 / (1.0 + np.exp(-v['opacity']))

# Load 1024x1024 reference image and apply a subtle UnsharpMask to pre-compensate for the EWA 0.3px^2 low-pass filter
pil_img = Image.open(img_path).convert("RGB")
pil_sharp = pil_img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=135, threshold=2))
img = np.array(pil_sharp).astype(np.float64) / 255.0
img_raw = np.array(pil_img).astype(np.float64) / 255.0
H, W_img, _ = img.shape

def bilinear_sample(im, u, v_coord):
    u = np.clip(u, 0, W_img - 1.001)
    v_coord = np.clip(v_coord, 0, H - 1.001)
    u0 = u.astype(int)
    v0 = v_coord.astype(int)
    du = (u - u0)[:, None]
    dv = (v_coord - v0)[:, None]
    c00 = im[v0, u0]
    c10 = im[v0, u0 + 1]
    c01 = im[v0 + 1, u0]
    c11 = im[v0 + 1, u0 + 1]
    return (1 - du) * (1 - dv) * c00 + du * (1 - dv) * c10 + (1 - du) * dv * c01 + du * dv * c11

# Sub-pixel calibrated face UV projection parameters:
best_params = [0.16271783599385153, 928.3093485916694, 899.6661007353038, 516.2263783124168, 528.3070254118355, 0.1339837245489811, 0.016029790529503405, -57.66698368728337, -158.81597024661713]

def project_pts(px, py, pz, params):
    inv_R, fu, fv, cu, cv, pitch, yaw, k1, k2 = params
    x1 = px * np.cos(yaw) + pz * np.sin(yaw)
    z1 = -px * np.sin(yaw) + pz * np.cos(yaw)
    y2 = py * np.cos(pitch) - x1 * np.sin(pitch)
    x2 = py * np.sin(pitch) + x1 * np.cos(pitch)
    denom = np.maximum(0.1, 1.0 - inv_R * x2)
    xn = z1 / denom
    yn = y2 / denom
    u = cu + fu * xn + k1 * (xn * yn)
    v_c = cv + fv * yn + k2 * (yn * yn)
    return u, v_c, x2

u_all, v_all, x_cam = project_pts(x, y, z, best_params)

# 1. Build 512x512 Z-buffer in UV space for front-surface visibility
uv_bins = 512
ui = np.clip((u_all * (uv_bins / 1024.0)).astype(int), 0, uv_bins - 1)
vi = np.clip((v_all * (uv_bins / 1024.0)).astype(int), 0, uv_bins - 1)

zbuf = np.full((uv_bins, uv_bins), -10.0)
valid_op = op > 0.10
np.maximum.at(zbuf, (vi[valid_op], ui[valid_op]), x_cam[valid_op])
zbuf_smooth = gaussian_filter(maximum_filter(zbuf, size=3), sigma=0.8)

depth_diff = zbuf_smooth[vi, ui] - x_cam
w_depth = np.clip(1.0 - (depth_diff - 0.0020) / 0.0040, 0.0, 1.0)
w_front = np.clip((x - 0.06) / 0.03, 0.0, 1.0)

uv_rgb = bilinear_sample(img, u_all, v_all)

sat = np.maximum(np.maximum(r, g), b) - np.minimum(np.minimum(r, g), b)
luma = 0.299 * r + 0.587 * g + 0.114 * b
uv_luma = 0.299 * uv_rgb[:, 0] + 0.587 * uv_rgb[:, 1] + 0.114 * uv_rgb[:, 2]
uv_sat = np.maximum(np.maximum(uv_rgb[:, 0], uv_rgb[:, 1]), uv_rgb[:, 2]) - np.minimum(np.minimum(uv_rgb[:, 0], uv_rgb[:, 1]), uv_rgb[:, 2])

# Apply UV texture mapping strictly to the facial oval (forehead, eyebrows, eyes, nose, cheeks, lips, chin)
wy_top = np.clip((y - (-0.365)) / 0.020, 0.0, 1.0)
wy_bot = np.clip(((-0.020) - y) / 0.025, 0.0, 1.0)
wz_left = np.clip((z - (-0.105)) / 0.018, 0.0, 1.0)
wz_right = np.clip((0.125 - z) / 0.018, 0.0, 1.0)

face_oval_w = wy_top * wy_bot * wz_left * wz_right * 0.98
hairline_guard = (luma < 0.16) & (uv_luma > 0.22) & ((y < -0.27) | (z > 0.072) | (z < -0.072) | (y > -0.055))
face_oval_w[hairline_guard] = 0.0

w_uv = face_oval_w * w_depth * w_front

r_new = (1.0 - w_uv) * r + w_uv * uv_rgb[:, 0]
g_new = (1.0 - w_uv) * g + w_uv * uv_rgb[:, 1]
b_new = (1.0 - w_uv) * b + w_uv * uv_rgb[:, 2]

# Tighten the scale of interior front-face splats by -0.50 (preserving smooth jawline/chin boundary blending)
face_front_splats = (w_uv > 0.65) & (y > -0.34) & (y < -0.048) & (z > -0.092) & (z < 0.102)
v['scale_0'][face_front_splats] -= 0.50
v['scale_1'][face_front_splats] -= 0.50
v['scale_2'][face_front_splats] -= 0.50
v['opacity'][face_front_splats] += 1.0

# 2. Apply 360-degree Hair Halo cleaning & clean bottom hemline at y > 0.485:
face_ear_neck = (
    ((x > 0.055) & (z > -0.108) & (z < np.where(y > -0.145, 0.088, 0.145)) & (y > -0.365) & (y < -0.02)) |
    ((x > 0.015) & (z > 0.095) & (z < 0.155) & (y > -0.235) & (y < -0.135) & (sat > 0.14)) |
    ((x > 0.020) & (np.abs(z) < 0.088) & (y >= -0.05) & (y < 0.03))
)
dress_bodice = (y > 0.16) & (x > 0.035) & (z > -0.205) & (z < 0.235)
strap_right = (y > -0.005) & (y < 0.22) & (z > 0.145) & (z < 0.225) & (x > 0.025)
protected = face_ear_neck | dress_bodice | strap_right

head_hair_halo = (y < 0.00) & (~protected) & (luma > 0.045)
left_cascade_halo = (y >= 0.00) & (y < 0.46) & (z < -0.09) & (~protected) & ((sat < 0.28) | ((x < 0.02) & (sat < 0.35))) & (luma > 0.045)
right_and_back_halo = (
    (y >= 0.00) & (y < 0.34) & (~protected) &
    (((z > 0.06) & (y < 0.12) & (sat < 0.22)) | ((x < -0.015) & (sat < 0.24))) &
    (luma > 0.045)
)
halo_mask = head_hair_halo | left_cascade_halo | right_and_back_halo

# Suppress outer white halo floaters AND ragged bottom hemline floaters (y > 0.485):
outer_floaters = (halo_mask & (luma > 0.28) & (sat < 0.15)) | (y > 0.485)
v['opacity'][outer_floaters] = -12.0

target_luma = 0.026
scale_factor = np.clip(target_luma / np.maximum(luma[halo_mask], target_luma), 0.03, 0.50)
r_new[halo_mask] = r[halo_mask] * scale_factor
g_new[halo_mask] = g[halo_mask] * scale_factor * 0.94
b_new[halo_mask] = b[halo_mask] * scale_factor * 0.90

v['f_dc_0'] = (r_new - 0.5) / C0
v['f_dc_1'] = (g_new - 0.5) / C0
v['f_dc_2'] = (b_new - 0.5) / C0

# 3. UV-SPACE MICRO-GAUSSIAN DENSIFICATION (arXiv:2601.12770):
# Strictly reuse ONLY already-invisible outer halo floaters (outer_floaters) so zero dark hair splats are ever removed!
reusable_idx = np.where(outer_floaters)[0]
print(f"Reusable suppressed outer-halo splats for UV micro-grid: {len(reusable_idx)}")

# Select central high-frequency facial features (eyebrows, eyes, eyelashes, nose, lips: w_uv > 0.88, x > 0.098, z in [-0.068, 0.072])
high_detail_face = np.where((w_uv > 0.88) & (x > 0.098) & (y > -0.320) & (y < -0.075) & (z > -0.068) & (z < 0.072))[0]
print(f"High-detail interior face splats to micro-densify: {len(high_detail_face)}")

rng = np.random.default_rng(42)
n_clones = min(len(reusable_idx), len(high_detail_face) * 2)
src_idx = np.resize(high_detail_face, n_clones)
dst_idx = reusable_idx[:n_clones]

# Tangent-plane sub-millimeter offsets (dz, dy in [-0.40mm, +0.40mm]) and slightly in front (+0.12mm in x)
dz_off = rng.uniform(-0.00040, 0.00040, size=n_clones)
dy_off = rng.uniform(-0.00040, 0.00040, size=n_clones)

x_micro = x[src_idx] + 0.00012
y_micro = y[src_idx] + dy_off
z_micro = z[src_idx] + dz_off

u_micro, v_micro, _ = project_pts(x_micro, y_micro, z_micro, best_params)
rgb_micro = bilinear_sample(img, u_micro, v_micro)

v['x'][dst_idx] = x_micro.astype(np.float32)
v['y'][dst_idx] = y_micro.astype(np.float32)
v['z'][dst_idx] = z_micro.astype(np.float32)
v['f_dc_0'][dst_idx] = ((rgb_micro[:, 0] - 0.5) / C0).astype(np.float32)
v['f_dc_1'][dst_idx] = ((rgb_micro[:, 1] - 0.5) / C0).astype(np.float32)
v['f_dc_2'][dst_idx] = ((rgb_micro[:, 2] - 0.5) / C0).astype(np.float32)
# Micro-scale: exp(-7.55) = 0.52mm (< 1 pixel radius!), high opacity
v['scale_0'][dst_idx] = -7.55
v['scale_1'][dst_idx] = -7.55
v['scale_2'][dst_idx] = -7.55
v['opacity'][dst_idx] = 2.6
v['rot_0'][dst_idx] = 1.0
v['rot_1'][dst_idx] = 0.0
v['rot_2'][dst_idx] = 0.0
v['rot_3'][dst_idx] = 0.0

print(f"Injected {n_clones} sub-millimeter 4X UV micro-Gaussians onto the 3D facial surface!")

PlyData([PlyElement.describe(v, 'vertex')], text=False).write(out_path)
print(f"Saved micro-densified UV-3DGS PLY to {out_path}")
