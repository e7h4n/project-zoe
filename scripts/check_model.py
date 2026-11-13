"""Verify the approved floor/lip revision and real R0.35 upright mesh edges."""
from pathlib import Path
import math,json,sys
import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'model/project-zoe.blend'), use_scripts=False)
meshes = {}
for name in ['BrewDuo_C_shell_5mm', 'weighed_base']:
    obj = bpy.data.objects[name]
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    assert all(e.is_manifold for e in bm.edges), f'{name}: nonmanifold edges'
    bm.free()
    # Current source uses identity transforms; BVH is intentionally in design mm.
    assert all(abs(obj.matrix_world[i][j] - (1 if i == j else 0)) < 1e-6
               for i in range(4) for j in range(4)), 'Update BVH frame conversion for transformed source'
    meshes[name] = (evaluated, mesh, BVHTree.FromPolygons(
        [v.co.copy() for v in mesh.vertices], [list(p.vertices) for p in mesh.polygons]))

fixed = meshes['BrewDuo_C_shell_5mm'][2]
cover = meshes['weighed_base'][2]
for y in [15, 31, 32, 33, 60, 120, 160]:
    hit = fixed.ray_cast(Vector((0, y, 3.7)), Vector((0, 0, -1)), 5)[0]
    assert hit is not None and abs(hit.z - 2) < .002, f'Floor must be flat at Z2: Y{y}, {hit}'
for y in [12.1, 12.6, 13.1]:
    hit = cover.ray_cast(Vector((0, y, 2.1)), Vector((0, 0, 1)), 5)[0]
    assert hit is not None and abs(hit.z - 3.8) < .002, f'Rear lip must be removed: Y{y}, {hit}'

# Resolve a Z50 cross-section in the normal direction of the tapered side plane.
mesh = meshes['BrewDuo_C_shell_5mm'][1]
mesh.calc_loop_triangles()
errors = []
for tri in mesh.loop_triangles:
    vertices = [mesh.vertices[i].co for i in tri.vertices]
    for a, b in zip(vertices, vertices[1:] + vertices[:1]):
        if (a.z - 50) * (b.z - 50) < 0:
            p = a.lerp(b, (50 - a.z) / (b.z - a.z))
            u = (p.x + .05 * p.z - 25.5) / math.sqrt(1.0025)
            if p.x > 20 and 4.64 < p.y < 5.01 and -.36 < u < .01:
                errors.append(abs(math.hypot(u + .35, p.y - 4.65) - .35))
assert len(errors) > 10 and max(errors) < .003, f'R0.35 profile invalid: {errors}'
# No transverse raised/recessed fillet rail at either old Boolean seam.
for ys, bottom, top in [([10,10.1,11,30],315,320),
                        ([94,94.5,95,103,105,118],305,310)]:
    for y in ys:
        for z, direction in [(top, Vector((0,0,-1))), (bottom, Vector((0,0,1)))]:
            hit = fixed.ray_cast(Vector((0,y,z))-direction*2, direction, 3)[0]
            assert hit is not None and abs(hit.z-z) < .002, f'Upper seam step at Y{y}: {hit}'

# Upper arm and crown must have the same rounded treatment on BOTH rims.
# Radial ray samples catch a missed bottom rim or a bevel stopping at a height cutoff.
k = 3 / (105 - 10)
side = Vector((1, k, 0)).normalized()
h = 10 - k * (30 - 10)
upper_errors = {}
profiles = [
    ('arm_top', Vector((h - .35 * math.sqrt(1+k*k), 30, 319.65)), side, Vector((0,0,1))),
    ('arm_bottom', Vector((h - .35 * math.sqrt(1+k*k), 30, 315.35)), side, Vector((0,0,-1))),
    ('crown_top', Vector((21.65,125,309.65)), Vector((1,0,0)), Vector((0,0,1))),
    ('crown_bottom', Vector((21.65,125,305.35)), Vector((1,0,0)), Vector((0,0,-1))),
]
for label, center, n1, n2 in profiles:
    deviations = []
    for degrees in range(10, 81, 10):
        angle = math.radians(degrees)
        direction = n1 * math.cos(angle) + n2 * math.sin(angle)
        hit = fixed.ray_cast(center + direction * 2, -direction, 3)[0]
        assert hit is not None, f'{label}: missing surface'
        deviations.append(abs((hit-center).length - .35))
    upper_errors[label] = max(deviations)
    assert max(deviations) < .012, f'{label}: R0.35 missing or inconsistent: {deviations}'
