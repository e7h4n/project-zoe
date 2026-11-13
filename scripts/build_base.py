"""Rebuild the approved hollow weighing cover (CadQuery 2.8.0).
Exports CAD only; the complete assembly is authored in model/project-zoe.blend.
"""
from pathlib import Path
import cadquery as cq
import math
import json

ROOT = Path(__file__).resolve().parents[1]

def rounded_box(w, d, h, cx, cy, z, r):
    s = cq.Workplane('XY').box(w, d, h, centered=(True, True, False)).translate((cx, cy, z)).val()
    return s.fillet(r, [e for e in s.Edges() if e.BoundingBox().zlen > h-1e-6])

def box(x, y, z, dx, dy, dz):
    return cq.Workplane('XY').box(dx, dy, dz, centered=(False, False, False)).translate((x, y, z)).val()

# Hollow cover, R8 plan corners and R0.35 exposed upper edges.
cover = rounded_box(100, 170, 4.2, 0, 85, .8, 8)
cover = cover.fillet(.35, [e for e in cover.Edges() if e.BoundingBox().zlen < 1e-7 and abs(e.Center().z-5) < 1e-7])
pocket = rounded_box(97.6, 167.6, 5.8, 0, 85, -2, 6.8)
pocket = pocket.cut(box(-27, -2, -3, 54, 15.2, 10))
cover = cover.cut(pocket)
# Restore side wings around the original central stand clearance.
cover = cover.cut(box(-25.8, -2, -1, 51.6, 14, 8))
cover = cover.cut(box(-25.8, 10, 0, 51.6, 5, 2.8))
# Preserve the D85 x 0.5 seat and its two opposite R0.25 transitions.
r = 42.5
f = .25
out = r+2*f
q = f/math.sqrt(2)
tool = (cq.Workplane('XZ', origin=(0, 125, 0)).moveTo(0, 7).lineTo(out, 7).lineTo(out, 5)
        .threePointArc((out-q, 4.75+q), (r+f, 4.75))
        .threePointArc((r+q, 4.75-q), (r, 4.5)).lineTo(0, 4.5).close()
        .revolve(360, (0, 0), (0, 1)).val())
cover = cover.cut(tool).clean()
fixed = cq.importers.importStep(str(ROOT/'cad/fixed-base-local.step')).val()
assert cover.isValid() and len(cover.Solids()) == 1
assert cover.intersect(fixed).Volume() < 1e-6
assert cover.isInside(cq.Vector(35, 5, 4.2))
assert not cover.isInside(cq.Vector(0, 5, 4.2))
assert cover.isInside(cq.Vector(0, 125, 4.49))
assert not cover.isInside(cq.Vector(0, 125, 4.51))
for ext in ['step', 'stl']:
    cq.exporters.export(cover, str(ROOT/('cad/base.'+ext)),
                        **({'tolerance': .02, 'angularTolerance': .06} if ext == 'stl' else {}))
checks = {'upper_edge_radius_mm': .35, 'plan_corner_radius_mm': 8,
          'valid': cover.isValid(), 'solids': len(cover.Solids()),
          'fixed_overlap_mm3': cover.intersect(fixed).Volume(),
          'minimum_gap_mm': cover.distance(fixed), 'restored_rear_wings_y': 0,
          'central_notch': {'x': [-25.8, 25.8], 'y_end': 12},
          'seat_D85_depth_0_5_preserved': True,
          'scope': 'Appearance prototype. Hollow cover retained. No sensor fit/manufacturing validation.'}
(ROOT/'docs/checks.json').write_text(json.dumps(checks, indent=2)+'\n')
print(json.dumps(checks, indent=2))
