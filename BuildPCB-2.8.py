import bpy
import csv
import sys
import os
from mathutils import Vector, Matrix, Quaternion


# Location where all your converted files are stored
file_root       = "/home/matt/Dropbox/Projects/Marek/Mainboard/Gerber/"

# Base name of the files
file_name       = "Mainboard"

# Colour you want for the mask: blue, red, green, purple, black, white, yellow, bare
color           = "blue"

# Finish for the board: hasl, enig, bare
finish          = "hasl"

# Lower left coordinate of the board in PCB
offset_x        = 9.94
offset_y        = 40.1

# Location where all the component library files are stored
component_root = "/home/matt/Dropbox/gEDA/Models/components"

# List of manual rotations in the form of {"refdes": angle, "refdes": angle...}
rotations = {
}




file_outline    = file_root + file_name + ".outline.svg"
file_drill      = file_root + file_name + ".plated-drill.cnc"
file_csv        = file_root + file_name + ".xy"


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

drillsDone = []

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
        ob.select_set(True)
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
outline = [c for c in bpy.context.scene.objects if not c.select_get()]


deselectAll()
for c in outline:
    c.select_set(True)

bpy.context.view_layer.objects.active = outline[0]
bpy.ops.object.join()

outlineCurve = bpy.context.object
outlineCurve.location = [offset_x, offset_y, -0.8]

def vabs(v):
    return (abs(v[0]), abs(v[1]), abs(v[2]))

setMode('EDIT')

while (len(outlineCurve.data.splines) > 1):    
    print("Splines:")
    print (len(outlineCurve.data.splines))
    print("Lengths:")
    for s in outlineCurve.data.splines:
        print(len(s.bezier_points))
        
    for s in outlineCurve.data.splines:
        for p in s.bezier_points:
            p.select_control_point = False
    basecurve = outlineCurve.data.splines[0]     
    end = basecurve.bezier_points[len(basecurve.bezier_points)-1]
    
    done = False
    for i in range(1, len(outlineCurve.data.splines)):
        for p in outlineCurve.data.splines[i].bezier_points:
            d = vabs(p.co - end.co)
            if (d < (0.01, 0.01, 0.01)):
                print("Matched spline number " + str(i))
                print(end.co)
                print(p.co)
                end.select_control_point = True
                p.select_control_point = True    
                bpy.ops.curve.make_segment()
                done = True
                break
            if done:
                break
        if done:
            break

    if (done == False):
        break

for s in outlineCurve.data.splines:
    for p in s.bezier_points:
        p.select_control_point = False

basecurve = outlineCurve.data.splines[0]     
start = basecurve.bezier_points[0]
end = basecurve.bezier_points[len(basecurve.bezier_points)-1]

start.select_control_point = True
end.select_control_point = True
bpy.ops.curve.make_segment()

setMode("OBJECT")


selectAll()

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
            pos = Vector((x, y, 0))
            if (pos not in drillsDone):
                drillsDone.append(pos)
                bpy.ops.curve.primitive_bezier_circle_add(radius = drillWidth / 2, location = (x, y, -0.8))
                bpy.context.active_object.select_set(False)

holes = [c for c in bpy.context.scene.objects if not c.select_get()]

deselectAll()

for c in holes:
    c.select_set(True)
bpy.context.view_layer.objects.active = outlineCurve
bpy.ops.object.join()


outlineCurve.data.extrude = 0.8

outlineCurve.data.dimensions = "2D"
outlineCurve.data.fill_mode = 'BOTH'

bpy.ops.object.convert(target='MESH')

bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
pcb = bpy.context.object
pcb.name = 'PCB'


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
bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
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
            ob.select_set(True)
            bpy.ops.object.delete()
            
    mesh = bpy.data.meshes.get(name)
    dupli = objects_data.new(oname, mesh)
    dupli.location = loc
    dupli.rotation_euler = zrot
    bpy.context.scene.collection.objects.link(dupli)
    objects.append(oname)


bpy.ops.object.select_all(action='DESELECT')
    
for ob in objects:
    bpy.data.objects[ob].select_set(True)

bpy.data.objects['PCB'].select_set(True)


bpy.context.view_layer.objects.active = bpy.data.objects['PCB']
bpy.ops.object.join()
bpy.context.view_layer.objects.active = bpy.data.objects['PCB']
bpy.context.object.data.name = file_name
bpy.context.object.name = file_name

bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS')

for m in bpy.data.materials:
    if (m.users == 0):
        bpy.data.materials.remove(m)

print("END")




