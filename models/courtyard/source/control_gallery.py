"""Pass 07: north gallery, control pavilion, two return stairs and spine access."""
from .common import begin, save_pass, CFG


def stair(b,r,side,z):
    """Two 16-riser flights, 1.4 m wide treads, a full-width mid landing."""
    lower=side*29.5
    upper=side*31.2
    mid=side*30.35
    rise=z/32
    run=.29
    y0=25.7
    yn=y0+16*run
    b.box(r+"/Foundation",(mid,28.55,-.12),(3.6,6.8,.26),"lightConcrete")
    for i in range(16):
        yt=y0+(i+.5)*run
        top=(i+1)*rise
        b.box(r+f"/Lower/Tread{i:02}",(lower,yt,top-.04),(1.4,.30,.08),"silver")
        b.box(r+f"/Lower/Nose{i:02}",(lower,yt-.13,top+.007),(1.30,.025,.014),"graphite")
        yt=yn-(i+.5)*run
        top=16*rise+(i+1)*rise
        b.box(r+f"/Upper/Tread{i:02}",(upper,yt,top-.04),(1.4,.30,.08),"silver")
        b.box(r+f"/Upper/Nose{i:02}",(upper,yt+.13,top+.007),(1.30,.025,.014),"graphite")
    b.box(r+"/MidLanding",(mid,yn+.70,16*rise-.07),(3.1,1.4,.14),"graphite")
    b.box(r+"/TopLanding",(upper,25.575,z-.08),(1.4,.25,.16),"graphite")
    for j,dx in enumerate((-.65,.65)):
        b.beam(r+f"/Lower/Stringer{j}",(lower+dx,y0,.02),(lower+dx,yn,16*rise-.10),.10,.22,"graphite")
        b.beam(r+f"/Upper/Stringer{j}",(upper+dx,yn,16*rise-.1),(upper+dx,y0,z-.10),.10,.22,"graphite")
        b.rail(r+f"/Lower/Rail{j}",(lower+dx,y0+.145,rise),(lower+dx,yn-.145,16*rise))
        b.rail(r+f"/Upper/Rail{j}",(upper+dx,yn-.145,17*rise),(upper+dx,y0+.145,z))
        b.rail(r+f"/TopRail{j}",(upper+dx,25.45,z),(upper+dx,25.845,z))
    b.rail(r+"/MidNorth",(mid-1.55,yn+1.4,16*rise),(mid+1.55,yn+1.4,16*rise))
    for j,x in enumerate((mid-1.55,mid+1.55)):
        b.rail(r+f"/MidSide{j}",(x,yn,16*rise),(x,yn+1.4,16*rise))
        b.box(r+f"/MidPost{j}",(x,yn+.9,8*rise),(.14,.14,16*rise),"graphite")


