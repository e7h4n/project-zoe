"""Rebuilt upper strip and C2 plan transition to the crown, in millimetres."""
from pathlib import Path
import cadquery as cq
import math,json
ROOT=Path(__file__).resolve().parents[1]
O=ROOT/'cad'
R=.35; K=3/(105-10); START=58.333333; END=94.
def width(y):return 10-K*(y-10)
def section(y,z,n_y,n_z,h):
    pts=[cq.Vector(x,y+s*2.5*n_y,z+s*2.5*n_z) for x,s in [(-h,-1),(h,-1),(h,1),(-h,1)]]
    w=cq.Wire.makePolygon(pts,close=True)
    return w
# Separate analytic straight/bend pieces avoid a global interpolated loft
# overshooting the nominal planes at path transitions.
vertical=cq.Solid.makeLoft([section(2.5,z,-1,0,25.5-.05*z) for z in [294,310]],ruled=True)
p0=cq.Vector(0,2.5,310);pm=cq.Vector(0,10-7.5/math.sqrt(2),310+7.5/math.sqrt(2));p1=cq.Vector(0,10,317.5)
bend_path=cq.Wire.assembleEdges([cq.Edge.makeThreePointArc(p0,pm,p1)])
bend=cq.Solid.sweep(section(2.5,310,-1,0,10),[],bend_path,makeSolid=True,isFrenet=True)
straight=cq.Solid.makeLoft([section(y,317.5,0,1,width(y)) for y in [10,START]],ruled=True)
# Smoothstep-5 downset has zero slope AND curvature at both ends.
wires=[]
ys=[START+(END-START)*i/48 for i in range(49)]
for y in ys:
    t=max(0,min(1,(y-START)/(END-START)))
    f=10*t**3-15*t**4+6*t**5
    df=30*t*t*(1-t)**2/(END-START)
    z=317.5-10*f; dz=-10*df;den=math.sqrt(1+dz*dz)
    wires.append(section(y,z,-dz/den,1/den,width(y)))
downset=cq.Solid.makeLoft(wires,ruled=False)
strip=vertical.fuse(bend).fuse(straight).fuse(downset).clean()
assert strip.isValid() and len(strip.Solids())==1, 'invalid loft union'
# Quintic Bezier side rails match straight taper and circle position, tangent,
# and curvature. Y itself is linear along the Bezier parameter.
y0=END;y1=118.;L=y1-y0;x0=width(y0);x1=math.sqrt(22**2-(y1-125)**2)
d0=-K;dd0=0;d1=(125-y1)/x1;dd1=-22**2/x1**3
controls=[(x0,y0),(x0+d0*L/5,y0+L/5),(x0+2*d0*L/5+dd0*L*L/20,y0+2*L/5),(x1-2*d1*L/5+dd1*L*L/20,y1-2*L/5),(x1-d1*L/5,y1-L/5),(x1,y1)]
vec=lambda p:cq.Vector(p[0],p[1],305)
right=cq.Edge.makeBezier([vec(p) for p in controls])
left=cq.Edge.makeBezier([vec((-x,y)) for x,y in controls[::-1]])
arc=cq.Edge.makeThreePointArc(vec((x1,y1)),vec((0,147)),vec((-x1,y1)))
rear=cq.Edge.makeLine(vec((-x0,y0)),vec((x0,y0)))
outline=cq.Wire.assembleEdges([rear,right,arc,left])
crown=cq.Solid.extrudeLinear(outline,[],cq.Vector(0,0,5))
assert crown.isValid(), 'invalid crown'
upper=strip.fuse(crown).clean()
assert upper.isValid() and len(upper.Solids())==1,'upper must be one valid solid'
# Fillet AFTER the exact solid union: independently rounded touching pieces
# otherwise differ by a microscopic elliptical/circular section at the seam.
round_edges=[]
for e in upper.Edges():
 if e.BoundingBox().zmax<294.001:continue
 faces=[f for f in upper.Faces() if any(fe.isSame(e) for fe in f.Edges())]
 if len(faces)!=2:continue
 p=e.positionAt(.5)
 n0=faces[0].normalAt(p);n1=faces[1].normalAt(p)
 if abs(n0.dot(n1))<.7:round_edges.append(e)
print('FILLET_EDGES',len(round_edges),flush=True)
upper=upper.fillet(R,round_edges)
assert upper.isValid() and len(upper.Solids())==1,'invalid fillet'
cq.exporters.export(upper,str(O/'upper-tangent.step'))
assert upper.exportStl(str(O/'upper-tangent.stl'),tolerance=.005,angularTolerance=.075,relative=False)
checks={'valid':upper.isValid(),'solid_count':len(upper.Solids()),'edge_radius_mm':R,'crown_radius_mm':22,'crown_center_xy':[0,125],'crown_z_range_mm':[305,310],'flare_y_range_mm':[y0,y1],'flare_bezier_control_points_xy':controls,'join_continuity':'C2 in plan at both ends of each quintic rail; zero-slope/zero-curvature downset end.','scope':'Exact solid for the upper structure only, starting Z294; not a complete manufacturing-validated assembly.'}
checks.update({'tessellation_tolerance_mm':.005,'relative_tessellation':False,'angular_tolerance_rad':.075,'fillet_method':'R0.35 applied once after exact union of strip and crown.','downset_end_y_mm':END})
(ROOT/'docs/upper-checks.json').write_text(json.dumps(checks,indent=2))
print(json.dumps(checks,indent=2))
