"""Rebuild only the recessed base from the supplied pre-recess STEP.
Requires CadQuery 2.8.0. The complete upper assembly is authored in Blender.
"""
import math
from pathlib import Path
import cadquery as cq

ROOT = Path(__file__).resolve().parents[1]
source = cq.importers.importStep(str(ROOT / 'cad/base-before-recess.step')).val()
flat_radius = 42.5
fillet_radius = .25
outer_radius = flat_radius + 2 * fillet_radius
q = fillet_radius / math.sqrt(2)
cutter = (
    cq.Workplane('XZ', origin=(0, 125, 0))
    .moveTo(0, 7).lineTo(outer_radius, 7).lineTo(outer_radius, 5)
    .threePointArc((outer_radius-q, 4.75+q), (flat_radius+fillet_radius, 4.75))
    .threePointArc((flat_radius+q, 4.75-q), (flat_radius, 4.5))
    .lineTo(0, 4.5).close().revolve(360, (0, 0), (0, 1)).val()
)
base = source.cut(cutter)
assert base.isValid() and len(base.Solids()) == 1
assert base.cut(source).Volume() < 1e-7
assert base.isInside(cq.Vector(0, 125, 4.49))
assert not base.isInside(cq.Vector(0, 125, 4.51))
assert base.isInside(cq.Vector(44, 125, 4.99))
assert source.cut(base).BoundingBox().zmin >= 4.5 - 1e-7
cq.exporters.export(base, str(ROOT / 'cad/base.step'))
cq.exporters.export(base, str(ROOT / 'cad/base.stl'), tolerance=.005, angularTolerance=.025)
print('Rebuilt valid 100 x 170 x 5mm base; flat seat Ø85, depth 0.5, two R0.25 arcs.')
print('CAD exports are the base only. Import base.stl to replace weighed_base in Blender.')
