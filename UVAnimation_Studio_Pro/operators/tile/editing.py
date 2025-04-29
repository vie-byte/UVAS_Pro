# operators/tile/editing.py
# -*- coding: utf-8 -*-
import bpy
import numpy as np
import logging
import os
from PIL import Image, ImageDraw, ImageFont
from .utils import ImageManager
from .generation import UVAS_OT_SetTileIndex

# ログ設定（INFOレベル以上）
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UVAS_OT_ApplyMirror(bpy.types.Operator):
    bl_idname = "uvas.apply_mirror"
    bl_label = "Apply Mirror"
    bl_description = "Apply mirror operation to the selected tile"
    bl_options = {'REGISTER'}

    _image_manager = ImageManager()

    @classmethod
    def poll(cls, context):
        scene = context.scene
        return scene.operation_mode == "TILE" and scene.tile_operation_mode == "MIRROR" and scene.image_reference is not None and scene.last_clicked_index > 0

    def execute(self, context):
        scene = context.scene
        index = scene.last_clicked_index
        if not self.poll(context):
            self.report({'ERROR'}, "Invalid state for mirror operation")
            return {'CANCELLED'}

        try:
            ref_img = scene.image_reference
            TILE_SPLIT_X = int(scene.x_split)
            TILE_SPLIT_Y = int(scene.y_split)
            tile_width = ref_img.size[0] // TILE_SPLIT_X
            tile_height = ref_img.size[1] // TILE_SPLIT_Y
            if ref_img.size == (0, 0):
                raise ValueError("Reference image has zero size")
            expected_size = ref_img.size[0] * ref_img.size[1] * 4
            pixel_array = np.array(ref_img.pixels[:], dtype=np.float32)
            if pixel_array.size != expected_size:
                raise ValueError(f"Invalid pixel data size: expected {expected_size}, got {pixel_array.size}")
            if np.any(np.isnan(pixel_array)) or np.any(np.isinf(pixel_array)):
                raise ValueError("Pixel data contains invalid values (NaN or Inf)")

            # 古いUVAS_EDITED_IMAGE_*をクリーンアップ（現在のimage_referenceを除外）
            exclude_names = [ref_img.name] if ref_img else []
            self._image_manager.cleanup_edited_images(exclude_names=exclude_names)

            self._image_manager.edited_image_counter += 1
            unique_name = f"UVAS_EDITED_IMAGE_{self._image_manager.edited_image_counter}"
            edited_img = self._image_manager.create_image(unique_name, ref_img.size[0], ref_img.size[1], pixel_array, use_fake_user=True)

            index = index - 1
            tile_x = (index % TILE_SPLIT_X) * tile_width
            tile_y = (TILE_SPLIT_Y - 1 - (index // TILE_SPLIT_X)) * tile_height

            base_pixels = np.array(edited_img.pixels[:], dtype=np.float32).reshape(ref_img.size[1], ref_img.size[0], 4)
            tile_pixels = base_pixels[tile_y:tile_y+tile_height, tile_x:tile_x+tile_width, :].copy()

            mid_x = tile_width // 2
            mid_y = tile_height // 2
            if scene.mirror_direction == "LEFT_TO_RIGHT":
                tile_pixels[:, mid_x:] = np.flip(tile_pixels[:, :mid_x], axis=1)
                mirror_description = "left to right"
            elif scene.mirror_direction == "RIGHT_TO_LEFT":
                tile_pixels[:, :mid_x] = np.flip(tile_pixels[:, mid_x:], axis=1)
                mirror_description = "right to left"
            elif scene.mirror_direction == "TOP_TO_BOTTOM":
                tile_pixels[mid_y:, :] = np.flip(tile_pixels[:mid_y, :], axis=0)
                mirror_description = "top to bottom"
            else:
                tile_pixels[:mid_y, :] = np.flip(tile_pixels[mid_y:, :], axis=0)
                mirror_description = "bottom to top"

            base_pixels[tile_y:tile_y+tile_height, tile_x:tile_x+tile_width, :] = tile_pixels
            edited_img.pixels[:] = base_pixels.ravel()
            edited_img.update()
            UVAS_OT_SetTileIndex.try_generate_preview(edited_img)

            scene.image_reference = edited_img
            # Update reference preview
            if scene.image_reference:
                UVAS_OT_SetTileIndex.try_generate_preview(scene.image_reference)
                for area in context.screen.areas:
                    if area.type == 'IMAGE_EDITOR':
                        area.spaces.active.image = scene.image_reference
                        area.tag_redraw()
                context.area.tag_redraw()
                bpy.ops.wm.redraw_timer(type='DRAW', iterations=1)

            self.report({'INFO'}, f"Tile at index {index + 1} mirrored {mirror_description}")
            scene.last_clicked_index = index + 1

            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Mirror operation failed: {str(e)}")
            logger.error(f"Mirror operation failed: {str(e)}")
            return {'CANCELLED'}

class UVAS_OT_ApplyText(bpy.types.Operator):
    bl_idname = "uvas.apply_text"
    bl_label = "Apply Text"
    bl_description = "Permanently apply text insertion to the selected tile"
    bl_options = {'REGISTER'}

    _image_manager = ImageManager()

    @classmethod
    def poll(cls, context):
        scene = context.scene
        return scene.operation_mode == "TILE" and scene.tile_operation_mode == "INSERT_TEXT" and scene.image_reference is not None and scene.last_clicked_index > 0

    def execute(self, context):
        scene = context.scene
        index = scene.last_clicked_index
        if not self.poll(context):
            self.report({'ERROR'}, "No tile selected or invalid state for text insertion!")
            return {'CANCELLED'}

        ref_img = scene.image_reference
        if not ref_img:
            self.report({'ERROR'}, "No image referenced for text insertion!")
            return {'CANCELLED'}

        try:
            TILE_SPLIT_X = int(scene.x_split)
            TILE_SPLIT_Y = int(scene.y_split)
            TILE_RESOLUTION_X = ref_img.size[0]
            TILE_RESOLUTION_Y = ref_img.size[1]
            tile_width = TILE_RESOLUTION_X // TILE_SPLIT_X
            tile_height = TILE_RESOLUTION_Y // TILE_SPLIT_Y
            if tile_width <= 0 or tile_height <= 0:
                raise ValueError(f"Invalid tile dimensions: {tile_width}x{tile_height}")
            expected_size = TILE_RESOLUTION_X * TILE_RESOLUTION_Y * 4
            pixel_array = np.array(ref_img.pixels[:], dtype=np.float32)
            if pixel_array.size != expected_size:
                raise ValueError(f"Invalid pixel data size: expected {expected_size}, got {pixel_array.size}")

            # 古いUVAS_EDITED_IMAGE_*をクリーンアップ（現在のimage_referenceを除外）
            exclude_names = [ref_img.name] if ref_img else []
            self._image_manager.cleanup_edited_images(exclude_names=exclude_names)

            self._image_manager.edited_image_counter += 1
            unique_name = f"UVAS_EDITED_IMAGE_{self._image_manager.edited_image_counter}"
            edited_img = self._image_manager.create_image(unique_name, TILE_RESOLUTION_X, TILE_RESOLUTION_Y, pixel_array, use_fake_user=True)

            index = index - 1
            tile_x = (index % TILE_SPLIT_X) * tile_width
            tile_y = (TILE_SPLIT_Y - 1 - (index // TILE_SPLIT_X)) * tile_height

            base_pixels = np.array(edited_img.pixels[:], dtype=np.float32).reshape(TILE_RESOLUTION_Y, TILE_RESOLUTION_X, 4)
            tile_pixels = base_pixels[tile_y:tile_y+tile_height, tile_x:tile_x+tile_width, :].copy()

            tile_pixels_pil = np.flipud(tile_pixels)
            tile_pixels_uint8 = (tile_pixels_pil * 255).astype(np.uint8)
            tile_img = Image.fromarray(tile_pixels_uint8, mode='RGBA')
            draw = ImageDraw.Draw(tile_img)

            font = None
            font_size = max(8, min(scene.text_font_size, 72))
            if scene.text_font and os.path.exists(bpy.path.abspath(scene.text_font)):
                font_path = bpy.path.abspath(scene.text_font)
                try:
                    font = ImageFont.truetype(font_path, font_size)
                except Exception as e:
                    logger.warning(f"Failed to load custom font '{font_path}': {str(e)}")
            
            if font is None:
                try:
                    font = ImageFont.truetype("cour.ttf", font_size)
                except Exception as e:
                    logger.warning(f"Failed to load Courier font: {str(e)}")
                    font = ImageFont.load_default()

            text = scene.text_content if scene.text_content else str(index + 1)
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            text_x = (tile_width - text_width) // 2 + scene.text_offset_x
            text_y = (tile_height - text_height) // 2 - scene.text_offset_y
            draw.text((text_x, text_y), text, fill=(255, 255, 255, 255), font=font)

            new_tile_pixels = np.array(tile_img, dtype=np.float32) / 255.0
            new_tile_pixels = np.flipud(new_tile_pixels)
            base_pixels[tile_y:tile_y+tile_height, tile_x:tile_x+tile_width, :] = new_tile_pixels

            # テキストプレビューを更新（UVAS_TEXT_PREVIEW を使用）
            preview_img_name = "UVAS_TEXT_PREVIEW"
            exclude_names = [ref_img.name, unique_name]
            self._image_manager.cleanup_by_prefix("UVAS_TEXT_PREVIEW_", exclude_names=exclude_names)
            preview_img = self._image_manager.create_image(preview_img_name, tile_width, tile_height, new_tile_pixels.ravel())

            scene.text_preview = preview_img
            scene.text_preview_index = index + 1
            UVAS_OT_SetTileIndex.try_generate_preview(preview_img)

            edited_img.pixels[:] = base_pixels.ravel()
            edited_img.update()
            UVAS_OT_SetTileIndex.try_generate_preview(edited_img)

            scene.image_reference = edited_img
            # Update reference preview
            if scene.image_reference:
                UVAS_OT_SetTileIndex.try_generate_preview(scene.image_reference)
                for area in context.screen.areas:
                    if area.type == 'IMAGE_EDITOR':
                        area.spaces.active.image = edited_img
                        area.tag_redraw()
                context.area.tag_redraw()
                bpy.ops.wm.redraw_timer(type='DRAW', iterations=1)

            self.report({'INFO'}, f"Inserted text '{text}' at tile index {index + 1}")
            # テキストプレビューのシーン参照を解除
            scene.text_preview = None
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error applying text: {str(e)}")
            logger.error(f"Error applying text: {str(e)}")
            return {'CANCELLED'}

class UVAS_OT_ApplyTextSetting(bpy.types.Operator):
    bl_idname = "uvas.apply_text_setting"
    bl_label = "Preview Text"
    bl_description = "Generate a temporary text preview in the panel for the selected tile. Requires a selected tile and Image Reference."
    bl_options = {'REGISTER'}

    _image_manager = ImageManager()

    @classmethod
    def poll(cls, context):
        scene = context.scene
        return scene.operation_mode == "TILE" and scene.tile_operation_mode == "INSERT_TEXT" and scene.image_reference is not None

    def execute(self, context):
        scene = context.scene
        index = scene.last_clicked_index

        if index <= 0:
            self.report({'WARNING'}, "No tile selected for text preview. Please select a tile.")
            logger.warning("No tile selected for text preview")
            return {'CANCELLED'}

        try:
            ref_img = scene.image_reference
            if not ref_img:
                self.report({'ERROR'}, "No reference image for text preview")
                return {'CANCELLED'}

            TILE_SPLIT_X = int(scene.x_split)
            TILE_SPLIT_Y = int(scene.y_split)
            tile_width = ref_img.size[0] // TILE_SPLIT_X
            tile_height = ref_img.size[1] // TILE_SPLIT_Y
            if tile_width <= 0 or tile_height <= 0:
                raise ValueError(f"Invalid tile dimensions: {tile_width}x{tile_height}")
            expected_size = ref_img.size[0] * ref_img.size[1] * 4
            pixel_array = np.array(ref_img.pixels[:], dtype=np.float32)
            if pixel_array.size != expected_size:
                raise ValueError(f"Invalid pixel data size: expected {expected_size}, got {pixel_array.size}")

            index = index - 1
            tile_x = (index % TILE_SPLIT_X) * tile_width
            tile_y = (TILE_SPLIT_Y - 1 - (index // TILE_SPLIT_X)) * tile_height

            ref_pixels = pixel_array.reshape(ref_img.size[1], ref_img.size[0], 4)
            tile_pixels = ref_pixels[tile_y:tile_y+tile_height, tile_x:tile_x+tile_width, :].copy()

            preview_img_name = "UVAS_TEXT_PREVIEW"
            exclude_names = [ref_img.name, "UVAS_EDITED_IMAGE"]

            # 旧形式の UVAS_TEXT_PREVIEW_{index} と既存の UVAS_TEXT_PREVIEW をクリーンアップ
            self._image_manager.cleanup_by_prefix("UVAS_TEXT_PREVIEW_", exclude_names=exclude_names)
            self._image_manager.cleanup_by_prefix("UVAS_TEXT_PREVIEW", exclude_names=exclude_names)
            preview_img = self._image_manager.create_image(preview_img_name, tile_width, tile_height, tile_pixels.ravel())

            scene.text_preview = preview_img
            scene.text_preview_index = index + 1

            tile_pixels_pil = np.flipud(tile_pixels)
            tile_pixels_uint8 = (tile_pixels_pil * 255).astype(np.uint8)
            tile_img = Image.fromarray(tile_pixels_uint8, mode='RGBA')
            draw = ImageDraw.Draw(tile_img)

            font = None
            font_size = max(8, min(scene.text_font_size, 72))
            if scene.text_font and os.path.exists(bpy.path.abspath(scene.text_font)):
                font_path = bpy.path.abspath(scene.text_font)
                try:
                    font = ImageFont.truetype(font_path, font_size)
                except Exception as e:
                    logger.warning(f"Failed to load custom font '{font_path}': {str(e)}")
            
            if font is None:
                try:
                    font = ImageFont.truetype("cour.ttf", font_size)
                except Exception as e:
                    logger.warning(f"Failed to load Courier font: {str(e)}")
                    font = ImageFont.load_default()

            text = scene.text_content if scene.text_content else str(index + 1)
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            text_x = (tile_width - text_width) // 2 + scene.text_offset_x
            text_y = (tile_height - text_height) // 2 - scene.text_offset_y
            draw.text((text_x, text_y), text, fill=(255, 255, 255, 255), font=font)

            new_tile_pixels = np.array(tile_img, dtype=np.float32) / 255.0
            new_tile_pixels = np.flipud(new_tile_pixels)
            preview_img.pixels[:] = new_tile_pixels.ravel()
            preview_img.update()
            UVAS_OT_SetTileIndex.try_generate_preview(preview_img)

            self.report({'INFO'}, f"Generated text preview for tile index {index + 1}. Check panel for preview.")
            context.area.tag_redraw()
            bpy.ops.wm.redraw_timer(type='DRAW', iterations=1)
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to generate text preview: {str(e)}")
            logger.error(f"Failed to generate text preview: {str(e)}, index={index + 1}")
            return {'CANCELLED'}

def register():
    bpy.utils.register_class(UVAS_OT_ApplyMirror)
    bpy.utils.register_class(UVAS_OT_ApplyText)
    bpy.utils.register_class(UVAS_OT_ApplyTextSetting)

def unregister():
    bpy.utils.unregister_class(UVAS_OT_ApplyTextSetting)
    bpy.utils.unregister_class(UVAS_OT_ApplyText)
    bpy.utils.unregister_class(UVAS_OT_ApplyMirror)