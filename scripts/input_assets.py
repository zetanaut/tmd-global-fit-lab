#!/usr/bin/env python3
"""Pack/fetch immutable release assets; never put the numerical bundle in Git."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tmdlab.io import read,write,sha,within
from tmdlab.bundle import Bundle

REPO="zetanaut/tmd-global-fit-lab"

def pack(args):
    bundle=Bundle(args.bundle,verify_all=True);out=Path(args.out)
    out.mkdir(parents=True,exist_ok=False)
    names=["bundle.json",*sorted(bundle.index["files"])]
    groups=[[]];size=0
    for name in names:
        n=(bundle.root/name).stat().st_size
        if n>900*2**20: raise ValueError("single file exceeds asset partition target")
        if size+n>900*2**20: groups.append([]);size=0
        groups[-1].append(name);size+=n
    assets=[]
    for i,names in enumerate(groups):
        target=out/f"baseline-v1-{i:03d}.tar"
        with tarfile.open(target,"w") as tar:
            for name in names:
                source=within(bundle.root,name)
                info=tarfile.TarInfo("baseline-v1/"+name)
                info.size=source.stat().st_size;info.mode=0o644;info.mtime=0
                with source.open("rb") as f:tar.addfile(info,f)
        assets.append(dict(name=target.name,bytes=target.stat().st_size,sha256=sha(target)))
    write(args.lock,dict(schema="tmd-input-release-v1",repository=REPO,tag="inputs-baseline-v1",bundle_identity=bundle.index["identity"],bundle_json_sha256=sha(bundle.root/"bundle.json"),assets=assets,publication_status="prepared_not_uploaded"))
    print(args.lock)

def fetch(args):
    lock=read(args.lock);cache=Path(args.cache);dest=Path(args.dest)
    cache.mkdir(parents=True,exist_ok=True)
    if (dest/"baseline-v1").exists(): raise ValueError("destination already exists; verify it or choose a new destination")
    for item in lock["assets"]:
        path=cache/item["name"]
        if not path.exists():subprocess.run([args.gh,"release","download",lock["tag"],"--repo",lock["repository"],"--pattern",item["name"],"--dir",str(cache)],check=True)
        if path.stat().st_size!=item["bytes"] or sha(path)!=item["sha256"]:raise ValueError("asset hash/size failed")
    dest.mkdir(parents=True,exist_ok=True)
    for item in lock["assets"]:
        with tarfile.open(cache/item["name"],"r") as tar:
            for member in tar:
                if not member.isfile() or not member.name.startswith("baseline-v1/"):raise ValueError("non-regular/unexpected tar member")
                target=within(dest,member.name)
                if target.exists():raise ValueError("duplicate/overwriting tar member")
                target.parent.mkdir(parents=True,exist_ok=True)
                with tar.extractfile(member) as src,target.open("xb") as dst:shutil.copyfileobj(src,dst)
    if sha(dest/"baseline-v1/bundle.json")!=lock["bundle_json_sha256"]:raise ValueError("bundle manifest hash failed")
    bundle=Bundle(dest/"baseline-v1",verify_all=True)
    if bundle.index["identity"]!=lock["bundle_identity"]:raise ValueError("bundle identity failed")
    print(dest/"baseline-v1")

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest="command",required=True)
    a=sub.add_parser("pack");a.add_argument("--bundle",required=True);a.add_argument("--out",default="dist/input-assets");a.add_argument("--lock",default="data/baseline-v1.json")
    a=sub.add_parser("fetch");a.add_argument("--lock",default="data/baseline-v1.json");a.add_argument("--cache",default="artifacts/downloads");a.add_argument("--dest",default="inputs");a.add_argument("--gh",default="gh")
    args=p.parse_args();pack(args) if args.command=="pack" else fetch(args)
