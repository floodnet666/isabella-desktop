use bytemuck::{Pod, Zeroable};
use glam::{Mat4, Vec3};
use std::sync::Arc;
use wgpu::util::DeviceExt;
use winit::window::Window;

use crate::ply_loader::SplatGpu;

#[repr(C)]
#[derive(Clone, Copy, Pod, Zeroable)]
struct QuadVertex {
    pos: [f32; 2],
}

const QUAD_VERTICES: [QuadVertex; 6] = [
    QuadVertex { pos: [-1.0, -1.0] },
    QuadVertex { pos: [1.0, -1.0] },
    QuadVertex { pos: [-1.0, 1.0] },
    QuadVertex { pos: [-1.0, 1.0] },
    QuadVertex { pos: [1.0, -1.0] },
    QuadVertex { pos: [1.0, 1.0] },
];

#[repr(C)]
#[derive(Clone, Copy, Pod, Zeroable)]
struct Uniforms {
    view_proj: [f32; 16],
    view: [f32; 16],
    viewport: [f32; 4],  // width, height, focal_x, focal_y
    params: [f32; 4],    // jaw_open, time, mouse_x, mouse_y
    expr: [f32; 4],      // blink, smile, lip_round, lip_spread
    emotion_a: [f32; 4], // joy, anger, disgust, fear
    emotion_b: [f32; 4], // sadness, surprise, smirk, brow_raise
}

#[derive(Clone, Copy, Debug, Default)]
pub struct ExpressionParams {
    pub jaw_open: f32,
    pub blink: f32,
    pub smile: f32,
    pub lip_round: f32,
    pub lip_spread: f32,
    // Canais emocionais FACS
    pub joy: f32,
    pub anger: f32,
    pub disgust: f32,
    pub fear: f32,
    pub sadness: f32,
    pub surprise: f32,
    pub smirk: f32,
    pub brow_raise: f32,
}

pub struct SplatRenderer {
    surface: wgpu::Surface<'static>,
    device: wgpu::Device,
    queue: wgpu::Queue,
    config: wgpu::SurfaceConfiguration,
    pipeline: wgpu::RenderPipeline,
    quad_buffer: wgpu::Buffer,
    instance_buffer: wgpu::Buffer,
    instance_count: u32,
    uniform_buffer: wgpu::Buffer,
    uniform_bind_group: wgpu::BindGroup,
    splats: Vec<SplatGpu>,
    start_time: std::time::Instant,
}

