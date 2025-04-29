# operators/uv_anim.py
# -*- coding: utf-8 -*-
import bpy
import time
from ..node import UVAS_UVAnimationCoordinatesNode
from ..utils import ensure_animation_data

class UVAS_OT_UVAnimPlay(bpy.types.Operator):
    bl_idname = "uvas.uv_anim_play"
    bl_label = "Toggle UV Animation"
    bl_description = "Toggle UV animation playback"
    bl_options = {'REGISTER'}

    node_name: bpy.props.StringProperty()
    _timer = None
    _last_time = 0.0

    def modal(self, context, event):
        if not context.area:
            if self._timer:
                context.window_manager.event_timer_remove(self._timer)
                self._timer = None
            return {'CANCELLED'}

        node = context.space_data.node_tree.nodes.get(self.node_name)
        if not node or not isinstance(node, UVAS_UVAnimationCoordinatesNode) or not node.is_playing:
            if self._timer:
                context.window_manager.event_timer_remove(self._timer)
                self._timer = None
            return {'FINISHED'}

        try:
            if event.type == 'TIMER':
                current_time = time.time()
                if current_time - self._last_time >= 1.0 / node.speed:
                    if node.uv_index >= node.end_frame:
                        node.uv_index = node.start_frame
                    else:
                        node.uv_index += 1
                    node.update_mapping(context)
                    context.area.tag_redraw()
                    self._last_time = current_time
        except Exception as e:
            print(f"[ERROR] event.type={getattr(event, 'type', None)} で例外発生: {e}")
            if self._timer:
                context.window_manager.event_timer_remove(self._timer)
                self._timer = None
            return {'CANCELLED'}

        return {'PASS_THROUGH'}

    def execute(self, context):
        node = context.space_data.node_tree.nodes.get(self.node_name)
        if not node or not isinstance(node, UVAS_UVAnimationCoordinatesNode):
            self.report({'ERROR'}, "Node not found or invalid")
            return {'CANCELLED'}

        wm = context.window_manager
        if node.is_playing:
            node.is_playing = False
            if self._timer:
                wm.event_timer_remove(self._timer)
                self._timer = None
        else:
            node.is_playing = True
            if node.uv_index < node.start_frame or node.uv_index > node.end_frame:
                node.uv_index = node.start_frame
            self._timer = wm.event_timer_add(0.01, window=context.window)
            self._last_time = time.time()
            wm.modal_handler_add(self)

        context.area.tag_redraw()
        return {'RUNNING_MODAL'} if node.is_playing else {'FINISHED'}

class UVAS_OT_InsertKeyframeUV(bpy.types.Operator):
    bl_idname = "uvas.insert_keyframe_uv"
    bl_label = "Insert Keyframe UV"
    bl_description = "Insert keyframes for current UV X and UV Y coordinates"
    bl_options = {'REGISTER', 'UNDO'}

    node_name: bpy.props.StringProperty()

    def execute(self, context):
        tree = context.space_data.node_tree
        if not tree:
            self.report({'ERROR'}, "No node tree found")
            return {'CANCELLED'}

        node = tree.nodes.get(self.node_name)
        if not node or not isinstance(node, UVAS_UVAnimationCoordinatesNode) or not node.node_tree:
            self.report({'ERROR'}, "Node not found or invalid")
            return {'CANCELLED'}

        mapping = node.node_tree.nodes.get("Mapping")
        if not mapping:
            self.report({'ERROR'}, "Mapping node not found")
            return {'CANCELLED'}

        frame = context.scene.frame_current
        x_value = mapping.inputs["Location"].default_value[0]
        y_value = mapping.inputs["Location"].default_value[1]

        mapping.inputs["Location"].keyframe_insert(data_path="default_value", index=0, frame=frame)
        mapping.inputs["Location"].keyframe_insert(data_path="default_value", index=1, frame=frame)

        action = ensure_animation_data(node.node_tree)
        fcurves = action.fcurves
        data_path = 'nodes["Mapping"].inputs[1].default_value'

        for i, value in enumerate((x_value, y_value)):
            fcurve = fcurves.find(data_path, index=i)
            if not fcurve:
                fcurve = fcurves.new(data_path, index=i, action_group="Mapping")
            for kf in fcurve.keyframe_points:
                if kf.co.x == frame:
                    kf.interpolation = node.keyframe_interpolation
                    if node.keyframe_interpolation == "BEZIER":
                        kf.handle_left_type = kf.handle_right_type = "AUTO"
                    else:
                        kf.handle_left_type = kf.handle_right_type = "VECTOR"
                    break

        context.area.tag_redraw()
        return {'FINISHED'}

class UVAS_OT_DeleteKeyframeUV(bpy.types.Operator):
    bl_idname = "uvas.delete_keyframe_uv"
    bl_label = "Delete Keyframe UV"
    bl_description = "Delete keyframes for current UV X and Y coordinates at the current frame"
    bl_options = {'REGISTER', 'UNDO'}

    node_name: bpy.props.StringProperty()

    def execute(self, context):
        tree = context.space_data.node_tree
        if not tree:
            self.report({'ERROR'}, "No node tree found")
            return {'CANCELLED'}

        node = tree.nodes.get(self.node_name)
        if not node or not isinstance(node, UVAS_UVAnimationCoordinatesNode) or not node.node_tree:
            self.report({'ERROR'}, "Node not found or invalid")
            return {'CANCELLED'}

        mapping = node.node_tree.nodes.get("Mapping")
        if not mapping or not node.node_tree.animation_data or not node.node_tree.animation_data.action:
            self.report({'ERROR'}, "No keyframes or mapping node found")
            return {'CANCELLED'}

        frame = context.scene.frame_current
        success_x = mapping.inputs["Location"].keyframe_delete(data_path="default_value", index=0, frame=frame)
        success_y = mapping.inputs["Location"].keyframe_delete(data_path="default_value", index=1, frame=frame)

        bpy.context.view_layer.update()
        for area in context.screen.areas:
            area.tag_redraw()
        bpy.ops.wm.redraw_timer(type='DRAW', iterations=1)

        if success_x or success_y:
            return {'FINISHED'}
        return {'CANCELLED'}

