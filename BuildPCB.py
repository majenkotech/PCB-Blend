import bpy
import csv
import sys
import os
from mathutils import Vector, Matrix, Quaternion


file_root       = "/home/matt/Dropbox/Projects/TFTDisplay/Gerber/"
file_name       = "TFTDisplay"
color           = "blue"
finish          = "hasl"

offset_x = 2.48
offset_y = 124.55
file_outline    = file_root + file_name + ".outline.svg"
file_drill      = file_root + file_name + ".plated-drill.cnc"
file_csv        = file_root + file_name + ".xy"
component_root = "/home/matt/Dropbox/gEDA/Models/components"

rotations = {
}

def NormalInDirection( normal, direction, limit = 0.5 ):
    return direction.dot( normal ) > limit

def GoingUp( normal, limit = 0.5 ):
    return NormalInDirection( normal, Vector( (0, 0, 1 ) ), limit )

def GoingDown( normal, limit = 0.5 ):
    return NormalInDirection( normal, Vector( (0, 0, -1 ) ), limit )

def GoingLeft( normal, limit = 0.5 ):
    return NormalInDirection( normal, Vector( (-1, 0, 0) ), limit)

def GoingRight( normal, limit = 0.5 ):
    return NormalInDirection( normal, Vector( (1, 0, 0) ), limit)

def GoingFore( normal, limit = 0.5 ):
    return NormalInDirection( normal, Vector( (0, 1, 0) ), limit)

def GoingBack( normal, limit = 0.5 ):
    return NormalInDirection( normal, Vector( (0, -1, 0) ), limit)

def GoingSide( normal, limit = 0.5 ):
    return GoingUp( normal, limit ) == False and GoingDown( normal, limit ) == False

def setViewOrientation(vec, angle = 0):
    for win in bpy.data.window_managers[0].windows:
        for a in win.screen.areas:
            if (a.type == "VIEW_3D"):
                for s in a.spaces:
                    if (s.type == "VIEW_3D"):
                        view = s
                        s.region_3d.view_rotation = Quaternion(vec, angle)


def projectFromView():
    for oWindow in bpy.context.window_manager.windows:
        oScreen = oWindow.screen
        for oArea in oScreen.areas:
            if oArea.type == 'VIEW_3D':  
                for oRegion in oArea.regions:
                    if oRegion.type == 'WINDOW':
                        override = {'window': oWindow, 'screen': oScreen, 'area': oArea, 'region': oRegion, 'scene': bpy.context.scene, 'edit_object': bpy.context.edit_object, 'active_object': bpy.context.active_object, 'selected_objects': bpy.context.selected_objects}
                        bpy.ops.uv.project_from_view(override , camera_bounds=False, correct_aspect=False, scale_to_bounds=True)

