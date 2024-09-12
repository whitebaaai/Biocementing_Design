##
##

import bpy
import bmesh
import mathutils

import numpy as np


class BIOCEMENT_PT_MainPanel(bpy.types.Panel):
    bl_label = "BioCement"
    bl_idname = "BIOCEMENT_PT_MainPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "BioCement"

    def draw(self, context):
        layout = self.layout

        # # Dropdown menu 1
        # layout.label(text="Dropdown Menu 1:")
        # layout.prop(context.scene, "my_dropdown_menu_1", text="")

        # # Dropdown menu 2
        # layout.label(text="Dropdown Menu 2:")
        # layout.prop(context.scene, "my_dropdown_menu_2", text="")
        
        # # TODO: Move this to a CSV or a database that stores good combinations
        # # Display an icon and text depending on which recipe is selected
        # if context.scene.my_dropdown_menu_1 == "option1" and context.scene.my_dropdown_menu_2 == "optionA":
        #     layout.label(text="Recipe: Good", icon='CHECKMARK')
        # else:
        #     layout.label(text="Recipe: Unknown", icon='QUESTION')

        # Button to copy selected faces
        layout.operator("biocement.validate_geometry", text="Validate Geometry")
        # Display an icon and text depending on if the geometry is valid
        if context.scene.mesh_thickness:
            layout.label(text="Mesh Thickness: Good", icon='CHECKMARK')
        else:
            layout.label(text="Mesh Thickness: Bad", icon='ERROR')
        if context.scene.mesh_manifold:
            layout.label(text="Mesh Manifold: Good", icon='CHECKMARK')
        else:
            layout.label(text="Mesh Manifold: Bad", icon='ERROR')
        if context.scene.edge_sharpness:
            layout.label(text="Edge Sharpness: Good", icon='CHECKMARK')
        else:
            layout.label(text="Edge Sharpness: Bad", icon='ERROR')
        if context.scene.vertex_sharpness:
            layout.label(text="Vertex Sharpness: Good", icon='CHECKMARK')
        else:
            layout.label(text="Vertex Sharpness: Bad", icon='ERROR')

        layout.operator("biocement.create_conf_outer_mold", text="Create Conformal Outer Mold")
        layout.operator("biocement.create_cast_outer_mold", text="Create Castable Outer Mold")
        layout.operator("biocement.generate_recipe", text="Generate Recipe")
        # TODO: Add ability to create two piece molds

        layout.label(text=f"3D Artifact Volume: {context.scene.artifact_volume:.3f} L")
        layout.label(text=f"Aggregate Size: 0.4 - 2 mm")
        layout.label(text=f"Aggregate Weight: {context.scene.sand:.3f} kg")
        layout.label(text=f"Culture Media Volume: {context.scene.culture_media:.3f} L")
        layout.label(text=f"Biocementing Solution Volume: {context.scene.cementing_solution:.3f} L")
        layout.label(text=f"# of Treatments: {context.scene.treatment_count}")

class BIOCEMENT_OT_validate_geometry(bpy.types.Operator):
    "Validate that the geometry is suitable for casting in BioCement. Checks minimum mesh thickness and edge sharpness."
    bl_idname = "biocement.validate_geometry"
    bl_label = "Validate Geometry"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'WARNING'}, "No active mesh object")
            return {'CANCELLED'}
        
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.transform_apply(scale=True)

        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)

        if not validate_mesh_thickness(obj, bm):
            self.report({'WARNING'}, "Mesh does not meet the minimum thickness requirement")
            context.scene.mesh_thickness = False
            return {'CANCELLED'}
        else:
            context.scene.mesh_thickness = True

        try:
            if not validate_edge_sharpness(bm):
                self.report({'WARNING'}, "Mesh has sharp edges")
                context.scene.edge_sharpness = False
                return {'CANCELLED'}
            else:
                context.scene.edge_sharpness = True
            context.scene.mesh_manifold = True
        except ValueError:  
            self.report({'WARNING'}, "Mesh is non-manifold")
            context.scene.mesh_manifold = False
            return {'CANCELLED'}

        if not validate_vertex_sharpness(bm):
            self.report({'WARNING'}, "Mesh has sharp vertices")
            context.scene.vertex_sharpness = False
            return {'CANCELLED'}
        else:
            context.scene.vertex_sharpness = True

        return {'FINISHED'}
    
