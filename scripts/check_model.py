"""Check current manual stand and flush three-layer concept, in design mm.
Nominal geometric checks only; not sensor-fit or manufacturing certification.
"""
from pathlib import Path
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'model/project-zoe.blend'), use_scripts=False)
names = ('BrewDuo_C_shell_5mm', 'weighed_base', 'New_recessed_ground_plate_CONCEPT')
trees = {}
for name in names:
    obj = bpy.data.objects[name]
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    bm = bmesh.new(); bm.from_mesh(mesh)
    assert all(e.is_manifold for e in bm.edges), f'{name}: nonmanifold mesh'
    bm.free()
    vertices = [obj.matrix_world @ v.co for v in mesh.vertices]
    trees[name] = BVHTree.FromPolygons(vertices, [list(p.vertices) for p in mesh.polygons])
    if name == names[0]:
        assert abs(min(v.z for v in vertices)-.5)<.002, 'M bend bottom must align at Z0.5'
        assert abs(max(v.x for v in vertices)-48.3)<.002, 'M perimeter must align with G'
    if name == 'weighed_base':
        assert abs(min(v.z for v in vertices) - .5) < .002
        assert abs(max(v.z for v in vertices) - 5) < .002
    if name == names[2]:
        assert abs(min(v.z for v in vertices) - .5) < .002
        assert abs(max(v.z for v in vertices) - 1.5) < .002
        for axis, span in [(0,96.6), (1,166.6)]:
            assert abs(max(v[axis] for v in vertices)-min(v[axis] for v in vertices)-span)<.002
        assert abs(min(v.y for v in vertices)-1.7)<.002, 'Ground rear wings must be Y1.7'
        assert abs(max(v.y for v in vertices)-168.3)<.002, 'Ground front edge must be Y168.3'
        assert abs(max(v.x for v in vertices)-48.3)<.002, 'Ground side must be X48.3'
        # Front plan corner shares center (42,162) with C.
        import math
        corner = [v for v in vertices if v.x>42.01 and v.y>162.01]
        assert len(corner)>10
        assert max(abs(math.hypot(v.x-42,v.y-162)-6.3) for v in corner)<.012, 'G plan radius must be R6.3'
    evaluated.to_mesh_clear()
fixed, cover = trees[names[0]], trees[names[1]]
def z_hit(tree, point, direction, expected, distance=10):
    hit = tree.ray_cast(Vector(point), Vector(direction), distance)[0]
    assert hit is not None and abs(hit.z-expected)<.01, (point, hit, expected)
for y in [10.01,10.5,11,11.5,12,12.5,13,13.5,14,15,31,32,33,60,120,160]:
    z_hit(fixed, (0,y,3.4), (0,0,-1), 3)
    z_hit(fixed, (0,y,1.7), (0,0,1), 2)
for y in [12.1,12.6,13.1]:
    z_hit(cover, (0,y,3.1), (0,0,1), 3.5)
# Aligned rear crossing edge, not the former Y13.7 ground edge.
for tree,z in [(cover,4),(trees[names[2]],1)]:
    hit=tree.ray_cast(Vector((0,11,z)), Vector((0,1,0)),5)[0]
    assert hit is not None and abs(hit.y-12)<.01, ('rear Y12 alignment',hit)
# A true 3mm downward skirt, not only a roof; aligned with G at Z.5.
z_hit(cover, (49.4,85,-1), (0,0,1), .5)
z_hit(trees[names[2]], (0,85,-1), (0,0,1), .5)
z_hit(cover, (0,125,10), (0,0,-1), 4.5)
z_hit(cover, (40,85,10), (0,0,-1), 5)
# Level ring: OD60 / ID48, underside113.5 / top118.5, center(0,125).
for x,y in [(27,125),(-27,125),(0,152),(0,98)]:
    z_hit(fixed, (x,y,125), (0,0,-1), 118.5, 20)
    z_hit(fixed, (x,y,108), (0,0,1), 113.5, 20)
assert fixed.ray_cast(Vector((0,125,125)), Vector((0,0,-1)), 20)[0] is None
obj = bpy.data.objects[names[0]]
assert max((obj.matrix_world@v.co).z for v in obj.data.vertices)<120, 'Automatic crown still present'
assert bpy.data.objects.get('Triangular_pyramid_arm_flat_face_UP') is None
print('PASS: three manifold product meshes; continuous 1mm neck/web; 1.5/.5/1/.5/1mm stack; 3mm straight skirt aligned with G at Z.5; unchanged seat and upper ring; no feet. Sensor fit, loaded clearances and accuracy NOT validated.')
