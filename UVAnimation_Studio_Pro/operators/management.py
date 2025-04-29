# operators/management.py
# -*- coding: utf-8 -*-
import bpy
import numpy as np
import os
import logging
from .tile.generation import UVAS_OT_SetTileIndex

# デバッグ用ログ設定
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class UVAS_OT_CleanUnusedImages(bpy.types.Operator):
    bl_idname = "uvas.clean_unused_images"
    bl_label = "Clean Unused Images"
    bl_description = "Remove images with zero users from the Blender data"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        removed_count = 0
        for img in bpy.data.images:
            if img.users == 0:
                logger.debug(f"Removing unused image: {img.name}")
                bpy.data.images.remove(img)
                removed_count += 1
        self.report({'INFO'}, f"Removed {removed_count} unused images.")
        logger.debug(f"Cleaned {removed_count} unused images")
        return {'FINISHED'}

class UVAS_OT_ExportGeneratedImages(bpy.types.Operator):
    bl_idname = "uvas.export_generated_images"
    bl_label = "Export Generated Images"
    bl_description = "Export all generated images to the output directory"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        output_dir = bpy.path.abspath(scene.output_dir) if scene.output_dir else bpy.path.abspath("//")
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        exported_count = 0
        for img in bpy.data.images:
            if img.name.startswith(("UVAS_Full_Image", "UVAS_Single_Tile", "UVAS_Tile_", "UVAS_Patched", "UVAS_EDITED")):
                base_name = img.name.replace("UVAS_", "").replace("_", "_").lower() + ".png"
                output_path = os.path.join(output_dir, base_name)
                counter = 1
                while os.path.exists(output_path):
                    name_parts = base_name.split(".png")
                    output_path = os.path.join(output_dir, f"{name_parts[0]}.{str(counter).zfill(3)}.png")
                    counter += 1
                
                img.filepath_raw = output_path
                img.file_format = 'PNG'
                img.save()
                exported_count += 1

        self.report({'INFO'}, f"Exported {exported_count} generated images to {output_dir}")
        logger.debug(f"Exported {exported_count} images to {output_dir}")
        return {'FINISHED'}

class UVAS_OT_SelectImage(bpy.types.Operator):
    bl_idname = "uvas.select_image"
    bl_label = "Select Image"
    bl_description = "Display the selected image in the image viewer"
    bl_options = {'REGISTER', 'UNDO'}

    image_name: bpy.props.StringProperty(name="Image Name")

    def execute(self, context):
        if self.image_name in bpy.data.images:
            img = bpy.data.images[self.image_name]
            for area in context.screen.areas:
                if area.type == 'IMAGE_EDITOR':
                    area.spaces.active.image = img
            self.report({'INFO'}, f"Selected image: {self.image_name}")
            logger.debug(f"Selected image: {self.image_name}")
        else:
            self.report({'ERROR'}, f"Image {self.image_name} not found!")
            logger.error(f"Image not found: {self.image_name}")
        return {'FINISHED'}

class UVAS_OT_DeleteImage(bpy.types.Operator):
    bl_idname = "uvas.delete_image"
    bl_label = "Delete Image"
    bl_description = "Delete the selected image from memory"
    bl_options = {'REGISTER', 'UNDO'}

    image_name: bpy.props.StringProperty(name="Image Name")

    def execute(self, context):
        if self.image_name in bpy.data.images:
            logger.debug(f"Deleting image: {self.image_name}")
            bpy.data.images.remove(bpy.data.images[self.image_name])
            self.report({'INFO'}, f"Deleted image: {self.image_name}")
            logger.debug(f"Deleted image: {self.image_name}")
        else:
            self.report({'ERROR'}, f"Image {self.image_name} not found!")
            logger.error(f"Image not found: {self.image_name}")
        return {'FINISHED'}

