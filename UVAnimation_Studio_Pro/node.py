# node.py
# -*- coding: utf-8 -*-
import bpy
import time
import logging

# ログ設定（INFOレベル以上）
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UVAS_UVAnimationCoordinatesNode(bpy.types.ShaderNodeCustomGroup):
    bl_label = "UVAS UV Animation Coordinates"
    bl_idname = "UVAS_UVAnimationCoordinatesNode"

    _updating = False

    def update_node(self, context):
        """イメージプロパティ変更時のコールバック"""
        if self.node_tree and self.image:
            self.setup_internal_nodes(context)
            try:
                self.ensure_preview(context)
            except Exception as e:
                logger.warning(f"Error in ensure_preview: {str(e)}")
        else:
            self.setup_internal_nodes(context)

    def update_mapping(self, context):
        """UVインデックスや分割数変更時のマッピング更新"""
        if self._updating:
            return
        self._updating = True
        try:
            if not self.node_tree or not self.image:
                return
            mapping = self.node_tree.nodes.get("Mapping")
            if mapping and self.split_x > 0 and self.split_y > 0:
                max_index = self.split_x * self.split_y
                if self.uv_index > max_index:
                    self.uv_index = max_index
                elif self.uv_index < 1:
                    self.uv_index = 1
                index = max(0, min(self.uv_index - 1, max_index - 1))
                cell_width = 1.0 / self.split_x
                cell_height = 1.0 / self.split_y
                x = (index % self.split_x) * cell_width
                y = -(index // self.split_x) * cell_height
                mapping.inputs["Location"].default_value = (x, y, 0)
        except Exception as e:
            logger.warning(f"Error in update_mapping: {str(e)}")
        finally:
            self._updating = False

    def ensure_preview(self, context):
        """プレビューを安全に更新"""
        if not self.node_tree:
            return
        image_tex = self.node_tree.nodes.get("UVAnimationImageTex")
        if image_tex and image_tex.image:
            try:
                if hasattr(image_tex.image, 'preview') and not image_tex.image.preview:
                    image_tex.image.preview_ensure()
                for area in context.screen.areas:
                    if area.type in ['NODE_EDITOR', 'VIEW_3D']:
                        area.tag_redraw()
            except Exception as e:
                logger.warning(f"Error ensuring preview: {str(e)}")

    def update_range(self, context):
        """アニメーション範囲の更新"""
        if self.end_frame < self.start_frame:
            self.end_frame = self.start_frame
        max_index = self.split_x * self.split_y
        if self.end_frame > max_index:
            self.end_frame = max_index
        if self.start_frame > max_index:
            self.start_frame = max_index

    image: bpy.props.PointerProperty(
        name="Image",
        type=bpy.types.Image,
        description="Image to use for UV animation",
        update=update_node
    )

    texture_interpolation: bpy.props.EnumProperty(
        name="Interpolation",
        items=[
            ("Closest", "Closest", "No interpolation"),
            ("Linear", "Linear", "Linear interpolation"),
            ("Cubic", "Cubic", "Cubic interpolation")
        ],
        default="Closest",
        update=update_node
    )

    split_x: bpy.props.IntProperty(
        name="Split X",
        default=1,
        min=1,
        max=8,
        update=update_mapping
    )

    split_y: bpy.props.IntProperty(
        name="Split Y",
        default=1,
        min=1,
        max=8,
        update=update_mapping
    )

    uv_index: bpy.props.IntProperty(
        name="UV Index",
        default=1,
        min=1,
        update=update_mapping
    )

    show_preview: bpy.props.BoolProperty(
        name="Preview",
        default=True,
        description="Toggle visibility of Image and Split Previews"
    )

    keyframe_interpolation: bpy.props.EnumProperty(
        name="Keyframe Interpolation",
        items=[
            ("CONSTANT", "Constant", "No interpolation"),
            ("LINEAR", "Linear", "Linear interpolation"),
            ("BEZIER", "Bezier", "Smooth interpolation")
        ],
        default="CONSTANT"
    )

    speed: bpy.props.FloatProperty(
        name="Speed",
        default=1.0,
        min=0.01,
        max=60.0,
        description="Frames per second (higher = faster)"
    )

    is_playing: bpy.props.BoolProperty(
        name="Is Playing",
        default=False
    )

    start_frame: bpy.props.IntProperty(
        name="Start",
        default=1,
        min=1,
        update=update_range
    )

    end_frame: bpy.props.IntProperty(
        name="End",
        default=1,
        min=1,
        update=update_range
    )

    def init(self, context):
        """ノードの初期化"""
        if not self.node_tree:
            self.node_tree = bpy.data.node_groups.new(f"{self.bl_idname}_tree", "ShaderNodeTree")

        interface = self.node_tree.interface
        existing_sockets = {item.name: item for item in interface.items_tree if item.in_out == "OUTPUT"}
        if "Color" not in existing_sockets:
            interface.new_socket(name="Color", socket_type="NodeSocketColor", in_out="OUTPUT")
        if "Alpha" not in existing_sockets:
            interface.new_socket(name="Alpha", socket_type="NodeSocketFloat", in_out="OUTPUT")
        items = list(interface.items_tree)
        for i, item in enumerate(items):
            if item.name == "Color" and i != 0:
                interface.move(items[i], 0)
            elif item.name == "Alpha" and i != 1:
                interface.move(items[i], 1)

        if self.id_data.animation_data:
            self.id_data.animation_data_clear()

        self.end_frame = max(1, self.split_x * self.split_y)
        self.setup_internal_nodes(context)

    def setup_internal_nodes(self, context):
        """内部ノードの設定"""
        if not self.node_tree:
            return

        nodes = self.node_tree.nodes
        links = self.node_tree.links

        tex_coord = nodes.get("TexCoord") or nodes.new("ShaderNodeTexCoord")
        tex_coord.name = "TexCoord"
        mapping = nodes.get("Mapping") or nodes.new("ShaderNodeMapping")
        mapping.name = "Mapping"
        image_tex = nodes.get("UVAnimationImageTex") or nodes.new("ShaderNodeTexImage")
        image_tex.name = "UVAnimationImageTex"
        output = nodes.get("GroupOutput") or nodes.new("NodeGroupOutput")
        output.name = "GroupOutput"

        if self.image:
            image_tex.image = self.image
            image_tex.interpolation = self.texture_interpolation
            image_tex.extension = "REPEAT"
            image_tex.image_user.use_auto_refresh = False
            if image_tex.image:
                image_tex.image.colorspace_settings.name = "sRGB"
                image_tex.image.alpha_mode = "STRAIGHT"
        else:
            if image_tex.image:
                image_tex.image = None

        if not any(link.to_node == mapping for link in tex_coord.outputs["UV"].links):
            links.new(tex_coord.outputs["UV"], mapping.inputs["Vector"])
        if not any(link.to_node == image_tex for link in mapping.outputs["Vector"].links):
            links.new(mapping.outputs["Vector"], image_tex.inputs["Vector"])
        if not any(link.to_socket.name == "Color" for link in image_tex.outputs["Color"].links):
            links.new(image_tex.outputs["Color"], output.inputs["Color"])
        if not any(link.to_socket.name == "Alpha" for link in image_tex.outputs["Alpha"].links):
            links.new(image_tex.outputs["Alpha"], output.inputs["Alpha"])

        if self.image:
            self.update_mapping(context)

    def draw_buttons(self, context, layout):
        """ノードの UI 描画"""
        layout.template_ID(self, "image", new="image.new", open="image.open")
        layout.prop(self, "texture_interpolation", text="")

        row = layout.row(align=True)
        row.prop(self, "split_x")
        row.prop(self, "split_y")

        row = layout.row(align=True)
        row.prop(self, "uv_index")
        row.operator("uvas.insert_keyframe_uv", text="", icon="KEY_HLT").node_name = self.name
        row.operator("uvas.delete_keyframe_uv", text="", icon="KEY_DEHLT").node_name = self.name

        layout.prop(self, "keyframe_interpolation", text="")

        if self.node_tree:
            mapping = self.node_tree.nodes.get("Mapping")
            if mapping:
                layout.label(text=f"UV X/Y: ({mapping.inputs['Location'].default_value[0]:.2f}, {mapping.inputs['Location'].default_value[1]:.2f})")
            else:
                layout.label(text="UV X/Y: (0.00, 0.00)")
        else:
            layout.label(text="UV X/Y: (0.00, 0.00)")

        if self.image:
            layout.prop(self, "show_preview")
            if self.show_preview:
                row = layout.row(align=True)
                row.alignment = 'LEFT'
                row.operator("uvas.refresh_uv_preview", text="Refresh").node_name = self.name

                if self.node_tree:
                    image_tex = self.node_tree.nodes.get("UVAnimationImageTex")
                    if image_tex and image_tex.image:
                        if hasattr(image_tex.image, "preview") and image_tex.image.preview:
                            layout.template_icon(icon_value=image_tex.image.preview.icon_id, scale=10.0)
                        else:
                            layout.label(text="No preview available", icon="QUESTION")
                    else:
                        layout.label(text="No image loaded", icon="ERROR")
                else:
                    layout.label(text="Node tree not initialized", icon="ERROR")

                if not self.image or self.split_x == 0 or self.split_y == 0:
                    layout.label(text="画像が選択されていないか、分割数が未設定です")
                else:
                    base_scale = 10.0
                    scale_x = base_scale / self.split_x
                    scale_y = base_scale / self.split_y

                    grid = layout.grid_flow(
                        row_major=True,
                        columns=self.split_x,
                        even_columns=True,
                        even_rows=True,
                        align=True
                    )
                    grid.scale_x = scale_x
                    grid.scale_y = scale_y
                    for y in range(self.split_y):
                        for x in range(self.split_x):
                            cell_index = y * self.split_x + x + 1
                            op = grid.operator("uvas.set_uv_index", text=str(cell_index), depress=self.uv_index == cell_index)
                            op.node_name = self.name
                            op.new_index = cell_index

                layout.separator()
                row = layout.row(align=True)
                icon = 'PLAY' if not self.is_playing else 'PAUSE'
                row.operator("uvas.uv_anim_play", text="", icon=icon).node_name = self.name
                layout.label(text="Playback Range:")
                layout.prop(self, "start_frame")
                layout.prop(self, "end_frame")
                layout.prop(self, "speed", text="Speed (FPS)")

def register():
    bpy.utils.register_class(UVAS_UVAnimationCoordinatesNode)

def unregister():
    bpy.utils.unregister_class(UVAS_UVAnimationCoordinatesNode)