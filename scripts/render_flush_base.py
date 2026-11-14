from pathlib import Path
import bpy
from mathutils import Vector
R=Path(__file__).resolve().parents[1];O=R/'docs/flush-base'
bpy.ops.wm.open_mainfile(filepath=str(R/'model/project-zoe.blend'),use_scripts=False)
names=['BrewDuo_C_shell_5mm','weighed_base','New_recessed_ground_plate_CONCEPT']
S=bpy.context.scene;cam=S.camera
S.render.engine='CYCLES';S.cycles.samples=24
S.render.resolution_percentage=100;S.render.film_transparent=False
for ob in bpy.data.objects:
 if ob.type=='MESH' and ob.name not in names:ob.hide_render=True
ld=bpy.data.lights.new('Base_review_softbox','AREA');ld.energy=1600000;ld.shape='DISK';ld.size=280
lo=bpy.data.objects.new('Base_review_softbox',ld);S.collection.objects.link(lo);lo.location=(-120,-60,-240);lo.rotation_euler=(Vector((0,85,0))-lo.location).to_track_quat('-Z','Y').to_euler()
def render(name,loc,target,scale,w=1400,h=1000):
 cam.data.type='ORTHO';cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
 S.render.resolution_x=w;S.render.resolution_y=h;S.render.filepath=str(O/name);bpy.ops.render.render(write_still=True)
render('overall.png',(-245,340,135),(0,85,48),245)
render('rear-detail.png',(-130,-125,70),(0,22,4),106)
render('underside.png',(0,85,-400),(0,85,0),190,1000,1600)
# Explanatory explosion only; source .blend is NOT saved in this state.
bpy.data.objects['weighed_base'].location.z=14
bpy.data.objects['New_recessed_ground_plate_CONCEPT'].location.z=-14
render('exploded.png',(-190,-230,145),(0,65,7),205)