class UVAS_OT_RenameImage(bpy.types.Operator):
    bl_idname = "uvas.rename_image"
    bl_label = "Rename Image"
    bl_description = "Rename the selected image"
    bl_options = {'REGISTER', 'UNDO'}

    image_name: bpy.props.StringProperty(name="Image Name")
    new_name_suffix: bpy.props.StringProperty(name="New Name Suffix", default="")

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Current Name: {self.image_name}")
        layout.prop(self, "new_name_suffix", text="New Suffix (UVAS_ will be prefixed)")

    def execute(self, context):
        if self.image_name in bpy.data.images:
            img = bpy.data.images[self.image_name]
            new_name = f"UVAS_{self.new_name_suffix}" if self.new_name_suffix else self.image_name
            if new_name != self.image_name and new_name not in bpy.data.images:
                img.name = new_name
                self.report({'INFO'}, f"Renamed image from {self.image_name} to {new_name}")
                logger.debug(f"Renamed image: {self.image_name} to {new_name}")
            elif new_name == self.image_name:
                self.report({'INFO'}, "Name unchanged.")
                logger.debug(f"Image name unchanged: {self.image_name}")
            else:
                self.report({'ERROR'}, f"Name {new_name} already exists!")
                logger.error(f"Image name already exists: {new_name}")
                return {'CANCELLED'}
        else:
            self.report({'ERROR'}, f"Image {self.image_name} not found!")
            logger.error(f"Image not found: {self.image_name}")
            return {'CANCELLED'}
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class UVAS_OT_NegateImage(bpy.types.Operator):
    bl_idname = "uvas.negate_image"
    bl_label = "Negate Image"
    bl_description = "Invert the colors of the referenced image"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        if not scene.image_reference:
            self.report({'ERROR'}, "No image referenced for negation!")
            logger.error("No image referenced for NEGATE")
            return {'CANCELLED'}

        ref_img = scene.image_reference
        try:
            width, height = ref_img.size
        except Exception as e:
            self.report({'ERROR'}, f"Error accessing image size: {str(e)}")
            logger.error(f"Error accessing image size for NEGATE: {str(e)}")
            return {'CANCELLED'}

        # 外部画像をメモリにコピー（非破壊性維持）
        if ref_img.filepath and not ref_img.is_dirty:
            if "UVAS_EDITED_IMAGE" in bpy.data.images:
                bpy.data.images.remove(bpy.data.images["UVAS_EDITED_IMAGE"])
            new_img = bpy.data.images.new("UVAS_EDITED_IMAGE", width=width, height=height)
            new_img.pixels[:] = ref_img.pixels[:]
            new_img.update()
            scene.image_reference = new_img
        else:
            new_img = ref_img

        try:
            # ピクセルデータを取得し、RGBを反転（アルファは保持）
            pixels = np.array(new_img.pixels[:]).reshape(height, width, 4)
            pixels[:, :, :3] = 1.0 - pixels[:, :, :3]  # RGBを反転
            new_img.pixels[:] = pixels.ravel()
            new_img.update()
            UVAS_OT_SetTileIndex.try_generate_preview(new_img)

            for area in context.screen.areas:
                if area.type == 'IMAGE_EDITOR':
                    area.spaces.active.image = new_img

            self.report({'INFO'}, "Image colors negated successfully")
            logger.debug("Completed NEGATE operation")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error during negate operation: {str(e)}")
            logger.error(f"Error during NEGATE: {str(e)}")
            return {'CANCELLED'}

