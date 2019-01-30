import bpy
import csv
import sys
import os
from mathutils import Vector, Matrix, Quaternion
import time


# Useful colours

# Finishes
hasl = (0.6, 0.6, 0.6, 1.0)
enig = (0.865, 0.524, 0.0, 1.0)

# Silk colours
white = (1.0, 1.0, 1.0, 1.0)
black = (0.0, 0.0, 0.0, 1.0)

# Mask colours
red = (0.55, 0.0, 0.0, 1.0)
green = (0.0, 0.25, 0.0, 1.0)
blue = (0.0, 0.195, 0.828, 1.0)
purple = (0.174, 0.0, 0.574, 1.0)
yellow = (0.814, 0.429, 0.0, 1.0)
# black - use silk colour
# white - use silk colour


class PCBImport(bpy.types.Operator):

    # Location where all your converted files are stored
    file_root       = "/home/matt/Dropbox/Projects/Marek/MPC1000/Gerber/"

    # Base name of the files
    file_name       = "MPC1000"

    # Colour you want for the mask: blue, red, green, purple, black, white, yellow
    color           = blue

    # Finish for the board: hasl, enig
    finish          = hasl

    # Silk screen colour: black, white
    silk            = white

    # Lower left coordinate of the board in PCB
    offset_x        = 45
    offset_y        = 79.1

    # Location where all the component library files are stored
    component_root = "/home/matt/Dropbox/gEDA/Models/components"

    # Whether or not to join everything into one single object
    doJoin = True

    # List of manual rotations in the form of {"refdes": angle, "refdes": angle...}
    rotations = {
    }




    bl_label = "Import gEDA PCB Models"
    bl_idname = "wm.modal_timer_operator"
    bl_options = {'BLOCKING'}

    file_outline    = file_root + file_name + ".outline.svg"
    file_drill      = file_root + file_name + ".plated-drill.cnc"
    file_csv        = file_root + file_name + ".xy"



    txt = None    
    outlineCurve = None
    pcb = None


    def NormalInDirection(self, normal, direction, limit = 0.5 ):
        return direction.dot( normal ) > limit

    def GoingUp(self, normal, limit = 0.5 ):
        return self.NormalInDirection( normal, Vector( (0, 0, 1 ) ), limit )

    def GoingDown(self, normal, limit = 0.5 ):
        return self.NormalInDirection( normal, Vector( (0, 0, -1 ) ), limit )

    def GoingLeft(self, normal, limit = 0.5 ):
        return self.NormalInDirection( normal, Vector( (-1, 0, 0) ), limit)

    def GoingRight(self, normal, limit = 0.5 ):
        return self.NormalInDirection( normal, Vector( (1, 0, 0) ), limit)

    def GoingFore(self, normal, limit = 0.5 ):
        return self.NormalInDirection( normal, Vector( (0, 1, 0) ), limit)

    def GoingBack(self, normal, limit = 0.5 ):
        return self.NormalInDirection( normal, Vector( (0, -1, 0) ), limit)

    def GoingSide(self, normal, limit = 0.5 ):
        return self.GoingUp( normal, limit ) == False and self.GoingDown( normal, limit ) == False

    def setViewOrientation(self,vec, angle = 0):
        for win in bpy.data.window_managers[0].windows:
            for a in win.screen.areas:
                if (a.type == "VIEW_3D"):
                    for s in a.spaces:
                        if (s.type == "VIEW_3D"):
                            view = s
                            s.region_3d.view_rotation = Quaternion(vec, angle)

    def projectFromView(self):
        print("Project from view")
        for oWindow in bpy.context.window_manager.windows:
            oScreen = oWindow.screen
            for oArea in oScreen.areas:
                print ("Area type: " + oArea.type)
                if oArea.type == 'VIEW_3D':  
                    for oRegion in oArea.regions:
                        if oRegion.type == 'WINDOW':
                            self.setMode('EDIT')
                            override = {'window': oWindow, 'screen': oScreen, 'area': oArea, 'region': oRegion, 'scene': bpy.context.scene, 'edit_object': bpy.context.edit_object, 'active_object': bpy.context.active_object, 'selected_objects': bpy.context.selected_objects}
                            bpy.ops.uv.project_from_view(override , camera_bounds=False, correct_aspect=False, scale_to_bounds=True)



    def clearMeshSelections(self):
        self.setMode('EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        self.setMode('OBJECT')

    def meshSelectAll(self):
        self.setMode('EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        self.setMode('OBJECT')

    def setMode(self, newmode):
        bpy.ops.object.mode_set(mode=newmode, toggle=False)

    def deselectAll(self):
        bpy.ops.object.select_all(action='DESELECT')
        
    def selectAll(self):
        bpy.ops.object.select_all(action='SELECT')


    def openBuildReport(self):
        self.txt = bpy.data.texts.get("BuildReport.txt")
        if not self.txt:
            self.txt = bpy.data.texts.new("BuildReport.txt")
        self.txt.clear()

    def deleteExistingBoard(self):
        self.deselectAll()
        for ob in bpy.data.objects:
            if ob.name == self.file_name:
                self.setSelect(ob, True)
                bpy.ops.object.delete()
        self.deselectAll()        

    def deleteOrphans(self):           
        self.deselectAll()
        for m in bpy.data.materials:
            if (m.users == 0):
                bpy.data.materials.remove(m)

        for m in bpy.data.meshes:
            if (m.users == 0):
                bpy.data.meshes.remove(m)

        for m in bpy.data.images:
            if (m.users == 0):
                bpy.data.images.remove(m)

    def vabs(self, v):
        return (abs(v[0]), abs(v[1]), abs(v[2]))


    ############################
    # Version abstraction routines
    def version(self):
        return bpy.data.version[0] + (bpy.data.version[1]/100)    

    def setSelect(self, object, state):
        if self.version() < 2.80:
            object.select = state
        else:
            object.select_set(state)
            
    def getSelect(self, object):
        if self.version() < 2.80:
            return object.select
        else:
            return object.select_get()

    def setActiveObject(self, object):
        if self.version() < 2.80:
            bpy.context.scene.objects.active = object
        else:
            bpy.context.view_layer.objects.active = object
            
    def linkObject(self, object):
        if self.version() < 2.80:
            bpy.context.scene.objects.link(object)
        else:
            bpy.context.scene.collection.objects.link(object)

    #
    #########################################
    
    def matchingVertices(self, f1, f2):
        count = 0
        for v1 in f1.vertices:
            for v2 in f2.vertices:
                if v1 == v2:
                    count += 1
        return count
        
    def selectOuterFaces(self, object):
        faces = object.data.polygons

        for f in faces:
            f.select = False
            
        sideFaces = [f for f in faces if self.GoingSide(f.normal)]

        maxObject = None
        maxArea = 0

        linkedFaces = []
        for f in sideFaces:
            if (len(f.vertices) == 4):
                if f.area > maxArea:
                    maxArea = f.area
                    maxObject = f

        sideFaces.remove(maxObject)
        linkedFaces.append(maxObject)

        while True:
            print("-----------------------------------")
            foundsome = False
            foundFaces = []
            for testface in linkedFaces:
                for face in sideFaces:
                    if len(face.vertices) == 4:
                        mv = self.matchingVertices(testface, face)
                        if (mv == 2):
                            print("(" + str(testface.vertices[0]) + ", " + str(testface.vertices[1]) + ", " + str(testface.vertices[2]) + ", " + str(testface.vertices[3]) + ")")
                            print("(" + str(face.vertices[0]) + ", " + str(face.vertices[1]) + ", " + str(face.vertices[2]) + ", " + str(face.vertices[3]) + ")")
                            print(mv)
                            print("")
                            if face not in foundFaces:
                                foundFaces.append(face)
                            foundsome = True
            for face in foundFaces:
                sideFaces.remove(face)
                linkedFaces.append(face)
            if not foundsome:
                break

        for f in linkedFaces:
            f.select = True
            

    def importOutline(self):
        self.selectAll()
        bpy.ops.import_curve.svg(filepath = self.file_outline)
        outline = [c for c in bpy.context.scene.objects if not self.getSelect(c)]

        self.deselectAll()
        for c in outline:
            self.setSelect(c, True)

        self.setActiveObject(outline[0])
        bpy.ops.object.join()

        self.outlineCurve = bpy.context.object
        self.outlineCurve.location = [self.offset_x, self.offset_y, -0.8]

        self.setMode('EDIT')

        while (len(self.outlineCurve.data.splines) > 1):                
            for s in self.outlineCurve.data.splines:
                for p in s.bezier_points:
                    p.select_control_point = False
            basecurve = self.outlineCurve.data.splines[0]     
            end = basecurve.bezier_points[len(basecurve.bezier_points)-1]
            
            done = False
            for i in range(1, len(self.outlineCurve.data.splines)):
                for p in self.outlineCurve.data.splines[i].bezier_points:
                    d = self.vabs(p.co - end.co)
                    if (d < (0.01, 0.01, 0.01)):
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

        for s in self.outlineCurve.data.splines:
            for p in s.bezier_points:
                p.select_control_point = False

        basecurve = self.outlineCurve.data.splines[0]     
        start = basecurve.bezier_points[0]
        end = basecurve.bezier_points[len(basecurve.bezier_points)-1]

        start.select_control_point = True
        end.select_control_point = True
        bpy.ops.curve.make_segment()

        self.setMode("OBJECT")

    def drillBoard(self):
        drillsDone = []
        self.selectAll()
        with open(self.file_drill, newline='', encoding='ISO-8859-15') as f:
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
                        self.setSelect(bpy.context.active_object, False)

        holes = [c for c in bpy.context.scene.objects if not self.getSelect(c)]

        self.deselectAll()

        for c in holes:
            self.setSelect(c, True)
        self.setActiveObject(self.outlineCurve)
        bpy.ops.object.join()


    def extrudeBoard(self):
        self.outlineCurve.data.extrude = 0.8
        self.outlineCurve.data.dimensions = "2D"
        self.outlineCurve.data.fill_mode = 'BOTH'

        bpy.ops.object.convert(target='MESH')
        
        self.meshSelectAll()
        self.setMode('EDIT')
        bpy.ops.mesh.remove_doubles(threshold = 0.01)

        self.setMode('OBJECT')
        self.pcb = bpy.context.object
        self.pcb.name = 'PCB'


    def loadMaterials(self):
        with bpy.data.libraries.load(self.component_root + "/materials.blend", link=True) as (data_from, data_to):
            data_to.materials = ["Metal", "PCB Texture", "PCB Substrate"]

        top = None
        try:
            top = bpy.data.materials['PCB Top']
        except:
            top = bpy.data.materials['PCB Texture'].copy();
            top.name = "PCB Top"

        btm = None
        try:
            btm = bpy.data.materials['PCB Bottom']
        except:
            btm = bpy.data.materials['PCB Texture'].copy();
            btm.name = "PCB Bottom"
            

        top.node_tree.nodes['copper'].image = bpy.data.images.load(filepath = self.file_root + "/" + self.file_name + ".top.png")
        top.node_tree.nodes['soldermask'].image = bpy.data.images.load(filepath = self.file_root + "/" + self.file_name + ".topmask.png")
        top.node_tree.nodes['silk'].image = bpy.data.images.load(filepath = self.file_root + "/" + self.file_name + ".topsilk.png")
        top.node_tree.nodes['pcbtexture'].inputs['Color'].default_value = self.color
        top.node_tree.nodes['pcbtexture'].inputs['Finish'].default_value = self.finish
        top.node_tree.nodes['pcbtexture'].inputs['Silk Color'].default_value = self.silk
        top.node_tree.nodes['mapping'].scale = (1, 1, 1)
        
        btm.node_tree.nodes['copper'].image = bpy.data.images.load(filepath = self.file_root + "/" + self.file_name + ".bottom.png")
        btm.node_tree.nodes['soldermask'].image = bpy.data.images.load(filepath = self.file_root + "/" + self.file_name + ".bottommask.png")
        btm.node_tree.nodes['silk'].image = bpy.data.images.load(filepath = self.file_root + "/" + self.file_name + ".bottomsilk.png")
        btm.node_tree.nodes['pcbtexture'].inputs['Color'].default_value = self.color
        btm.node_tree.nodes['pcbtexture'].inputs['Finish'].default_value = self.finish
        btm.node_tree.nodes['pcbtexture'].inputs['Silk Color'].default_value = self.silk
        btm.node_tree.nodes['mapping'].scale = (1, -1, 1)
                    
        self.pcb.data.materials.append(bpy.data.materials['Metal'])
        self.pcb.data.materials.append(top)
        self.pcb.data.materials.append(btm)
        self.pcb.data.materials.append(bpy.data.materials['PCB Substrate'])
        bpy.data.materials.remove(bpy.data.materials['SVGMat'])

    def facesTouching(self, one, two):
        return False
        
    def faceArea(self, f):
        return f.area

    def assignMaterials(self):
        # Metal
        self.clearMeshSelections()
        self.setMode('OBJECT')
        for face in self.pcb.data.polygons:
            face.select = self.GoingSide(face.normal)        
        self.pcb.active_material_index = 0
        self.setMode('EDIT')
        bpy.ops.object.material_slot_assign()
        self.setMode('OBJECT')

        ## PCBTop
        self.clearMeshSelections()
        for face in self.pcb.data.polygons:
            face.select = self.GoingUp(face.normal)        
        self.pcb.active_material_index = 1
        self.setMode('EDIT')
        bpy.ops.object.material_slot_assign()
        self.setMode('OBJECT')

        # PCBBottom
        self.clearMeshSelections()
        for face in self.pcb.data.polygons:
            face.select = self.GoingDown(face.normal)        
        self.pcb.active_material_index = 2
        self.setMode('EDIT')
        bpy.ops.object.material_slot_assign()
        self.setMode('OBJECT')

        # PCB Substrate

        # This one is a little harder. First
        # select all the side faces.
        # Second work out which is the biggest - 
        # that's guaranteed to be an outside face.
        # Then repeatedly look through all the side
        # faces finding any that touch that first one.
        # Add them to an array, then repeat looking
        # for any faces that touch any in the array.
        
        self.selectOuterFaces(self.pcb)
        self.pcb.active_material_index = 3
        self.setMode('EDIT')
        bpy.ops.object.material_slot_assign()
        self.setMode('OBJECT')

    def selectTopView(self):
        self.clearMeshSelections()
        self.setMode('OBJECT')
        for face in self.pcb.data.polygons:
            face.select = self.GoingUp(face.normal)        
        self.setViewOrientation((0, 0, 1))

    def selectBottomView(self):
        self.clearMeshSelections()
        self.setMode('OBJECT')
        for face in self.pcb.data.polygons:
            face.select = self.GoingDown(face.normal)        
        self.setViewOrientation((1, 0, 0), 3.141592653)

    def populate(self):
        self.setMode('OBJECT')
        with open(self.file_csv, newline='', encoding='ISO-8859-15') as fobj:
            reader = csv.reader(filter(lambda row: row[0] != '#', fobj))
            layout_table = list(reader)

        required = list(col[1] for col in layout_table)

        compfiles = []
        for compfile in os.listdir(self.component_root):
            if compfile.lower().endswith('.blend'):
                compfiles.append(self.component_root + os.sep + compfile)

        for compfile in compfiles:
            self.txt.write("Loading models from " + compfile + "\n")
            with bpy.data.libraries.load(compfile, link=True) as (data_from, data_to):
                found = [value for value in data_from.meshes if value in required]
                for f in found:
                    self.txt.write("    Found: " + f + "\n")
                data_to.meshes = found
                required = [value for value in required if value not in data_from.meshes]
                
        self.txt.write("\nMissing components:\n")
        for missing in required:
            self.txt.write("    " + missing + "\n")
                
        objects_data  = bpy.data.objects
        objects_scene = bpy.context.scene.objects

        self.deselectAll()

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
                    self.setSelect(ob, True)
                    bpy.ops.object.delete()
                    
            mesh = bpy.data.meshes.get(name)
            dupli = objects_data.new(oname, mesh)
            dupli.location = loc
            dupli.rotation_euler = zrot
            self.linkObject(dupli)
            objects.append(oname)

        self.deselectAll()

        if self.doJoin:            
            for ob in objects:
                self.setSelect(bpy.data.objects[ob], True)

            self.setSelect(bpy.data.objects['PCB'], True)

            self.setActiveObject(bpy.data.objects['PCB'])
            bpy.ops.object.join()
            self.setActiveObject(bpy.data.objects['PCB'])
            bpy.context.object.data.name = self.file_name
            bpy.context.object.name = self.file_name

        bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS')


    ## Modal stuff

    _timer = None
    _tick = 0
    _phase = 0

    def modal(self, context, event):

        if event.type == 'TIMER':
            dir(event)
            self.stopTimer()

            now = int(time.time() * 1000)
            passed = now - self._tick
            self._tick = now
            
            print(str(self._phase) + ": " + str(passed))
            
            if (passed < 1000):
                # Strange extra ticks
                self.startTimer()
                return {'PASS_THROUGH'}
            
            
            if (self._phase == 0):
                print("START")
                self.openBuildReport()
                self.deleteExistingBoard()
                self.deleteOrphans()
                self.importOutline()
                self.drillBoard()
                self.extrudeBoard()
                self.loadMaterials()
                self.assignMaterials()
                self.selectTopView()
                self._phase+=1
                self.startTimer()
                return {'PASS_THROUGH'}
#                return {'FINISHED'}
            if (self._phase == 1):
                self.projectFromView()
                self.selectBottomView()
                self._phase+=1
                self.startTimer()
                return {'PASS_THROUGH'}

            if (self._phase == 2):
                self.projectFromView()
                self.populate()
                self.deleteOrphans()
                self.setViewOrientation((1, 1, 1), 0.2)
                print("END")
                return {'FINISHED'}

        return {'PASS_THROUGH'}

    wm = None
    context = None
    def startTimer(self):
        self._timer = self.wm.event_timer_add(1, window=self.context.window)
        
    def stopTimer(self):
        self.wm.event_timer_remove(self._timer)

    def execute(self, context):
        self._tick = int(time.time() * 1000) - self._tick

        print("Starting...")
        self.wm = context.window_manager
        self.context = context
        self.startTimer()
        self.wm.modal_handler_add(self)
        self._phase = 0
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        self.stopTimer()


def register():
    bpy.utils.register_class(PCBImport)
    print("Registered modal")
    bpy.ops.wm.modal_timer_operator()


def unregister():
    bpy.utils.unregister_class(PCBImport)
    print("Unregistered modal")


if __name__ == "__main__":
    register()

