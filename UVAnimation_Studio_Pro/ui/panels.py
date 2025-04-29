# ui/panels.py
# -*- coding: utf-8 -*-
import bpy
from PIL import Image
import os
import logging
from ..node import UVAS_UVAnimationCoordinatesNode
from ..operators.generate import UVAS_OT_ImportAnimatedImageToTiles
from ..operators.tile.generation import UVAS_OT_SetTileIndex

# ログ設定（INFOレベル以上）
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UVAS_PT_TilePanel(bpy.types.Panel):
    bl_label = "UVAnimation Studio Pro"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'UVAS Studio'

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        split = layout.split(factor=0.5, align=True)
        split.label(text="Split X/Y:")
        row = split.row(align=True)
        if hasattr(scene, 'x_split'):
            row.prop(scene, "x_split", text="", expand=False)
        if hasattr(scene, 'y_split'):
            row.prop(scene, "y_split", text="", expand=False)

        try:
            split_x = int(getattr(scene, 'x_split', 1))
            split_y = int(getattr(scene, 'y_split', 1))
            if split_x > 0 and split_y > 0:
                base_scale = 10.0
                scale_x = base_scale / split_x
                scale_y = base_scale / split_y

                grid = layout.grid_flow(
                    row_major=True,
                    columns=split_x,
                    even_columns=True,
                    even_rows=True,
                    align=True
                )
                grid.scale_x = scale_x
                grid.scale_y = scale_y

                for y in range(split_y):
                    for x in range(split_x):
                        cell_index = y * split_x + x + 1
                        is_depressed = False
                        if getattr(scene, 'operation_mode', 'TILE') == "TILE":
                            if getattr(scene, 'tile_operation_mode', 'EXTRACT') in ["EXTRACT", "MIRROR", "INSERT_TEXT"]:
                                is_depressed = (getattr(scene, 'last_clicked_index', 0) == cell_index)
                            elif getattr(scene, 'tile_operation_mode', 'EXTRACT') == "SWAP":
                                is_depressed = (getattr(scene, 'swap_first_index', -1) == cell_index or
                                               getattr(scene, 'swap_second_index', -1) == cell_index)
                            elif getattr(scene, 'tile_operation_mode', 'EXTRACT') == "SHUFFLE" and getattr(scene, 'swap_first_index', -1) != -1:
                                if getattr(scene, 'shuffle_second_index', -1) == -1:
                                    is_depressed = (getattr(scene, 'swap_first_index', -1) == cell_index)
                                else:
                                    first_index = getattr(scene, 'swap_first_index', -1) - 1
                                    second_index = getattr(scene, 'shuffle_second_index', -1) - 1
                                    first_x = first_index % split_x
                                    first_y = split_y - 1 - (first_index // split_x)
                                    second_x = second_index % split_x
                                    second_y = split_y - 1 - (second_index // split_x)
                                    min_x = min(first_x, second_x)
                                    max_x = max(first_x, second_x)
                                    min_y = min(first_y, second_y)
                                    max_y = max(first_y, second_y)
                                    curr_x = (cell_index - 1) % split_x
                                    curr_y = split_y - 1 - ((cell_index - 1) // split_x)
                                    if min_x <= curr_x <= max_x and min_y <= curr_y <= max_y:
                                        is_depressed = True

                        op = grid.operator(
                            "uvas.set_tile_index",
                            text=str(cell_index),
                            depress=is_depressed
                        )
                        op.index = cell_index
        except Exception as e:
            layout.label(text=f"Error rendering grid: {str(e)}", icon='ERROR')

class UVAS_PT_Operations(bpy.types.Panel):
    bl_label = "Operations"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'UVAS Studio'
    bl_parent_id = "UVAS_PT_TilePanel"
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 1

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.label(text="Image Reference")
        if hasattr(scene, 'image_reference'):
            layout.template_ID(scene, "image_reference", new="image.new", open="image.open")
            if getattr(scene, 'image_reference', None):
                if scene.image_reference.preview:
                    layout.template_icon(icon_value=scene.image_reference.preview.icon_id, scale=5.0)
                else:
                    layout.label(text="Preview not available", icon='IMAGE')
                    try:
                        UVAS_OT_SetTileIndex.try_generate_preview(scene.image_reference)
                        if scene.image_reference.preview:
                            layout.template_icon(icon_value=scene.image_reference.preview.icon_id, scale=5.0)
                        else:
                            logger.warning(f"Failed to generate preview for image_reference '{scene.image_reference.name}'")
                            layout.label(text="Preview generation failed", icon='ERROR')
                    except Exception as e:
                        logger.warning(f"Failed to generate preview for image_reference: {str(e)}")
                        layout.label(text="Preview generation failed", icon='ERROR')
            else:
                layout.label(text="Please select an image in Image Reference", icon='ERROR')

        layout.label(text="Operation Mode")
        if hasattr(scene, 'operation_mode'):
            layout.prop(scene, "operation_mode", text="")

        if getattr(scene, 'operation_mode', 'TILE') == "TILE":
            layout.label(text="Tile Operation Mode")
            if hasattr(scene, 'tile_operation_mode'):
                layout.prop(scene, "tile_operation_mode", text="")
            if getattr(scene, 'tile_operation_mode', 'EXTRACT') == "ROTATE_AND_FLIP" and getattr(scene, 'image_reference', None):
                layout.label(text="Rotate or Flip Mode")
                if hasattr(scene, 'rotate_flip_mode'):
                    layout.prop(scene, "rotate_flip_mode", text="")
                if getattr(scene, 'rotate_flip_mode', 'ROTATE') == "ROTATE":
                    tile_width = scene.image_reference.size[0] // int(getattr(scene, 'x_split', 1)) if hasattr(scene, 'x_split') else 1
                    tile_height = scene.image_reference.size[1] // int(getattr(scene, 'y_split', 1)) if hasattr(scene, 'y_split') else 1
                    if tile_width != tile_height:
                        layout.label(text="Rotate Direction: 180° (non-square tile)")
                    else:
                        layout.label(text="Rotate Direction")
                        if hasattr(scene, 'rotate_direction'):
                            layout.prop(scene, "rotate_direction", text="")
                else:
                    layout.label(text="Flip Direction")
                    if hasattr(scene, 'flip_direction'):
                        layout.prop(scene, "flip_direction", text="")
            elif getattr(scene, 'tile_operation_mode', 'EXTRACT') == "ROTATE_AND_FLIP":
                layout.label(text="Select an image first")
            elif getattr(scene, 'tile_operation_mode', 'EXTRACT') == "MIRROR" and getattr(scene, 'image_reference', None):
                layout.label(text="Mirror Direction")
                if hasattr(scene, 'mirror_direction'):
                    layout.prop(scene, "mirror_direction", text="")
                if getattr(scene, 'last_clicked_index', 0) > 0:
                    layout.operator("uvas.apply_mirror", text="Apply Mirror", icon='FILE_REFRESH')
                else:
                    layout.label(text="Select a tile to mirror", icon='INFO')
            elif getattr(scene, 'tile_operation_mode', 'EXTRACT') == "MIRROR":
                layout.label(text="Select an image first")
            elif getattr(scene, 'tile_operation_mode', 'EXTRACT') == "PATCH":
                layout.label(text="Tile Reference")
                if hasattr(scene, 'tile_reference'):
                    layout.template_ID(scene, "tile_reference", new="image.new", open="image.open")
                if getattr(scene, 'tile_reference', None):
                    if scene.tile_reference.preview:
                        layout.template_icon(icon_value=scene.tile_reference.preview.icon_id, scale=5.0)
                    else:
                        layout.label(text="Preview not available", icon='IMAGE')
                        try:
                            UVAS_OT_SetTileIndex.try_generate_preview(scene.tile_reference)
                            if scene.tile_reference.preview:
                                layout.template_icon(icon_value=scene.tile_reference.preview.icon_id, scale=5.0)
                            else:
                                logger.warning(f"Failed to generate preview for tile_reference '{scene.tile_reference.name}'")
                                layout.label(text="Preview generation failed", icon='ERROR')
                        except Exception as e:
                            logger.warning(f"Failed to generate preview for tile_reference: {str(e)}")
                            layout.label(text="Preview generation failed", icon='ERROR')
            elif getattr(scene, 'tile_operation_mode', 'EXTRACT') == "EXTRACT" and getattr(scene, 'image_reference', None):
                if getattr(scene, 'last_clicked_index', 0) > 0:
                    layout.operator("uvas.apply_extract", text="Apply Extract", icon='FILE_REFRESH')
                else:
                    layout.label(text="Select a tile to extract", icon='INFO')
            elif getattr(scene, 'tile_operation_mode', 'EXTRACT') == "EXTRACT":
                layout.label(text="Select an image first")
            elif getattr(scene, 'tile_operation_mode', 'EXTRACT') == "SWAP":
                if getattr(scene, 'swap_first_index', -1) != -1 and getattr(scene, 'swap_second_index', -1) != -1:
                    layout.operator("uvas.apply_swap", text="Apply Swap", icon='FILE_REFRESH')
                else:
                    layout.label(text="Select two tiles for swapping", icon='INFO')
            elif getattr(scene, 'tile_operation_mode', 'EXTRACT') == "SHUFFLE":
                if getattr(scene, 'swap_first_index', -1) != -1 and getattr(scene, 'shuffle_second_index', -1) != -1:
                    layout.operator("uvas.apply_shuffle", text="Apply Shuffle", icon='FILE_REFRESH')
                else:
                    layout.label(text="Select two tiles for shuffling", icon='INFO')
            elif getattr(scene, 'tile_operation_mode', 'EXTRACT') == "INSERT_TEXT" and getattr(scene, 'image_reference', None):
                layout.label(text="Text Content")
                if hasattr(scene, 'text_content'):
                    layout.prop(scene, "text_content", text="")
                layout.label(text="Text Font")
                row = layout.row(align=True)
                if hasattr(scene, 'text_font'):
                    row.prop(scene, "text_font", text="")
                    row.operator("uvas.clear_text_font", text="", icon='X')
                layout.label(text="Font Size")
                if hasattr(scene, 'text_font_size'):
                    layout.prop(scene, "text_font_size", text="")
                layout.label(text="Text Offset (pixels)")
                row = layout.row(align=True)
                if hasattr(scene, 'text_offset_x'):
                    row.prop(scene, "text_offset_x", text="X")
                if hasattr(scene, 'text_offset_y'):
                    row.prop(scene, "text_offset_y", text="Y")
                if getattr(scene, 'last_clicked_index', 0) > 0:
                    layout.operator("uvas.apply_text_setting", text="Preview Text", icon='VIEWZOOM')
                    layout.operator("uvas.apply_text", text="Apply Text", icon='MODIFIER')
                    layout.label(text="Text Preview")
                    if hasattr(scene, 'text_preview') and scene.text_preview and scene.text_preview_index == scene.last_clicked_index:
                        if scene.text_preview.preview:
                            layout.template_icon(icon_value=scene.text_preview.preview.icon_id, scale=3.0)
                        else:
                            layout.label(text="Text preview not available", icon='IMAGE')
                            try:
                                UVAS_OT_SetTileIndex.try_generate_preview(scene.text_preview)
                                if scene.text_preview.preview:
                                    layout.template_icon(icon_value=scene.text_preview.preview.icon_id, scale=3.0)
                                else:
                                    logger.warning(f"Failed to generate text preview for '{scene.text_preview.name}'")
                                    layout.label(text="Text preview generation failed", icon='ERROR')
                            except Exception as e:
                                logger.warning(f"Failed to generate text preview: {str(e)}")
                                layout.label(text="Text preview generation failed", icon='ERROR')
                    else:
                        layout.label(text="Click 'Preview Text' to see the preview", icon='INFO')
                else:
                    layout.label(text="Select a tile to insert text", icon='INFO')
            elif getattr(scene, 'tile_operation_mode', 'EXTRACT') == "INSERT_TEXT":
                layout.label(text="Select an image first")

        elif getattr(scene, 'operation_mode', 'TILE') == "IMAGE":
            layout.label(text="Image Operation Mode")
            if hasattr(scene, 'image_operation_mode'):
                layout.prop(scene, "image_operation_mode", text="")
            if getattr(scene, 'image_reference', None):
                if getattr(scene, 'image_operation_mode', 'NEGATE') == "ROTATE_AND_FLIP":
                    layout.label(text="Rotate or Flip Mode")
                    if hasattr(scene, 'rotate_flip_mode'):
                        layout.prop(scene, "rotate_flip_mode", text="")
                    if getattr(scene, 'rotate_flip_mode', 'ROTATE') == "ROTATE":
                        layout.label(text="Rotate Direction")
                        if hasattr(scene, 'rotate_direction'):
                            layout.prop(scene, "rotate_direction", text="")
                        layout.operator("uvas.rotate_image", text="Apply Rotate", icon='MODIFIER')
                    else:
                        layout.label(text="Flip Direction")
                        if hasattr(scene, 'flip_direction'):
                            layout.prop(scene, "flip_direction", text="")
                        layout.operator("uvas.flip_image", text="Apply Flip", icon='MODIFIER')
                elif getattr(scene, 'image_operation_mode', 'NEGATE') == "MIRROR":
                    layout.label(text="Mirror Direction")
                    if hasattr(scene, 'mirror_direction'):
                        layout.prop(scene, "mirror_direction", text="")
                    layout.operator("uvas.mirror_image", text="Apply Mirror", icon='MODIFIER')
                elif getattr(scene, 'image_operation_mode', 'NEGATE') == "NEGATE":
                    layout.operator("uvas.negate_image", text="Apply Negate", icon='MODIFIER')
                elif getattr(scene, 'image_operation_mode', 'NEGATE') == "GRAYSCALE":
                    layout.operator("uvas.grayscale_image", text="Apply Grayscale", icon='MODIFIER')
            else:
                layout.label(text="Select an image first", icon='ERROR')

class UVAS_PT_Generate(bpy.types.Panel):
    bl_label = "Generate"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'UVAS Studio'
    bl_parent_id = "UVAS_PT_TilePanel"
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 2

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.label(text="Generate Mode")
        if hasattr(scene, 'generate_mode'):
            layout.prop(scene, "generate_mode", text="")

        if getattr(scene, 'generate_mode', 'FILL') == "GRID":
            layout.label(text="Border Type")
            if hasattr(scene, 'grid_border_type'):
                layout.prop(scene, "grid_border_type", text="")
            layout.label(text="Border Width")
            if hasattr(scene, 'border_width'):
                layout.prop(scene, "border_width", text="")

        row = layout.row()
        row.label(text="Resolution X")
        if hasattr(scene, 'resolution_x'):
            row.prop(scene, "resolution_x", text="")
        row = layout.row()
        row.label(text="Resolution Y")
        if hasattr(scene, 'resolution_y'):
            row.prop(scene, "resolution_y", text="")
        layout.operator("uvas.generate_full_image", icon='IMAGE')
        layout.operator("uvas.generate_single_tile", icon='MESH_PLANE')

class UVAS_PT_GifApng(bpy.types.Panel):
    bl_label = "GIF/APNG"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'UVAS Studio'
    bl_parent_id = "UVAS_PT_TilePanel"
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 3

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        row = layout.row()
        row.label(text="X Tiling")
        if hasattr(scene, 'x_split'):
            row.prop(scene, "x_split", text="")
        row = layout.row()
        row.label(text="Y Tiling")
        if hasattr(scene, 'y_split'):
            row.prop(scene, "y_split", text="")
        
        layout.label(text="GIF/APNG Image Reference")
        if hasattr(scene, 'gif_image_reference'):
            layout.template_ID(scene, "gif_image_reference", new="image.new", open="image.open")
        if getattr(scene, 'gif_image_reference', None):
            if scene.gif_image_reference.preview:
                layout.template_icon(icon_value=scene.gif_image_reference.preview.icon_id, scale=5.0)
            else:
                layout.label(text="Preview not available", icon='IMAGE')
                try:
                    scene.gif_image_reference.preview_ensure()
                    if scene.gif_image_reference.preview:
                        layout.template_icon(icon_value=scene.gif_image_reference.preview.icon_id, scale=5.0)
                    else:
                        logger.warning(f"Failed to generate preview for gif_image_reference '{scene.gif_image_reference.name}'")
                        layout.label(text="Preview generation failed", icon='ERROR')
                except Exception as e:
                    logger.warning(f"Failed to generate preview for gif_image_reference: {str(e)}")
                    layout.label(text="Preview generation failed", icon='ERROR')

            filepath = bpy.path.abspath(scene.gif_image_reference.filepath) if scene.gif_image_reference.filepath else None
            if filepath and os.path.exists(filepath):
                try:
                    with Image.open(filepath) as pil_img:
                        if not hasattr(pil_img, 'is_animated') or not pil_img.is_animated:
                            layout.label(text="Selected image is not an animated GIF/APNG", icon='ERROR')
                        else:
                            frame_count = pil_img.n_frames
                            width, height = pil_img.size
                            total_res_x = width * int(getattr(scene, 'x_split', 1))
                            total_res_y = height * int(getattr(scene, 'y_split', 1))
                            layout.label(text=f"Total Tiles: {int(getattr(scene, 'x_split', 1)) * int(getattr(scene, 'y_split', 1))}")
                            row = layout.row(align=True)
                            row.label(text=f"Image Frames: {frame_count}")
                            if hasattr(scene, 'reduce_frames'):
                                row.prop(scene, "reduce_frames", text="Reduce Frames")
                            layout.label(text=f"Tile Resolution: {width}x{height}")
                            layout.label(text=f"Total Resolution X: {total_res_x}")
                            layout.label(text=f"Total Resolution Y: {total_res_y}")
                            if getattr(scene, 'reduce_frames', False):
                                if hasattr(scene, 'frame_reduction_ratio'):
                                    layout.prop(scene, "frame_reduction_ratio", text="Frame Reduction Ratio")
                except Exception as e:
                    layout.label(text=f"Error reading image info: {str(e)}", icon='ERROR')
            else:
                layout.label(text="Invalid or missing file path", icon='ERROR')

        layout.operator("uvas.import_animated_image_to_tiles", icon='FILE_MOVIE')
        layout.operator("uvas.export_animated_image_from_tiles", text="Export Animated Image from Tiles", icon='FILE_MOVIE')
        layout.label(text=f"Total Frames: {int(getattr(scene, 'x_split', 1)) * int(getattr(scene, 'y_split', 1))}")
        layout.label(text="GIF/APNG import overrides resolution based on image size and splits.")

class UVAS_PT_UVAnimation(bpy.types.Panel):
    bl_label = "UV Animation"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'UVAS Studio'
    bl_parent_id = "UVAS_PT_TilePanel"
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 4

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        if getattr(scene, 'image_reference', None):
            layout.operator("uvas.create_uv_animation_node", text="Create UV Animation Node", icon='NODE')
            layout.label(text="Select a UV Animation Node:")
            obj = context.active_object
            if obj and obj.active_material and obj.active_material.use_nodes:
                node_tree = obj.active_material.node_tree
                uv_nodes = [node for node in node_tree.nodes if isinstance(node, UVAS_UVAnimationCoordinatesNode)]
                if uv_nodes:
                    for node in uv_nodes:
                        row = layout.row(align=True)
                        row.label(text=node.name)
                        icon = 'PLAY' if not node.is_playing else 'PAUSE'
                        row.operator("uvas.uv_anim_play", text="", icon=icon).node_name = node.name
                        row.operator("uvas.insert_keyframe_uv", text="", icon="KEY_HLT").node_name = node.name
                        row.operator("uvas.delete_keyframe_uv", text="", icon="KEY_DEHLT").node_name = node.name
                        layout.prop(node, "uv_index", text="UV Index")
                        layout.prop(node, "speed", text="Speed (FPS)")
                        layout.prop(node, "start_frame", text="Start Frame")
                        layout.prop(node, "end_frame", text="End Frame")
                else:
                    layout.label(text="No UV Animation Nodes found in active material.")
            else:
                layout.label(text="Select an object with a node-based material.")
        else:
            layout.label(text="No image reference selected for UV animation.")

class UVAS_PT_Management(bpy.types.Panel):
    bl_label = "Management"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'UVAS Studio'
    bl_parent_id = "UVAS_PT_TilePanel"
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 5

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.label(text="Memory Explorer")
        box = layout.box()
        # UVAS_ プレフィックスを持つ画像をフィルタリング、UVAS_TEXT_PREVIEW_ は除外
        uvas_images = [img for img in bpy.data.images if img.name.startswith("UVAS_") and not img.name.startswith("UVAS_TEXT_PREVIEW_")]
        if uvas_images:
            for img in uvas_images:
                row = box.row(align=True)
                if img.preview:
                    row.template_icon(icon_value=img.preview.icon_id, scale=2.0)
                else:
                    row.label(text="", icon='IMAGE')
                    try:
                        UVAS_OT_SetTileIndex.try_generate_preview(img)
                        if img.preview:
                            row.template_icon(icon_value=img.preview.icon_id, scale=2.0)
                        else:
                            logger.warning(f"Failed to generate preview for '{img.name}'")
                            row.label(text="", icon='ERROR')
                    except Exception as e:
                        logger.warning(f"Failed to generate preview for '{img.name}': {str(e)}")
                        row.label(text="", icon='ERROR')
                row.operator("uvas.select_image", text=img.name, emboss=True).image_name = img.name
                row.operator("uvas.rename_image", text="", icon='GREASEPENCIL').image_name = img.name
                row.operator("uvas.delete_image", text="", icon='X').image_name = img.name
        else:
            box.label(text="No UVAS images in memory")

        layout.label(text="Output Directory")
        if hasattr(scene, 'output_dir'):
            layout.prop(scene, "output_dir", text="")

        layout.operator("uvas.export_generated_images", text="Export Generated Images", icon='EXPORT')
        layout.operator("uvas.clean_unused_images", text="Clean Unused Images", icon='TRASH')

def register():
    bpy.utils.register_class(UVAS_PT_TilePanel)
    bpy.utils.register_class(UVAS_PT_Operations)
    bpy.utils.register_class(UVAS_PT_Generate)
    bpy.utils.register_class(UVAS_PT_GifApng)
    bpy.utils.register_class(UVAS_PT_UVAnimation)
    bpy.utils.register_class(UVAS_PT_Management)

def unregister():
    bpy.utils.unregister_class(UVAS_PT_Management)
    bpy.utils.unregister_class(UVAS_PT_UVAnimation)
    bpy.utils.unregister_class(UVAS_PT_GifApng)
    bpy.utils.unregister_class(UVAS_PT_Generate)
    bpy.utils.unregister_class(UVAS_PT_Operations)
    bpy.utils.unregister_class(UVAS_PT_TilePanel)