class UVAS_OT_GrayscaleImage(bpy.types.Operator):
    bl_idname = "uvas.grayscale_image"
    bl_label = "Grayscale Image"
    bl_description = "Convert the referenced image to grayscale"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        if not scene.image_reference:
            self.report({'ERROR'}, "No image referenced for grayscale conversion!")
            logger.error("No image referenced for GRAYSCALE")
            return {'CANCELLED'}

        ref_img = scene.image_reference
        try:
            width, height = ref_img.size
        except Exception as e:
            self.report({'ERROR'}, f"Error accessing image size: {str(e)}")
            logger.error(f"Error accessing image size for GRAYSCALE: {str(e)}")
            return {'CANCELLED'}

        # 外部画像をメモリにコピー（非破壊性維持）
        if ref_img.filepath and not ref_img.is_dirty:
            if "UVAS_EDITED_IMAGE" in bpy.data.images:
                bpy.data.images.remove(bpy.data.images["UVAS_EDITED_IMAGE"])
            new_img = bpy.data.images.new("UVAS_EDITED_IMAGE", width=width, height=height)
            new_img.pixels[:] = ref_img.pixels[:]
            new_img.update()
            scene.image_reference = new_img
        else:
            new_img = ref_img

        try:
            # ピクセルデータを取得し、グレースケールに変換（輝度計算）
            pixels = np.array(new_img.pixels[:]).reshape(height, width, 4)
            # 輝度 = 0.299*R + 0.587*G + 0.114*B
            gray = 0.299 * pixels[:, :, 0] + 0.587 * pixels[:, :, 1] + 0.114 * pixels[:, :, 2]
            pixels[:, :, 0] = gray  # R
            pixels[:, :, 1] = gray  # G
            pixels[:, :, 2] = gray  # B
            new_img.pixels[:] = pixels.ravel()
            new_img.update()
            UVAS_OT_SetTileIndex.try_generate_preview(new_img)

            for area in context.screen.areas:
                if area.type == 'IMAGE_EDITOR':
                    area.spaces.active.image = new_img

            self.report({'INFO'}, "Image converted to grayscale successfully")
            logger.debug("Completed GRAYSCALE operation")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error during grayscale operation: {str(e)}")
            logger.error(f"Error during GRAYSCALE: {str(e)}")
            return {'CANCELLED'}

class UVAS_OT_RotateImage(bpy.types.Operator):
    bl_idname = "uvas.rotate_image"
    bl_label = "Rotate Image"
    bl_description = "Rotate the referenced image by 90, -90, or 180 degrees"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        if not scene.image_reference:
            self.report({'ERROR'}, "No image referenced for rotation!")
            logger.error("No image referenced for ROTATE")
            return {'CANCELLED'}

        ref_img = scene.image_reference
        try:
            width, height = ref_img.size
        except Exception as e:
            self.report({'ERROR'}, f"Error accessing image size: {str(e)}")
            logger.error(f"Error accessing image size for ROTATE: {str(e)}")
            return {'CANCELLED'}

        # 外部画像をメモリにコピー（非破壊性維持）
        if ref_img.filepath and not ref_img.is_dirty:
            if "UVAS_EDITED_IMAGE" in bpy.data.images:
                bpy.data.images.remove(bpy.data.images["UVAS_EDITED_IMAGE"])
            new_img = bpy.data.images.new("UVAS_EDITED_IMAGE", width=width, height=height)
            new_img.pixels[:] = ref_img.pixels[:]
            new_img.update()
            scene.image_reference = new_img
        else:
            new_img = ref_img

        try:
            # 回転方向に基づく処理
            if scene.rotate_direction == "90":
                rotation_k = -1  # 90°反時計回り
                rotation_direction = "90 degrees"
            elif scene.rotate_direction == "-90":
                rotation_k = 1  # 90°時計回り
                rotation_direction = "-90 degrees"
            else:  # 180
                rotation_k = 2  # 180°回転
                rotation_direction = "180 degrees"

            # ピクセルデータを取得し、画像全体を回転
            pixels = np.array(new_img.pixels[:]).reshape(height, width, 4)
            rotated_pixels = np.rot90(pixels, k=rotation_k)
            new_height, new_width = rotated_pixels.shape[:2]
            
            # 新しい画像サイズで更新
            if "UVAS_EDITED_IMAGE" in bpy.data.images:
                bpy.data.images.remove(bpy.data.images["UVAS_EDITED_IMAGE"])
            new_img = bpy.data.images.new("UVAS_EDITED_IMAGE", width=new_width, height=new_height)
            new_img.pixels[:] = rotated_pixels.ravel()
            new_img.update()
            scene.image_reference = new_img
            UVAS_OT_SetTileIndex.try_generate_preview(new_img)

            for area in context.screen.areas:
                if area.type == 'IMAGE_EDITOR':
                    area.spaces.active.image = new_img

            self.report({'INFO'}, f"Image rotated by {rotation_direction} successfully")
            logger.debug(f"Completed ROTATE operation: {rotation_direction}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error during rotate operation: {str(e)}")
            logger.error(f"Error during ROTATE: {str(e)}")
            return {'CANCELLED'}