# TODO: Update this default with a real number
def validate_mesh_thickness(obj, bm, min_thickness=0.01):
    # Check if the mesh has a minimum thickness
    for face in bm.faces:
        center = face.calc_center_median()
        normal = -face.normal.normalized()

        # Slightly offset the ray origin along the normal to avoid precision issues
        offset_center = center + normal * 0.001
        
        # Add an arrow to the scene to visualize the normal
        # bpy.ops.object.empty_add(type='SINGLE_ARROW', location=center, rotation=normal.to_track_quat('Z', 'Y').to_euler())

        # Cast a ray from the center point along the face normal
        result, location, normal, index = obj.ray_cast(offset_center, normal)

        # If the ray doesn't hit anything, the distance is None
        if (location - offset_center).length < min_thickness:
            return False
        
    return True

# TODO: Update this default with a real number
def validate_edge_sharpness(bm, min_angle=np.pi/6):
    # Check if the mesh has sharp edges
    for edge in bm.edges:
        # Get the angle between the normals of the two faces adjacent to the edge
        try:
            angle = edge.calc_face_angle()
        except ValueError:
            bpy.ops.object.empty_add(type='PLAIN_AXES', location=(edge.verts[0].co + edge.verts[1].co)/2)
            raise ValueError("Non-manifold mesh")
        if angle > np.pi - min_angle:
            return False
    return True

# TODO: Update this default with a real number
def validate_vertex_sharpness(bm, min_angle=np.pi/6):
    # Check for sharp vertices using face normals
    for vert in bm.verts:
        linked_faces = vert.link_faces
        for i, face1 in enumerate(linked_faces):
            for face2 in linked_faces[i+1:]:
                normal1 = face1.normal
                normal2 = face2.normal
                angle = normal1.angle(normal2)
                if angle > np.pi - min_angle:
                    bpy.ops.object.empty_add(type='PLAIN_AXES', location=vert.co)
                    return False    
    return True

class BIOCEMENT_OT_create_conf_outer_mold(bpy.types.Operator):
    """Create Conformal Outer Mold. Select all faces except the faces that will be exposed to air."""
    bl_idname = "biocement.create_conf_outer_mold"
    bl_label = "Create Conformal Outer Mold"
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

        # Create a cylinder at the lowest point of the mesh for the drain
        # This needs to be done before the mold is created so that the boolean modifier works correctly
        drain_point = get_drain_point(bm)
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.05,
            depth=0.26,
            location=(drain_point.x, drain_point.y, drain_point.z - 0.025)
        )
        context.active_object.name = "Drain"
        
        # Create a new mesh for the copy
        new_mesh = bpy.data.meshes.new(name="ConfOuterMold")
        new_obj = bpy.data.objects.new("ConfOuterMold", new_mesh)
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

        # Boolean difference to create the drain
        bpy.ops.object.modifier_add(type='BOOLEAN')
        bpy.context.object.modifiers["Boolean"].operation = 'DIFFERENCE'
        bpy.context.object.modifiers["Boolean"].object = bpy.data.objects["Drain"]
        bpy.ops.object.modifier_apply(modifier="Boolean")

        # Delete the cylinder
        bpy.data.objects.remove(bpy.data.objects["Drain"])

        bpy.ops.object.mode_set(mode='EDIT')
        return {'FINISHED'}
    
