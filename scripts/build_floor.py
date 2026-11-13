from pathlib import Path
import cadquery as cq
import json
ROOT=Path(__file__).resolve().parents[1]
O=ROOT/'cad'

def box(x,y,z,dx,dy,dz):
 return cq.Workplane('XY').box(dx,dy,dz,centered=(False,False,False)).translate((x,y,z)).val()
floor=cq.Workplane('XY').box(96,166,1.2,centered=(True,True,False)).translate((0,85,0)).val()
floor=floor.fillet(6,[e for e in floor.Edges() if e.BoundingBox().zlen>1.19])
# Inset counterpart of the cover rear notch; keep the old central stand tongue.
floor=floor.cut(box(-27.8,-2,-1,55.6,16,4)).clean()
# Small exposed horizontal edge rounds; rear mating edges remain unrounded.
edges=[e for e in floor.Edges() if e.BoundingBox().zlen<1e-7 and (abs(e.Center().z)<1e-7 or abs(e.Center().z-1.2)<1e-7)]
floor=floor.fillet(.35,edges)
old_joint=cq.importers.importStep(str(O/'fixed-rear-joint.step')).val()
fixed=old_joint.fuse(floor).clean()
cover=cq.importers.importStep(str(O/'base.step')).val()
assert floor.isValid() and fixed.isValid() and len(fixed.Solids())==1
assert cover.intersect(fixed).Volume()<1e-6
assert cover.distance(fixed)>.79
for name,s in [('fixed_flat_floor',floor),('fixed-base-local',fixed)]:
 for ext in ['step','stl']:
  cq.exporters.export(s,str(O/(name+'.'+ext)),**({'tolerance':.02,'angularTolerance':.06} if ext=='stl' else {}))
checks={'floor_plan_dimensions_mm':[96,166],'floor_rear_y_mm':2,'floor_front_y_mm':168,'floor_thickness_mm':1.2,'floor_plan_radius_mm':6,'cover_plan_radius_mm':8,'external_contour_inset_mm':2,'nominal_gap_to_1_2mm_cover_skirt_mm':.8,'rear_wings_follow_cover':True,'floor_rear_notch':{'x':[-27.8,27.8],'y_end':14},'fixed_cover_overlap_mm3':cover.intersect(fixed).Volume(),'minimum_fixed_cover_distance_mm':cover.distance(fixed),'fixed_local_valid':fixed.isValid(),'fixed_local_solids':len(fixed.Solids()),'scope':'Contour prototype only. Clearances are nominal CAD values, not production or weighing validation.'}
(ROOT/'docs/floor-checks.json').write_text(json.dumps(checks,indent=2));print(checks)