class UVAS_OT_FlipImage(bpy.types.Operator):
    bl_idname = "uvas.flip_image"
    bl_label = "Flip Image"
    bl_description = "Flip the referenced image horizontally or vertically"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        if not scene.image_reference:
            self.report({'ERROR'}, "No image referenced for flipping!")
            logger.error("No image referenced for FLIP")
            return {'CANCELLED'}

        ref_img = scene.image_reference
        try:
            width, height = ref_img.size
        except Exception as e:
            self.report({'ERROR'}, f"Error accessing image size: {str(e)}")
            logger.error(f"Error accessing image size for FLIP: {str(e)}")
            return {'CANCELLED'}

        # 外部画像をメモリにコピー（非破壊性維持）
        if ref_img.filepath and not ref_img.is_dirty:
            if "UVAS_EDITED_IMAGE" in bpy.data.images:
                bpy.data.images.remove(bpy.data.images["UVAS_EDITED_IMAGE"])
            new_img = bpy.data.images.new("UVAS_EDITED_IMAGE", width=width, height=height)
            new_img.pixels[:] = ref_img.pixels[:]
            new_img.update()
            scene.image_reference = new_img
        else:
            new_img = ref_img

        try:
            # フリップ方向に基づく処理
            if scene.flip_direction in ["-X_TO_X", "X_TO_-X"]:
                axis = 1  # X軸（水平）反転
                flip_description = "left to right" if scene.flip_direction == "-X_TO_X" else "right to left"
            else:  # Y_TO_-Y, -Y_TO_Y
                axis = 0  # Y軸（垂直）反転
                flip_description = "up to down" if scene.flip_direction == "Y_TO_-Y" else "down to up"

            # ピクセルデータを取得し、画像全体をフリップ
            pixels = np.array(new_img.pixels[:]).reshape(height, width, 4)
            flipped_pixels = np.flip(pixels, axis=axis)
            
            # 新しい画像で更新
            new_img.pixels[:] = flipped_pixels.ravel()
            new_img.update()
            UVAS_OT_SetTileIndex.try_generate_preview(new_img)

            for area in context.screen.areas:
                if area.type == 'IMAGE_EDITOR':
                    area.spaces.active.image = new_img

            self.report({'INFO'}, f"Image flipped {flip_description} successfully")
            logger.debug(f"Completed FLIP operation: {flip_description}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error during flip operation: {str(e)}")
            logger.error(f"Error during FLIP: {str(e)}")
            return {'CANCELLED'}

