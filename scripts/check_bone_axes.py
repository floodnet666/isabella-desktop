import bpy

blend_path = r'D:\isabella-desktop\assets\models\warrior_girl_v3_expressions.blend'
bpy.ops.wm.open_mainfile(filepath=blend_path)

arm_obj = bpy.data.objects.get('Armature_WarriorGirl')
head_bone = arm_obj.data.bones.get('Head')

print(f"Head bone matrix_local:\n{head_bone.matrix_local}")
print(f"Head bone head: {head_bone.head}, tail: {head_bone.tail}")
print(f"Head bone vector: {head_bone.vector}")
