"""
    This file is part of Align Objects.

    Copyright (C) 2021 Project Studio Q inc.

    Animation Offset Shift is free software; you can redistribute it and/or
    modify it under the terms of the GNU General Public License
    as published by the Free Software Foundation; either version 2
    of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""

import bpy
import math
import mathutils
import functools

# -----------------------------------------------------------------------------

DEBUG_MODE = False

# -----------------------------------------------------------------------------

def _get_target_object( ):
    props = bpy.context.scene.q_align_objects
    obj = props.object
    obj_sub = props.object_subtarget

    if obj is None:
        return None

    if obj.type == "ARMATURE":
        if obj_sub in obj.pose.bones:
            return obj.pose.bones[obj_sub]

    return obj

# -----------------------------------------------------------------------------

def _update_position_all( self, context ):
    props = bpy.context.scene.q_align_objects

    props.position_flags[0] = props.position_all
    props.position_flags[1] = props.position_all
    props.position_flags[2] = props.position_all

def _update_rotation_all( self, context ):
    props = bpy.context.scene.q_align_objects

    props.rotation_flags[0] = props.rotation_all
    props.rotation_flags[1] = props.rotation_all
    props.rotation_flags[2] = props.rotation_all

def _update_scale_all( self, context ):
    props = bpy.context.scene.q_align_objects

    props.scale_flags[0] = props.scale_all
    props.scale_flags[1] = props.scale_all
    props.scale_flags[2] = props.scale_all

class QCOMMON_Props_align_objects(bpy.types.PropertyGroup):
    object: bpy.props.PointerProperty(name="Target Object", description="Target Object", type=bpy.types.Object, options= {'HIDDEN'})
    object_subtarget: bpy.props.StringProperty(name="Target Object's Sub Target", description="Target Object's Sub Target", default="", options= {'HIDDEN'} )

    position_all: bpy.props.BoolProperty(name="Position All", default=True, update=_update_position_all, options= {'HIDDEN'})
    rotation_all: bpy.props.BoolProperty(name="Rotation All", default=True, update=_update_rotation_all, options= {'HIDDEN'})
    scale_all: bpy.props.BoolProperty(name="Scale All", default=True, update=_update_scale_all, options= {'HIDDEN'})

    position_flags: bpy.props.BoolVectorProperty(name="Position (World)", subtype="XYZ", default=(True, True, True), options= {'HIDDEN'})
    rotation_flags: bpy.props.BoolVectorProperty(name="Rotation (Local)", subtype="XYZ", default=(True, True, True), options= {'HIDDEN'})
    scale_flags: bpy.props.BoolVectorProperty(name="Scale", subtype="XYZ", default=(True, True, True), options= {'HIDDEN'})

    bone_length: bpy.props.BoolProperty(name="Length", default=False, options= {'HIDDEN'})


# -----------------------------------------------------------------------------

class QCOMMON_OT_align_objects(bpy.types.Operator):
    bl_idname = "qcommon.align_objects"
    bl_label = "Align objects"
    bl_description = "Align Objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = bpy.context.scene.q_align_objects
        a_obj = props.object
        a = _get_target_object( )

        depsgraph = bpy.context.evaluated_depsgraph_get( )

        # コピー元から取得
        location = mathutils.Vector((0,0,0))
        rotation = mathutils.Matrix( )
        scale = mathutils.Vector((1, 1, 1))
        length = None

        if isinstance( a, bpy.types.PoseBone ):
            a_obj = a_obj.evaluated_get( depsgraph )

            if DEBUG_MODE:
                print( a.matrix, a.bone.matrix )

            location = a_obj.matrix_world.to_translation( ) + a.matrix.to_translation( )
            rotation = a_obj.matrix_world.to_3x3( ).normalized( ) @ a.matrix.to_3x3( ).normalized( )
            scale.x = a_obj.matrix_world.to_3x3( )[0].length + a.matrix.to_3x3( )[0].length
            scale.y = a_obj.matrix_world.to_3x3( )[1].length + a.matrix.to_3x3( )[1].length
            scale.z = a_obj.matrix_world.to_3x3( )[2].length + a.matrix.to_3x3( )[2].length
            length = a.length
        else:
            a = a.evaluated_get( depsgraph )

            location = a.matrix_world.to_translation( )
            rotation = a.matrix_world.to_3x3( ).normalized( )
            scale.x = a.matrix_world.to_3x3( )[0].length
            scale.y = a.matrix_world.to_3x3( )[1].length
            scale.z = a.matrix_world.to_3x3( )[2].length

        if DEBUG_MODE:
            print( "LOC", location )
            print( "ROT", rotation )
            print( "SCL", scale )
            print( "LEN", length )

        def _get_depth( t ):
            depth = 0

            while t.parent:
                depth += 1
                t = t.parent

            return depth
        def object_pass_index( a, b ):
            return a[0] - b[0]

        # コピー先特定
        select_list = None
        select_list_with_object = None
        b_obj = None
        if bpy.context.active_object.mode == "OBJECT":
            depth_ordered_objects = []
            for o in bpy.context.selected_objects:
                depth_ordered_objects.append( ( _get_depth( o ), o ) )

            depth_ordered_objects.sort( key=functools.cmp_to_key(object_pass_index) )
            select_list = []
            for t in depth_ordered_objects:
                select_list.append( t[1] )

        elif bpy.context.active_object.mode == "POSE":
            depth_ordered_bones = []
            for o in bpy.context.selected_pose_bones:
                depth_ordered_bones.append( ( _get_depth( o ), o ) )

            depth_ordered_bones.sort( key=functools.cmp_to_key(object_pass_index) )
            select_list = []
            select_list_with_object = []
            for t in depth_ordered_bones:
                select_list.append( t[1] )
                select_list_with_object.append( ( bpy.context.active_object, t[1] ) )

            for o in bpy.context.selected_objects:
                if o.type == "ARMATURE":
                    b_obj = o.evaluated_get( depsgraph )
                    break

        if select_list is None:
            return

        # 各々のオブジェクトを移動させる
        for b in select_list:
            if a == b:
                continue

            if isinstance( b, bpy.types.PoseBone ):
                if b_obj is not None:
                    object_world_matrix = b_obj.matrix_world
                    old_location = object_world_matrix @ b.matrix.translation
                    old_rotation = b.matrix.to_3x3( ).normalized( )
                    b.matrix = mathutils.Matrix()
                    depsgraph.update( )
                    origin_matrix = object_world_matrix.to_3x3( ) @ b.matrix.to_3x3( ).normalized( )

                    # 移動
                    new_location = location
                    for i in range( len( props.position_flags ) ):
                        if not props.position_flags[i]:
                            new_location[i] = old_location[i]
                    b.matrix.translation = ( new_location @ origin_matrix ) - ( object_world_matrix.translation )

                    # 回転
                    # 一度回転度を0にもどしてローカルを初期状態に戻す
                    if b.rotation_mode == "QUATERNION":
                        b.rotation_quaternion = mathutils.Quaternion( )
                    elif b.rotation_mode == "AXIS_ANGLE":
                        b.rotation_axis_angle = mathutils.Vector((0,0,0,0))
                    else:
                        b.rotation_euler.x = 0.0
                        b.rotation_euler.y = 0.0
                        b.rotation_euler.z = 0.0
                    depsgraph.update( )

                    # 実際に回転反映
                    new_rotation = object_world_matrix.to_3x3( ) @ old_rotation
                    for i in range( 3 ):
                        if props.rotation_flags[i]:
                            new_rotation[i] = rotation[i]
                    new_rotation = new_rotation.normalized( )
                    local_matrix = object_world_matrix.to_3x3( ) @ b.matrix.to_3x3( )
                    new_rotation = local_matrix.inverted( ) @ new_rotation
                    if b.rotation_mode == "QUATERNION":
                        b.rotation_quaternion = new_rotation.to_quaternion( )
                    elif b.rotation_mode == "AXIS_ANGLE":
                        b.rotation_axis_angle = new_rotation.to_axis_angle( )
                    else:
                        b.rotation_euler = new_rotation.to_euler( b.rotation_euler.order )

                    # 拡大
                    for i in range( len( props.scale_flags ) ):
                        if props.scale_flags[i]:
                            b.scale[i] = a.scale[i]
            else:
                new_location = location.copy( )
                if b.parent:
                    new_location = ( new_location - b.parent.matrix_world.to_translation( ) ) @ b.parent.matrix_world.to_3x3( )
                for i in range( len( props.position_flags ) ):
                    if props.position_flags[i]:
                        b.location[i] = new_location[i]
                        b.delta_location[i] = 0.0

                new_rotation = b.matrix_world.to_3x3( )
                for i in range( 3 ):
                    if props.rotation_flags[i]:
                        new_rotation[i] = rotation[i]
                new_rotation = new_rotation.normalized( )
                if b.parent:
                    new_rotation = b.parent.matrix_world.to_3x3( ).inverted( ) @ new_rotation

                if b.rotation_mode == "QUATERNION":
                    b.rotation_quaternion = new_rotation.to_quaternion( )
                    b.delta_rotation_quaternion = mathutils.Quaternion( )
                elif b.rotation_mode == "AXIS_ANGLE":
                    b.rotation_axis_angle = new_rotation.to_axis_angle( )
                else:
                    b.rotation_euler = new_rotation.to_euler( b.rotation_euler.order )
                    b.delta_rotation_euler = (0,0,0)

                for i in range( len( props.scale_flags ) ):
                    if props.scale_flags[i]:
                        b.scale[i] = a.scale[i]
                        b.delta_scale[i] = 1.0

        # 長さがオンの場合は、Editで長さをコピーする
        if props.bone_length and length:
            saved_mode = bpy.context.active_object.mode
            self.set_length_to_edit_bones( select_list_with_object, length )
            bpy.ops.object.mode_set(mode=saved_mode)

        return {'FINISHED'}

    def set_length_to_edit_bones( self, select_list_with_object, origin_length ):
        if select_list_with_object is None:
            return

        select_object_names = []
        for t in select_list_with_object:
            select_object_names.append( ( t[0].name, t[1].name ) )

        for t in select_object_names:
            obj_name = t[0]
            bone_name = t[1]
            self._switch_edit_mode( obj_name )
            bpy.data.objects[obj_name].data.edit_bones[bone_name].length = origin_length
            self._switch_object_mode( )

    def _switch_object_mode( self ):
        if bpy.context.active_object is not None:
            if bpy.context.active_object.mode != "OBJECT":
                bpy.ops.object.mode_set(mode='OBJECT')
        if bpy.context.view_layer.objects.active is not None:
            if bpy.context.view_layer.objects.active.mode != "OBJECT":
                bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')

    def _switch_edit_mode( self, obj_name ):
        self._switch_object_mode( )

        try:
            bpy.context.scene.objects[obj_name].select_set(True)
            bpy.context.view_layer.objects.active = bpy.context.scene.objects[obj_name]
            bpy.ops.object.mode_set(mode='EDIT')
        except:
            return False
        return True

class QCOMMON_OT_align_objects_object_picker(bpy.types.Operator):
    bl_idname = "qcommon.align_objects_object_picker"
    bl_label = "Align Objects Set Object"
    bl_description = "Align Objects Set Object"
    bl_options = {'REGISTER'}

    def execute( self, context ):
        if bpy.context.active_object is not None:
            props = bpy.context.scene.q_align_objects
            props.objects_object = bpy.context.active_object

        return {'FINISHED'}

class QCOMMON_OT_align_objects_bone_picker(bpy.types.Operator):
    bl_idname = "qcommon.align_objects_bone_picker"
    bl_label = "Align Objects Set Bone Name"
    bl_description = "Align Objects Set Bone Name"
    bl_options = {'REGISTER'}

    def execute( self, context ):
        if bpy.context.active_pose_bone is not None:
            props = bpy.context.scene.q_align_objects
            props.object_subtarget = bpy.context.active_pose_bone.name

        return {'FINISHED'}

# -----------------------------------------------------------------------------

def draw_ui( layout, show_execute = True ):
    props = bpy.context.scene.q_align_objects

    row = layout.row( align=True )
    row.prop(props, "object")
    row.operator( QCOMMON_OT_align_objects_object_picker.bl_idname, text="", icon='EYEDROPPER' )
    if props.object is None:
        return

    if props.object.type == "ARMATURE":
        row = layout.row( align=True )
        row.prop_search( props, "object_subtarget", props.object.pose, "bones" )
        row.operator( QCOMMON_OT_align_objects_bone_picker.bl_idname, text="", icon='EYEDROPPER' )

    row = layout.row( )
    row.prop(props, "position_flags", toggle=True)
    row.prop(props, "position_all", toggle=True, text="All")

    row = layout.row( )
    row.prop(props, "rotation_flags", toggle=True)
    row.prop(props, "rotation_all", toggle=True, text="All")

    row = layout.row( )
    row.prop(props, "scale_flags", toggle=True)
    row.prop(props, "scale_all", toggle=True, text="All")

    if props.object.type == "ARMATURE" and bpy.context.active_object is not None and bpy.context.active_object.mode == "POSE":
        row = layout.row( )
        row.prop(props, "bone_length", toggle=True)

    if show_execute:
        layout.operator( QCOMMON_OT_align_objects.bl_idname, text="Execute", icon="CHECKMARK" )

# -----------------------------------------------------------------------------

class QCOMMON_PT_align_objects_base(bpy.types.Panel):
    """
        ベースパネル
        実際の追加は下の_for_***のほうで行う
    """

    bl_label = "Align Objects"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll( self, context ):
        return (
            context.active_object
        and (
                context.active_object.mode == "OBJECT"
            or  context.active_object.mode == "POSE"
            )
        )

    def draw(self, context):
        ''' UI設定
        '''
        draw_ui( self.layout )

# -----------------------------------------------------------------------------

class QCOMMON_PT_align_objects_for_rig(QCOMMON_PT_align_objects_base):
    bl_idname = "QCOMMON_PT_align_objects"
    bl_category = "Q_RIG"

class QCOMMON_PT_align_objects_for_anim(QCOMMON_PT_align_objects_base):
    bl_idname = "QANIM_PT_align_objects"
    bl_category = "Q_ANIM"

class QCOMMON_PT_align_objects_for_model(QCOMMON_PT_align_objects_base):
    bl_idname = "QMODEL_PT_align_objects"
    bl_category = "Q_MDL"

# -----------------------------------------------------------------------------

class QCOMMON_OT_menu_align_objects(bpy.types.Operator):
    # XXX: ショートカット登録のために qcommon外にしている
    bl_idname = "view3d.menu_align_objects"
    bl_label = "Align Objects(Q)"
    bl_description = "Align Objects"

    bl_options = {'INTERNAL'}

    width = 300     # ポップアップの表示幅

    def draw(self, context):
        draw_ui( self.layout, False )

    def execute(self, context):
        return bpy.ops.qcommon.align_objects( )

    def invoke(self, context, event):
        return bpy.context.window_manager.invoke_props_dialog(self, width=self.width)

# -----------------------------------------------------------------------------

def menu_fn(self,context):
    self.layout.operator(QCOMMON_OT_menu_align_objects.bl_idname)

# -----------------------------------------------------------------------------

classes = (
    QCOMMON_Props_align_objects,

    QCOMMON_OT_align_objects,
    QCOMMON_OT_align_objects_object_picker,
    QCOMMON_OT_align_objects_bone_picker,

    QCOMMON_OT_menu_align_objects,

    QCOMMON_PT_align_objects_for_rig,
    QCOMMON_PT_align_objects_for_anim,
    QCOMMON_PT_align_objects_for_model,
)

def register():
    """
        クラス登録
    """
    for i in classes:
        bpy.utils.register_class(i)

    bpy.types.Scene.q_align_objects = bpy.props.PointerProperty( type= QCOMMON_Props_align_objects )
    bpy.types.VIEW3D_MT_object.append(menu_fn)
    bpy.types.VIEW3D_MT_pose.append(menu_fn)

def unregister():
    """
        クラス登録解除
    """
    bpy.types.VIEW3D_MT_pose.remove(menu_fn)
    bpy.types.VIEW3D_MT_object.remove(menu_fn)
    del bpy.types.Scene.q_align_objects

    for i in classes:
        bpy.utils.unregister_class(i)
