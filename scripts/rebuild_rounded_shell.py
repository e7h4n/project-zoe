"""Rebuild the reviewed mesh from the pinned pre-cover source.
Run build_floor.py and build_base.py first to generate the two STL inputs.
This overwrites model/project-zoe.blend; run the site build/QA afterwards.
"""
import bpy,bmesh,os,json,math,hashlib,subprocess,tempfile
from mathutils import Vector,Matrix
from mathutils.kdtree import KDTree
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
O=ROOT/'docs'
source=Path(tempfile.gettempdir())/'zoe-pinned-authoring-source.blend'
source.write_bytes(subprocess.check_output(['git','show','7aaa157:model/project-zoe.blend'],cwd=ROOT))
bpy.ops.wm.open_mainfile(filepath=str(source.resolve()),use_scripts=False)
S=bpy.context.scene;cam=S.camera
shell=bpy.data.objects['BrewDuo_C_shell_5mm'];silver=shell.data.materials[0]
# Bake original display modifiers once; record the evaluated upper geometry.
bpy.ops.object.select_all(action='DESELECT');shell.select_set(True);bpy.context.view_layer.objects.active=shell
bpy.ops.object.convert(target='MESH')
before=[(shell.matrix_world@v.co).copy() for v in shell.data.vertices if (shell.matrix_world@v.co).z>10.1]
# Permanently union the flat floor into the existing stand, not a separate frame.
bpy.ops.wm.stl_import(filepath=str(ROOT/'cad/fixed_flat_floor.stl'));floor=bpy.context.object;floor.data.materials.append(silver)
bpy.context.view_layer.objects.active=shell
m=shell.modifiers.new('Integrate_flat_bottom_plate','BOOLEAN');m.operation='UNION';m.solver='MANIFOLD';m.object=floor
bpy.ops.object.modifier_apply(modifier=m.name);bpy.data.objects.remove(floor,do_unlink=True)
# Preserve the rest of the model; replace only the former solid weighing slab.
bpy.data.objects.remove(bpy.data.objects['weighed_base'],do_unlink=True)
bpy.ops.wm.stl_import(filepath=str(ROOT/'cad/base.stl'));cover=bpy.context.object;cover.name='weighed_base';cover.data.materials.append(silver)
# Recalculate topological normals and retain sharp creases on the imported cover.
for obj in [shell,cover]:
 bm=bmesh.new();bm.from_mesh(obj.data)
 if obj==shell:
  # The Exact Boolean can split nearly coincident bevel vertices at the remote
  # disc junction. Weld only within 0.00001mm, far below geometric tolerances.
  bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-5)
  bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-5)
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
 if obj==cover:
  for p in obj.data.polygons:p.use_smooth=True
  obj.data.set_sharp_from_angle(angle=math.radians(30))
  w=obj.modifiers.new('Weighted_cover_normals','WEIGHTED_NORMAL');w.keep_sharp=True
shell['assembly_role']='Fixed upright and flat base integrated as one mesh. No raised perimeter frame.'
cover['assembly_role']='Weighing surface with four downward skirts. Translate +Z to inspect the empty interior.'
cover['prototype_only']='Original 5mm base envelope retained; no sensor selection or mounting designed. No rejected section 03 mechanism adopted.'
# Prove that the evaluated upper-stand vertices have not moved.
after=[shell.matrix_world@v.co for v in shell.data.vertices]
tree=KDTree(len(after))
for i,p in enumerate(after):tree.insert(p,i)
tree.balance();max_delta=max(tree.find(p)[2] for p in before)
assert max_delta<1e-4,max_delta
# Replace the numerically clamped old edge break with a true 0.35mm mesh fillet
# on the four exposed upright perimeter chains, continuing around the lower bend.
bm=bmesh.new();bm.from_mesh(shell.data)
print('PRE_CLEAN_NONMANIFOLD',sum(not e.is_manifold for e in bm.edges),flush=True)
# Remove the old Boolean's micron-scale sawtooth at the bend/arm seam.
# Both adjoining surfaces nominally share Z315/Z320. Without this cleanup,
# a new fillet would round the spurious transverse micro-steps into raised bars.
for v in bm.verts:
 # Make the final arm/crown overlap share the same two planes rather than
 # rounding the Boolean's sub-0.08mm crescent into an unintended extra lip.
 if v.co.y>102.9:
  if abs(v.co.z-305)<.08:v.co.z=305
  if abs(v.co.z-310)<.08:v.co.z=310
 if v.co.z>314.9 and 9.4<v.co.y<10.1 and abs(v.co.x)>9.9:
  v.co.x=math.copysign(10-3*max(0,v.co.y-9.7)/(105-9.7),v.co.x)
 if 9.4<v.co.y<58.34:
  if abs(v.co.z-315)<.02:v.co.z=315
  if abs(v.co.z-320)<.02:v.co.z=320
