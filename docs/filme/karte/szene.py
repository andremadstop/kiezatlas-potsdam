# Blender-Szene „Potsdam wächst aus den Daten“ (headless, EEVEE, Python-Modul bpy 5.1.2).
# Aufruf: python docs/filme/karte/szene.py --prep <prep> --aus <frames> [--zeiten 6,12.5] [--von F --bis F] [--pct 100]
# Liest <prep>/meta.json, gebaeude.npz, zellen.npz, nutzung.npz (prep.py) und schreibt <aus>/b_NNNN.png.
import argparse
import math
import os
import sys
import time

import bpy
import numpy as np
from mathutils import Matrix, Vector

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
import zeitplan as Z

ap = argparse.ArgumentParser()
ap.add_argument("--prep", required=True)
ap.add_argument("--aus", required=True)
ap.add_argument("--zeiten", default="")
ap.add_argument("--von", type=int, default=0)
ap.add_argument("--bis", type=int, default=Z.N - 1)
ap.add_argument("--pct", type=int, default=100)
ap.add_argument("--samples", type=int, default=24)
args = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])
META = Z.lade(args.prep)
FPS = Z.FPS


def lin(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple((x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c) + (1.0,)


# Farben aus DESIGN.md / atlas.css
GROUND = lin("#f1f2ee")
SURFACE = lin("#fafbf8")
INK = lin("#13212a")
NEUTRAL = lin(META["geb_nd"])   # Gebäude vor der Auswertung: Grau wie „nicht datiert“ (GEB_ND, jahre.js)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE"
sc.render.resolution_x, sc.render.resolution_y = Z.W, Z.H
sc.render.resolution_percentage = args.pct
sc.render.fps = FPS
sc.eevee.taa_render_samples = args.samples
for k, v in (("use_raytracing", False), ("shadow_resolution_scale", 1.0), ("use_shadows", True)):
    try:
        setattr(sc.eevee, k, v)
    except Exception:
        pass
sc.view_settings.view_transform = "Standard"
sc.view_settings.look = "None"
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGB"
sc.frame_start, sc.frame_end = 0, Z.N - 1

world = bpy.data.worlds.new("Welt")
sc.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (1.0, 1.0, 1.0, 1.0)
bg.inputs[1].default_value = 0.15
EMIT = 0.35            # Eigenleuchten: Flächen zeigen oben fast ihre Legendenfarbe
WERTE = {}


def wert(nt, name):
    n = nt.nodes.new("ShaderNodeValue")
    n.label = name
    WERTE.setdefault(name, []).append(n)
    return n.outputs[0]


def attr(nt, name):
    n = nt.nodes.new("ShaderNodeAttribute")
    n.attribute_name = name
    n.attribute_type = "GEOMETRY"
    return n


def mth(nt, op, a, b=None, clamp=False):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    n.use_clamp = clamp
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def mix(nt, fac, a, b):
    n = nt.nodes.new("ShaderNodeMix")
    n.data_type = "RGBA"
    for sock, v in ((n.inputs[0], fac), (n.inputs[6], a), (n.inputs[7], b)):
        if isinstance(v, (int, float, tuple)):
            sock.default_value = v
        else:
            nt.links.new(v, sock)
    return n.outputs[2]


def schattierung(nt, farbe, alpha=None):
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    dif = nt.nodes.new("ShaderNodeBsdfDiffuse")
    dif.inputs["Roughness"].default_value = 1.0
    nt.links.new(farbe, dif.inputs["Color"])
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(farbe, em.inputs["Color"])
    em.inputs["Strength"].default_value = EMIT
    add = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(dif.outputs[0], add.inputs[0])
    nt.links.new(em.outputs[0], add.inputs[1])
    sh = add.outputs[0]
    if alpha is not None:
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        ms = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(alpha, ms.inputs[0])
        nt.links.new(tr.outputs[0], ms.inputs[1])
        nt.links.new(sh, ms.inputs[2])
        sh = ms.outputs[0]
    nt.links.new(sh, out.inputs[0])


def material(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes.clear()
    try:
        m.surface_render_method = "DITHERED"
    except Exception:
        pass
    return m, m.node_tree


def mat_grund():
    m, nt = material("Grund")
    rgb = nt.nodes.new("ShaderNodeRGB")
    rgb.outputs[0].default_value = GROUND
    schattierung(nt, rgb.outputs[0])
    return m


def mat_gebaeude():
    m, nt = material("Gebaeude")
    F = wert(nt, "frame")
    t0 = attr(nt, "t0f").outputs["Fac"]
    tf = attr(nt, "tff").outputs["Fac"]
    aus = attr(nt, "aus").outputs["Fac"]
    kc = attr(nt, "kcol").outputs["Color"]
    neutral = mix(nt, aus, NEUTRAL, kc)                 # außerhalb: kcol ist dort der hellere Grauton
    x = mth(nt, "DIVIDE", mth(nt, "SUBTRACT", F, mth(nt, "ADD", t0, Z.GROW * FPS)), Z.NEU_FADE * FPS, clamp=True)
    c1 = mix(nt, x, INK, neutral)                       # „neu“: kurz dunkel, dann Grundfarbe
    y = mth(nt, "DIVIDE", mth(nt, "SUBTRACT", F, tf), Z.FARB_DAUER * FPS, clamp=True)
    y = mth(nt, "MULTIPLY", y, mth(nt, "SUBTRACT", 1.0, aus))
    c2 = mix(nt, y, c1, kc)                             # Auswertung: Bauzeit-Klasse
    schattierung(nt, c2)
    return m


def mat_zellen():
    m, nt = material("Zellen")
    F = wert(nt, "frame")
    tz = attr(nt, "tzf").outputs["Fac"]
    st = attr(nt, "struktur").outputs["Fac"]
    kc = attr(nt, "kcol").outputs["Color"]
    a = mth(nt, "DIVIDE", mth(nt, "SUBTRACT", F, tz), Z.ZELL_IN * FPS, clamp=True)
    a = mth(nt, "MULTIPLY", a, wert(nt, "zell_sicht"))
    puls = mth(nt, "MULTIPLY", wert(nt, "puls"), st)
    c = mix(nt, mth(nt, "MULTIPLY", puls, 0.75), kc, SURFACE)
    c = mix(nt, wert(nt, "zell_mix"), GROUND, c)
    schattierung(nt, c, a)
    return m


def mat_nutzung():
    m, nt = material("Nutzung")
    F = wert(nt, "frame")
    t0 = attr(nt, "t0f").outputs["Fac"]
    kc = attr(nt, "kcol").outputs["Color"]
    a = mth(nt, "DIVIDE", mth(nt, "SUBTRACT", F, t0), 0.4 * FPS, clamp=True)
    schattierung(nt, kc, a)
    return m


def gn_wachsen():
    """z = z * Wachstum(Frame - t0f); vor dem Start unter den Boden."""
    ng = bpy.data.node_groups.new("Wachsen", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    n = ng.nodes
    gi, go = n.new("NodeGroupInput"), n.new("NodeGroupOutput")
    st = n.new("GeometryNodeInputSceneTime")
    na = n.new("GeometryNodeInputNamedAttribute")
    na.data_type = "FLOAT"
    na.inputs["Name"].default_value = "t0f"
    pos = n.new("GeometryNodeInputPosition")
    sep = n.new("ShaderNodeSeparateXYZ")
    ng.links.new(pos.outputs[0], sep.inputs[0])

    def m(op, a, b=None, clamp=False):
        x = n.new("ShaderNodeMath")
        x.operation = op
        x.use_clamp = clamp
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                x.inputs[i].default_value = v
            else:
                ng.links.new(v, x.inputs[i])
        return x.outputs[0]
    d = m("SUBTRACT", st.outputs["Frame"], na.outputs["Attribute"])
    g = m("DIVIDE", d, float(Z.GROW * FPS), clamp=True)
    e = m("MULTIPLY", m("MULTIPLY", g, g), m("SUBTRACT", 3.0, m("MULTIPLY", g, 2.0)))
    an = m("GREATER_THAN", d, 0.0)
    z = m("ADD", m("MULTIPLY", sep.outputs[2], e), m("MULTIPLY", m("SUBTRACT", 1.0, an), -50.0))
    comb = n.new("ShaderNodeCombineXYZ")
    ng.links.new(sep.outputs[0], comb.inputs[0])
    ng.links.new(sep.outputs[1], comb.inputs[1])
    ng.links.new(z, comb.inputs[2])
    sp = n.new("GeometryNodeSetPosition")
    ng.links.new(gi.outputs[0], sp.inputs["Geometry"])
    ng.links.new(comb.outputs[0], sp.inputs["Position"])
    ng.links.new(sp.outputs[0], go.inputs[0])
    return ng


def mesh_aus(name, v, t, mat, attrs, z=0.0):
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(v))
    me.vertices.foreach_set("co", v.astype(np.float32).ravel())
    me.loops.add(t.size)
    me.loops.foreach_set("vertex_index", t.astype(np.int32).ravel())
    me.polygons.add(len(t))
    me.polygons.foreach_set("loop_start", np.arange(0, t.size, 3, dtype=np.int32))
    me.update(calc_edges=True)
    for an, (typ, data) in attrs.items():
        a = me.attributes.new(an, typ, "POINT")
        if typ == "FLOAT_COLOR":
            rgba = np.ones((len(data), 4), np.float32)
            c = data.astype(np.float32)
            rgba[:, :3] = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)  # sRGB -> linear
            a.data.foreach_set("color", rgba.ravel())
        else:
            a.data.foreach_set("value", data.astype(np.float32))
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    ob.location.z = z
    sc.collection.objects.link(ob)
    return ob


t_bau = time.time()
P = args.prep
# Grund
gv = np.array([(-2e5, -2e5, 0), (2e5, -2e5, 0), (2e5, 2e5, 0), (-2e5, 2e5, 0)], np.float32)
mesh_aus("Grund", gv, np.array([(0, 1, 2), (0, 2, 3)]), mat_grund(), {})

# Nutzung (Kachel 2 km, zeilenweise wie die Pipeline)
d = np.load(os.path.join(P, "nutzung.npz"))
a, b = Z.P["alkis_nutzung"]
nk = META["kachel_nutz"][1] * META["kachel_nutz"][2]
t0f = (a + d["t0"] / nk * (b - a - 0.4)) * FPS
mesh_aus("Nutzung", d["v"], d["t"], mat_nutzung(), {"t0f": ("FLOAT", t0f), "kcol": ("FLOAT_COLOR", d["kcol"])}, z=0.6)

# Zellen
d = np.load(os.path.join(P, "zellen.npz"))
a, b = Z.P["zensus_gitter"]
tzf = (a + d["tz"] * (b - a - Z.ZELL_IN)) * FPS
ob_z = mesh_aus("Zellen", d["v"], d["t"], mat_zellen(), {"tzf": ("FLOAT", tzf), "kcol": ("FLOAT_COLOR", d["kcol"]),
                                                          "struktur": ("FLOAT", d["struktur"])}, z=0.3)

# Gebäude (Kachel 1 km, zeilenweise; Takt je Kachel schematisch gleich lang)
d = np.load(os.path.join(P, "gebaeude.npz"))
a, b = Z.P["gebaeude_alkis"]
ng = META["kachel_geb"][1] * META["kachel_geb"][2]
t0f = (a + d["t0"] / ng * (b - a - Z.GROW - 0.2)) * FPS
nst = len(META["stadtteile"])
tff = np.where(d["nr"] >= 0, (Z.AW0 + 0.2 + d["nr"] / nst * (Z.AW1 - Z.AW0 - Z.FARB_DAUER - 0.6)) * FPS, 1e9)
ob_g = mesh_aus("Gebaeude", d["v"], d["t"], mat_gebaeude(), {"t0f": ("FLOAT", t0f), "tff": ("FLOAT", tff),
                                                              "aus": ("FLOAT", d["aus"]),
                                                              "kcol": ("FLOAT_COLOR", d["kcol"])})
mod = ob_g.modifiers.new("Wachsen", "NODES")
mod.node_group = gn_wachsen()
d = None
print("Szene gebaut", round(time.time() - t_bau, 1), "s", flush=True)

# Kamera
cd = bpy.data.cameras.new("Kamera")
cd.type = "PERSP"
cd.lens = Z.LENS
cd.sensor_fit = "HORIZONTAL"
cd.sensor_width = Z.SENSOR
cd.shift_x = Z.SHIFT_X
cd.clip_start = 1000.0  # Kamera ist immer über 2 km hoch; ein kleiner clip_start ließ die Ebenen (0 / 0,3 / 0,6 / 0,9 m)
#                         in der Tiefe zusammenfallen (z-fighting: graue Keile über Wald und Feld, etwa 29 bis 30,5 s)
cd.clip_end = 150000.0
cam = bpy.data.objects.new("Kamera", cd)
sc.collection.objects.link(cam)
sc.camera = cam

ld = bpy.data.lights.new("Sonne", "SUN")
ld.angle = math.radians(0.6)
try:
    ld.use_shadow = True
except Exception:
    pass
sun = bpy.data.objects.new("Sonne", ld)
sc.collection.objects.link(sun)


def setze(t):
    pos, (r, u, f), D, tilt = Z.kamera(t)
    M = Matrix((r, u, (-f[0], -f[1], -f[2]))).transposed()
    cam.matrix_world = Matrix.Translation(Vector(pos)) @ M.to_4x4()
    elev, saz, _ = Z.sonne(t)
    e, a_ = math.radians(elev), math.radians(saz)
    von = Vector((math.sin(a_) * math.cos(e), math.cos(a_) * math.cos(e), math.sin(e)))
    sun.rotation_euler = (-von).to_track_quat("-Z", "Y").to_euler()
    ld.energy = 0.5 * math.pi / math.sin(e)   # waagerechte Fläche im Licht: halbe Albedo aus der Sonne
    for n in WERTE.get("frame", []):
        n.outputs[0].default_value = t * FPS
    for n in WERTE.get("zell_mix", []):
        n.outputs[0].default_value = Z.zell_mix(t)
    for n in WERTE.get("zell_sicht", []):
        n.outputs[0].default_value = Z.zell_sicht(t)
    for n in WERTE.get("puls", []):
        n.outputs[0].default_value = Z.struktur_puls(t)
    ob_z.location.z = Z.zell_hoch(t)


def render(frame, pfad):
    t = frame / FPS
    sc.frame_set(frame)
    setze(t)
    sc.render.filepath = pfad
    bpy.ops.render.render(write_still=True)


os.makedirs(args.aus, exist_ok=True)
t_start = time.time()
if args.zeiten:
    for s in args.zeiten.split(","):
        fr = int(round(float(s) * FPS))
        render(fr, os.path.join(args.aus, "b_%04d.png" % fr))
        print("FERTIG", s, round(time.time() - t_start, 1), flush=True)
else:
    for fr in range(args.von, min(args.bis, Z.N - 1) + 1):
        pf = os.path.join(args.aus, "b_%04d.png" % fr)
        if os.path.exists(pf):
            continue
        render(fr, pf)
        if fr % 30 == 0:
            print("FRAME", fr, round(time.time() - t_start, 1), flush=True)
print("GESAMT", round(time.time() - t_start, 1))
