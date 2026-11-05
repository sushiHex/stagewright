"""Pass 06: east metrology and power-service hall, open toward the court."""
from .common import begin, save_pass, CFG


def build():
    s,b,r=begin(6,"metrology","06 | East metrology and power hall",
        "Inspect fabricated cassettes on two measurement beds, with independent power service and instrument preparation to the north.")
    x0,x1=CFG["east_hall"]["x_bounds"]
    b.box(r+"/Foundation",(32.5,4.5,-.12),(8,27,.26),"lightConcrete")
    b.box(r+"/EntryApron",(32.5,-12.1,-.12),(8,6.2,.26),"concrete")
    b.box(r+"/CourtConnection",(27.25,-14.45,.035),(3.0,1.5,.07),"lightConcrete")
    # The lower, level service hall contrasts with the west sawtooth roof.
    # An open inner roof strip exposes both inspection beds to the shared view.
    for i,y in enumerate((-9,-3.6,1.8,7.2,12.6,18)):
        p=r+f"/Frame{i}"
        for j,x in enumerate((x0+.2,x1-.2)):
            b.box(p+f"/Foot{j}",(x,y,.1),(.65,.65,.20),"darkConcrete")
            b.box(p+f"/Column{j}",(x,y,3.38),(.22,.26,6.6),"graphite")
            b.beam(p+f"/Knee{j}",(x,y,5.2),(x+(1 if j==0 else -1)*1.4,y,6.55),.12,.14,"silver")
        b.box(p+"/Header",(32.5,y,6.65),(7.8,.24,.30),"steel")
        b.box(p+"/Light",(32.0,y,6.45),(3.1,.1,.065),"lamp")
    for j,x in enumerate((28.7,32.2,36.3)):
        b.box(r+f"/RoofRail{j}",(x,4.5,6.82),(.15,27.2,.24),"silver")
    for i in range(5):
        y=-6.3+i*5.4
        p=r+f"/RoofBay{i}"
        b.box(p+"/WeatherStrip",(34.4,y,6.98),(4.3,4.25,.10),"silver")
        b.box(p+"/LightSlot",(34.4,y+2.35,7.08),(4.3,.36,.06),"glazing")
        # High back glazing and a low wall enclose services without closing
        # the west-facing work aisles.
        b.box(p+"/SillWall",(36.5,y,1.2),(.12,5.24,2.4),"lightConcrete")
        b.box(p+"/BackWindow",(36.5,y,3.75),(.07,5.24,2.6),"glazing")
        for j in range(5):
            b.box(p+f"/Mullion{j}",(36.44,y-2.1+j*1.05,3.75),(.10,.055,2.7),"silver")
        b.box(p+"/HighLouver",(36.5,y,5.85),(.12,5.24,1.2),"steel")
        for j in range(5):
            b.box(p+f"/Louver{j}",(36.4,y,5.4+j*.21),(.06,5.1,.07),"graphite")
    # Solid metrology blocks and slender sensor bridges read differently from
    # the open west fabrication cradles. All equipment remains parked geometry.
    for i,y in enumerate((-4.5,3.0)):
        b.box(r+f"/IsolationPad{i}",(32.1,y,.12),(3.7,5.1,.22),"darkConcrete")
        b.instance(r+f"/Inspection/Bed{i}","MetrologyBed",(32.1,y,.23))
        for j,x in enumerate((30.1,34.1)):
            b.box(r+f"/PadLine{i}_{j}",(x,y,.029),(.055,5.65,.018),"white")
    for i,y in enumerate((10.5,12.2,13.9,15.6)):
        b.instance(r+f"/Power/Cabinet{i}","PowerCabinet",(35.6,y,.02),-90)
    b.instance(r+"/Preparation/BenchA","AssemblyTable",(31.5,10.2,.02))
    b.instance(r+"/Preparation/BenchB","AssemblyTable",(31.5,14.0,.02))
    # Cable trays join the static service cabinets, without routing any object
    # into the original drive station or mechanism namespace.
    for j,x in enumerate((35.2,35.85)):
        b.box(r+f"/CableTray/Rail{j}",(x,12.8,3.55),(.045,8.1,.12),"graphite")
    for i in range(28):
        b.box(r+f"/CableTray/Rung{i}",(35.525,8.9+i*.29,3.51),(.65,.035,.055),"silver")
    for i,y in enumerate((9.0,12.5,16.5)):
        b.tube(r+f"/ServiceDrop{i}",(35.95,y,3.55),(35.95,y,.4),.045,"steel")
    b.box(r+"/ServiceDivider",(33.1,7.6,1.2),(5.8,.12,2.4),"steel")
    b.box(r+"/DividerWindow",(33.1,7.6,2.85),(5.8,.06,.75),"glazing")
    # Leave the west end of the divider open as the longitudinal route.
    b.label(r+"/ServicesLabel","POWER / PREP",(30.45,7.525,1.70),.36,"graphite")
    b.box(r+"/NameBand",(32.5,-9.18,5.3),(7.7,.12,.82),"graphite")
    b.label(r+"/Name","METROLOGY",(29.10,-9.25,5.10),.58)
    b.label(r+"/FloorID","E01",(30.4,-13.8,.03),.85,"graphite","XY")
    b.box(r+"/WestWalkLine",(29.2,3.7,.026),(.06,24.8,.018),"white")
    save_pass(s,6,"metrology","East metrology and power hall",
        "A second 27 m hall balances the west workshop with two granite measurement beds, power cabinets, preparation benches and an elevated cable distribution spine.")
