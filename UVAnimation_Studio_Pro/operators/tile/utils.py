# operators/tile/utils.py
# -*- coding: utf-8 -*-
import bpy
import numpy as np
import logging

# ログ設定（INFOレベル以上）
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImageManager:
    """UVAS_Full_Image, UVAS_EDITED_IMAGE, UVAS_TEXT_PREVIEW のライフサイクルを管理"""
    def __init__(self):
        self.images = {}  # 名前 -> bpy.types.Image のマッピング
        self.edited_image_counter = 0  # 編集済み画像のカウンター

    def create_image(self, name, width, height, pixels=None, use_fake_user=False):
        """新しい画像を作成し、既存の同名画像を安全に削除"""
        try:
            if name in bpy.data.images:
                img_to_remove = bpy.data.images[name]
                for scene in bpy.data.scenes:
                    if scene.get('image_reference') and scene.image_reference == img_to_remove:
                        logger.warning(f"Image '{name}' is referenced by scene.image_reference, skipping removal")
                        return img_to_remove
                bpy.data.images.remove(img_to_remove)

            img = bpy.data.images.new(name, width=width, height=height)
            if use_fake_user:
                img.use_fake_user = True

            expected_size = width * height * 4
            if pixels is not None:
                pixel_array = np.array(pixels, copy=True, dtype=np.float32)
                if pixel_array.size != expected_size:
                    raise ValueError(f"Pixel data size mismatch: expected {expected_size}, got {pixel_array.size}")
                if np.any(np.isnan(pixel_array)) or np.any(np.isinf(pixel_array)):
                    raise ValueError("Pixel data contains invalid values (NaN or Inf)")
                img.pixels[:] = pixel_array.ravel()
            else:
                img.pixels[:] = np.zeros(expected_size, dtype=np.float32)

            img.update()
            self.images[name] = img
            return img
        except Exception as e:
            logger.error(f"Error creating image '{name}': {str(e)}")
            raise

    def get_image(self, name):
        """指定された名前の画像を取得、存在しない場合は None を返す"""
        img = self.images.get(name)
        if img and name in bpy.data.images:
            try:
                expected_size = img.size[0] * img.size[1] * 4
                pixel_array = img.pixels[:]
                if len(pixel_array) != expected_size:
                    logger.warning(f"Image '{name}' has invalid pixel data size: expected {expected_size}, got {len(pixel_array)}")
                    return None
                return img
            except Exception:
                logger.warning(f"Image '{name}' has invalid pixel data")
                return None
        logger.warning(f"Image '{name}' not found or invalid")
        return None

    def cleanup_by_prefix(self, prefix, exclude_names=None):
        """指定されたプレフィックスを持つ画像を削除（除外リストを考慮）"""
        if exclude_names is None:
            exclude_names = []
        for name in list(self.images.keys()):
            if name.startswith(prefix) and name not in exclude_names:
                try:
                    if name in bpy.data.images:
                        img = self.images[name]
                        bpy.data.images.remove(img)
                        del self.images[name]
                    else:
                        logger.warning(f"Image '{name}' already removed from bpy.data.images")
                        del self.images[name]
                except Exception as e:
                    logger.warning(f"Failed to remove image '{name}': {str(e)}")

    def cleanup_edited_images(self, exclude_names=None):
        """UVAS_EDITED_IMAGE_で始まる画像を削除（除外リストを考慮）"""
        if exclude_names is None:
            exclude_names = []
        for name in list(self.images.keys()):
            if name.startswith("UVAS_EDITED_IMAGE_") and name not in exclude_names:
                try:
                    if name in bpy.data.images:
                        img = self.images[name]
                        bpy.data.images.remove(img)
                        del self.images[name]
                    else:
                        logger.warning(f"Edited image '{name}' already removed from bpy.data.images")
                        del self.images[name]
                except Exception as e:
                    logger.warning(f"Failed to remove edited image '{name}': {str(e)}")