class UVAS_OT_RefreshUVPreview(bpy.types.Operator):
    bl_idname = "uvas.refresh_uv_preview"
    bl_label = "Refresh UV Preview"
    bl_description = "Manually refresh the texture preview"
    bl_options = {'REGISTER'}

    node_name: bpy.props.StringProperty()

    def execute(self, context):
        tree = context.space_data.node_tree
        if not tree:
            self.report({'ERROR'}, "No node tree found")
            return {'CANCELLED'}

        node = tree.nodes.get(self.node_name)
        if not node or not isinstance(node, UVAS_UVAnimationCoordinatesNode):
            self.report({'ERROR'}, "Node not found or invalid")
            return {'CANCELLED'}

        node.ensure_preview(context)
        return {'FINISHED'}

class UVAS_OT_SetUVIndex(bpy.types.Operator):
    bl_idname = "uvas.set_uv_index"
    bl_label = "Set UV Index"
    bl_description = "Set the UV index by clicking a cell"
    bl_options = {'REGISTER', 'UNDO'}

    node_name: bpy.props.StringProperty()
    new_index: bpy.props.IntProperty()

    def execute(self, context):
        tree = context.space_data.node_tree
        if not tree:
            self.report({'ERROR'}, "No node tree found")
            return {'CANCELLED'}
        node = tree.nodes.get(self.node_name)
        if not node or not isinstance(node, UVAS_UVAnimationCoordinatesNode):
            self.report({'ERROR'}, "Node not found or invalid")
            return {'CANCELLED'}
        max_index = node.split_x * node.split_y
        node.uv_index = min(max(1, self.new_index), max_index)
        return {'FINISHED'}

class UVAS_OT_ReplaceWithUVAnim(bpy.types.Operator):
    bl_idname = "uvas.replace_with_uv_anim"
    bl_label = "Replace with UV Animation Coordinates"
    bl_description = "Replace an Image Texture node with a UV Animation Coordinates node"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        node_tree = context.space_data.edit_tree
        active_node = context.active_node

        if not active_node or active_node.type != 'TEX_IMAGE':
            self.report({'WARNING'}, "Image Texture node must be selected")
            return {'CANCELLED'}

        input_links = {input.name: input.links[0].from_socket
                       for input in active_node.inputs if input.is_linked}
        output_links = {output.name: [link.to_socket for link in output.links]
                        for output in active_node.outputs if output.is_linked}

        image = active_node.image
        interpolation = active_node.interpolation

        node_loc = active_node.location.copy()
        node_tree.nodes.remove(active_node)

        new_node = node_tree.nodes.new("UVAS_UVAnimationCoordinatesNode")
        new_node.location = node_loc

        new_node.image = image
        new_node.texture_interpolation = interpolation

        for input_name, from_socket in input_links.items():
            if input_name in new_node.inputs:
                node_tree.links.new(from_socket, new_node.inputs[input_name])

        for output_name, to_sockets in output_links.items():
            if output_name in new_node.outputs:
                for to_socket in to_sockets:
                    node_tree.links.new(new_node.outputs[output_name], to_socket)

        for node in node_tree.nodes:
            node.select = False
        new_node.select = True
        node_tree.nodes.active = new_node

        for area in context.screen.areas:
            if area.type == 'NODE_EDITOR':
                area.tag_redraw()

        return {'FINISHED'}

class UVAS_OT_CreateUVAnimationNode(bpy.types.Operator):
    bl_idname = "uvas.create_uv_animation_node"
    bl_label = "Create UV Animation Node"
    bl_description = "Create a new UV Animation Coordinates node"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj or not obj.active_material or not obj.active_material.use_nodes:
            self.report({'ERROR'}, "Active object has no node-based material")
            return {'CANCELLED'}

        node_tree = obj.active_material.node_tree
        node = node_tree.nodes.new('UVAS_UVAnimationCoordinatesNode')
        node.location = (0, 0)
        if context.scene.image_reference:
            node.image = context.scene.image_reference
        # 3D View を更新
        node_tree.update()
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        return {'FINISHED'}

def register():
    bpy.utils.register_class(UVAS_OT_UVAnimPlay)
    bpy.utils.register_class(UVAS_OT_InsertKeyframeUV)
    bpy.utils.register_class(UVAS_OT_DeleteKeyframeUV)
    bpy.utils.register_class(UVAS_OT_RefreshUVPreview)
    bpy.utils.register_class(UVAS_OT_SetUVIndex)
    bpy.utils.register_class(UVAS_OT_ReplaceWithUVAnim)
    bpy.utils.register_class(UVAS_OT_CreateUVAnimationNode)

def unregister():
    bpy.utils.unregister_class(UVAS_OT_CreateUVAnimationNode)
    bpy.utils.unregister_class(UVAS_OT_ReplaceWithUVAnim)
    bpy.utils.unregister_class(UVAS_OT_SetUVIndex)
    bpy.utils.unregister_class(UVAS_OT_RefreshUVPreview)
    bpy.utils.unregister_class(UVAS_OT_DeleteKeyframeUV)
    bpy.utils.unregister_class(UVAS_OT_InsertKeyframeUV)
    bpy.utils.unregister_class(UVAS_OT_UVAnimPlay)