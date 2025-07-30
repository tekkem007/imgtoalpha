bl_info = {
    "name": "Batch Convert Image to Brush Asset Library",
    "blender": (4, 0, 0),
    "category": "Paint",
    "author": "Voyager_Vishnu",
    "description": "Batch converts all images to alphas."
}

import bpy
from bpy.types import Operator, Panel
from bpy.props import StringProperty
import os
import re

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".psd", ".exr", ".hdr", ".tga", ".gif", ".dds", ".jp2", ".webp")

def make_unique_name(base_name, existing_names):
    name = base_name
    i = 1
    while name in existing_names:
        name = f"{base_name}_{i}"
        i += 1
    return name

def sanitize_filename(name):
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', name)

class BATCH_OT_image_to_blend_library(Operator):
    bl_idname = "paint.image_to_blend_library"
    bl_label = "Batch Images to Single Brush Asset Library"
    bl_description = "Converts all images in a folder into a single .blend file as brush assets"
    bl_options = {'REGISTER', 'INTERNAL'}

    image_folder: StringProperty(name="Image Folder", subtype='DIR_PATH')
    output_blend: StringProperty(
        name="Output Blend File",
        subtype='FILE_PATH',
        description="Path for the .blend asset library to create"
    )

    # Modal properties
    _timer = None
    _step = 0
    _image_files = []
    _num_files = 0
    _created_brushes = []
    _existing_brush_names = set()
    _done = False
    _failures = []

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        image_folder = self.image_folder
        output_blend = self.output_blend

        if not os.path.isdir(image_folder):
            self.report({'ERROR'}, "Invalid image folder path.")
            return {'CANCELLED'}

        output_dir = os.path.dirname(output_blend)
        if not os.path.isdir(output_dir):
            self.report({'ERROR'}, "Invalid output blend folder.")
            return {'CANCELLED'}

        # Accept all supported image file formats
        self._image_files = [f for f in os.listdir(image_folder)
                             if f.lower().endswith(IMAGE_EXTENSIONS)]
        if not self._image_files:
            self.report({'ERROR'}, "No image files found in the selected folder.")
            return {'CANCELLED'}

        self._num_files = len(self._image_files)
        self._step = 0
        self._created_brushes = []
        self._existing_brush_names = {b.name for b in bpy.data.brushes}
        self._done = False
        self._failures = []

        wm = context.window_manager
        wm.progress_begin(0, self._num_files)
        self._timer = wm.event_timer_add(0.05, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        wm = context.window_manager

        def finish(result_status):
            if self._timer:
                wm.event_timer_remove(self._timer)
            wm.progress_end()
            self._done = True
            return {result_status}

        if event.type == 'TIMER':
            if self._step < self._num_files:
                img_file = self._image_files[self._step]
                full_path = os.path.join(self.image_folder, img_file)
                try:
                    image = bpy.data.images.load(full_path)
                    image.name = os.path.splitext(img_file)[0]
                    tex = bpy.data.textures.new(name=f"{image.name}_Texture", type='IMAGE')
                    tex.image = image
                    brush_name = make_unique_name(f"{image.name}_Brush", self._existing_brush_names)
                    brush = bpy.data.brushes.new(name=brush_name, mode='TEXTURE_PAINT')
                    brush.texture = tex
                    brush.texture_slot.map_mode = 'VIEW_PLANE'
                    brush.curve_preset = 'CONSTANT'
                    brush.asset_mark()
                    image.asset_mark()
                    brush.asset_data.author = "Batch Image Import"
                    image.asset_data.author = "Batch Image Import"
                    self._created_brushes.append(brush)
                    self._existing_brush_names.add(brush.name)
                except Exception as e:
                    self._failures.append(img_file)
                    self.report({'WARNING'}, f"Failed to load {img_file}: {e}")
                finally:
                    wm.progress_update(self._step + 1)
                    self._step += 1
                    if context.area:
                        context.area.tag_redraw()
            else:
                try:
                    # Sanitize .blend path if needed
                    blend_path = self.output_blend
                    if not blend_path.lower().endswith('.blend'):
                        blend_path += '.blend'
                    bpy.ops.wm.save_mainfile(filepath=blend_path)
                    msg = f"Saved {len(self._created_brushes)} brush assets in: {blend_path}\nOpen in Asset Browser to set previews."
                    if self._failures:
                        msg += f"\nSome files failed: {', '.join(self._failures)}"
                    self.report({'INFO'}, msg)
                except Exception as e:
                    self.report({'ERROR'}, f"Failed to save blend: {e}")
                return finish('FINISHED')
        return {'PASS_THROUGH'}

class BATCH_PT_image_to_blend_library_panel(Panel):
    bl_idname = "VIEW3D_PT_image_to_blend_library"
    bl_label = "Batch Images to Brush Asset Library"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Brush'

    def draw(self, context):
        layout = self.layout
        layout.operator(BATCH_OT_image_to_blend_library.bl_idname, text="Batch Images to Asset Library", icon='BRUSH_DATA')
        layout.label(text="All brushes go into a single .blend file.")
        layout.label(text="Open .blend and right-click asset > Edit Preview.")

def register():
    bpy.utils.register_class(BATCH_OT_image_to_blend_library)
    bpy.utils.register_class(BATCH_PT_image_to_blend_library_panel)

def unregister():
    bpy.utils.unregister_class(BATCH_OT_image_to_blend_library)
    bpy.utils.unregister_class(BATCH_PT_image_to_blend_library_panel)

if __name__ == "__main__":
    register()
