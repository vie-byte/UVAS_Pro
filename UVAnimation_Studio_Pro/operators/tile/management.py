# operators/tile/management.py
# -*- coding: utf-8 -*-
import bpy
import numpy as np
import logging
import random
from .utils import ImageManager
from .generation import UVAS_OT_SetTileIndex

# ログ設定（INFOレベル以上）
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UVAS_OT_ApplySwap(bpy.types.Operator):
    bl_idname = "uvas.apply_swap"
    bl_label = "Apply Swap"
    bl_description = "Apply swap operation to the selected tiles"
    bl_options = {'REGISTER'}

    _image_manager = ImageManager()

    @classmethod
    def poll(cls, context):
        scene = context.scene
        return scene.operation_mode == "TILE" and scene.tile_operation_mode == "SWAP" and scene.image_reference is not None and scene.swap_first_index > 0 and scene.swap_second_index > 0

    def execute(self, context):
        scene = context.scene
        if not self.poll(context):
            self.report({'ERROR'}, "Invalid state for swap operation")
            return {'CANCELLED'}

        first_index = scene.swap_first_index
        second_index = scene.swap_second_index

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

            first_index = first_index - 1
            second_index = second_index - 1

            first_tile_x = (first_index % TILE_SPLIT_X) * tile_width
            first_tile_y = (TILE_SPLIT_Y - 1 - (first_index // TILE_SPLIT_X)) * tile_height
            second_tile_x = (second_index % TILE_SPLIT_X) * tile_width
            second_tile_y = (TILE_SPLIT_Y - 1 - (second_index // TILE_SPLIT_X)) * tile_height

            base_pixels = np.array(edited_img.pixels[:], dtype=np.float32).reshape(ref_img.size[1], ref_img.size[0], 4)
            temp_pixels = base_pixels[first_tile_y:first_tile_y+tile_height, first_tile_x:first_tile_x+tile_width, :].copy()
            base_pixels[first_tile_y:first_tile_y+tile_height, first_tile_x:first_tile_x+tile_width, :] = \
                base_pixels[second_tile_y:second_tile_y+tile_height, second_tile_x:second_tile_x+tile_width, :]
            base_pixels[second_tile_y:second_tile_y+tile_height, second_tile_x:second_tile_x+tile_width, :] = temp_pixels

            edited_img.pixels[:] = base_pixels.ravel()
            edited_img.update()
            UVAS_OT_SetTileIndex.try_generate_preview(edited_img)

            scene.image_reference = edited_img
            if scene.image_reference:
                UVAS_OT_SetTileIndex.try_generate_preview(scene.image_reference)
                for area in context.screen.areas:
                    if area.type == 'IMAGE_EDITOR':
                        area.spaces.active.image = scene.image_reference
                        area.tag_redraw()
                context.area.tag_redraw()
                bpy.ops.wm.redraw_timer(type='DRAW', iterations=1)

            self.report({'INFO'}, f"Swapped tiles between index {first_index + 1} and {second_index + 1}")
            scene.swap_first_index = -1
            scene.swap_second_index = -1

            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Swap operation failed: {str(e)}")
            logger.error(f"Swap operation failed: {str(e)}")
            return {'CANCELLED'}

class UVAS_OT_ApplyShuffle(bpy.types.Operator):
    bl_idname = "uvas.apply_shuffle"
    bl_label = "Apply Shuffle"
    bl_description = "Apply shuffle operation to all selected tiles"
    bl_options = {'REGISTER'}

    _image_manager = ImageManager()

    @classmethod
    def poll(cls, context):
        scene = context.scene
        return scene.operation_mode == "TILE" and scene.tile_operation_mode == "SHUFFLE" and scene.image_reference is not None and scene.swap_first_index > 0 and scene.shuffle_second_index > 0

    def execute(self, context):
        scene = context.scene
        if not self.poll(context):
            self.report({'ERROR'}, "Invalid state for shuffle operation")
            return {'CANCELLED'}

        first_index = scene.swap_first_index
        second_index = scene.shuffle_second_index

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

            first_index = first_index - 1
            second_index = second_index - 1

            # 選択範囲内の全タイルインデックスを取得
            first_x = first_index % TILE_SPLIT_X
            first_y = first_index // TILE_SPLIT_X
            second_x = second_index % TILE_SPLIT_X
            second_y = second_index // TILE_SPLIT_X
            min_x = min(first_x, second_x)
            max_x = max(first_x, second_x)
            min_y = min(first_y, second_y)
            max_y = max(first_y, second_y)

            tile_indices = []
            for y in range(min_y, max_y + 1):
                for x in range(min_x, max_x + 1):
                    idx = y * TILE_SPLIT_X + x
                    if 0 <= idx < (TILE_SPLIT_X * TILE_SPLIT_Y):
                        tile_indices.append(idx)

            logger.info(f"Shuffling {len(tile_indices)} tiles in selected range")
            shuffled_indices = tile_indices.copy()
            random.shuffle(shuffled_indices)

            base_pixels = np.array(edited_img.pixels[:], dtype=np.float32).reshape(ref_img.size[1], ref_img.size[0], 4)
            temp_tiles = []

            # タイルデータを取得
            for idx in tile_indices:
                tile_x = (idx % TILE_SPLIT_X) * tile_width
                tile_y = (TILE_SPLIT_Y - 1 - (idx // TILE_SPLIT_X)) * tile_height
                tile_pixels = base_pixels[tile_y:tile_y+tile_height, tile_x:tile_x+tile_width, :].copy()
                temp_tiles.append(tile_pixels)

            # シャッフルされた順序でタイルを配置
            for i, original_tile in enumerate(temp_tiles):
                new_idx = shuffled_indices[i]
                tile_x = (new_idx % TILE_SPLIT_X) * tile_width
                tile_y = (TILE_SPLIT_Y - 1 - (new_idx // TILE_SPLIT_X)) * tile_height
                base_pixels[tile_y:tile_y+tile_height, tile_x:tile_x+tile_width, :] = original_tile

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

            self.report({'INFO'}, f"Shuffled {len(tile_indices)} tiles in selected range")
            # 選択状態を維持
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Shuffle operation failed: {str(e)}")
            logger.error(f"Shuffle operation failed: {str(e)}")
            return {'CANCELLED'}

class UVAS_OT_ClearTextFont(bpy.types.Operator):
    bl_idname = "uvas.clear_text_font"
    bl_label = "Clear Text Font"
    bl_description = "Clear the selected font file for text insertion"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene
        scene.text_font = ""
        self.report({'INFO'}, "Text font cleared")
        return {'FINISHED'}

def register():
    bpy.utils.register_class(UVAS_OT_ApplySwap)
    bpy.utils.register_class(UVAS_OT_ApplyShuffle)
    bpy.utils.register_class(UVAS_OT_ClearTextFont)

def unregister():
    bpy.utils.unregister_class(UVAS_OT_ClearTextFont)
    bpy.utils.unregister_class(UVAS_OT_ApplyShuffle)
    bpy.utils.unregister_class(UVAS_OT_ApplySwap)