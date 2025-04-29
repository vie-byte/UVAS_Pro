# -*- coding: utf-8 -*-
# utils.py
import bpy
import os

def ensure_animation_data(node_tree):
    """ノードツリーにアニメーションデータを確保"""
    if not node_tree.animation_data:
        node_tree.animation_data_create()
    action = node_tree.animation_data.action
    if not action:
        action = bpy.data.actions.new(f"{node_tree.name}_action")
        node_tree.animation_data.action = action
    return action

def get_output_filepath(scene, filename, extension="png"):
    """シーンから出力ディレクトリを取得し、ファイルパスを生成"""
    output_dir = bpy.path.abspath(scene.output_dir) if scene.output_dir else bpy.path.abspath("//")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    return os.path.join(output_dir, f"{filename}.{extension}")