clean_verts=[v for v in bm.verts if v.co.z>4.99]
bmesh.ops.remove_doubles(bm,verts=clean_verts,dist=.002)
clean_edges=[e for e in bm.edges if all(v.co.z>4.99 for v in e.verts)]
bmesh.ops.dissolve_degenerate(bm,edges=clean_edges,dist=.002)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
bmesh.ops.dissolve_limit(bm,angle_limit=1e-6,verts=[v for v in bm.verts if v.co.z>4.99],edges=[e for e in bm.edges if all(v.co.z>4.99 for v in e.verts)],use_dissolve_boundaries=False)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
bevel_edges=[]
for e in bm.edges:
 if not e.is_manifold or e.calc_face_angle()<math.radians(40):continue
 ps=[v.co for v in e.verts]
 is_upright=all(8<abs(p.x)<25.01 and p.z<310.01 and p.y<11.01 for p in ps) and max(p.z for p in ps)>4.99 and (abs(ps[0].z-ps[1].z)>.002 or min(p.z for p in ps)>9.99)
 is_upper=all(p.z>299.99 for p in ps)
 if is_upright or is_upper:bevel_edges.append(e)
bevel_count=len(bevel_edges);assert bevel_count>100
print('POST_CLEAN_NONMANIFOLD',sum(not e.is_manifold for e in bm.edges),'BEVEL_EDGES',bevel_count,flush=True)
bmesh.ops.bevel(bm,geom=bevel_edges,offset=.35,offset_type='OFFSET',segments=12,profile=.5,affect='EDGES',clamp_overlap=False,loop_slide=True)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
bm.to_mesh(shell.data);bm.free()
for p in shell.data.polygons:p.use_smooth=True
shell.data.set_sharp_from_angle(angle=math.radians(30))
w=shell.modifiers.new('Weighted_upright_edge_normals','WEIGHTED_NORMAL');w.keep_sharp=True
shell['upright_edge_radius_mm']=.35
shell['upper_perimeter_edge_radius_mm']=.35
shell['edge_continuity']='R0.35 continues from upright around upper bend, arm and circular crown; no abrupt stop at Z310.'
shell['floor_revision']='2mm floor continuous with old joint; Y32 step removed.'
cover['rear_revision']='Central rear notch downturned lip removed; top and remaining skirts retained.'
mesh_checks={}
for obj in [shell,cover]:
 bm=bmesh.new();bm.from_mesh(obj.data)
 mesh_checks[obj.name]={'vertices':len(bm.verts),'faces':len(bm.faces),'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges)}
 assert mesh_checks[obj.name]['nonmanifold_edges']==0,mesh_checks[obj.name]
 bm.free()
cam.location=(-420,610,430);cam.rotation_euler=(Vector((0,72,160))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=435
S.render.filepath='//preview.png'
bpy.ops.object.select_all(action='DESELECT');cover.select_set(True);bpy.context.view_layer.objects.active=cover
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'model/project-zoe.blend'),compress=True)
(O/'bottom-blender-checks.json').write_text(json.dumps({'original_model_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'upper_evaluated_vertex_count_checked':len(before),'upper_prebevel_vertex_max_movement_mm':max_delta,'upright_bevel_radius_mm':.35,'upright_beveled_edge_count':bevel_count,'numerical_cleanup_weld_tolerance_mm':.002,'fixed_base_is_unioned_into_stand':True,'mesh_checks':mesh_checks,'original_source_not_overwritten':True},indent=2))
