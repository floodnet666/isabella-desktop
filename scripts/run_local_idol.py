import json
import os
import time
import numpy as np
import torch
from PIL import Image
from safetensors.torch import load_file
from tensordict import TensorDict

import sys
sys.path.insert(0, r"D:\isabella-desktop\idol-sdk")

from idol.camera import decode_camera
from idol.conditioning import ImageEncoder
from idol.models import BiRefNet, GaussianFixedlenDecoder, LatentSeqMMFlowModel, OctreeProbabilityFixedlenDecoder
from idol.preprocess import preprocess_image
from idol.sampler import sample_flow

WEIGHTS_DIR = r"C:\Users\thiag\.cache\huggingface\hub\models--speridlabs--idol\snapshots\2731c2291fc65a797c5cb627a5e5526fc1490902"
DINOV3_DIR = r"D:\isabella-desktop\assets\models\dinov3_vith16plus_hf"
FLUX2_VAE_DIR = r"C:\Users\thiag\.cache\huggingface\hub\models--black-forest-labs--FLUX.2-klein-4B\snapshots\e7b7dc27f91deacad38e78976d1f2b499d76a294"

def run_local_idol(image_path: str, out_ply_path: str, crop_margin: float = 1.08, steps: int = 60, cfg_strength: float = 3.2, seed: int = 42, num_gaussians: int = 1048576):
    t0 = time.time()
    device = torch.device("cuda")
    with open(os.path.join(WEIGHTS_DIR, "config.json")) as f:
        config = json.load(f)

    print(f"[Local Idol] 1/4 Pre-processando imagem ({image_path}) com crop_margin={crop_margin}...")
    birefnet = BiRefNet()
    birefnet.load_state_dict(load_file(os.path.join(WEIGHTS_DIR, "birefnet.safetensors")), strict=True)
    birefnet = birefnet.eval().requires_grad_(False).half().to(device)

    img = Image.open(image_path)
    prepared = preprocess_image(img, background_remover=birefnet, image_size=config["image_size"], crop_margin=crop_margin)
    prep_path = out_ply_path.replace(".ply", "_input1024.png")
    prepared.save(prep_path)
    print(f"[Local Idol] Imagem 1024x1024 salva em: {prep_path}")

    del birefnet
    torch.cuda.empty_cache()

    print("[Local Idol] 2/4 Extraindo tokens visuais DINOv3 ViT-H/16+ e FLUX.2 VAE em bf16...")
    pixels = torch.from_numpy(np.array(prepared)).permute(2, 0, 1).float().div(255.0)[None].to(device)
    encoder = ImageEncoder(DINOV3_DIR, FLUX2_VAE_DIR, dinov3_dtype="bf16", device="cuda")
    cond = encoder(pixels)
    del encoder
    torch.cuda.empty_cache()
    print(f"[Local Idol] Tokens extraídos: feature1={cond['feature1'].shape}, feature2={cond['feature2'].shape}")

    print(f"[Local Idol] 3/4 Amostrando LatentSeqMMFlowModel ({steps} steps, cfg={cfg_strength})...")
    denoiser = LatentSeqMMFlowModel(**config["denoiser"]["args"])
    denoiser.load_state_dict(load_file(os.path.join(WEIGHTS_DIR, "denoiser.safetensors")), strict=True)
    denoiser = denoiser.eval().requires_grad_(False).to(device)

    torch.manual_seed(seed)
    noise = TensorDict({
        "latent": torch.randn(1, denoiser.q_token_length, denoiser.in_channels, device=device),
        "camera": torch.randn(1, 1, denoiser.cam_channels, device=device),
    }, batch_size=1, device=device)

    torch.backends.cuda.matmul.allow_tf32 = True
    with torch.amp.autocast("cuda", dtype=torch.bfloat16):
        sample = sample_flow(denoiser, noise, cond=cond, neg_cond=cond.apply(torch.zeros_like),
                             steps=steps, rescale_t=3.0, cfg_strength=cfg_strength, verbose=True, batch_cfg=True)

    latent = sample["latent"].float()
    cam_info = decode_camera(sample["camera"][0, 0].float())
    print(f"[Local Idol] Câmera estimada: {cam_info}")

    del denoiser, cond, sample, noise
    torch.cuda.empty_cache()

    print(f"[Local Idol] 4/4 Decodificando Octree e {num_gaussians:,} Gaussianas...")
    decoder = OctreeProbabilityFixedlenDecoder(**config["decoder"]["args"])
    decoder.load_state_dict(load_file(os.path.join(WEIGHTS_DIR, "decoder.safetensors")), strict=True)
    decoder = decoder.eval().requires_grad_(False).to(device)

    decoder_gs = GaussianFixedlenDecoder(**config["decoder_gs"]["args"])
    decoder_gs.load_state_dict(load_file(os.path.join(WEIGHTS_DIR, "decoder_gs.safetensors")), strict=True)
    decoder_gs = decoder_gs.eval().requires_grad_(False).to(device)

    per_anchor = decoder_gs.rep_config["num_gaussians"]
    anchors = OctreeProbabilityFixedlenDecoder.sample(
        decoder, latent,
        num_points=max(1, int(num_gaussians) // per_anchor),
        level=config["max_voxel_level"]
    )
    del decoder
    torch.cuda.empty_cache()

    with torch.amp.autocast("cuda", dtype=torch.bfloat16):
        gs_raw = decoder_gs(anchors, latent)
    gaussian = decoder_gs.to_representation(anchors, gs_raw.float())[0]
    gaussian.save_ply(out_ply_path)
    print(f"[Local Idol] Concluído com sucesso em {time.time() - t0:.1f}s -> {out_ply_path}")

if __name__ == "__main__":
    run_local_idol(
        image_path=r"D:\isabella-desktop\assets\references\isabella_bust_4x.png",
        out_ply_path=r"D:\isabella-desktop\assets\models\isabella_bust_4x_1m.ply",
        crop_margin=1.08,
        steps=60,
        cfg_strength=3.2,
        seed=42,
        num_gaussians=1048576
    )