class BIOCEMENT_OT_create_cast_outer_mold(bpy.types.Operator):
    """Create Castable Outer Mold. Select all faces that will be exposed to air."""
    bl_idname = "biocement.create_cast_outer_mold"
    bl_label = "Create Castable Outer Mold"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'WARNING'}, "No active mesh object")
            return {'CANCELLED'}
        
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.transform_apply(location=True, scale=True)

        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)

        # # Average normals of un-selected faces
        # avg_normal = mathutils.Vector((0, 0, 0))
        # for f in bm.faces:
        #     if not f.select:
        #         avg_normal += f.normal

        # # List of perpendicular distances of vertexes from the average normal
        # bm.verts.ensure_lookup_table()
        # vertices = np.array([v.co for v in bm.verts])
        # distances = np.linalg.norm(np.cross(vertices, avg_normal), axis=1) / np.linalg.norm(avg_normal)
        # max_idx = np.argmax(distances)

        # # Use this to establish basis
        # n_avg_normal = avg_normal.normalized()
        # max_vertex_co = bm.verts[max_idx].co
        # basis_vec1 = -(max_vertex_co.dot(n_avg_normal) * n_avg_normal - max_vertex_co)
        # basis_vec2 = basis_vec1.cross(avg_normal)

        # # Calculate bounds using the basis
        # x_comp = [v.dot(basis_vec1.normalized()) for v in vertices]
        # y_comp = [v.dot(basis_vec2.normalized()) for v in vertices]
        # x_min, x_max = np.min(x_comp), np.max(x_comp)
        # y_min, y_max = np.min(y_comp), np.max(y_comp)

        # print(f"X: {x_min} to {x_max}")
        # print(f"Y: {y_min} to {y_max}")

        # # Plot the basis using the empty plain axes object centered at the origin
        # basis = bpy.data.objects.new("Basis", None)
        # basis.rotation_euler = basis_vec1.to_track_quat('X', 'Z').to_euler()
        # context.collection.objects.link(basis)

        # NVM the above, it's more complicated than we need, just use an axis-aligned bounding box

        # Get boundary of un-selected faces and calculate average Z
        selected_faces = [f for f in bm.faces if not f.select]
        if len(selected_faces) > 1:
            boundary_face = bmesh.utils.face_join(selected_faces)
        else:
            boundary_face = selected_faces[0]
        bound_z_avg = sum([v.co.z for v in boundary_face.verts]) / len(boundary_face.verts)

        x_min, x_max = obj.bound_box[0][0], obj.bound_box[6][0]
        y_min, y_max = obj.bound_box[0][1], obj.bound_box[6][1]
        z_min, z_max = obj.bound_box[0][2], bound_z_avg
        
        # Create a cylinder at the lowest point of the mesh for the drain
        # This needs to be done before the cube is created so that the boolean modifier works correctly
        drain_point = get_drain_point(bm)
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.05,
            depth=0.26,
            location=(drain_point.x, drain_point.y, drain_point.z - 0.025)
        )
        context.active_object.name = "Drain"

        # Create a cube that bounds the object
        bpy.ops.mesh.primitive_cube_add(
            size=1, 
            location=((x_min + x_max) / 2, (y_min + y_max) / 2, (z_min + z_max - 0.15) / 2), 
            scale=(x_max - x_min + 0.3, y_max - y_min + 0.3, z_max - z_min + 0.14)
        )

        # Boolean difference to create the castable outer mold
        bpy.ops.object.modifier_add(type='BOOLEAN')
        bpy.context.object.modifiers["Boolean"].operation = 'DIFFERENCE'
        bpy.context.object.modifiers["Boolean"].object = obj
        bpy.ops.object.modifier_apply(modifier="Boolean")

        # Boolean difference to create the drain
        bpy.ops.object.modifier_add(type='BOOLEAN')
        bpy.context.object.modifiers["Boolean"].operation = 'DIFFERENCE'
        bpy.context.object.modifiers["Boolean"].object = bpy.data.objects["Drain"]
        bpy.ops.object.modifier_apply(modifier="Boolean")

        # Delete the cylinder
        bpy.data.objects.remove(bpy.data.objects["Drain"])

        bpy.ops.object.mode_set(mode='EDIT')
        return {'FINISHED'}
    
def get_drain_point(bm):
    # Get the lowest point of the mesh
    min_z = float('inf')
    drain_point = None
    for v in bm.verts:
        if v.co.z < min_z:
            min_z = v.co.z
            drain_point = v.co
    return drain_point

class BIOCEMENT_OT_generate_recipe(bpy.types.Operator): 
    """Generate Recipe. Recipe is based on the volume of the mold."""
    bl_idname = "biocement.generate_recipe"
    bl_label = "Generate Recipe"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'WARNING'}, "No active mesh object")
            return {'CANCELLED'}
        
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.transform_apply(scale=True)

        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)

        volume = calc_volume(bm)
        # self.report({'INFO'}, f"Volume: {volume:.2f} m^3")

        # Treatement count is a function of height
        # treatment_count = int(np.ceil(obj.dimensions.z / 2))
        treatment_count = 2

        context.scene.artifact_volume = volume                              # Map m^3 to L (assuming people won't change the default unit)
        context.scene.treatment_count = treatment_count
        context.scene.sand = volume * 1.6                                   # 1.6 kg/liter
        context.scene.culture_media = volume * 0.2                          # 20% of the volume
        context.scene.cementing_solution = volume * 0.2                     # 20% of the volume

        return {'FINISHED'}
    
