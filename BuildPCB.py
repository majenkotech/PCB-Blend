import bpy
import csv
import sys
import os

file_root       = "/home/matt/Dropbox/Projects/Marek/Mainboard/Gerber/"
file_name       = "Mainboard"
offset_x = 10
offset_y = 40
file_outline    = file_root + file_name + ".outline.svg"
file_drill      = file_root + file_name + ".plated-drill.cnc"
file_csv        = file_root + file_name + ".xy"
file_components = "/home/matt/Dropbox/gEDA/Models/components.blend"
component_root = "/home/matt/Dropbox/gEDA/Models/components"

rotations = {
    "U7" : 360,
    "CONN1" : 90,
    "CONN2" : 270,
    "CONN5" : 270
}

txt = bpy.data.texts.get("BuildReport.txt")
if not txt:
    txt = bpy.data.texts.new("BuildReport.txt")
txt.clear()


def subtract(target, opObj):
   bpy.ops.object.select_all(action='DESELECT')
   target.select = True
   bpy.context.scene.objects.active = target
   bpy.ops.object.modifier_add(type='BOOLEAN')
   mod = target.modifiers.new("Drill", type='BOOLEAN')
   mod.operation = 'DIFFERENCE'
   mod.object = opObj
   bpy.context.scene.update()
   target.data = target.to_mesh(bpy.context.scene, True, 'PREVIEW')
   target.modifiers.remove(mod)

gotPCB = False
try:
    pcb = bpy.data.objects.get("PCB")
    if pcb:
        gotPCB = True
except:
    pass

if not gotPCB:
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.import_curve.svg(filepath = file_outline)
    newcurves = [c for c in bpy.context.scene.objects if not c.select]
    bpy.ops.object.select_all(action='DESELECT')
    for c in newcurves:
        c.select = True
    bpy.context.scene.objects.active = newcurves[0]
    bpy.ops.object.join()
    curve = bpy.context.object
    curve.scale = [36, 36, 1]
    bpy.ops.object.convert(target='MESH')
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.01)
    bpy.ops.mesh.extrude_edges_move(
        MESH_OT_extrude_edges_indiv={
            "mirror": False
        },
        TRANSFORM_OT_translate={
            "value": (0, 0, 1.6),
            "constraint_axis": (False, False, True),
            "constraint_orientation": 'GLOBAL',
            "mirror": False,
            "proportional": 'DISABLED',
            "proportional_edit_falloff": 'SMOOTH',
            "proportional_size": 1,
            "snap": False,
            "snap_target": 'CLOSEST',
            "snap_point": (0, 0, 0),
            "snap_align": False,
            "snap_normal": (0, 0, 0),
            "gpencil_strokes": False,
            "texture_space": False,
            "remove_on_cancel": False,
            "release_confirm": False
        }
    )
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.edge_face_add()
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
    pcb = bpy.context.object
    pcb.name = 'PCB'
    pcb.location = [offset_x, offset_y, -1.6]
    with open(file_drill, newline='', encoding='ISO-8859-15') as f:
        content = f.read().splitlines()
    drills = {}
    inHeader = True
    drillWidth = 0
    bits = []
    nbits = 0
    for line in content:
        if line == '%':
            inHeader = False
            continue
        if inHeader:
            if line.startswith('T'):
                parts = line.split('C')
                drills[parts[0]] = float(parts[1])
        else:
            if line.startswith('T'):
                drillWidth = drills[line]
                continue
            if line.startswith('X'):
                nbits = nbits + 1
                coords = line[1:].split('Y')
                x = float(coords[0])
                y = float(coords[1])
                x = x / 1000
                y = y / 1000
                bpy.ops.mesh.primitive_cylinder_add()
                newbit = bpy.context.object
                newbit.name="Drill Bit." + str(nbits)
                newbit.dimensions=[drillWidth,drillWidth,50]
                bits.append(newbit)
                newbit.location=[x, y, 0]
    bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
    bpy.ops.object.select_all(action='DESELECT')
    for abit in bits:
        abit.select = True
    bpy.context.scene.objects.active = bits[0]
    bpy.ops.object.join()
    allbits = bpy.context.object
    subtract(pcb, allbits)
    bpy.ops.object.select_all(action='DESELECT')
    allbits.select = True
    bpy.ops.object.delete()
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.scene.objects.active = pcb
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project()
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

# Populate with components

with open(file_csv, newline='', encoding='ISO-8859-15') as fobj:
    reader = csv.reader(filter(lambda row: row[0] != '#', fobj))
    layout_table = list(reader)

required = list(col[1] for col in layout_table)

compfiles = []
for compfile in os.listdir(component_root):
    if compfile.lower().endswith('.blend'):
        compfiles.append(component_root + os.sep + compfile)

for compfile in compfiles:
    txt.write("Loading models from " + compfile + "\n")
    with bpy.data.libraries.load(compfile, link=True) as (data_from, data_to):
        found = [value for value in data_from.meshes if value in required]
        for f in found:
            txt.write("    Found: " + f + "\n")
        data_to.meshes = found
        required = [value for value in required if value not in data_from.meshes]
        
txt.write("\nMissing components:\n")
for missing in required:
    txt.write("    " + missing + "\n")
        
objects_data  = bpy.data.objects
objects_scene = bpy.context.scene.objects

bpy.ops.object.select_all(action='DESELECT')

print("START")

for lib in bpy.data.libraries:
    lib.reload()
    
for mesh in bpy.data.meshes:
    print(mesh)

for id, name, value, x, y, rot, side in layout_table:
    z = 0
    yrot = 0
    if side == "bottom":
        z = -1.6
        yrot = 180 / 57.2957795
    loc = tuple(float(val) for val in (x, y, z))
    frot = float(rot)
    try:
        if rotations[id]:
            frot = rotations[id]
    except:
        pass
    frot = frot / 57.2957795
    zrot = tuple(float(val) for val in (0, yrot, frot))

    oname = id + " - " + name
    for ob in bpy.data.objects:
        if ob.name.startswith(id + " - "):
            ob.select = True
            bpy.ops.object.delete()
            
    mesh = bpy.data.meshes.get(name)
    dupli = objects_data.new(oname, mesh)
    dupli.location = loc
    dupli.rotation_euler = zrot
    objects_scene.link(dupli)

