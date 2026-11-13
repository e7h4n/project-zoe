"""Check current manual stand and concealed three-layer concept, in design mm.
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
    if name == 'weighed_base':
        assert abs(min(v.z for v in vertices) + 3.5) < .002
        assert abs(max(v.z for v in vertices) - 5) < .002
    if name == names[2]:
        assert abs(min(v.z for v in vertices) + 4) < .002
        assert abs(max(v.z for v in vertices) + 2) < .002
        for axis, span in [(0,94), (1,164)]:
            assert abs(max(v[axis] for v in vertices)-min(v[axis] for v in vertices)-span)<.002
    evaluated.to_mesh_clear()
fixed, cover = trees[names[0]], trees[names[1]]
def z_hit(tree, point, direction, expected, distance=10):
    hit = tree.ray_cast(Vector(point), Vector(direction), distance)[0]
    assert hit is not None and abs(hit.z-expected)<.01, (point, hit, expected)
for y in [15,31,32,33,60,120,160]:
    z_hit(fixed, (0,y,3.7), (0,0,-1), 2)
for y in [12.1,12.6,13.1]:
    z_hit(cover, (0,y,2.1), (0,0,1), 3.8)
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
print('PASS: three manifold product meshes; flat Z2 floor; unchanged seat; level manual ring; concealed G; 0.5mm nominal skirt/table gap. Sensor fit, loaded clearances and accuracy NOT validated.')