def calc_volume(bm):
    # Triangulate the mesh to ensure that the volume is calculated correctly
    bmesh.ops.triangulate(bm, faces=bm.faces)
    volume = 0
    for face in bm.faces:
        # Get the vector for each vertex of the face
        verts = [v.co for v in face.verts]
        # Calculate the volume of the tetrahedron formed by the face and the origin
        volume += np.dot(verts[0], np.cross(verts[1], verts[2]))
    return np.abs(volume / 6)

def register():
    # # Populate the dropdown menus
    # bpy.types.Scene.my_dropdown_menu_1 = bpy.props.EnumProperty(
    #     items=[
    #         ("option1", "Option 1", ""),
    #         ("option2", "Option 2", ""),
    #         ("option3", "Option 3", "")
    #     ]
    # )
    # bpy.types.Scene.my_dropdown_menu_2 = bpy.props.EnumProperty(
    #     items=[
    #         ("optionA", "Option A", ""),
    #         ("optionB", "Option B", ""),
    #         ("optionC", "Option C", "")
    #     ]
    # )

    # Register the operators and panels
    bpy.types.Scene.treatment_count = bpy.props.IntProperty(
        name="Treatment Count",
        description="Number of treatments needed",
        default=0
    )

    bpy.types.Scene.artifact_volume = bpy.props.FloatProperty(
        name="Artifact Volume",
        description="Volume of the Artifact in m^3",
        default=0.0
    )

    bpy.types.Scene.sand = bpy.props.FloatProperty(
        name="Sand Weight",
        description="Amount of sand needed in kg",
        default=0.0
    )

    bpy.types.Scene.culture_media = bpy.props.FloatProperty(
        name="Culture Media Volume",
        description="Volume of culture media in ml",
        default=0.0
    )

    bpy.types.Scene.cementing_solution = bpy.props.FloatProperty(
        name="Biocementing Solution Volume",
        description="Volume of biocementing solution in g",
        default=0.0
    )

    bpy.types.Scene.mesh_thickness = bpy.props.BoolProperty(
        name="Mesh Thickness",
        description="Whether the geometry meets the thickness requirement",
        default=False
    )

    bpy.types.Scene.edge_sharpness = bpy.props.BoolProperty(
        name="Edge Sharpness",
        description="Whether the geometry has edges that are too sharp",
        default=False
    )

    bpy.types.Scene.mesh_manifold = bpy.props.BoolProperty(
        name="Manifold Mesh",
        description="Whether the geometry is manifold",
        default=False
    )

    bpy.types.Scene.vertex_sharpness = bpy.props.BoolProperty(
        name="Vertex Sharpness",
        description="Whether the geometry has vertices that are too sharp",
        default=False
    )

    bpy.utils.register_class(BIOCEMENT_OT_validate_geometry)
    bpy.utils.register_class(BIOCEMENT_OT_create_conf_outer_mold)
    bpy.utils.register_class(BIOCEMENT_OT_create_cast_outer_mold)
    bpy.utils.register_class(BIOCEMENT_OT_generate_recipe)
    bpy.utils.register_class(BIOCEMENT_PT_MainPanel)

def unregister():
    bpy.utils.unregister_class(BIOCEMENT_OT_validate_geometry)
    bpy.utils.unregister_class(BIOCEMENT_OT_create_conf_outer_mold)
    bpy.utils.unregister_class(BIOCEMENT_OT_create_cast_outer_mold)
    bpy.utils.unregister_class(BIOCEMENT_OT_generate_recipe)
    bpy.utils.unregister_class(BIOCEMENT_PT_MainPanel)
    del bpy.types.Scene.my_dropdown_menu_1
    del bpy.types.Scene.my_dropdown_menu_2

if __name__ == "__main__":
    register()