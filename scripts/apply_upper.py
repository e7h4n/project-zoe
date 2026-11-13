from pathlib import Path
import bpy,bmesh,math,json
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
O=ROOT/'cad'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'model/project-zoe.blend'),use_scripts=False)
S=bpy.context.scene;cam=S.camera;shell=bpy.data.objects['BrewDuo_C_shell_5mm'];silver=shell.data.materials[0]
for m in list(shell.modifiers):shell.modifiers.remove(m)
def boolean(tool,op):
 bpy.context.view_layer.objects.active=shell
 m=shell.modifiers.new('Rebuild_tangent_upper_structure','BOOLEAN');m.operation=op;m.solver='MANIFOLD';m.object=tool
 bpy.ops.object.modifier_apply(modifier=m.name);bpy.data.objects.remove(tool,do_unlink=True)
bpy.ops.mesh.primitive_cube_add(size=1,location=(0,50,497.5))
c=bpy.context.object;c.dimensions=(300,500,405);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
boolean(c,'DIFFERENCE')
bpy.ops.wm.stl_import(filepath=str(O/'upper-tangent.stl'));o=bpy.context.object;o.data.materials.append(silver);boolean(o,'UNION')
bm=bmesh.new();bm.from_mesh(shell.data)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
non=sum(not e.is_manifold for e in bm.edges)
assert non==0,non
volume=bm.calc_volume();bm.to_mesh(shell.data);bm.free()
for p in shell.data.polygons:p.use_smooth=True
shell.data.set_sharp_from_angle(angle=math.radians(30))
w=shell.modifiers.new('Weighted_silver_normals','WEIGHTED_NORMAL');w.keep_sharp=True
shell['crown_transition']='Rebuilt C2 quintic plan rails; downset ends with zero slope/curvature; shared exact solid before meshing.'
shell['upper_perimeter_edge_radius_mm']=.35
shell['upright_edge_radius_mm']=.35
shell['upper_solid_cad']='cad/upper-tangent.step, partial exact CAD from Z294 upwards'
for obj in bpy.data.objects:
 if obj.type in ['MESH','CURVE','SURFACE','FONT'] and obj.name not in ['BrewDuo_C_shell_5mm','weighed_base','Studio_ground','Triangular_pyramid_arm_flat_face_UP']:obj.hide_render=True
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'model/project-zoe.blend'),compress=True)
(ROOT/'docs/upper-blender-checks.json').write_text(json.dumps({'shell_nonmanifold_edges':non,'shell_volume_mm3':volume,'upper_stl_tolerance_mm':.005,'scope':'Exact upper solid joined to the existing lower mesh, not full assembly parametric CAD.'},indent=2))