class UVAS_OT_MirrorImage(bpy.types.Operator):
    bl_idname = "uvas.mirror_image"
    bl_label = "Mirror Image"
    bl_description = "Mirror the referenced image symmetrically"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        if not scene.image_reference:
            self.report({'ERROR'}, "No image referenced for mirroring!")
            logger.error("No image referenced for MIRROR")
            return {'CANCELLED'}

        ref_img = scene.image_reference
        try:
            width, height = ref_img.size
        except Exception as e:
            self.report({'ERROR'}, f"Error accessing image size: {str(e)}")
            logger.error(f"Error accessing image size for MIRROR: {str(e)}")
            return {'CANCELLED'}

        # 外部画像をメモリにコピー（非破壊性維持）
        if ref_img.filepath and not ref_img.is_dirty:
            if "UVAS_EDITED_IMAGE" in bpy.data.images:
                bpy.data.images.remove(bpy.data.images["UVAS_EDITED_IMAGE"])
            new_img = bpy.data.images.new("UVAS_EDITED_IMAGE", width=width, height=height)
            new_img.pixels[:] = ref_img.pixels[:]
            new_img.update()
            scene.image_reference = new_img
        else:
            new_img = ref_img

        try:
            # ピクセルデータを取得
            pixels = np.array(new_img.pixels[:]).reshape(height, width, 4)
            new_pixels = pixels.copy()

            # ミラー方向に基づく処理（中央を基準に半分をコピー）
            mid_x = width // 2
            mid_y = height // 2
            if scene.mirror_direction == "LEFT_TO_RIGHT":
                # 左半分を右にミラーコピー
                new_pixels[:, mid_x:] = np.flip(new_pixels[:, :mid_x], axis=1)
                mirror_description = "left to right"
            elif scene.mirror_direction == "RIGHT_TO_LEFT":
                # 右半分を左にミラーコピー
                new_pixels[:, :mid_x] = np.flip(new_pixels[:, mid_x:], axis=1)
                mirror_description = "right to left"
            elif scene.mirror_direction == "TOP_TO_BOTTOM":
                # 上半分を下にミラーコピー
                new_pixels[mid_y:, :] = np.flip(new_pixels[:mid_y, :], axis=0)
                mirror_description = "top to bottom"
            else:  # BOTTOM_TO_TOP
                # 下半分を上にミラーコピー
                new_pixels[:mid_y, :] = np.flip(new_pixels[mid_y:, :], axis=0)
                mirror_description = "bottom to top"

            # 新しい画像で更新
            new_img.pixels[:] = new_pixels.ravel()
            new_img.update()
            UVAS_OT_SetTileIndex.try_generate_preview(new_img)

            for area in context.screen.areas:
                if area.type == 'IMAGE_EDITOR':
                    area.spaces.active.image = new_img

            self.report({'INFO'}, f"Image mirrored {mirror_description} successfully")
            logger.debug(f"Completed MIRROR operation: {mirror_description}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error during mirror operation: {str(e)}")
            logger.error(f"Error during MIRROR: {str(e)}")
            return {'CANCELLED'}

def register():
    bpy.utils.register_class(UVAS_OT_CleanUnusedImages)
    bpy.utils.register_class(UVAS_OT_ExportGeneratedImages)
    bpy.utils.register_class(UVAS_OT_SelectImage)
    bpy.utils.register_class(UVAS_OT_DeleteImage)
    bpy.utils.register_class(UVAS_OT_RenameImage)
    bpy.utils.register_class(UVAS_OT_NegateImage)
    bpy.utils.register_class(UVAS_OT_GrayscaleImage)
    bpy.utils.register_class(UVAS_OT_RotateImage)
    bpy.utils.register_class(UVAS_OT_FlipImage)
    bpy.utils.register_class(UVAS_OT_MirrorImage)
    logger.debug("Registered management operators")

def unregister():
    bpy.utils.unregister_class(UVAS_OT_MirrorImage)
    bpy.utils.unregister_class(UVAS_OT_FlipImage)
    bpy.utils.unregister_class(UVAS_OT_RotateImage)
    bpy.utils.unregister_class(UVAS_OT_GrayscaleImage)
    bpy.utils.unregister_class(UVAS_OT_NegateImage)
    bpy.utils.unregister_class(UVAS_OT_RenameImage)
    bpy.utils.unregister_class(UVAS_OT_DeleteImage)
    bpy.utils.unregister_class(UVAS_OT_SelectImage)
    bpy.utils.unregister_class(UVAS_OT_ExportGeneratedImages)
    bpy.utils.unregister_class(UVAS_OT_CleanUnusedImages)
    logger.debug("Unregistered management operators")