def drill(target, x, y, size):
    print("Drilling " + str(x) + "," + str(y) + " @ " + str(size) + "mm")
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=size/2, depth=10, location=(x, y, 0))
    newbit = bpy.context.object
    bpy.ops.object.select_all(action='DESELECT')
    target.select = True
    bpy.context.scene.objects.active = target
    bpy.ops.object.modifier_add(type='BOOLEAN')
    mod = target.modifiers.new("Drill", type='BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.object = newbit
    bpy.context.scene.update()
    target.data = target.to_mesh(bpy.context.scene, True, 'PREVIEW')
    target.modifiers.remove(mod)
    bpy.data.objects.remove(newbit)
#    bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

def clearMeshSelections():
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

def setMode(newmode):
    bpy.ops.object.mode_set(mode=newmode, toggle=False)

def deselectAll():
    bpy.ops.object.select_all(action='DESELECT')
    
def selectAll():
    bpy.ops.object.select_all(action='SELECT')

#---------------------------

txt = bpy.data.texts.get("BuildReport.txt")
if not txt:
    txt = bpy.data.texts.new("BuildReport.txt")
txt.clear()

print("START")

deselectAll()

for ob in bpy.data.objects:
    if ob.name == file_name:
        ob.select = True
        bpy.ops.object.delete()

deselectAll()        
       
bpy.ops.object.select_all(action='DESELECT') 
        
for m in bpy.data.materials:
    if (m.users == 0):
        bpy.data.materials.remove(m)

for m in bpy.data.meshes:
    if (m.users == 0):
        bpy.data.meshes.remove(m)

for m in bpy.data.images:
    if (m.users == 0):
        bpy.data.images.remove(m)


selectAll()
bpy.ops.import_curve.svg(filepath = file_outline)
newcurves = [c for c in bpy.context.scene.objects if not c.select]
deselectAll()
for c in newcurves:
    c.select = True
bpy.context.scene.objects.active = newcurves[0]
bpy.ops.object.join()
curve = bpy.context.object
bpy.ops.object.convert(target='MESH')
setMode('EDIT')
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

bpy.ops.mesh.normals_make_consistent(inside=False)

bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
pcb = bpy.context.object
pcb.name = 'PCB'
pcb.location = [offset_x, offset_y, -1.6]


with bpy.data.libraries.load(component_root + "/materials.blend", link=True) as (data_from, data_to):
    data_to.materials = ["Metal", "Image Textured Surface", "PCB Substrate"]

top = None
try:
    top = bpy.data.materials['PCB Top']
except:
    top = bpy.data.materials['Image Textured Surface'].copy();
    top.name = "PCB Top"

btm = None
try:
    btm = bpy.data.materials['PCB Bottom']
except:
    btm = bpy.data.materials['Image Textured Surface'].copy();
    btm.name = "PCB Bottom"
    

top.node_tree.nodes['imagemap'].image = bpy.data.images.load(filepath = file_root + "/" + file_name + ".top-" + color + "-" + finish + ".png")
top.node_tree.nodes['bumpmap'].image = bpy.data.images.load(filepath = file_root + "/" + file_name + ".topbump.png")
top.node_tree.nodes['mirrormap'].image = bpy.data.images.load(filepath = file_root + "/" + file_name + ".topmirror.png")
top.node_tree.nodes['translucentmap'].image = bpy.data.images.load(filepath = file_root + "/" + file_name + ".toptranslucency.png")

btm.node_tree.nodes['imagemap'].image = bpy.data.images.load(filepath = file_root + "/" + file_name + ".bottom-" + color + "-" + finish + ".png")
btm.node_tree.nodes['bumpmap'].image = bpy.data.images.load(filepath = file_root + "/" + file_name + ".bottombump.png")
btm.node_tree.nodes['mirrormap'].image = bpy.data.images.load(filepath = file_root + "/" + file_name + ".bottommirror.png")
btm.node_tree.nodes['translucentmap'].image = bpy.data.images.load(filepath = file_root + "/" + file_name + ".bottomtranslucency.png")
            
pcb.data.materials.append(bpy.data.materials['Metal'])
pcb.data.materials.append(top)
pcb.data.materials.append(btm)
pcb.data.materials.append(bpy.data.materials['PCB Substrate'])
bpy.data.materials.remove(bpy.data.materials['SVGMat'])



bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
for face in pcb.data.polygons:
    face.select = GoingSide(face.normal)        
pcb.active_material_index = 3
bpy.ops.object.mode_set(mode='EDIT', toggle=False)
bpy.ops.object.material_slot_assign()
bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

clearMeshSelections()


# Drill it


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
            drill(pcb, x, y, drillWidth)


clearMeshSelections()

for face in pcb.data.polygons:
    face.select = GoingUp(face.normal)        
pcb.active_material_index = 1

bpy.ops.object.mode_set(mode='EDIT', toggle=False)
bpy.ops.object.material_slot_assign()
setViewOrientation((0, 0, 1))
bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
projectFromView()
bpy.ops.object.mode_set(mode='OBJECT', toggle=False)



clearMeshSelections()

for face in pcb.data.polygons:
    face.select = GoingDown(face.normal)        
pcb.active_material_index = 2

bpy.ops.object.mode_set(mode='EDIT', toggle=False)
bpy.ops.object.material_slot_assign()
setViewOrientation((1, 0, 0), 3.141592653)
bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
projectFromView()
bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

setViewOrientation((1, 0, 0), -0.2991)
setViewOrientation((0, 1, 0), -0.0781)
setViewOrientation((0, 0, 1), -0.2403)


bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

bpy.ops.object.select_all(action='DESELECT')
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

objects = []

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
    objects.append(oname)


bpy.ops.object.select_all(action='DESELECT')
    
for ob in objects:
    bpy.data.objects[ob].select = True

bpy.data.objects['PCB'].select = True


bpy.context.scene.objects.active = bpy.data.objects['PCB']
bpy.ops.object.join()
bpy.context.scene.objects.active = bpy.data.objects['PCB']
bpy.context.object.data.name = file_name
bpy.context.object.name = file_name

bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS')

for m in bpy.data.materials:
    if (m.users == 0):
        bpy.data.materials.remove(m)

print("END")
