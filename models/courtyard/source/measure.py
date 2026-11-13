"""Conservative geometric opening measurements from frozen solver recordings.

Project the transformed bounds of each individual geometric prim, clip them to
Court C01, and compute their rectangle-union area. The result is a lower bound
on open area because a projected bound can overestimate geometry obstruction.
The empty space between the yoke arms is never replaced by an aggregate box.

    python models/courtyard/source/measure.py RESULT_DIR NEW_OUT_DIR

RESULT_DIR is an engine result (input.usdz and recording/). No native physics or renderer.
"""
import argparse
import csv
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
from pxr import Gf, Usd, UsdGeom, UsdPhysics

CONDITION = json.loads((Path(__file__).resolve().parent / "parameters.json").read_text())["opening_condition"]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rotation(q):
    x,y,z,w = q / np.linalg.norm(q)
    return np.array([
        [1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
        [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
        [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)],
    ])


def geometry_bounds(stage, body_paths):
    bounds = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"])
    transforms = UsdGeom.XformCache()
    groups = {path: [] for path in body_paths}
    groups["static"] = []
    labels = {path: [] for path in groups}
    inverses = {path: transforms.GetLocalToWorldTransform(stage.GetPrimAtPath(path)).GetInverse() for path in body_paths}
    for prim in Usd.PrimRange.Stage(stage, Usd.TraverseInstanceProxies()):
        if not prim.IsA(UsdGeom.Gprim):
            continue
        if UsdGeom.Imageable(prim).ComputeVisibility() == "invisible":
            continue
        path = str(prim.GetPath())
        owner = next((body for body in body_paths if path.startswith(body+"/")), "static")
        extent = bounds.ComputeUntransformedBound(prim).ComputeAlignedRange()
        if extent.IsEmpty():
            continue
        lo, hi = extent.GetMin(), extent.GetMax()
        matrix = transforms.GetLocalToWorldTransform(prim)
        if owner != "static":
            matrix = matrix * inverses[owner]
        points = np.array([tuple(matrix.Transform(Gf.Vec3d(*v))) for v in itertools.product(*zip(lo,hi))])
        if not np.isfinite(points).all():
            raise ValueError("Non-finite geometry: "+path)
        groups[owner].append(points)
        labels[owner].append(path)
    return {key: np.array(value).reshape((-1,8,3)) for key,value in groups.items()}, labels


def rectangles(corners):
    lo, hi = corners.min(axis=1), corners.max(axis=1)
    xmin,xmax = CONDITION["x_bounds_m"]
    ymin,ymax = CONDITION["y_bounds_m"]
    zmin,zmax = CONDITION["z_bounds_m"]
    keep=(hi[:,2]>zmin)&(lo[:,2]<zmax)&(hi[:,0]>xmin)&(lo[:,0]<xmax)&(hi[:,1]>ymin)&(lo[:,1]<ymax)
    lo,hi=lo[keep],hi[keep]
    if len(lo)==0:
        return np.empty((0,4))
    return np.column_stack([np.maximum(lo[:,0],xmin),np.minimum(hi[:,0],xmax),np.maximum(lo[:,1],ymin),np.minimum(hi[:,1],ymax)])


def rectangle_union(rects):
    """Exact union of axis-aligned projected bounding rectangles, in square metres."""
    if len(rects)==0:
        return 0.0
    area=(rects[:,1]-rects[:,0])*(rects[:,3]-rects[:,2])
    candidates=rects[np.argsort(-area)]
    reduced=[]
    while len(candidates):
        r=candidates[0]
        reduced.append(r)
        contained=(candidates[:,0]>=r[0])&(candidates[:,1]<=r[1])&(candidates[:,2]>=r[2])&(candidates[:,3]<=r[3])
        candidates=candidates[~contained]
    rects=np.array(reduced)
    xs=np.unique(rects[:,:2].ravel())
    total=0.0
    for x0,x1 in zip(xs[:-1],xs[1:]):
        mid=(x0+x1)/2
        intervals=rects[(rects[:,0]<mid)&(rects[:,1]>mid),2:]
        if len(intervals)==0:
            continue
        intervals=intervals[np.argsort(intervals[:,0])]
        bottom,top=intervals[0]
        length=0.0
        for a,b in intervals[1:]:
            if a>top:
                length+=top-bottom
                bottom,top=a,b
            else:
                top=max(top,b)
        total+=(length+top-bottom)*(x1-x0)
    return float(total)


def hinge_errors(stage, paths, samples):
    indices={path:i for i,path in enumerate(paths)}
    results={}
    for prim in stage.Traverse():
        if not prim.IsA(UsdPhysics.RevoluteJoint):
            continue
        joint=UsdPhysics.RevoluteJoint(prim)
        points=[]
        for k in [0,1]:
            target=getattr(joint,f"GetBody{k}Rel")().GetTargets()
            local=np.array(getattr(joint,f"GetLocalPos{k}Attr")().Get(),float)
            if target:
                poses=samples[:,indices[str(target[0])]]
                points.append(np.array([rotation(p[3:])@local+p[:3] for p in poses]))
            else:
                points.append(np.tile(local,(len(samples),1)))
        distance=np.linalg.norm(points[0]-points[1],axis=1)
        results[str(prim.GetPath())]={"max_anchor_separation_m":float(distance.max()),"final_anchor_separation_m":float(distance[-1])}
    return results


def measure(directory, output):
    record=json.loads((directory/"recording/result.json").read_text())
    frozen=directory/"input.usdz"
    if sha256(frozen)!=record["source_sha256"]:
        raise ValueError("Frozen geometry does not match recording hash")
    stage=Usd.Stage.Open(str(frozen))
    with np.load(directory/"recording/poses.npz",allow_pickle=False) as data:
        paths=list(map(str,data["paths"]))
        poses=data["poses"].copy()
        seconds=data["seconds"].copy()
    if not np.isfinite(poses).all():
        raise ValueError("Non-finite recording")
    if seconds[-1]-seconds[0] < CONDITION["final_hold_seconds"]:
        raise ValueError("Recording is shorter than the final hold window")
    groups,labels=geometry_bounds(stage,paths)
    fixed=rectangles(groups["static"])
    area=(CONDITION["x_bounds_m"][1]-CONDITION["x_bounds_m"][0])*(CONDITION["y_bounds_m"][1]-CONDITION["y_bounds_m"][0])
    rows=[]
    for second,sample in zip(seconds,poses):
        parts=[fixed]
        angles={}
        for path,pose in zip(paths,sample):
            r=rotation(pose[3:])
            corners=groups[path]@r.T+pose[:3]
            parts.append(rectangles(corners))
            angles[path.rsplit("/",1)[-1]]=float(np.degrees(np.arctan2(r[2,1],r[1,1])))
        covered=rectangle_union(np.concatenate(parts))
        rows.append({"seconds":float(second),"open_area_lower_bound_m2":max(0.0,area-covered),"open_fraction_lower_bound":max(0.0,1-covered/area),**{name+"_angle_deg":value for name,value in angles.items()}})
    fraction=np.array([row["open_fraction_lower_bound"] for row in rows])
    final_mask=seconds>=seconds[-1]-CONDITION["final_hold_seconds"]-1e-8
    passing=fraction>=CONDITION["minimum_open_fraction"]
    settled=np.logical_and.accumulate(passing[::-1])[::-1]
    first=np.flatnonzero(settled)
    final_poses={}
    for path in paths:
        j=paths.index(path)
        p=poses[-1,j]
        verts=groups[path]@rotation(p[3:]).T+p[:3]
        final_poses[path]={"position_m":p[:3].tolist(),"quaternion_xyzw":p[3:].tolist(),"geometry_world_min_m":verts.min(axis=(0,1)).tolist(),"geometry_world_max_m":verts.max(axis=(0,1)).tolist()}
    summary={
        "result_directory":str(directory),
        "condition":CONDITION,
        "method":"Union of clipped per-geometry projected bounds transformed by actual recorded body poses. Conservative lower bound on open area, with static scene geometry included.",
        "sampling":"Every recorded sample. The final window is every sample within final_hold_seconds of the last. No unrecorded pose is substituted or animated.",
        "input_sha256":sha256(frozen),
        "poses_sha256":sha256(directory/"recording/poses.npz"),
        "feedback_sha256":sha256(directory/"feedback.json"),
        "recorded_samples":len(rows),
        "recorded_time_range_s":[float(seconds[0]),float(seconds[-1])],
        "initial_recorded_open_fraction_lower_bound":float(fraction[0]),
        "final_open_fraction_lower_bound":float(fraction[-1]),
        "minimum_open_fraction_in_final_window":float(fraction[final_mask].min()),
        "final_window_samples":int(final_mask.sum()),
        "useful_opening_condition_met":bool(passing[final_mask].all()),
        "first_pass_and_hold_to_end_s":float(seconds[first[0]]) if len(first) else None,
        "final_body_geometry":final_poses,
        "joint_anchor_errors":hinge_errors(stage,paths,poses),
        "geometry_counts":{key:len(value) for key,value in groups.items()},
        "limitations":"Projected bounds can count empty space within individual shapes as blocked. This makes area conservative. Pose and geometric clearance records do not establish structural adequacy, contact safety or actuator sizing. Continuous physical behavior between solver samples is not independently observed.",
    }
    output.mkdir(parents=True,exist_ok=False)
    with (output/"clearance.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (output/"summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    (output/"geometry_inventory.json").write_text(json.dumps(labels,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({key:summary[key] for key in ["result_directory","useful_opening_condition_met","final_open_fraction_lower_bound","minimum_open_fraction_in_final_window","first_pass_and_hold_to_end_s","joint_anchor_errors"]},indent=2))
    return summary


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("result",type=Path,help="engine result directory")
    parser.add_argument("out",type=Path,help="new directory for the measurement")
    args=parser.parse_args()
    measure(args.result.resolve(),args.out.resolve())
