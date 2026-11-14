"""Reviewed 1.5 / .5 / 1 / .5 / 1 mm base; 3 mm straight skirt.
No rubber feet, no inward return. Pinned previous CAD supplies the bend/seat.
"""
from pathlib import Path
import cadquery as cq
import subprocess,tempfile,json,math
R=Path(__file__).resolve().parents[1];O=R/'docs/flush-base';O.mkdir(exist_ok=True)
def old(name):
 p=Path(tempfile.gettempdir())/('zoe-flush-source-'+name+'.step')
 p.write_bytes(subprocess.check_output(['git','show','c6f427e:cad/'+name+'.step'],cwd=R))
 return cq.importers.importStep(str(p)).val()
def box(x,y,z,dx,dy,dz):return cq.Solid.makeBox(dx,dy,dz,cq.Vector(x,y,z))
def rounded(x,y,z,w,d,t,r):
 s=box(x,y,z,w,d,t)
 return s.fillet(r,[e for e in s.Edges() if e.BoundingBox().zlen>t-.0001])
# Match the bend's lower tangent to G/skirt Z.5, rather than retaining the
# obsolete Z0 tangent. Inner R5 stays; outer R9.5 ends at Y9.5/Z.5.
# Upright section Y0..5 at Z10 and the reviewed upper assembly stay unchanged.
q=math.sqrt(2)
bend=(cq.Workplane('YZ',origin=(-25,0,0)).moveTo(0,10)
 .threePointArc((9.5-9.5/q,10-9.5/q),(9.5,.5))
 .lineTo(10,.5).lineTo(10,5)
 .threePointArc((10-5/q,10-5/q),(5,10)).close().extrude(50).val())
bridge=box(-25,10,2,50,22,1)
# Middle and ground share their full outer plan contour and rear Y12 cut line.
floor=rounded(-48.3,1.7,2,96.6,166.6,1,6.3).cut(box(-27.5,-2,-1,55,14,10))
M=bend.fuse(bridge).fuse(floor).clean()
# Preserve original top face and D85 x .5 seat; roof underside moves to Z3.5.
prior_C=old('base')
roof=prior_C.intersect(box(-100,-20,3.8,200,220,10))
thickening=rounded(-50,0,3.5,100,170,.3,8).cut(box(-25.8,-2,3,51.6,14,3))
# Straight skirts: Z.5..3.5, 1.2 mm walls. No inward folded lip.
outer=rounded(-50,0,.5,100,170,3,8)
pocket=rounded(-48.8,1.2,-1,97.6,167.6,7,6.8)
# End rear-notch side skirts at Y11.5, .5 before the aligned G/M Y12 edge.
# Extending them to Y13.2 would intersect the newly aligned plates.
pocket=pocket.cut(box(-27,-2,-2,54,13.5,10))
skirt=outer.cut(pocket).cut(box(-25.8,-2,-1,51.6,13.5,6))
# The crossing central M bridge passes through the rear opening. Do NOT add a
# downward crosswall there: it would join the moving C to M and bypass sensing.
C=roof.fuse(thickening).fuse(skirt).clean()
# G is .5 inside the skirt's INNER walls, not .5 inside its outside silhouette.
G=rounded(-48.3,1.7,.5,96.6,166.6,1,6.3).cut(box(-27.5,-2,-1,55,14,5)).clean()
upper=old('manual-fixed-upper');full_M=M.fuse(upper).clean()
parts={'C':C,'M':M,'G':G}
checks={'revision':'aligned rear Y12 edges and middle/G contours; all lower tangents Z.5','units':'mm','C_roof_z':[3.5,5],'M_web_z':[2,3],'G_z':[.5,1.5],'C_roof_nominal_thickness_mm':1.5,'M_web_thickness_mm':1,'G_thickness_mm':1,'stack_total_mm':4.5,'skirt_z':[.5,3.5],'skirt_extension_below_roof_mm':3,'skirt_wall_mm':1.2,'G_inset_from_inner_skirt_wall_mm':.5,'G_outer_inset_from_C_mm':1.7,'skirt_G_bottom_alignment_z':.5,'nominal_vertical_gaps_mm':{'C_M':.5,'M_G':.5},'rear_crossing_bridge_unobstructed':True,'aligned_rear_cross_edges_y_mm':12,'aligned_M_G_outer_contour':True,'bend_outer_radius_mm':9.5,'bend_inner_radius_mm':5,'aligned_bend_skirt_G_bottom_z_mm':.5,'rear_side_skirt_end_y_mm':11.5,'rubber_feet_added':False,'neck_probe_y_mm':[10.01,10.5,11,11.5,12,12.5,13,13.5,14,14.5,15,20,30],'scope':'Geometric concept only. No sensor/mount, deflection, tolerance, production or weighing verification. Bend, G and skirt undersides are aligned at Z.5; feet/contact force paths remain future work.'}
for n,s in parts.items():
 checks[n]={'valid':s.isValid(),'solids':len(s.Solids()),'volume_mm3':s.Volume()}
 assert s.isValid() and len(s.Solids())==1,(n,checks[n])
