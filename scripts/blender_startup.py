import bpy
import addon_utils

for addon_name in ['blender_mcp_ultra', '3dgs_render_blender_addon']:
    try:
        addon_utils.enable(addon_name, default_set=True)
        print(f'[Startup] Enabled addon: {addon_name}')
    except Exception as e:
        print(f'[Startup] Error enabling {addon_name}: {e}')

try:
    bpy.ops.mcp_ultra.start_server()
    print('[Startup] MCP Ultra server started on :9876')
except Exception as e:
    print(f'[Startup] MCP server status: {e}')