impl SplatRenderer {
    pub async fn new(
        window: Arc<Window>,
        mut splats: Vec<SplatGpu>,
    ) -> Result<Self, Box<dyn std::error::Error>> {
        let size = window.inner_size();
        let instance = wgpu::Instance::new(wgpu::InstanceDescriptor {
            backends: wgpu::Backends::VULKAN | wgpu::Backends::DX12,
            ..Default::default()
        });

        let surface = instance.create_surface(window.clone())?;
        let adapter = instance
            .request_adapter(&wgpu::RequestAdapterOptions {
                power_preference: wgpu::PowerPreference::HighPerformance,
                compatible_surface: Some(&surface),
                force_fallback_adapter: false,
            })
            .await
            .ok_or("Nenhum adaptador GPU compativel encontrado")?;

        let (device, queue) = adapter
            .request_device(
                &wgpu::DeviceDescriptor {
                    required_features: wgpu::Features::empty(),
                    required_limits: wgpu::Limits::default(),
                    label: Some("Isabella Device"),
                },
                None,
            )
            .await?;

        let caps = surface.get_capabilities(&adapter);

        let surface_format = caps
            .formats
            .iter()
            .copied()
            .find(|f| f.is_srgb())
            .unwrap_or(caps.formats[0]);

        let alpha_mode = if caps
            .alpha_modes
            .contains(&wgpu::CompositeAlphaMode::PreMultiplied)
        {
            println!("[Renderer] Alpha mode PreMultiplied ativado para fundo 100% transparente.");
            wgpu::CompositeAlphaMode::PreMultiplied
        } else if caps
            .alpha_modes
            .contains(&wgpu::CompositeAlphaMode::PostMultiplied)
        {
            println!("[Renderer] Alpha mode PostMultiplied ativado.");
            wgpu::CompositeAlphaMode::PostMultiplied
        } else if caps.alpha_modes.contains(&wgpu::CompositeAlphaMode::Auto) {
            println!("[Renderer] Alpha mode Auto ativado.");
            wgpu::CompositeAlphaMode::Auto
        } else {
            println!("[Renderer] Fallback alpha mode: {:?}", caps.alpha_modes[0]);
            caps.alpha_modes[0]
        };

        let config = wgpu::SurfaceConfiguration {
            usage: wgpu::TextureUsages::RENDER_ATTACHMENT,
            format: surface_format,
            width: size.width.max(1),
            height: size.height.max(1),
            present_mode: wgpu::PresentMode::AutoVsync,
            alpha_mode,
            view_formats: vec![],
            desired_maximum_frame_latency: 2,
        };
        surface.configure(&device, &config);

        // Ordenar splats back-to-front ao longo do eixo Z frontal (elimina granulação e dither)
        println!(
            "[Renderer] Ordenando {} gaussianas por profundidade...",
            splats.len()
        );
        splats.sort_by(|a, b| {
            a.position[2]
                .partial_cmp(&b.position[2])
                .unwrap_or(std::cmp::Ordering::Equal)
        });

        let quad_buffer = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
            label: Some("Quad Buffer"),
            contents: bytemuck::cast_slice(&QUAD_VERTICES),
            usage: wgpu::BufferUsages::VERTEX,
        });

        let instance_count = splats.len() as u32;
        let instance_buffer = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
            label: Some("Splat Instance Buffer"),
            contents: bytemuck::cast_slice(&splats),
            usage: wgpu::BufferUsages::VERTEX | wgpu::BufferUsages::COPY_DST,
        });

        let uniform_buffer = device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("Uniform Buffer"),
            size: std::mem::size_of::<Uniforms>() as u64,
            usage: wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: false,
        });

        let uniform_bind_group_layout =
            device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
                label: Some("Uniform Bind Group Layout"),
                entries: &[wgpu::BindGroupLayoutEntry {
                    binding: 0,
                    visibility: wgpu::ShaderStages::VERTEX | wgpu::ShaderStages::FRAGMENT,
                    ty: wgpu::BindingType::Buffer {
                        ty: wgpu::BufferBindingType::Uniform,
                        has_dynamic_offset: false,
                        min_binding_size: None,
                    },
                    count: None,
                }],
            });

        let uniform_bind_group = device.create_bind_group(&wgpu::BindGroupDescriptor {
            label: Some("Uniform Bind Group"),
            layout: &uniform_bind_group_layout,
            entries: &[wgpu::BindGroupEntry {
                binding: 0,
                resource: uniform_buffer.as_entire_binding(),
            }],
        });

        let shader = device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: Some("Splat Shader"),
            source: wgpu::ShaderSource::Wgsl(include_str!("shader.wgsl").into()),
        });

        let pipeline_layout = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
            label: Some("Pipeline Layout"),
            bind_group_layouts: &[&uniform_bind_group_layout],
            push_constant_ranges: &[],
        });

        let pipeline = device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
            label: Some("Splat Pipeline"),
            layout: Some(&pipeline_layout),
            vertex: wgpu::VertexState {
                module: &shader,
                entry_point: "vs_main",
                buffers: &[
                    wgpu::VertexBufferLayout {
                        array_stride: std::mem::size_of::<QuadVertex>() as wgpu::BufferAddress,
                        step_mode: wgpu::VertexStepMode::Vertex,
                        attributes: &[wgpu::VertexAttribute {
                            offset: 0,
                            shader_location: 0,
                            format: wgpu::VertexFormat::Float32x2,
                        }],
                    },
                    wgpu::VertexBufferLayout {
                        array_stride: std::mem::size_of::<SplatGpu>() as wgpu::BufferAddress,
                        step_mode: wgpu::VertexStepMode::Instance,
                        attributes: &[
                            wgpu::VertexAttribute {
                                offset: 0,
                                shader_location: 1,
                                format: wgpu::VertexFormat::Float32x4,
                            },
                            wgpu::VertexAttribute {
                                offset: 16,
                                shader_location: 2,
                                format: wgpu::VertexFormat::Float32x4,
                            },
                            wgpu::VertexAttribute {
                                offset: 32,
                                shader_location: 3,
                                format: wgpu::VertexFormat::Float32x4,
                            },
                            wgpu::VertexAttribute {
                                offset: 48,
                                shader_location: 4,
                                format: wgpu::VertexFormat::Float32x4,
                            },
                        ],
                    },
                ],
            },
            fragment: Some(wgpu::FragmentState {
                module: &shader,
                entry_point: "fs_main",
                targets: &[Some(wgpu::ColorTargetState {
                    format: config.format,
                    // Pre-multiplied alpha elimina a dupla multiplicação de alpha que causava manchas escuras e ruído
                    blend: Some(wgpu::BlendState::PREMULTIPLIED_ALPHA_BLENDING),
                    write_mask: wgpu::ColorWrites::ALL,
                })],
            }),
            primitive: wgpu::PrimitiveState {
                topology: wgpu::PrimitiveTopology::TriangleList,
                strip_index_format: None,
                front_face: wgpu::FrontFace::Ccw,
                cull_mode: None,
                unclipped_depth: false,
                polygon_mode: wgpu::PolygonMode::Fill,
                conservative: false,
            },
            depth_stencil: None,
            multisample: wgpu::MultisampleState::default(),
            multiview: None,
        });

        Ok(Self {
            surface,
            device,
            queue,
            config,
            pipeline,
            quad_buffer,
            instance_buffer,
            instance_count,
            uniform_buffer,
            uniform_bind_group,
            splats,
            start_time: std::time::Instant::now(),
        })
    }

    pub fn resize(&mut self, new_size: winit::dpi::PhysicalSize<u32>) {
        if new_size.width > 0 && new_size.height > 0 {
            self.config.width = new_size.width;
            self.config.height = new_size.height;
            self.surface.configure(&self.device, &self.config);
        }
    }

    pub fn render(
        &mut self,
        mouse_norm: (f32, f32),
        expr: ExpressionParams,
    ) -> Result<(), wgpu::SurfaceError> {
        let output = self.surface.get_current_texture()?;
        let view = output
            .texture
            .create_view(&wgpu::TextureViewDescriptor::default());

        let w_f = self.config.width as f32;
        let h_f = self.config.height as f32;
        let aspect = w_f / h_f;
        let fov_y = 45.0f32.to_radians();
        let proj = Mat4::perspective_rh(fov_y, aspect, 0.1, 100.0);
        let focal_y = 0.5 * h_f / (0.5 * fov_y).tan();
        let focal_x = focal_y;

        // Câmera frontal ancorada: Y=0.07 posiciona a base do busto rente à borda inferior da janela,
        // eliminando qualquer folga ou espaço vazio na parte inferior sobre a barra de tarefas
        let eye = Vec3::new(0.0, 0.07, 1.45);
        let target = Vec3::new(0.0, 0.07, 0.0);
        let up = Vec3::Y;
        let view_mat = Mat4::look_at_rh(eye, target, up);

        let view_proj = proj * view_mat;
        let elapsed = self.start_time.elapsed().as_secs_f32();

        let uniforms = Uniforms {
            view_proj: view_proj.to_cols_array(),
            view: view_mat.to_cols_array(),
            viewport: [w_f, h_f, focal_x, focal_y],
            params: [expr.jaw_open, elapsed, mouse_norm.0, mouse_norm.1],
            expr: [expr.blink, expr.smile, expr.lip_round, expr.lip_spread],
            emotion_a: [expr.joy, expr.anger, expr.disgust, expr.fear],
            emotion_b: [expr.sadness, expr.surprise, expr.smirk, expr.brow_raise],
        };

        self.queue
            .write_buffer(&self.uniform_buffer, 0, bytemuck::cast_slice(&[uniforms]));

        let mut encoder = self
            .device
            .create_command_encoder(&wgpu::CommandEncoderDescriptor {
                label: Some("Render Encoder"),
            });

        {
            let mut rpass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
                label: Some("Splat Pass"),
                color_attachments: &[Some(wgpu::RenderPassColorAttachment {
                    view: &view,
                    resolve_target: None,
                    ops: wgpu::Operations {
                        // Fundo 100% transparente (Alpha 0.0) integrado ao compositor DWM do Windows
                        load: wgpu::LoadOp::Clear(wgpu::Color {
                            r: 0.0,
                            g: 0.0,
                            b: 0.0,
                            a: 0.0,
                        }),
                        store: wgpu::StoreOp::Store,
                    },
                })],
                depth_stencil_attachment: None,
                timestamp_writes: None,
                occlusion_query_set: None,
            });

            rpass.set_pipeline(&self.pipeline);
            rpass.set_bind_group(0, &self.uniform_bind_group, &[]);
            rpass.set_vertex_buffer(0, self.quad_buffer.slice(..));
            rpass.set_vertex_buffer(1, self.instance_buffer.slice(..));
            rpass.draw(0..6, 0..self.instance_count);
        }

        self.queue.submit(std::iter::once(encoder.finish()));
        output.present();

        Ok(())
    }

    pub async fn render_view(
        &self,
        width: u32,
        height: u32,
        eye: Vec3,
        target: Vec3,
        clear_color: wgpu::Color,
        output_path: &str,
    ) -> Result<(), Box<dyn std::error::Error>> {
        self.render_expression_view(
            width,
            height,
            eye,
            target,
            clear_color,
            (0.0, 0.0),
            0.0,
            ExpressionParams::default(),
            output_path,
        )
        .await
    }

    #[allow(clippy::too_many_arguments)]
    pub async fn render_expression_view(
        &self,
        width: u32,
        height: u32,
        eye: Vec3,
        target: Vec3,
        clear_color: wgpu::Color,
        mouse_norm: (f32, f32),
        time: f32,
        expr: ExpressionParams,
        output_path: &str,
    ) -> Result<(), Box<dyn std::error::Error>> {
        // Reordenar gaussianas back-to-front estritamente para o ângulo da câmera
        let mut sorted = self.splats.clone();
        sorted.sort_by(|a, b| {
            let pa = Vec3::new(a.position[0], a.position[1], a.position[2]);
            let pb = Vec3::new(b.position[0], b.position[1], b.position[2]);
            let da = (pa - eye).length_squared();
            let db = (pb - eye).length_squared();
            db.partial_cmp(&da).unwrap_or(std::cmp::Ordering::Equal)
        });
        self.queue
            .write_buffer(&self.instance_buffer, 0, bytemuck::cast_slice(&sorted));

        let texture_desc = wgpu::TextureDescriptor {
            label: Some("Snapshot Texture"),
            size: wgpu::Extent3d {
                width,
                height,
                depth_or_array_layers: 1,
            },
            mip_level_count: 1,
            sample_count: 1,
            dimension: wgpu::TextureDimension::D2,
            format: self.config.format,
            usage: wgpu::TextureUsages::RENDER_ATTACHMENT | wgpu::TextureUsages::COPY_SRC,
            view_formats: &[],
        };
        let texture = self.device.create_texture(&texture_desc);
        let view = texture.create_view(&wgpu::TextureViewDescriptor::default());

        let w_f = width as f32;
        let h_f = height as f32;
        let aspect = w_f / h_f;
        let fov_y = 45.0f32.to_radians();
        let proj = Mat4::perspective_rh(fov_y, aspect, 0.1, 100.0);
        let focal_y = 0.5 * h_f / (0.5 * fov_y).tan();
        let focal_x = focal_y;
        let up = Vec3::Y;
        let view_mat = Mat4::look_at_rh(eye, target, up);
        let view_proj = proj * view_mat;

        let uniforms = Uniforms {
            view_proj: view_proj.to_cols_array(),
            view: view_mat.to_cols_array(),
            viewport: [w_f, h_f, focal_x, focal_y],
            params: [expr.jaw_open, time, mouse_norm.0, mouse_norm.1],
            expr: [expr.blink, expr.smile, expr.lip_round, expr.lip_spread],
            emotion_a: [expr.joy, expr.anger, expr.disgust, expr.fear],
            emotion_b: [expr.sadness, expr.surprise, expr.smirk, expr.brow_raise],
        };
        self.queue
            .write_buffer(&self.uniform_buffer, 0, bytemuck::cast_slice(&[uniforms]));

        let mut encoder = self
            .device
            .create_command_encoder(&wgpu::CommandEncoderDescriptor {
                label: Some("Snapshot Encoder"),
            });

        {
            let mut rpass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
                label: Some("Snapshot Splat Pass"),
                color_attachments: &[Some(wgpu::RenderPassColorAttachment {
                    view: &view,
                    resolve_target: None,
                    ops: wgpu::Operations {
                        load: wgpu::LoadOp::Clear(clear_color),
                        store: wgpu::StoreOp::Store,
                    },
                })],
                depth_stencil_attachment: None,
                timestamp_writes: None,
                occlusion_query_set: None,
            });

            rpass.set_pipeline(&self.pipeline);
            rpass.set_bind_group(0, &self.uniform_bind_group, &[]);
            rpass.set_vertex_buffer(0, self.quad_buffer.slice(..));
            rpass.set_vertex_buffer(1, self.instance_buffer.slice(..));
            rpass.draw(0..6, 0..self.instance_count);
        }

        let bytes_per_pixel = 4;
        let unpadded_bytes_per_row = width * bytes_per_pixel;
        let align = wgpu::COPY_BYTES_PER_ROW_ALIGNMENT;
        let padded_bytes_per_row = unpadded_bytes_per_row.div_ceil(align) * align;
        let buffer_size = (padded_bytes_per_row * height) as u64;

        let output_buffer = self.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("Readback Buffer"),
            size: buffer_size,
            usage: wgpu::BufferUsages::COPY_DST | wgpu::BufferUsages::MAP_READ,
            mapped_at_creation: false,
        });

        encoder.copy_texture_to_buffer(
            wgpu::ImageCopyTexture {
                texture: &texture,
                mip_level: 0,
                origin: wgpu::Origin3d::ZERO,
                aspect: wgpu::TextureAspect::All,
            },
            wgpu::ImageCopyBuffer {
                buffer: &output_buffer,
                layout: wgpu::ImageDataLayout {
                    offset: 0,
                    bytes_per_row: Some(padded_bytes_per_row),
                    rows_per_image: Some(height),
                },
            },
            wgpu::Extent3d {
                width,
                height,
                depth_or_array_layers: 1,
            },
        );

        self.queue.submit(std::iter::once(encoder.finish()));

        let slice = output_buffer.slice(..);
        let (tx, rx) = tokio::sync::oneshot::channel();
        slice.map_async(wgpu::MapMode::Read, move |res| {
            let _ = tx.send(res);
        });
        self.device.poll(wgpu::Maintain::Wait);
        rx.await??;

        let padded_data = slice.get_mapped_range();
        let mut unpadded_data = Vec::with_capacity((width * height * 4) as usize);
        for chunk in padded_data.chunks(padded_bytes_per_row as usize) {
            unpadded_data.extend_from_slice(&chunk[..unpadded_bytes_per_row as usize]);
        }
        drop(padded_data);
        output_buffer.unmap();

        if self.config.format == wgpu::TextureFormat::Bgra8Unorm
            || self.config.format == wgpu::TextureFormat::Bgra8UnormSrgb
        {
            for pixel in unpadded_data.chunks_exact_mut(4) {
                pixel.swap(0, 2);
            }
        }

        image::save_buffer(
            output_path,
            &unpadded_data,
            width,
            height,
            image::ColorType::Rgba8,
        )?;

        println!("[Renderer] Salvo com sucesso: {}", output_path);
        Ok(())
    }

    pub async fn render_to_image(
        &self,
        width: u32,
        height: u32,
        output_path: &str,
    ) -> Result<(), Box<dyn std::error::Error>> {
        self.render_view(
            width,
            height,
            Vec3::new(0.0, -0.02, 1.45),
            Vec3::new(0.0, -0.02, 0.0),
            wgpu::Color {
                r: 1.0,
                g: 1.0,
                b: 1.0,
                a: 1.0,
            },
            output_path,
        )
        .await
    }
}
