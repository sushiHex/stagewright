"""Pass 05: west fabrication hall with a visible assembly lane and machine bay."""
from .common import begin, save_pass, CFG


def build():
    s,b,r=begin(5,"fabrication","05 | West fabrication hall",
        "Receive stock, cut and machine it, then assemble full-size roof cassettes outside the moving court.")
    west=CFG["west_hall"]
    x0,x1=west["x_bounds"]
    y0,y1=west["y_bounds"]
    b.box(r+"/Foundation",(-32.5,4.5,-.12),(8,27,.26),"lightConcrete")
    b.box(r+"/EntryApron",(-32.5,-12.1,-.12),(8,6.2,.26),"concrete")
    # A short raised walk crosses the existing low terrace steps at the south.
    b.box(r+"/CourtConnection",(-27.25,-14.45,.035),(3.0,1.5,.07),"lightConcrete")
    for i,y in enumerate((-9,-3.6,1.8,7.2,12.6,18)):
        p=r+f"/Portal{i}"
        for j,x in enumerate((x0+.20,x1-.20)):
            b.box(p+f"/Pad{j}",(x,y,.08),(.65,.65,.16),"darkConcrete")
            b.box(p+f"/Column{j}",(x,y,3.60),(.24,.30,7.04),"graphite")
            for k,dx in enumerate((-.2,.2)):
                b.cylinder(p+f"/Anchor{j}{k}",(x+dx,y,.185),.04,.05,"silver")
        for k,z in enumerate((6.5,7.13)):
            b.box(p+f"/Chord{k}",(-32.5,y,z),(7.7,.18,.15),"silver")
        for k in range(8):
            x=x0+.25+k*.94
            b.beam(p+f"/Web{k}",(x,y,6.5 if k%2==0 else 7.13),
                   (x+.94,y,7.13 if k%2==0 else 6.5),.075,.075,"steel")
    for j,x in enumerate((x0+.2,x1-.2)):
        b.box(r+f"/Eave{j}",(x,4.5,7.12),(.18,27.35,.28),"steel")
    # Five sawtooth strips shelter the outer workbench lane. The inner assembly
    # aisle is open to the sky and court, preserving readable large workpieces.
    for i in range(5):
        ya=y0+i*5.4
        p=r+f"/RoofFold{i}"
        pts=[(x0,ya,7.2),(-31.4,ya,7.2),(-31.4,ya+5.25,8.05),(x0,ya+5.25,8.05)]
        b.mesh(p+"/Sheet",pts,[[0,1,2,3]],"silver")
        b.box(p+"/Northlight",(-33.95,ya+5.25,7.62),(5.1,.06,.80),"glazing")
        for j,x in enumerate((x0,-31.4)):
            b.beam(p+f"/FoldEdge{j}",(x,ya,7.2),(x,ya+5.25,8.05),.08,.10,"graphite")
        b.box(p+"/Light",(-34.15,ya+2.4,6.78),(3.1,.12,.075),"lamp")
        b.box(p+"/OuterWall",(x0,ya+2.7,1.5),(.12,5.23,3),"steel")
        b.beam(p+"/WindBrace",(x0+.10,ya+.2,3.2),(x0+.10,ya+5.1,6.8),.075,.075,"silver")
    # The assembly zone is outlined; the two metre walk lies between the jigs
    # and the outer bench lane.
    for i,x in enumerate((-32.1,-28.9)):
        b.box(r+f"/AisleLine{i}",(x,3.9,.023),(.06,24.8,.018),"white")
    b.instance(r+"/Assembly/JigA","RoofCassette",(-30.5,-4.1,.02))
    b.instance(r+"/Assembly/JigB","RoofCassette",(-30.5,3.5,.02))
    for i,y in enumerate((-5.2,.5,6.2)):
        b.instance(r+f"/Benches/B{i}","AssemblyTable",(-34.7,y,.02),90)
    b.instance(r+"/Machine","MachineCell",(-32.65,11.7,.02),90)
    b.instance(r+"/Stock","StockRack",(-32.6,16.5,.02))
    b.box(r+"/NameBand",(-32.5,-9.18,5.6),(7.7,.12,.82),"graphite")
    b.label(r+"/Name","FABRICATION",(-36.05,-9.25,5.4),.56)
    b.label(r+"/FloorID","W01",(-34.6,-13.8,.03),.85,"graphite","XY")
    b.label(r+"/RouteLabel","ASSEMBLY",(-31.25,14.5,.03),.32,"white","XY")
    save_pass(s,5,"fabrication","West fabrication hall",
        "A 27 m long five-bay sawtooth workshop adds stock storage, machining, three benches and two full-size assembly jigs on the west terrace.")
