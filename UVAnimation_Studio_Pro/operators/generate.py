# operators/generate.py
# -*- coding: utf-8 -*-
import bpy
import numpy as np
import os
import random
from PIL import Image, ImageDraw
from .tile.generation import UVAS_OT_SetTileIndex
from ..utils import get_output_filepath

class UVAS_OT_GenerateFullImage(bpy.types.Operator):
    bl_idname = "uvas.generate_full_image"
    bl_label = "Generate Full Image"
    bl_description = "Generate a full image based on the specified resolution and split settings"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        try:
            resolution_x = int(scene.resolution_x)
            resolution_y = int(scene.resolution_y)
            split_x = int(scene.x_split)
            split_y = int(scene.y_split)
            border_width = int(scene.border_width) if scene.generate_mode == "GRID" else 0
            is_outer = scene.grid_border_type == "OUTER" if scene.generate_mode == "GRID" else False
        except Exception as e:
            self.report({'ERROR'}, f"Invalid settings: {str(e)}")
            return {'CANCELLED'}

        tile_width = resolution_x // split_x
        tile_height = resolution_y // split_y
        full_width = resolution_x
        full_height = resolution_y

        if is_outer:
            full_width += 2 * border_width * split_x
            full_height += 2 * border_width * split_y
            tile_width += 2 * border_width
            tile_height += 2 * border_width

        try:
            if "UVAS_Full_Image" in bpy.data.images:
                bpy.data.images.remove(bpy.data.images["UVAS_Full_Image"])
            
            full_img = bpy.data.images.new("UVAS_Full_Image", width=full_width, height=full_height)
            pixels = np.ones((full_height, full_width, 4), dtype=np.float32)

            if scene.generate_mode == "FILL":
                for y in range(split_y):
                    for x in range(split_x):
                        tile_x = x * tile_width
                        tile_y = (split_y - 1 - y) * tile_height
                        tile_pixels = np.ones((tile_height, tile_width, 4), dtype=np.float32)
                        tile_pixels[:, :, 0] = random.random()
                        tile_pixels[:, :, 1] = random.random()
                        tile_pixels[:, :, 2] = random.random()
                        pixels[tile_y:tile_y+tile_height, tile_x:tile_x+tile_width, :] = tile_pixels
            elif scene.generate_mode == "GRID":
                pixels[:, :, :] = 0.0
                for y in range(split_y):
                    for x in range(split_x):
                        tile_x = x * tile_width
                        tile_y = (split_y - 1 - y) * tile_height
                        if is_outer:
                            tile_x += border_width
                            tile_y += border_width
                            border_color = [1.0, 1.0, 1.0, 1.0]
                            pixels[tile_y-border_width:tile_y+tile_height+border_width, tile_x-border_width:tile_x, :] = border_color
                            pixels[tile_y-border_width:tile_y+tile_height+border_width, tile_x+tile_width:tile_x+tile_width+border_width, :] = border_color
                            pixels[tile_y-border_width:tile_y, tile_x:tile_x+tile_width, :] = border_color
                            pixels[tile_y+tile_height:tile_y+tile_height+border_width, tile_x:tile_x+tile_width, :] = border_color
                        else:
                            border_color = [1.0, 1.0, 1.0, 1.0]
                            pixels[tile_y:tile_y+tile_height, tile_x:tile_x+border_width, :] = border_color
                            pixels[tile_y:tile_y+tile_height, tile_x+tile_width-border_width:tile_x+tile_width, :] = border_color
                            pixels[tile_y:tile_y+border_width, tile_x:tile_x+tile_width, :] = border_color
                            pixels[tile_y+tile_height-border_width:tile_y+tile_height, tile_x:tile_x+tile_width, :] = border_color

            pixels = np.flipud(pixels)
            full_img.pixels[:] = pixels.ravel()
            full_img.update()
            UVAS_OT_SetTileIndex.try_generate_preview(full_img)

            # Set generated image as scene.image_reference for OPERATION panel
            scene.image_reference = full_img

            for area in context.screen.areas:
                if area.type == 'IMAGE_EDITOR':
                    area.spaces.active.image = full_img

            self.report({'INFO'}, f"Generated full image: {full_width}x{full_height}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error generating full image: {str(e)}")
            return {'CANCELLED'}