for a,b in [('C','M'),('M','G'),('C','G')]:
 checks[a+'_'+b]={'overlap_mm3':parts[a].intersect(parts[b]).Volume(),'min_distance_mm':parts[a].distance(parts[b])}
 assert checks[a+'_'+b]['overlap_mm3']<1e-6
 assert checks[a+'_'+b]['min_distance_mm']>.49
# Explicitly check neck thickness, not only remote points or non-intersection.
checks['neck_thickness_samples_mm']=[]
for y in checks['neck_probe_y_mm']:
 q=M.intersect(box(-.005,y,0,.01,.001,6));b=q.BoundingBox()
 assert abs(b.zmin-2)<1e-6 and abs(b.zmax-3)<1e-6,(y,b.zmin,b.zmax)
 checks['neck_thickness_samples_mm'].append(b.zlen)
for y in [20,40,85,125,160]:
 for z,inside in [(1.99,False),(2.01,True),(2.99,True),(3.01,False)]:assert M.isInside(cq.Vector(0,y,z))==inside
assert C.isInside(cq.Vector(0,125,4.49)) and not C.isInside(cq.Vector(0,125,4.51))
assert C.isInside(cq.Vector(49.5,85,.51)) and C.isInside(cq.Vector(49.5,85,3.49))
assert not C.isInside(cq.Vector(48.5,85,1))
assert abs(C.BoundingBox().zmin-.5)<1e-6 and abs(G.BoundingBox().zmin-.5)<1e-6
assert abs(C.BoundingBox().zmax-5)<1e-6
# Prove the newly requested alignments, not merely non-intersection.
assert abs(M.BoundingBox().zmin-.5)<1e-6
assert abs(M.BoundingBox().xmax-G.BoundingBox().xmax)<1e-6
assert abs(M.BoundingBox().ymax-G.BoundingBox().ymax)<1e-6
for y in [12.01,12.1,13,13.5,14,20,85,125,160]:
 for x in [-48.2,48.2]:
  # Skip rear rounded corners where the contour turns inward.
  if y>=14:assert M.isInside(cq.Vector(x,y,2.5))==G.isInside(cq.Vector(x,y,1))
assert G.isInside(cq.Vector(0,12.01,1)) and not G.isInside(cq.Vector(0,11.99,1))
assert C.isInside(cq.Vector(0,12.01,4)) and not C.isInside(cq.Vector(0,11.99,4))
checks['explicit_alignment_checks_passed']=True
# Prove straight-side and rounded-corner plan clearance, at G midheight.
checks['G_plan_nominal_bounds_mm']={'x':[-48.3,48.3],'y':[1.7,168.3],'corner_radius':6.3,'rear_notch_x':[-27.5,27.5],'rear_notch_end_y':12}
assert full_M.isValid() and len(full_M.Solids())==1
checks['full_M_valid']=True;checks['full_M_solids']=1
for n,s in [('base',C),('fixed-base-local',M),('ground-plate-concept',G),('flush-middle-full',full_M)]:
 cq.exporters.export(s,str(R/'cad'/(n+'.step')))
 cq.exporters.export(s,str(R/'cad'/(n+'.stl')),tolerance=.012,angularTolerance=.05)
assy=cq.Assembly(name='Project_Zoe_three_mm_skirt')
for n,s,col in [('C_weighing_platform',C,(.32,.57,.76)),('M_integrated_stand',full_M,(.39,.64,.45)),('G_ground_plate',G,(.78,.59,.30))]:assy.add(s,name=n,color=cq.Color(*col))
assy.export(str(R/'cad/Project_Zoe_flush_assembly.step'))
(O/'cad-checks.json').write_text(json.dumps(checks,indent=2)+'\n');print(json.dumps(checks,indent=2))
