"""Reusable static workshop components with self-contained material bindings."""
from .common import Builder, fresh
from pxr import UsdGeom


def build():
    s = fresh("assets/workshop_kit.usda", "Kit")
    UsdGeom.Xform.Define(s, "/Kit")
    s.GetRootLayer().documentation = "Original procedural components. No physics, motion, textures or external assets."

    def component(name):
        r = "/Kit/" + name
        b = Builder(s, r+"/Looks")
        b.group(r).SetCustomDataByKey("staticSceneEvolution", True)
        return b, r

    b, r = component("AssemblyTable")
    b.box(r+"/Top",(0,0,1.02),(2.7,1.25,.14),"silver")
    for i,x in enumerate((-1.05,1.05)):
        for j,y in enumerate((-.44,.44)):
            b.box(r+f"/Leg{i}{j}",(x,y,.47),(.10,.10,.94),"graphite")
        b.box(r+f"/Foot{i}",(x,0,.06),(.30,1.12,.12),"graphite")
    b.box(r+"/Shelf",(0,0,.28),(2.3,.95,.08),"steel")
    for i in range(9):
        for j in range(4):
            b.cylinder(r+f"/Socket{i}_{j}",(-1.1+i*.275,-.4+j*.267,1.096),.024,.009,"graphite")
    for i,x in enumerate((-.8,.8)):
        b.box(r+f"/Clamp{i}",(x,-.35,1.16),(.32,.23,.12),"graphite")
        b.cylinder(r+f"/Screw{i}",(x,-.35,1.28),.035,.23,"silver")

    b, r = component("StockRack")
    for i,x in enumerate((-2.3,0,2.3)):
        b.box(r+f"/Upright{i}",(x,.35,1.65),(.16,.16,3.3),"graphite")
        b.box(r+f"/Foot{i}",(x,-.18,.08),(.36,1.6,.16),"steel")
        for j,z in enumerate((.55,1.35,2.15,2.95)):
            b.box(r+f"/Arm{i}_{j}",(x,-.20,z),(.14,1.2,.12),"silver")
            b.box(r+f"/Stop{i}_{j}",(x,-.77,z+.1),(.14,.08,.2),"graphite")
    for j,z in enumerate((.68,1.48,2.28)):
        for k in range(3):
            b.box(r+f"/Stock{j}_{k}",(0,-.58+k*.26,z),(5.2,.18,.12),"steel" if j%2 else "silver")
    b.beam(r+"/BackBraceA",(-2.3,.44,.2),(2.3,.44,3.2),.06,.06,"steel")
    b.beam(r+"/BackBraceB",(2.3,.44,.2),(-2.3,.44,3.2),.06,.06,"steel")

    b, r = component("MachineCell")
    b.box(r+"/Base",(0,0,.35),(3.3,2.3,.7),"graphite")
    b.box(r+"/Bed",(0,0,.78),(3.1,1.9,.16),"silver")
    for i,x in enumerate((-1.4,1.4)):
        b.box(r+f"/Column{i}",(x,.7,1.65),(.32,.44,2.5),"steel")
    b.box(r+"/Crosshead",(0,.7,2.85),(3.2,.52,.34),"silver")
    p=b.box(r+"/Motor",(-.6,.65,3.16),(.60,.5,.36),"orange")
    b.role(p,"Drive motor housing, parked")
    p=b.box(r+"/Carriage",(-.6,.30,2.35),(.7,.65,.65),"blue")
    b.role(p,"Dependent spindle slide, parked")
    b.cylinder(r+"/Spindle",(-.6,.1,1.88),.1,.45,"silver")
    b.box(r+"/Fixture",(0,0,.98),(1.8,1.2,.24),"blue")
    b.box(r+"/Blank",(.2,0,1.18),(1.1,.75,.16),"lightConcrete")
    b.box(r+"/PanelStand",(1.85,-.65,1.02),(.12,.12,2.04),"graphite")
    b.box(r+"/Panel",(1.85,-.65,1.72),(.55,.18,.6),"steel")
    b.box(r+"/Display",(1.85,-.75,1.8),(.44,.015,.31),"glass")
    b.label(r+"/ID","CNC",(-1.3,-1.16,.22),.25)

    b, r = component("MetrologyBed")
    b.box(r+"/Base",(0,0,.4),(2.5,4.3,.8),"lightConcrete")
    b.box(r+"/Granite",(0,0,.89),(2.6,4.4,.18),"graphite")
    for i,x in enumerate((-1.13,1.13)):
        b.box(r+f"/Rail{i}",(x,0,1.04),(.15,4.1,.13),"silver")
        b.box(r+f"/Leg{i}",(x,.35,1.8),(.25,.3,1.6),"steel")
    b.box(r+"/Bridge",(0,.35,2.58),(2.55,.4,.26),"silver")
    p=b.box(r+"/Servo",(1.33,.35,2.58),(.34,.5,.4),"orange")
    b.role(p,"Measurement bridge servo, parked")
    p=b.box(r+"/ProbeSlide",(-.3,.35,2.1),(.30,.43,.85),"blue")
    b.role(p,"Dependent measurement slide, parked")
    b.cylinder(r+"/Probe",(-.3,.35,1.57),.025,.30,"silver")
    b.box(r+"/Specimen",(0,-.2,1.12),(.8,1.7,.23),"steel")
    b.label(r+"/ID","MEASURE",(-.95,-2.16,.36),.23,"graphite")

    b, r = component("PowerCabinet")
    b.box(r+"/Plinth",(0,0,.13),(1.4,.95,.26),"graphite")
    b.box(r+"/Case",(0,0,1.47),(1.25,.8,2.68),"steel")
    b.box(r+"/Face",(0,-.415,1.47),(1.12,.04,2.5),"lightConcrete")
    b.box(r+"/Display",(0,-.445,2.05),(.55,.02,.35),"glass")
    b.box(r+"/Handle",(.43,-.475,1.45),(.035,.05,.32),"graphite")
    for j in range(9):
        b.box(r+f"/Vent{j}",(0,-.446,.47+j*.075),(.8,.02,.028),"graphite")
    b.label(r+"/ID","POWER",(-.41,-.45,2.42),.17,"graphite")

    b, r = component("Console")
    b.box(r+"/Base",(0,.1,.40),(2.4,.65,.8),"graphite")
    b.box(r+"/Desk",(0,-.16,.9),(2.8,1.05,.10),"silver")
    for i,x in enumerate((-.72,.72)):
        b.box(r+f"/ScreenPost{i}",(x,.12,1.14),(.08,.08,.45),"graphite")
        b.box(r+f"/Screen{i}",(x,.1,1.46),(1.12,.09,.65),"graphite")
        b.box(r+f"/Glass{i}",(x,.047,1.46),(1.02,.01,.54),"glass")
        for j in range(3):
            b.box(r+f"/Trace{i}_{j}",(x-.1,.037,1.30+j*.12),(.65-j*.12,.008,.012),"silver")
    b.box(r+"/Keyboard",(0,-.37,.98),(1.0,.27,.06),"graphite")
    b.box(r+"/ChairSeat",(0,-1.0,.48),(.55,.5,.10),"steel")
    b.box(r+"/ChairBack",(0,-1.22,.79),(.55,.09,.55),"steel")
    b.cylinder(r+"/ChairStem",(0,-1,.25),.055,.45,"graphite")
    b.box(r+"/ChairFoot",(0,-1,.045),(.7,.65,.09),"graphite")

    b, r = component("RoofCassette")
    for i,x in enumerate((-1.25,1.25)):
        b.box(r+f"/Sill{i}",(x,0,.20),(.22,5.2,.4),"graphite")
    for j,y in enumerate((-2.3,0,2.3)):
        b.box(r+f"/Cradle{j}",(0,y,.55),(3,.22,.45),"steel")
    for i,x in enumerate((-1.4,1.4)):
        b.box(r+f"/Edge{i}",(x,0,1.0),(.15,5.0,.7),"silver")
    for j in range(6):
        y=-2.5+j
        b.box(r+f"/Rib{j}",(0,y,.95),(2.8,.11,.5),"steel")
        if j<5:
            b.beam(r+f"/Web{j}",(-1.3,y,.95),(1.3,y+1,.95),.07,.09,"steel")
    b.box(r+"/Skin",(-.70,0,1.32),(1.24,4.9,.055),"lightConcrete")
    b.label(r+"/ID","JIG",(-1.05,-2.62,.48),.24,"white")

    b, r = component("CableReel")
    for i,x in enumerate((-.58,.58)):
        b.cylinder(r+f"/Cheek{i}",(x,0,.9),.86,.08,"silver","X")
        b.cylinder(r+f"/Hub{i}",(x*1.1,0,.9),.17,.16,"graphite","X")
    b.cylinder(r+"/Winding",(0,0,.9),.62,1.08,"rubber","X")
    for j in range(12):
        b.cylinder(r+f"/Cable{j}",(-.48+j*.087,0,.9),.64,.055,"graphite","X")
    b.box(r+"/Stand",(0,0,.09),(1.5,1.4,.18),"steel")
    s.GetRootLayer().Save()
    print("Saved assets/workshop_kit.usda")
