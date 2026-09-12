"""Atomic remote claim branch. No expiry takeover or existing-ref overwrite."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import uuid
from .io import read,write,sha,utc
from .contracts import validate_trial

def cmd(*args,env=None,input=None):
    return subprocess.check_output(["git",*args],env=env,input=input,text=True).strip()

def main(args):
    trial=validate_trial(read(args.trial))
    if cmd("status","--porcelain"): raise ValueError("clean committed checkout required")
    commit=cmd("rev-parse","HEAD")
    remote=cmd("remote","get-url","origin")
    if remote not in ("https://github.com/zetanaut/tmd-global-fit-lab.git","git@github.com:zetanaut/tmd-global-fit-lab.git"):
        raise ValueError("origin is not the designated study repository")
    ref="refs/heads/claims/"+trial["trial_id"]
    if cmd("ls-remote","--heads","origin",ref): raise ValueError("trial already claimed; never steal or reset it")
    receipt=dict(schema="tmd-claim-v1",trial_id=trial["trial_id"],trial_sha256=sha(args.trial),code_commit=commit,owner=args.owner,nonce=uuid.uuid4().hex,claimed_utc=utc(),remote_ref=ref)
    with tempfile.TemporaryDirectory(prefix="tmd-claim-") as d:
        env=os.environ.copy(); env["GIT_INDEX_FILE"]=str(Path(d)/"index")
        cmd("read-tree",commit,env=env)
        blob=cmd("hash-object","-w","--stdin",input=json.dumps(receipt,sort_keys=True)+"\n")
        cmd("update-index","--add","--cacheinfo",f"100644,{blob},claims/{trial['trial_id']}.json",env=env)
        tree=cmd("write-tree",env=env)
        claim_commit=cmd("commit-tree",tree,"-p",commit,"-m",f"Claim {trial['trial_id']} {receipt['nonce']}")
    # Unique sibling commits make concurrent claims non-fast-forward. An empty
    # expected remote ref additionally makes the create-only precondition explicit.
    subprocess.run(["git","push",f"--force-with-lease={ref}:","origin",f"{claim_commit}:{ref}"],check=True)
    if cmd("ls-remote","--heads","origin",ref).split()[0]!=claim_commit: raise ValueError("remote claim readback failed")
    receipt["claim_commit"]=claim_commit
    write(args.out,receipt)
    print(args.out)

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--trial",type=Path,required=True);p.add_argument("--owner",required=True);p.add_argument("--out",type=Path,required=True)
    main(p.parse_args())