class UVAS_OT_GenerateSingleTile(bpy.types.Operator):
    bl_idname = "uvas.generate_single_tile"
    bl_label = "Generate Single Tile"
    bl_description = "Generate a single tile based on the specified resolution"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        try:
            resolution_x = int(scene.resolution_x)
            resolution_y = int(scene.resolution_y)
            border_width = int(scene.border_width) if scene.generate_mode == "GRID" else 0
            is_outer = scene.grid_border_type == "OUTER" if scene.generate_mode == "GRID" else False
        except Exception as e:
            self.report({'ERROR'}, f"Invalid settings: {str(e)}")
            return {'CANCELLED'}

        tile_width = resolution_x
        tile_height = resolution_y

        if is_outer:
            tile_width += 2 * border_width
            tile_height += 2 * border_width

        try:
            if "UVAS_Single_Tile" in bpy.data.images:
                bpy.data.images.remove(bpy.data.images["UVAS_Single_Tile"])
            
            tile_img = bpy.data.images.new("UVAS_Single_Tile", width=tile_width, height=tile_height)
            pixels = np.ones((tile_height, tile_width, 4), dtype=np.float32)

            if scene.generate_mode == "FILL":
                pixels[:, :, 0] = random.random()
                pixels[:, :, 1] = random.random()
                pixels[:, :, 2] = random.random()
            elif scene.generate_mode == "GRID":
                pixels[:, :, :] = 0.0
                if is_outer:
                    border_color = [1.0, 1.0, 1.0, 1.0]
                    pixels[0:border_width, :, :] = border_color
                    pixels[tile_height-border_width:tile_height, :, :] = border_color
                    pixels[:, 0:border_width, :] = border_color
                    pixels[:, tile_width-border_width:tile_width, :] = border_color
                else:
                    border_color = [1.0, 1.0, 1.0, 1.0]
                    pixels[0:border_width, :, :] = border_color
                    pixels[tile_height-border_width:tile_height, :, :] = border_color
                    pixels[:, 0:border_width, :] = border_color
                    pixels[:, tile_width-border_width:tile_width, :] = border_color

            pixels = np.flipud(pixels)
            tile_img.pixels[:] = pixels.ravel()
            tile_img.update()
            UVAS_OT_SetTileIndex.try_generate_preview(tile_img)

            # Set generated image as scene.image_reference for OPERATION panel
            scene.image_reference = tile_img

            for area in context.screen.areas:
                if area.type == 'IMAGE_EDITOR':
                    area.spaces.active.image = tile_img

            self.report({'INFO'}, f"Generated single tile: {tile_width}x{tile_height}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error generating single tile: {str(e)}")
            return {'CANCELLED'}

class UVAS_OT_ImportAnimatedImageToTiles(bpy.types.Operator):
    bl_idname = "uvas.import_animated_image_to_tiles"
    bl_label = "Import Animated Image to Tiles"
    bl_description = "Import an animated GIF/APNG and convert it to tiles"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        if not scene.gif_image_reference:
            self.report({'ERROR'}, "No GIF/APNG image referenced!")
            return {'CANCELLED'}

        filepath = bpy.path.abspath(scene.gif_image_reference.filepath)
        if not filepath or not os.path.exists(filepath):
            self.report({'ERROR'}, "Invalid or missing file path for GIF/APNG!")
            return {'CANCELLED'}

        try:
            with Image.open(filepath) as pil_img:
                if not hasattr(pil_img, 'is_animated') or not pil_img.is_animated:
                    self.report({'ERROR'}, "Selected image is not an animated GIF/APNG!")
                    return {'CANCELLED'}

                frame_count = pil_img.n_frames
                width, height = pil_img.size
                split_x = int(scene.x_split)
                split_y = int(scene.y_split)
                total_tiles = split_x * split_y
                reduce_frames = scene.reduce_frames
                frame_ratio = scene.frame_reduction_ratio if reduce_frames else "1/1"
                ratio_map = {"1/2": 2, "1/4": 4, "1/8": 8, "1/1": 1}
                frame_step = ratio_map.get(frame_ratio, 1)

                if frame_count < total_tiles:
                    self.report({'WARNING'}, f"Image has fewer frames ({frame_count}) than required tiles ({total_tiles})!")
                    return {'CANCELLED'}

                tile_width = width
                tile_height = height
                full_width = width * split_x
                full_height = height * split_y

                if "UVAS_Animated_Tiles" in bpy.data.images:
                    bpy.data.images.remove(bpy.data.images["UVAS_Animated_Tiles"])
                
                full_img = bpy.data.images.new("UVAS_Animated_Tiles", width=full_width, height=full_height)
                pixels = np.zeros((full_height, full_width, 4), dtype=np.float32)

                frame_index = 0
                for y in range(split_y):
                    for x in range(split_x):
                        if frame_index >= frame_count:
                            break
                        pil_img.seek(frame_index)
                        frame = pil_img.convert('RGBA')
                        frame_array = np.array(frame, dtype=np.float32) / 255.0
                        tile_x = x * tile_width
                        tile_y = (split_y - 1 - y) * tile_height
                        pixels[tile_y:tile_y+tile_height, tile_x:tile_x+tile_width, :] = frame_array
                        frame_index += frame_step

                pixels = np.flipud(pixels)
                full_img.pixels[:] = pixels.ravel()
                full_img.update()
                UVAS_OT_SetTileIndex.try_generate_preview(full_img)

                for area in context.screen.areas:
                    if area.type == 'IMAGE_EDITOR':
                        area.spaces.active.image = full_img

                self.report({'INFO'}, f"Imported animated image to tiles: {full_width}x{full_height}")
                return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error importing animated image: {str(e)}")
            return {'CANCELLED'}

def register():
    bpy.utils.register_class(UVAS_OT_GenerateFullImage)
    bpy.utils.register_class(UVAS_OT_GenerateSingleTile)
    bpy.utils.register_class(UVAS_OT_ImportAnimatedImageToTiles)

def unregister():
    bpy.utils.unregister_class(UVAS_OT_ImportAnimatedImageToTiles)
    bpy.utils.unregister_class(UVAS_OT_GenerateSingleTile)
    bpy.utils.unregister_class(UVAS_OT_GenerateFullImage)