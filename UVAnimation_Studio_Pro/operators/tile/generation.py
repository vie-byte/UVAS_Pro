# operators/tile/generation.py
# -*- coding: utf-8 -*-
import bpy
import numpy as np
import logging
import os
from PIL import Image, ImageDraw, ImageFont
import hashlib
import random
import time
from .utils import ImageManager

# ログ設定（INFOレベル以上）
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UVAS_OT_SetTileIndex(bpy.types.Operator):
    bl_idname = "uvas.set_tile_index"
    bl_label = "Set Tile Index"
    bl_description = "Select a tile for extract, patch, swap, rotate, flip, mirror, or insert text operations"
    bl_options = {'REGISTER'}

    index: bpy.props.IntProperty(name="Tile Index", default=1)
    _image_manager = ImageManager()

    @classmethod
    def poll(cls, context):
        scene = context.scene
        return scene.operation_mode == "TILE" and scene.tile_operation_mode in ["SWAP", "PATCH", "EXTRACT", "ROTATE_AND_FLIP", "MIRROR", "INSERT_TEXT", "SHUFFLE"] and scene.image_reference is not None

    @staticmethod
    def try_generate_preview(image):
        """プレビュー生成"""
        if not image:
            logger.warning("No image provided for preview generation")
            return False

        try:
            width, height = image.size
            if width <= 0 or height <= 0:
                logger.warning(f"Invalid image dimensions: {width}x{height}")
                return False
            expected_size = width * height * 4
            pixel_array = np.array(image.pixels[:], dtype=np.float32)
            if pixel_array.size != expected_size:
                logger.error(f"Invalid pixel data size: expected {expected_size}, got {pixel_array.size}")
                return False
            if np.any(np.isnan(pixel_array)) or np.any(np.isinf(pixel_array)):
                logger.warning("Pixel data contains invalid values (NaN or Inf)")
                return False
            image.preview_ensure()
            return True
        except Exception as e:
            logger.warning(f"Preview generation failed for '{image.name if image else 'None'}': {str(e)}")
            return False

    def execute(self, context):
        scene = context.scene
        mode = scene.tile_operation_mode if scene.operation_mode == "TILE" else None

        if not mode:
            self.report({'ERROR'}, "No valid operation mode specified")
            return {'CANCELLED'}

        if not self.poll(context):
            self.report({'ERROR'}, "Invalid state for tile operation. Please select an image in Image Reference.")
            return {'CANCELLED'}

        try:
            ref_img = scene.image_reference
            if not ref_img:
                raise ValueError("Reference image is None")
            TILE_SPLIT_X = int(scene.x_split)
            TILE_SPLIT_Y = int(scene.y_split)
            TILE_RESOLUTION_X = ref_img.size[0]
            TILE_RESOLUTION_Y = ref_img.size[1]
            if TILE_RESOLUTION_X <= 0 or TILE_RESOLUTION_Y <= 0:
                raise ValueError(f"Invalid image size: {TILE_RESOLUTION_X}x{TILE_RESOLUTION_Y}")
            expected_size = TILE_RESOLUTION_X * TILE_RESOLUTION_Y * 4
            pixel_array = np.array(ref_img.pixels[:], dtype=np.float32)
            if pixel_array.size != expected_size:
                raise ValueError(f"Invalid pixel data size: expected {expected_size}, got {pixel_array.size}")
            if np.any(np.isnan(pixel_array)) or np.any(np.isinf(pixel_array)):
                raise ValueError("Pixel data contains invalid values (NaN or Inf)")

            tile_width = TILE_RESOLUTION_X // TILE_SPLIT_X
            tile_height = TILE_RESOLUTION_Y // TILE_SPLIT_Y
            if tile_width <= 0 or tile_height <= 0:
                raise ValueError(f"Invalid tile dimensions: {tile_width}x{tile_height}")

            if mode == "SWAP":
                if scene.swap_first_index == -1:
                    scene.swap_first_index = self.index
                    self.report({'INFO'}, f"Selected first tile at index {self.index} for swapping.")
                elif scene.swap_second_index == -1:
                    scene.swap_second_index = self.index
                    self.report({'INFO'}, f"Selected second tile at index {self.index} for swapping. Press 'Apply Swap' button.")
                else:
                    scene.swap_first_index = -1
                    scene.swap_second_index = -1
                    self.report({'INFO'}, "Cancelled swap selection.")
                context.area.tag_redraw()
                return {'FINISHED'}

            elif mode == "PATCH":
                if not scene.tile_reference:
                    self.report({'ERROR'}, "No tile referenced for patching!")
                    return {'CANCELLED'}

                # 古いUVAS_EDITED_IMAGE_*をクリーンアップ（現在のimage_referenceを除外）
                exclude_names = [ref_img.name] if ref_img else []
                self._image_manager.cleanup_edited_images(exclude_names=exclude_names)

                self._image_manager.edited_image_counter += 1
                unique_name = f"UVAS_EDITED_IMAGE_{self._image_manager.edited_image_counter}"
                edited_img = self._image_manager.create_image(unique_name, TILE_RESOLUTION_X, TILE_RESOLUTION_Y, pixel_array, use_fake_user=True)
                tile_img = scene.tile_reference
                if tile_img.size[0] != tile_width or tile_img.size[1] != tile_height:
                    self.report({'WARNING'}, f"Tile size mismatch: expected {tile_width}x{tile_height}, got {tile_img.size[0]}x{tile_img.size[1]}")
                    return {'CANCELLED'}

                index = self.index - 1
                tile_x = (index % TILE_SPLIT_X) * tile_width
                tile_y = (TILE_SPLIT_Y - 1 - (index // TILE_SPLIT_X)) * tile_height

                base_pixels = np.array(edited_img.pixels[:], dtype=np.float32).reshape(TILE_RESOLUTION_Y, TILE_RESOLUTION_X, 4)
                tile_pixels = np.array(tile_img.pixels[:], dtype=np.float32).reshape(tile_height, tile_width, 4)
                base_pixels[tile_y:tile_y+tile_height, tile_x:tile_x+tile_width, :] = tile_pixels
                edited_img.pixels[:] = base_pixels.ravel()
                edited_img.update()
                UVAS_OT_SetTileIndex.try_generate_preview(edited_img)

                scene.image_reference = edited_img
                UVAS_OT_SetTileIndex.try_generate_preview(scene.image_reference)
                for area in context.screen.areas:
                    if area.type == 'IMAGE_EDITOR':
                        area.spaces.active.image = scene.image_reference
                        area.tag_redraw()
                self.report({'INFO'}, f"Patched tile at index {index + 1}")
                scene.last_clicked_index = index + 1
                context.area.tag_redraw()
                bpy.ops.wm.redraw_timer(type='DRAW', iterations=1)
                return {'FINISHED'}

            elif mode == "EXTRACT":
                if scene.last_clicked_index == self.index:
                    scene.last_clicked_index = 0
                    self.report({'INFO'}, f"Deselected tile index {self.index}")
                else:
                    scene.last_clicked_index = self.index
                    self.report({'INFO'}, f"Selected tile index {self.index} for extraction. Press 'Apply Extract' button.")
                context.area.tag_redraw()
                return {'FINISHED'}

            elif mode == "ROTATE_AND_FLIP":
                # 古いUVAS_EDITED_IMAGE_*をクリーンアップ（現在のimage_referenceを除外）
                exclude_names = [ref_img.name] if ref_img else []
                self._image_manager.cleanup_edited_images(exclude_names=exclude_names)

                self._image_manager.edited_image_counter += 1
                unique_name = f"UVAS_EDITED_IMAGE_{self._image_manager.edited_image_counter}"
                edited_img = self._image_manager.create_image(unique_name, TILE_RESOLUTION_X, TILE_RESOLUTION_Y, pixel_array, use_fake_user=True)

                index = self.index - 1
                tile_x = (index % TILE_SPLIT_X) * tile_width
                tile_y = (TILE_SPLIT_Y - 1 - (index // TILE_SPLIT_X)) * tile_height

                base_pixels = np.array(edited_img.pixels[:], dtype=np.float32).reshape(TILE_RESOLUTION_Y, TILE_RESOLUTION_X, 4)
                tile_pixels = base_pixels[tile_y:tile_y+tile_height, tile_x:tile_x+tile_width, :].copy()

                if scene.rotate_flip_mode == "ROTATE":
                    if tile_width != tile_height:
                        rotation_k = 2
                        rotation_direction = "180 degrees"
                    else:
                        if scene.rotate_direction == "90":
                            rotation_k = -1
                            rotation_direction = "90 degrees"
                        elif scene.rotate_direction == "-90":
                            rotation_k = 1
                            rotation_direction = "-90 degrees"
                        else:
                            rotation_k = 2
                            rotation_direction = "180 degrees"
                    transformed_pixels = np.rot90(tile_pixels, k=rotation_k)
                    transform_description = f"rotated by {rotation_direction}"
                else:
                    if scene.flip_direction in ["-X_TO_X", "X_TO_-X"]:
                        axis = 1
                        flip_description = "left to right" if scene.flip_direction == "-X_TO_X" else "right to left"
                    else:
                        axis = 0
                        flip_description = "up to down" if scene.flip_direction == "Y_TO_-Y" else "down to up"
                    transformed_pixels = np.flip(tile_pixels, axis=axis)
                    transform_description = f"flipped {flip_description}"

                base_pixels[tile_y:tile_y+tile_height, tile_x:tile_x+tile_width, :] = transformed_pixels
                edited_img.pixels[:] = base_pixels.ravel()
                edited_img.update()
                UVAS_OT_SetTileIndex.try_generate_preview(edited_img)

                scene.image_reference = edited_img
                UVAS_OT_SetTileIndex.try_generate_preview(scene.image_reference)
                for area in context.screen.areas:
                    if area.type == 'IMAGE_EDITOR':
                        area.spaces.active.image = scene.image_reference
                        area.tag_redraw()
                self.report({'INFO'}, f"Tile at index {index + 1} {transform_description}")
                scene.last_clicked_index = index + 1
                context.area.tag_redraw()
                bpy.ops.wm.redraw_timer(type='DRAW', iterations=1)
                return {'FINISHED'}

            elif mode == "MIRROR":
                if scene.last_clicked_index == self.index:
                    scene.last_clicked_index = 0
                    self.report({'INFO'}, f"Deselected tile index {self.index}")
                else:
                    scene.last_clicked_index = self.index
                    self.report({'INFO'}, f"Selected tile index {self.index} for mirroring. Press 'Apply Mirror' button.")
                context.area.tag_redraw()
                return {'FINISHED'}

            elif mode == "INSERT_TEXT":
                if scene.last_clicked_index == self.index:
                    scene.last_clicked_index = 0
                    scene.text_preview = None
                    scene.text_preview_index = -1
                    self._image_manager.cleanup_by_prefix("UVAS_TEXT_PREVIEW_")
                    self._image_manager.cleanup_by_prefix("UVAS_TEXT_PREVIEW", exclude_names=["UVAS_Full_Image", "UVAS_EDITED_IMAGE"])
                    self.report({'INFO'}, f"Deselected tile index {self.index}")
                else:
                    scene.last_clicked_index = self.index
                    index = self.index - 1
                    tile_x = (index % TILE_SPLIT_X) * tile_width
                    tile_y = (TILE_SPLIT_Y - 1 - (index // TILE_SPLIT_X)) * tile_height

                    ref_pixels = pixel_array.reshape(TILE_RESOLUTION_Y, TILE_RESOLUTION_X, 4)
                    tile_pixels = ref_pixels[tile_y:tile_y+tile_height, tile_x:tile_x+tile_width, :].copy()

                    preview_img_name = "UVAS_TEXT_PREVIEW"
                    exclude_names = [ref_img.name, "UVAS_EDITED_IMAGE"]

                    self._image_manager.cleanup_by_prefix("UVAS_TEXT_PREVIEW_", exclude_names=exclude_names)
                    self._image_manager.cleanup_by_prefix("UVAS_TEXT_PREVIEW", exclude_names=exclude_names)
                    preview_img = self._image_manager.create_image(preview_img_name, tile_width, tile_height, tile_pixels.ravel())
                    scene.text_preview = preview_img
                    scene.text_preview_index = self.index

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

                    text = scene.text_content if scene.text_content else str(self.index)
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

                    self.report({'INFO'}, f"Selected tile index {self.index} for text insertion")
                context.area.tag_redraw()
                bpy.ops.wm.redraw_timer(type='DRAW', iterations=1)
                return {'FINISHED'}

            elif mode == "SHUFFLE":
                if scene.swap_first_index == -1:
                    scene.swap_first_index = self.index
                    scene.shuffle_second_index = -1
                    self.report({'INFO'}, f"Selected first tile at index {self.index} for shuffling.")
                elif scene.shuffle_second_index == -1:
                    scene.shuffle_second_index = self.index
                    self.report({'INFO'}, f"Selected second tile at index {self.index} for shuffling. Press 'Apply Shuffle' button.")
                else:
                    scene.swap_first_index = -1
                    scene.shuffle_second_index = -1
                    self.report({'INFO'}, "Cancelled shuffle selection.")
                context.area.tag_redraw()
                return {'FINISHED'}

            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Operation failed: {str(e)}")
            logger.error(f"Operation failed: {str(e)}, index={self.index}")
            return {'CANCELLED'}

class UVAS_OT_ApplyExtract(bpy.types.Operator):
    bl_idname = "uvas.apply_extract"
    bl_label = "Apply Extract"
    bl_description = "Extract the selected tile from the referenced image"
    bl_options = {'REGISTER'}

    _image_manager = ImageManager()

    @classmethod
    def poll(cls, context):
        scene = context.scene
        return scene.operation_mode == "TILE" and scene.tile_operation_mode == "EXTRACT" and scene.image_reference is not None and scene.last_clicked_index > 0

    def execute(self, context):
        scene = context.scene
        index = scene.last_clicked_index
        if not self.poll(context):
            self.report({'ERROR'}, "Invalid state for extract operation")
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

            index = index - 1
            tile_x = (index % TILE_SPLIT_X) * tile_width
            tile_y = (TILE_SPLIT_Y - 1 - (index // TILE_SPLIT_X)) * tile_height

            ref_pixels = pixel_array.reshape(ref_img.size[1], ref_img.size[0], 4)
            tile_pixels = ref_pixels[tile_y:tile_y+tile_height, tile_x:tile_x+tile_width, :].copy()

            cropped_img = self._image_manager.create_image(f"UVAS_Tile_{index + 1}", tile_width, tile_height, tile_pixels.ravel(), use_fake_user=True)
            cropped_img.update()
            UVAS_OT_SetTileIndex.try_generate_preview(cropped_img)

            # Update reference preview
            if scene.image_reference:
                UVAS_OT_SetTileIndex.try_generate_preview(scene.image_reference)
                for area in context.screen.areas:
                    if area.type == 'IMAGE_EDITOR':
                        area.spaces.active.image = scene.image_reference
                        area.tag_redraw()
                context.area.tag_redraw()
                bpy.ops.wm.redraw_timer(type='DRAW', iterations=1)

            self.report({'INFO'}, f"Extracted tile generated in memory: UVAS_Tile_{index + 1}")
            scene.last_clicked_index = index + 1

            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Extract operation failed: {str(e)}")
            logger.error(f"Extract operation failed: {str(e)}")
            return {'CANCELLED'}

def register():
    bpy.utils.register_class(UVAS_OT_SetTileIndex)
    bpy.utils.register_class(UVAS_OT_ApplyExtract)

def unregister():
    bpy.utils.unregister_class(UVAS_OT_ApplyExtract)
    bpy.utils.unregister_class(UVAS_OT_SetTileIndex)