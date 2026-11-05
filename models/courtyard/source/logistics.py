"""Pass 08: material handling, supply yards and a connected delivery apron."""
from .common import begin, save_pass


def build():
    s,b,r=begin(8,"logistics","08 | Materials loop and handling yards",
        "Receive material under the west gantry, fabricate and inspect it in the side halls, then stage stock in the north racks and service equipment in the east supply yard.")
    # The new apron follows the footprint of the original terrain. It leaves
    # the proving court and its existing vehicle approach unobstructed.
    b.box(r+"/DeliveryApron/Paving",(0,-27.25,-.12),(73,4.5,.26),"concrete")
    b.box(r+"/DeliveryApron/EntryTie",(0,-23.5,-.12),(16,3,.26),"lightConcrete")
    for i,x in enumerate(range(-33,34,6)):
        b.box(r+f"/DeliveryApron/Dash{i}",(x,-27.25,.027),(2.8,.10,.015),"white")
    for side in (-1,1):
        p=r+f"/Forecourt{side+1}"
        b.box(p+"/Slab",(side*32.5,-20.1,-.12),(8,9.8,.26),"lightConcrete")
        b.box(p+"/StopLine",(side*32.5,-24.45,.027),(4.7,.12,.015),"white")
        b.box(p+"/Lane",(side*29.2,-20.2,.027),(.06,7.2,.015),"white")
    b.label(r+"/DeliveryApron/Name","MATERIALS",(-3.1,-28.9,.035),.68,"white","XY")
    b.label(r+"/ReceivingID","01 RECEIVE",(-35.55,-23.9,.035),.43,"graphite","XY")
    b.label(r+"/SupplyID","02 SUPPLY",(29.40,-23.9,.035),.43,"graphite","XY")
    # A parked double-girder handling gantry. Neutral fixed structure, orange
    # drive housing and blue dependent trolley follow the accepted visual code.
    p=r+"/WestGantry"
    for side,x in enumerate((-36.1,-28.9)):
        for i,y in enumerate((-24.4,-20.0,-15.8)):
            q=p+f"/Pier{side}_{i}"
            b.box(q+"/Pad",(x,y,.10),(.72,.72,.20),"darkConcrete")
            b.box(q+"/Column",(x,y,4.10),(.28,.32,8.0),"graphite")
            b.box(q+"/Cap",(x,y,8.05),(.54,.52,.18),"silver")
            if i==1:
                b.beam(q+"/Brace",(x,y-2.8,.25),(x,y,5.9),.12,.12,"steel")
        b.box(p+f"/Runway{side}",(x,-20.25,8.22),(.22,9.5,.32),"steel")
        b.box(p+f"/Rail{side}",(x,-20.25,8.42),(.085,9.55,.085),"silver")
    for j,y in enumerate((-20.84,-20.16)):
        b.box(p+f"/BridgeGirder{j}",(-32.5,y,8.63),(7.5,.20,.48),"silver")
    for j,x in enumerate((-36.1,-28.9)):
        b.box(p+f"/EndTruck{j}",(x,-20.5,8.56),(.50,1.45,.25),"graphite")
        for k,y in enumerate((-21.0,-20.0)):
            b.cylinder(p+f"/Wheel{j}_{k}",(x,y,8.46),.16,.25,"steel","X")
    q=b.box(p+"/Trolley",(-31.8,-20.5,8.98),(1.3,1.05,.30),"blue")
    b.role(q,"Dependent hoist trolley, parked")
    q=b.box(p+"/DriveHousing",(-31.8,-20.98,9.27),(.72,.42,.40),"orange")
    b.role(q,"Hoist drive motor housing, parked")
    b.cylinder(p+"/Drum",(-31.8,-20.5,8.70),.23,.86,"graphite","X")
    for j,x in enumerate((-32.08,-31.52)):
        b.tube(p+f"/Rope{j}",(x,-20.5,8.66),(x,-20.5,4.82),.018,"graphite")
    q=b.box(p+"/HookBlock",(-31.8,-20.5,4.72),(.78,.35,.44),"blue")
    b.role(q,"Dependent lifting block, parked")
    b.cylinder(p+"/HookPin",(-31.8,-20.5,4.38),.08,.4,"silver")
    b.box(p+"/Spreader",(-31.8,-20.5,4.15),(4.2,.32,.28),"blue")
    for j,x in enumerate((-33.65,-29.95)):
        b.box(p+f"/SpreaderEnd{j}",(x,-20.5,3.99),(.16,.55,.22),"silver")
    b.box(p+"/NameBand",(-32.5,-24.58,7.0),(6.9,.10,.72),"graphite")
    b.label(p+"/Name","MATERIAL HANDLING",(-35.7,-24.65,6.82),.44)
    b.instance(r+"/WestDispatch/Cassette","RoofCassette",(-32.1,-19.8,.02))
    for i,z in enumerate((.15,.38,.61)):
        b.box(r+f"/WestDispatch/PlateStack{i}",(-34.7,-16.85,z),(2.0,1.45,.18),"steel")
    for i,x in enumerate((-35.25,-34.15)):
        b.box(r+f"/WestDispatch/Dunnage{i}",(x,-16.85,.06),(.15,1.7,.12),"graphite")
    # East supply yard is an accessible low cantilever, leaving the reels and
    # staging table exposed to the court-facing camera.
    p=r+"/EastSupply"
    for i,y in enumerate((-24.4,-20.0,-15.8)):
        b.box(p+f"/Pad{i}",(36.15,y,.10),(.65,.65,.20),"darkConcrete")
        b.box(p+f"/Post{i}",(36.15,y,2.15),(.18,.22,4.1),"graphite")
        b.box(p+f"/Cantilever{i}",(34.9,y,4.28),(3.1,.16,.20),"silver")
        b.beam(p+f"/Knee{i}",(36.15,y,3.1),(34.5,y,4.2),.10,.10,"steel")
    b.box(p+"/Cover",(34.9,-20.1,4.43),(3.2,9.25,.12),"silver")
    for i,y in enumerate((-22.6,-20.85,-19.1)):
        b.instance(p+f"/Cabinet{i}","PowerCabinet",(35.5,y,.02),-90)
    for i,y in enumerate((-21.7,-18.3)):
        b.instance(p+f"/Reel{i}","CableReel",(31.6,y,.02))
    b.instance(p+"/StagingTable","AssemblyTable",(32.1,-16.0,.02))
    b.box(p+"/Fascia",(34.9,-24.77,4.2),(3.2,.08,.50),"graphite")
    b.label(p+"/Name","SUPPLY",(33.5,-24.82,4.03),.36)
    # Rear stock arcades finish the north ground level, while the upper gallery
    # remains an independent pedestrian route. Racks face the clear south aisle.
    for side in (-1,1):
        p=r+f"/NorthStock{side+1}"
        b.box(p+"/Apron",(side*18.6,28.55,-.12),(15.8,5.9,.26),"concrete")
        for i,xx in enumerate((10.8,18.5,26.2)):
            x=side*xx
            b.box(p+f"/Pad{i}",(x,31.25,.08),(.7,.7,.16),"lightConcrete")
            b.box(p+f"/Column{i}",(x,31.25,2.2),(.18,.18,4.24),"graphite")
            b.box(p+f"/Arm{i}",(x,30.25,4.35),(.16,2.25,.20),"silver")
            b.beam(p+f"/Knee{i}",(x,31.25,3.1),(x,29.7,4.3),.09,.09,"steel")
        b.box(p+"/Canopy",(side*18.5,30.4,4.53),(16.0,2.3,.12),"silver")
        b.box(p+"/Fascia",(side*18.5,29.2,4.3),(16,.08,.45),"graphite")
        b.label(p+"/Name","STOCK / WEST" if side<0 else "STOCK / EAST",
                (side*18.5-2.35,29.15,4.16),.31)
        for i,xx in enumerate((15,22)):
            x=side*xx
            b.instance(p+f"/Rack{i}","StockRack",(x,30.1,.02))
            b.box(p+f"/Pallet{i}",(x,27.0,.15),(3.2,1.5,.28),"graphite")
            for j in range(4):
                b.box(p+f"/Sections{i}_{j}",(x-1.15+j*.76,27.0,.52),(.45,1.2,.45),"silver")
            b.box(p+f"/LocationLine{i}",(x,26.1,.027),(3.5,.06,.015),"white")
    save_pass(s,8,"logistics","Materials loop and handling yards",
        "A west overhead handling gantry, an east cable and supply canopy, two rear stock arcades and a connected southern delivery apron complete the fabrication-to-inspection materials route.")
