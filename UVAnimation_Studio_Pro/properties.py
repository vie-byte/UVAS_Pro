# properties.py
# -*- coding: utf-8 -*-
import bpy
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def update_image_reference(self, context):
    if self.image_reference:
        for area in context.screen.areas:
            if area.type == 'IMAGE_EDITOR':
                area.spaces.active.image = self.image_reference

def update_gif_image_reference(self, context):
    if self.gif_image_reference:
        for area in context.screen.areas:
            if area.type == 'IMAGE_EDITOR':
                area.spaces.active.image = self.gif_image_reference

def update_operation_mode(self, context):
    valid_modes = ['TILE', 'IMAGE']
    if self.operation_mode not in valid_modes:
        self.operation_mode = 'TILE'
    # Reset tile selection states
    self.swap_first_index = -1
    self.swap_second_index = -1
    self.shuffle_second_index = -1
    self.last_clicked_index = 0
    context.area.tag_redraw()

def update_tile_operation_mode(self, context):
    # Reset tile selection states
    self.swap_first_index = -1
    self.swap_second_index = -1
    self.shuffle_second_index = -1
    self.last_clicked_index = 0
    context.area.tag_redraw()

def get_resolution_items(self, context):
    base_resolutions = [8, 16, 32, 64, 128, 256, 512, 1024]
    items = []
    border_width = int(getattr(self, 'border_width', '1'))
    x_split = int(getattr(self, 'x_split', '1'))
    y_split = int(getattr(self, 'y_split', '1'))
    is_grid_outer = getattr(self, 'generate_mode', 'FILL') == 'GRID' and getattr(self, 'grid_border_type', 'INNER') == 'OUTER'
    
    for res in base_resolutions:
        if is_grid_outer:
            adjusted_x = str(res + 2 * border_width * x_split)
            adjusted_y = str(res + 2 * border_width * y_split)
        else:
            adjusted_x = str(res)
            adjusted_y = str(res)
        items.append((adjusted_x, adjusted_x, ""))
    return items