def build():
    s,b,r=begin(7,"control_gallery","07 | North control gallery",
        "An elevated north route joins the two new halls, reaches the accepted service catwalk through its open east end, and supports a central control room.")
    z=CFG["north_gallery"]["deck_z"]
    b.box(r+"/Promenade/Deck",(0,24.25,z-.12),(66.4,2.4,.24),"graphite")
    # A shallow Warren truss supports the continuous open-front promenade.
    for side in (-1,1):
        y=24.25+side*1.12
        for j,zz in enumerate((4.62,5.50)):
            b.box(r+f"/Promenade/Girder{side+1}_{j}",(0,y,zz),(66.4,.16,.16),"silver")
        for i in range(44):
            x=-33.0+i*1.5
            b.beam(r+f"/Promenade/Web{side+1}_{i}",(x,y,4.62 if i%2==0 else 5.5),
                   (x+1.5,y,5.5 if i%2==0 else 4.62),.075,.075,"steel")
    for i,x in enumerate((-32,-24,-16,-8,8,16,24,32)):
        p=r+f"/Promenade/Pier{i}"
        b.box(p+"/Pad",(x,24.25,-.02),(1.0,1.5,.46),"lightConcrete")
        b.box(p+"/Column",(x,24.25,2.83),(.34,.50,5.26),"graphite")
        b.box(p+"/Head",(x,24.25,5.34),(.26,2.38,.30),"steel")
    for i in range(110):
        b.box(r+f"/Promenade/DeckJoint{i}",(-32.8+i*.6,24.25,z+.01),(.025,2.24,.018),"silver")
    for i,(a,c) in enumerate(((-33.2,20.4),(22.0,33.2))):
        b.rail(r+f"/Promenade/SouthRail{i}",(a,23.08,z),(c,23.08,z))
    for i,(a,c) in enumerate(((-33.2,-32),(-30.4,-9),(9,30.4),(32,33.2))):
        b.rail(r+f"/Promenade/NorthRail{i}",(a,25.42,z),(c,25.42,z))
    for side in (-1,1):
        b.rail(r+f"/Promenade/EndRail{side+1}",(side*33.2,23.08,z),(side*33.2,25.42,z))
        b.box(r+f"/GroundAccess/Apron{side+1}",(side*32.5,21.7,-.12),(8,7.4,.26),"concrete")
        stair(b,r+f"/Stair{side+1}",side,z)
    # Existing catwalk has a continuous north rail. Join its unobstructed east
    # end instead of attempting to cross or erase that accepted rail.
    p=r+"/SpineConnection"
    b.box(p+"/EastDeck",(17.025,14.8,z-.09),(8.35,1.6,.18),"graphite")
    b.box(p+"/NorthDeck",(21.2,18.925,z-.09),(1.6,8.25,.18),"graphite")
    b.box(p+"/CornerDeck",(21.6,14.4,z-.09),(.8,.8,.18),"graphite")
    for i,(a,c) in enumerate((((12.85,14.0,z),(22.0,14.0,z)),
                             ((12.85,15.6,z),(20.4,15.6,z)),
                             ((22.0,14.0,z),(22.0,23.05,z)),
                             ((20.4,15.6,z),(20.4,23.05,z)))):
        b.rail(p+f"/Rail{i}",a,c)
    for i,(x,y) in enumerate(((16.5,14.8),(21.2,16.5),(21.2,21.6))):
        b.box(p+f"/Foot{i}",(x,y,.08),(.7,.7,.16),"lightConcrete")
        b.box(p+f"/Post{i}",(x,y,2.85),(.20,.20,5.54),"graphite")
        b.box(p+f"/Cap{i}",(x,y,5.48),(.18,1.5,.22),"silver")
    # Central control pavilion rests behind the promenade, well north of the
    # accepted moving roof. Its interior is exposed by the glazed front.
    p=r+"/ControlRoom"
    b.box(p+"/Floor",(0,28.225,z-.14),(18,5.55,.28),"lightConcrete")
    for i,x in enumerate((-8.7,0,8.7)):
        b.box(p+f"/RearFoot{i}",(x,30.7,-.02),(1.0,1.0,.46),"lightConcrete")
        b.box(p+f"/RearPier{i}",(x,30.7,2.87),(.34,.34,5.30),"graphite")
    for i,x in enumerate((-8.8,-4.4,0,4.4,8.8)):
        for j,y in enumerate((26.5,30.8)):
            if x==0 and j==0:
                continue
            b.box(p+f"/Frame{i}_{j}",(x,y,8.0),(.15,.15,4.56),"graphite")
    for j,x in enumerate((-1.3,1.3)):
        b.box(p+f"/DoorJamb{j}",(x,26.5,7.75),(.10,.16,4.06),"silver")
    b.box(p+"/RearSill",(0,30.85,6.22),(17.6,.14,1.0),"steel")
    b.box(p+"/RearGlass",(0,30.85,8.35),(17.6,.06,3.1),"glazing")
    for side in (-1,1):
        b.box(p+f"/FrontSill{side+1}",(side*5.05,26.5,6.22),(7.5,.14,1.0),"steel")
        b.box(p+f"/FrontGlass{side+1}",(side*5.05,26.5,8.35),(7.5,.06,3.1),"glazing")
        b.box(p+f"/SideSill{side+1}",(side*8.8,28.65,6.22),(.14,4.3,1.0),"steel")
        b.box(p+f"/SideGlass{side+1}",(side*8.8,28.65,8.35),(.06,4.3,3.1),"glazing")
    b.box(p+"/DoorHeader",(0,26.5,9.95),(17.85,.22,.22),"silver")
    b.box(p+"/Roof",(0,28.4,10.48),(18.4,6.0,.20),"silver")
    for i,x in enumerate((-7,-3.5,0,3.5,7)):
        b.box(p+f"/RoofRib{i}",(x,28.4,10.29),(.12,5.7,.24),"graphite")
    b.mesh(p+"/MonitorRoof",[(-2,26.2,10.6),(2,26.2,10.6),(2,30.5,11.55),(-2,30.5,11.55)],[[0,1,2,3]],"steel")
    b.box(p+"/MonitorGlass",(0,30.5,11.05),(4,.08,.9),"glazing")
    for j,x in enumerate((-2,2)):
        b.mesh(p+f"/MonitorCheek{j}",[(x,26.2,10.6),(x,30.5,10.6),(x,30.5,11.55)],[[0,1,2]],"silver")
    for i,x in enumerate((-5.4,0,5.4)):
        b.instance(p+f"/Consoles/C{i}","Console",(x,28.0,z))
        b.box(p+f"/CeilingLight{i}",(x,28.4,10.08),(2.8,.15,.06),"lamp")
    b.box(p+"/SignBacking",(0,26.32,10.0),(10,.10,.6),"graphite")
    b.label(p+"/Sign","NORTH CONTROL",(-3.7,26.25,9.82),.48)
    # A static explanatory plate repeats the accepted color semantics, without
    # displaying simulated measurements or implying a new evaluated result.
    q=p+"/MechanismDiagram"
    b.box(q+"/Plate",(0,30.72,8.2),(7.3,.08,2.1),"graphite")
    b.label(q+"/Title","NORTH LIFT / 01",(-3.3,30.665,8.75),.33)
    for i,(a,c,mat) in enumerate((((-3,30.65,7.55),(-1,30.65,7.55),"orange"),
                                 ((-3,30.65,8.4),(-1,30.65,8.4),"blue"),
                                 ((-3,30.65,7.55),(-3,30.65,8.4),"blue"),
                                 ((-1,30.65,7.55),(-1,30.65,8.4),"silver"))):
        b.tube(q+f"/Link{i}",a,c,.035,mat)
    for i,(text,zz,mat) in enumerate((("M01 INPUT",8.30,"orange"),("J02 ROOF",7.96,"blueLight"),("J03 WALL",7.62,"blueLight"))):
        b.label(q+f"/Legend{i}",text,(-.4,30.65,zz),.23,mat)
    save_pass(s,7,"control_gallery","North gallery and control pavilion",
        "A 66.4 m elevated trussed promenade, two complete return stairs, an east catwalk connection and a glazed control pavilion unite both workshop halls.")
