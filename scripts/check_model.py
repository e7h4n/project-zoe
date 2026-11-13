"""Verify the approved floor/lip revision and real R0.35 upright mesh edges."""
from pathlib import Path
import math
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
for ys, bottom, top in [([9.8,9.85,9.9,10,10.1,11],315,320),
                        ([103,103.5,104,105,106],305,310)]:
    for y in ys:
        for z, direction in [(top, Vector((0,0,-1))), (bottom, Vector((0,0,1)))]:
            hit = fixed.ray_cast(Vector((0,y,z))-direction*2, direction, 3)[0]
            assert hit is not None and abs(hit.z-z) < .002, f'Upper seam step at Y{y}: {hit}'

# Upper arm and crown must have the same rounded treatment on BOTH rims.
# Radial ray samples catch a missed bottom rim or a bevel stopping at a height cutoff.
k = 3 / (105 - 9.7)
side = Vector((1, k, 0)).normalized()
h = 10 - k * (30 - 9.7)
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
    assert max(deviations) < .006, f'{label}: R0.35 missing or inconsistent: {deviations}'
for evaluated, mesh, tree in meshes.values():
    evaluated.to_mesh_clear()
print(f'PASS: manifold source, uniform 2mm floor, central rear lip removed, R0.35 upright profile ({max(errors):.6f}mm max radial deviation); upper arm/crown top AND bottom rims: {upper_errors}.')
