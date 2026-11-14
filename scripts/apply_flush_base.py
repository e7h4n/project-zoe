"""Apply the 3 mm straight-skirt CAD while retaining reviewed upper geometry."""
from pathlib import Path
import bpy,bmesh,json,subprocess,tempfile
from mathutils import Vector
from mathutils.kdtree import KDTree
R=Path(__file__).resolve().parents[1];O=R/'docs/flush-base'
p=Path(tempfile.gettempdir())/'zoe-pre-flush.blend'
p.write_bytes(subprocess.check_output(['git','show','c6f427e:model/project-zoe.blend'],cwd=R))
bpy.ops.wm.open_mainfile(filepath=str(p),use_scripts=False)
shell=bpy.data.objects['BrewDuo_C_shell_5mm'];mat=shell.data.materials[0]
bpy.ops.object.select_all(action='DESELECT');shell.select_set(True);bpy.context.view_layer.objects.active=shell
bpy.ops.object.convert(target='MESH')
upper=[(shell.matrix_world@v.co).copy() for v in shell.data.vertices if (shell.matrix_world@v.co).z>10.001]
def boolean(ob,tool,operation):
 bpy.context.view_layer.objects.active=ob
 m=ob.modifiers.new('Flush_base_'+operation,'BOOLEAN');m.operation=operation;m.solver='MANIFOLD';m.object=tool
 bpy.ops.object.modifier_apply(modifier=m.name);bpy.data.objects.remove(tool,do_unlink=True)
# Flat clipping plane is inside a straight stand section; CAD joint overlaps it.
bpy.ops.mesh.primitive_cube_add(size=1,location=(0,85,-95.25));cut=bpy.context.object;cut.dimensions=(400,400,209.5)
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
boolean(shell,cut,'DIFFERENCE')
bpy.ops.wm.stl_import(filepath=str(R/'cad/fixed-base-local.stl'));local=bpy.context.object
boolean(shell,local,'UNION')
for name,file in [('weighed_base','base'),('New_recessed_ground_plate_CONCEPT','ground-plate-concept')]:
 ob=bpy.data.objects[name]
 bpy.ops.wm.stl_import(filepath=str(R/'cad'/(file+'.stl')));tmp=bpy.context.object;mesh=tmp.data;bpy.data.objects.remove(tmp,do_unlink=True)
 ob.data=mesh;ob.matrix_world.identity();ob.data.materials.clear();ob.data.materials.append(mat)
 ob['revision']='1.5/.5/1/.5/1 mm stack. Straight skirt extends 3mm; no inward return, no feet.'
 # Keep G's lower plane exactly aligned with the skirt; no display-only bevel.
 for modifier in list(ob.modifiers):
  if modifier.type=='BEVEL':ob.modifiers.remove(modifier)
checks={}
for name in ['BrewDuo_C_shell_5mm','weighed_base','New_recessed_ground_plate_CONCEPT']:
 ob=bpy.data.objects[name]
 bm=bmesh.new();bm.from_mesh(ob.data)
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-5)
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 checks[name]={'vertices':len(bm.verts),'faces':len(bm.faces),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges)}
 assert checks[name]['nonmanifold_edges']==0,checks[name]
 bm.to_mesh(ob.data);bm.free()
 for face in ob.data.polygons:face.use_smooth=True
 ob.data.set_sharp_from_angle(angle=.52)
 if not any(m.type=='WEIGHTED_NORMAL' for m in ob.modifiers):
  m=ob.modifiers.new('Weighted_normals','WEIGHTED_NORMAL');m.keep_sharp=True
world=[shell.matrix_world@v.co for v in shell.data.vertices]
tree=KDTree(len(world))
for i,v in enumerate(world):tree.insert(v,i)
tree.balance();delta=max(tree.find(v)[2] for v in upper)
assert delta<1e-4,delta
checks['upper_vertex_max_movement_mm']=delta
shell['floor_revision']='Continuous 1mm web Z2..3; M/G perimeter and rear Y12 aligned; bend lower tangent raised to Z.5 using R9.5. Upper retained.'
S=bpy.context.scene;cam=S.camera;cam.data.type='ORTHO'
cam.location=(-245,340,135);cam.rotation_euler=(Vector((0,85,48))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=245
bpy.ops.object.select_all(action='DESELECT');shell.select_set(True);bpy.context.view_layer.objects.active=shell
bpy.ops.wm.save_as_mainfile(filepath=str(R/'model/project-zoe.blend'),compress=True)
(O/'blender-checks.json').write_text(json.dumps(checks,indent=2)+'\n');print(json.dumps(checks,indent=2))
