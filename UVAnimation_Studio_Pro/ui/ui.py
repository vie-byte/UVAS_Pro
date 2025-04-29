# ui.py
# -*- coding: utf-8 -*-
import bpy

class UVAS_MT_CustomMenu(bpy.types.Menu):
    bl_label = "Custom"
    bl_idname = "UVAS_MT_CustomMenu"

    def draw(self, context):
        layout = self.layout
        layout.operator("node.add_node", text="UV Animation Coordinates").type = "UVAS_UVAnimationCoordinatesNode"

def draw_replace_operator(self, context):
    node = context.active_node
    if node and node.type == 'TEX_IMAGE':
        self.layout.operator("uvas.replace_with_uv_anim", icon='NODE_TEXTURE')

def menu_func(self, context):
    self.layout.menu(UVAS_MT_CustomMenu.bl_idname)

def register():
    bpy.utils.register_class(UVAS_MT_CustomMenu)
    bpy.types.NODE_MT_add.append(menu_func)
    bpy.types.NODE_MT_context_menu.append(draw_replace_operator)

def unregister():
    bpy.types.NODE_MT_context_menu.remove(draw_replace_operator)
    bpy.types.NODE_MT_add.remove(menu_func)
    bpy.utils.unregister_class(UVAS_MT_CustomMenu)