def register():
    bpy.types.Scene.resolution_x = bpy.props.EnumProperty(
        name="Resolution X",
        items=get_resolution_items,
        default=5
    )
    bpy.types.Scene.resolution_y = bpy.props.EnumProperty(
        name="Resolution Y",
        items=get_resolution_items,
        default=5
    )
    bpy.types.Scene.gif_resolution_x = bpy.props.IntProperty(
        name="GIF Resolution X",
        default=256,
        min=1
    )
    bpy.types.Scene.gif_resolution_y = bpy.props.IntProperty(
        name="GIF Resolution Y",
        default=256,
        min=1
    )
    bpy.types.Scene.x_split = bpy.props.EnumProperty(
        name="X Split",
        items=[("1", "1", ""), ("2", "2", ""), ("4", "4", ""), ("6", "6", ""), ("8", "8", "")],
        default="4"
    )
    bpy.types.Scene.y_split = bpy.props.EnumProperty(
        name="Y Split",
        items=[("1", "1", ""), ("2", "2", ""), ("4", "4", ""), ("6", "6", ""), ("8", "8", "")],
        default="4"
    )
    bpy.types.Scene.image_reference = bpy.props.PointerProperty(
        name="Image Reference",
        type=bpy.types.Image,
        update=update_image_reference
    )
    bpy.types.Scene.tile_reference = bpy.props.PointerProperty(
        name="Tile Reference",
        type=bpy.types.Image
    )
    bpy.types.Scene.text_preview = bpy.props.PointerProperty(
        name="Text Preview",
        type=bpy.types.Image,
        description="Temporary preview image for text insertion"
    )
    bpy.types.Scene.text_preview_index = bpy.props.IntProperty(
        name="Text Preview Index",
        default=-1,
        description="Index of the tile for the current text preview"
    )
    bpy.types.Scene.last_clicked_index = bpy.props.IntProperty(
        name="Last Clicked Index",
        default=0
    )
    bpy.types.Scene.operation_mode = bpy.props.EnumProperty(
        name="Operation Mode",
        items=[
            ("TILE", "Tile", "Tile-based operations"),
            ("IMAGE", "Image", "Image-based operations")
        ],
        default="TILE",
        update=update_operation_mode
    )
    bpy.types.Scene.tile_operation_mode = bpy.props.EnumProperty(
        name="Tile Operation Mode",
        items=[
            ("ROTATE_AND_FLIP", "Rotate and Flip", "Rotate or flip the selected tile"),
            ("MIRROR", "Mirror", "Mirror the selected tile symmetrically"),
            ("EXTRACT", "Extract", "Extract a tile from the referenced image"),
            ("PATCH", "Patch", "Patch the tile onto the base image"),
            ("SWAP", "Swap", "Swap two tiles in the referenced image"),
            ("SHUFFLE", "Shuffle", "Randomly shuffle tiles in a rectangular range"),
            ("INSERT_TEXT", "Insert Text", "Insert text into the selected tile")
        ],
        default="EXTRACT",
        update=update_tile_operation_mode
    )
    bpy.types.Scene.image_operation_mode = bpy.props.EnumProperty(
        name="Image Operation Mode",
        items=[
            ("ROTATE_AND_FLIP", "Rotate and Flip", "Rotate or flip the entire image"),
            ("MIRROR", "Mirror", "Mirror the entire image symmetrically"),
            ("NEGATE", "Negate", "Invert the colors of the image"),
            ("GRAYSCALE", "Grayscale", "Convert the image to grayscale")
        ],
        default="NEGATE"
    )
    bpy.types.Scene.rotate_flip_mode = bpy.props.EnumProperty(
        name="Rotate or Flip Mode",
        items=[
            ("ROTATE", "Rotate", "Rotate the image or tile"),
            ("FLIP", "Flip", "Flip the image or tile")
        ],
        default="ROTATE"
    )
    bpy.types.Scene.flip_direction = bpy.props.EnumProperty(
        name="Flip Direction",
        items=[
            ("-X_TO_X", "-X to X (Left to Right)", "Flip horizontally, left side to right"),
            ("X_TO_-X", "X to -X (Right to Left)", "Flip horizontally, right side to left"),
            ("Y_TO_-Y", "Y to -Y (Up to Down)", "Flip vertically, top to bottom"),
            ("-Y_TO_Y", "-Y to Y (Down to Up)", "Flip vertically, bottom to top")
        ],
        default="-X_TO_X"
    )
    bpy.types.Scene.mirror_direction = bpy.props.EnumProperty(
        name="Mirror Direction",
        items=[
            ("LEFT_TO_RIGHT", "Left to Right", "Mirror left half to right"),
            ("RIGHT_TO_LEFT", "Right to Left", "Mirror right half to left"),
            ("TOP_TO_BOTTOM", "Top to Bottom", "Mirror top half to bottom"),
            ("BOTTOM_TO_TOP", "Bottom to Top", "Mirror bottom half to top")
        ],
        default="LEFT_TO_RIGHT"
    )
    bpy.types.Scene.output_dir = bpy.props.StringProperty(
        name="Output Directory",
        subtype='DIR_PATH',
        default="//"
    )
    bpy.types.Scene.swap_first_index = bpy.props.IntProperty(
        name="Swap First Index",
        default=-1
    )
    bpy.types.Scene.swap_second_index = bpy.props.IntProperty(
        name="Swap Second Index",
        default=-1,
        description="Stores the second selected tile index for swapping"
    )
    bpy.types.Scene.shuffle_second_index = bpy.props.IntProperty(
        name="Shuffle Second Index",
        default=-1
    )
    bpy.types.Scene.rotate_direction = bpy.props.EnumProperty(
        name="Rotate Direction",
        items=[
            ("90", "90 Degrees", "Rotate 90 degrees counterclockwise"),
            ("-90", "-90 Degrees", "Rotate 90 degrees clockwise"),
            ("180", "180 Degrees", "Rotate 180 degrees")
        ],
        default="90"
    )
    bpy.types.Scene.gif_image_reference = bpy.props.PointerProperty(
        name="GIF/APNG Image Reference",
        type=bpy.types.Image,
        update=update_gif_image_reference
    )
    bpy.types.Scene.reduce_frames = bpy.props.BoolProperty(
        name="Reduce Frames",
        default=False
    )
    bpy.types.Scene.frame_reduction_ratio = bpy.props.EnumProperty(
        name="Frame Reduction Ratio",
        items=[
            ("1/2", "1/2", "Keep every 2nd frame"),
            ("1/4", "1/4", "Keep every 4th frame"),
            ("1/8", "1/8", "Keep every 8th frame")
        ],
        default="1/2"
    )
    bpy.types.Scene.generate_mode = bpy.props.EnumProperty(
        name="Generate Mode",
        items=[
            ("FILL", "Fill", "Fill tiles with solid color"),
            ("GRID", "Grid", "Draw only the borders of tiles")
        ],
        default="FILL"
    )
    bpy.types.Scene.grid_border_type = bpy.props.EnumProperty(
        name="Border Type",
        items=[
            ("OUTER", "Outer", "Draw borders outside the tile"),
            ("INNER", "Inner", "Draw borders inside the tile")
        ],
        default="INNER"
    )
    bpy.types.Scene.border_width = bpy.props.EnumProperty(
        name="Border Width",
        items=[(str(i), f"{i} px", "") for i in [1, 2, 4, 6, 8]],
        default="1"
    )
    bpy.types.Scene.text_font = bpy.props.StringProperty(
        name="Text Font",
        subtype='FILE_PATH',
        default=""
    )
    bpy.types.Scene.text_font_size = bpy.props.IntProperty(
        name="Text Font Size",
        default=12,
        min=8,
        max=72
    )
    bpy.types.Scene.text_offset_x = bpy.props.IntProperty(
        name="Text Offset X",
        default=0,
        min=-1000,
        max=1000,
        description="Text offset in pixels (X-axis)"
    )
    bpy.types.Scene.text_offset_y = bpy.props.IntProperty(
        name="Text Offset Y",
        default=0,
        min=-1000,
        max=1000,
        description="Text offset in pixels (Y-axis, negative moves downward)"
    )
    bpy.types.Scene.text_content = bpy.props.StringProperty(
        name="Text Content",
        default=""
    )