# Check actual rebuilt side contour against its C2 Bezier specification.
spec = json.loads((ROOT/'docs/upper-checks.json').read_text())
xy_controls=spec['flare_bezier_control_points_xy']
controls = [Vector((x,y,0)) for x,y in xy_controls]
L = xy_controls[-1][1]-xy_controls[0][1]
xs=[p[0] for p in xy_controls]
slope0 = 5*(xs[1]-xs[0])/L
slope1 = 5*(xs[-1]-xs[-2])/L
curv0 = 20*(xs[2]-2*xs[1]+xs[0])/L**2
curv1 = 20*(xs[-1]-2*xs[-2]+xs[-3])/L**2
x1,y1 = xy_controls[-1]
assert abs(slope0+k)<1e-10 and abs(curv0)<1e-10
assert abs(slope1-(125-y1)/x1)<1e-10 and abs(curv1+484/x1**3)<1e-10
contour_errors=[]
for t in [i/40 for i in range(41)]:
    p=sum((controls[i]*(math.comb(5,i)*t**i*(1-t)**(5-i)) for i in range(6)),Vector((0,0,0)))
    for sign in [-1,1]:
        hit=fixed.ray_cast(Vector((sign*(p.x+2),p.y,307.5)),Vector((-sign,0,0)),4)[0]
        assert hit is not None, f'Missing flare at {p}'
        contour_errors.append(abs(abs(hit.x)-p.x))
assert max(contour_errors)<.012, f'Flare contour differs from C2 solid: {max(contour_errors)}'

# Upright front/back planes remain vertical; the existing plan-width taper
# must not be mistaken for a leaning guide. Sample outside the central slot.
front_y, back_y = [], []
for z in [20,50,100,160,220,280]:
    front = fixed.ray_cast(Vector((8,-5,z)),Vector((0,1,0)),15)[0]
    back = fixed.ray_cast(Vector((8,12,z)),Vector((0,-1,0)),15)[0]
    assert front is not None and back is not None, f'Missing guide plane at Z{z}'
    front_y.append(front.y); back_y.append(back.y)
assert max(front_y)-min(front_y)<.002 and max(back_y)-min(back_y)<.002, 'Upright must be perpendicular to floor'
# Geometric (not locking-mechanism) test: a pure-Z adjustment leaves ring XY
# unchanged. Fit its actual outer rim rather than relying on an Empty/label.
import numpy as np
arm = bpy.data.objects['Triangular_pyramid_arm_flat_face_UP']
rim = [arm.matrix_world@v.co for v in arm.data.vertices
       if abs((arm.matrix_world@v.co).z-162)<.002
       and abs(math.hypot((arm.matrix_world@v.co).x,(arm.matrix_world@v.co).y-125)-30)<.002]
assert len(rim)>20, 'Ring outer rim missing'
xy = np.array([[p.x,p.y] for p in rim])
fit = np.linalg.lstsq(np.column_stack([2*xy[:,0],2*xy[:,1],np.ones(len(xy))]),(xy*xy).sum(axis=1),rcond=None)[0]
assert abs(fit[0])<.002 and abs(fit[1]-125)<.002, f'Ring center moved: {fit[:2]}'
guide_slope=float(np.polyfit([20,50,100,160,220,280],back_y,1)[0])
center_samples=[[float(fit[0]),float(fit[1]+guide_slope*dz),float(162+dz)] for dz in [-30,0,50]]
assert max(p[1] for p in center_samples)-min(p[1] for p in center_samples)<.002
if '--report' in sys.argv:
    (ROOT/'docs/geometry-checks.json').write_text(json.dumps({
        'source_mesh_manifold':True,'upright_to_floor_angle_degrees':90-math.degrees(math.atan(guide_slope)),
        'upright_front_y_span_mm':max(front_y)-min(front_y),'upright_back_y_span_mm':max(back_y)-min(back_y),
        'ring_center_xyz_at_three_heights_mm':center_samples,
        'ring_xy_drift_mm':max(p[1] for p in center_samples)-min(p[1] for p in center_samples),
        'radius_profile_deviations_mm':upper_errors,'flare_contour_max_error_mm':max(contour_errors),
        'flare_plan_continuity':'C2 at straight taper and circular crown endpoints',
        'scope':'Geometric guide-axis/ideal translation check only. Real slider fit, locking, deflection and manufacturing tolerances are not validated.'
    },indent=2))
for evaluated, mesh, tree in meshes.values():
    evaluated.to_mesh_clear()
print(f'PASS: manifold source, flat Z2 floor, rear lip removed, R0.35 upright profile ({max(errors):.6f}mm max deviation); upper rims: {upper_errors}; C2 flare contour error {max(contour_errors):.6f}mm; upright/floor {90-math.degrees(math.atan(guide_slope)):.6f}deg; ideal ring XY drift <0.002mm.')
