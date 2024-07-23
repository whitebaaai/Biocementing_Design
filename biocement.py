##
##

import bpy
import bmesh

class BIOCEMENT_PT_MainPanel(bpy.types.Panel):
    bl_label = "BioCement"
    bl_idname = "biocement.main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "BioCement"

    def draw(self, context):
        layout = self.layout

        # Dropdown menu 1
        layout.label(text="Dropdown Menu 1:")
        layout.prop(context.scene, "my_dropdown_menu_1", text="")

        # Dropdown menu 2
        layout.label(text="Dropdown Menu 2:")
        layout.prop(context.scene, "my_dropdown_menu_2", text="")
        
        # TODO: Move this to a CSV or a database that stores good combinations
        # Display an icon next to the dropdown depending on which recipe is selected
        if context.scene.my_dropdown_menu_1 == "option1" and context.scene.my_dropdown_menu_2 == "optionA":
            layout.label(text="Manufacturability: Good", icon='CHECKMARK')
        else:
            layout.label(text="Manufacturability: Unknown", icon='QUESTION')

        # Button to copy selected faces
        layout.operator("biocement.create_outer_mold", text="Create Outer Mold")

        # TODO: Add ability to create two piece molds

        # TODO: Actually do this based on a volume to surface area ratio calculation
        layout.label(text="Expected Curing Time: 24 hours")

class BIOCEMENT_OT_create_outer_mold(bpy.types.Operator):
    """Create Outer Mold. Select all faces except the faces that will be exposed to air."""
    bl_idname = "biocement.create_outer_mold"
    bl_label = "Create Outer Mold"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'WARNING'}, "No active mesh object")
            return {'CANCELLED'}
        
        bpy.ops.object.mode_set(mode='OBJECT')
        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)
        
        # Create a new mesh for the copy
        new_mesh = bpy.data.meshes.new(name="OuterMold")
        new_obj = bpy.data.objects.new("OuterMold", new_mesh)
        context.collection.objects.link(new_obj)
        
        # Prepare a new BMesh for copied faces, to avoid altering the original mesh
        new_bm = bmesh.new()

        # Copy selected faces
        for face in bm.faces:
            if face.select:
                # Create a new face in new_bm with the same vertices as the selected face
                new_face_verts = [new_bm.verts.new(v.co) for v in face.verts]
                new_bm.faces.new(new_face_verts)
        
        # Write the new bmesh to the new mesh data block
        new_bm.to_mesh(new_mesh)
        new_bm.free()
        bm.free()

        # Select the new object
        context.view_layer.objects.active = new_obj
        new_obj.select_set(True)

        # Create a Weld modifier on the new object
        weld_modifier = new_obj.modifiers.new(name="Weld", type='WELD')
        weld_modifier.merge_threshold = 0.001  # Adjust the threshold as needed

        # Create a Solidify modifier on the new object
        solidify_modifier = new_obj.modifiers.new(name="Solidify", type='SOLIDIFY')
        solidify_modifier.thickness = -0.1  # Adjust the thickness as needed

        # Apply the modifier to make the change permanent
        bpy.ops.object.modifier_apply(modifier=weld_modifier.name)
        bpy.ops.object.modifier_apply(modifier=solidify_modifier.name)

        bpy.ops.object.mode_set(mode='EDIT')
        return {'FINISHED'}

def register():
    # TODO: Add real options to the dropdown menus
    # TODO: Add a dropdown for each parameter
    # TODO: Change the names of the dropdowns to be more descriptive
    # Populate the dropdown menus
    bpy.types.Scene.my_dropdown_menu_1 = bpy.props.EnumProperty(
        items=[
            ("option1", "Option 1", ""),
            ("option2", "Option 2", ""),
            ("option3", "Option 3", "")
        ]
    )
    bpy.types.Scene.my_dropdown_menu_2 = bpy.props.EnumProperty(
        items=[
            ("optionA", "Option A", ""),
            ("optionB", "Option B", ""),
            ("optionC", "Option C", "")
        ]
    )

    # Register the operators and panels
    bpy.utils.register_class(BIOCEMENT_OT_create_outer_mold)
    bpy.utils.register_class(BIOCEMENT_PT_MainPanel)

def unregister():
    bpy.utils.register_class(BIOCEMENT_OT_create_outer_mold)
    bpy.utils.unregister_class(BIOCEMENT_PT_MainPanel)
    del bpy.types.Scene.my_dropdown_menu_1
    del bpy.types.Scene.my_dropdown_menu_2

if __name__ == "__main__":
    register()