def unregister():
    del bpy.types.Scene.resolution_x
    del bpy.types.Scene.resolution_y
    del bpy.types.Scene.gif_resolution_x
    del bpy.types.Scene.gif_resolution_y
    del bpy.types.Scene.x_split
    del bpy.types.Scene.y_split
    del bpy.types.Scene.image_reference
    del bpy.types.Scene.tile_reference
    del bpy.types.Scene.text_preview
    del bpy.types.Scene.text_preview_index
    del bpy.types.Scene.last_clicked_index
    del bpy.types.Scene.operation_mode
    del bpy.types.Scene.tile_operation_mode
    del bpy.types.Scene.image_operation_mode
    del bpy.types.Scene.rotate_flip_mode
    del bpy.types.Scene.flip_direction
    del bpy.types.Scene.mirror_direction
    del bpy.types.Scene.output_dir
    del bpy.types.Scene.swap_first_index
    del bpy.types.Scene.swap_second_index
    del bpy.types.Scene.shuffle_second_index
    del bpy.types.Scene.rotate_direction
    del bpy.types.Scene.gif_image_reference
    del bpy.types.Scene.reduce_frames
    del bpy.types.Scene.frame_reduction_ratio
    del bpy.types.Scene.generate_mode
    del bpy.types.Scene.grid_border_type
    del bpy.types.Scene.border_width
    del bpy.types.Scene.text_font
    del bpy.types.Scene.text_font_size
    del bpy.types.Scene.text_offset_x
    del bpy.types.Scene.text_offset_y
    del bpy.types.Scene.text_content