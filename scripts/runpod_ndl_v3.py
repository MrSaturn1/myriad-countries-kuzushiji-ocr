"""Run the full NDL古典籍OCR ver.3 on a rented RunPod GPU.

ver.3 needs an NVIDIA GPU with CUDA 12.1 / torch 2.1.1, so it can't run on an
Apple-silicon Mac. This script rents a small pod (no network volume), installs
ver.3 the same way its Dockerfile does, OCRs the scans and pulls the results
back. Steps are separate so a failure doesn't mean paying for a new pod:

    python3 -I scripts/runpod_ndl_v3.py up       # rent a pod, wait for SSH
    python3 -I scripts/runpod_ndl_v3.py setup    # install ver.3 + models
    python3 -I scripts/runpod_ndl_v3.py run      # upload scans, OCR, download
    python3 -I scripts/runpod_ndl_v3.py down     # terminate the pod
    python3 -I scripts/runpod_ndl_v3.py status

The API key is read from the file named by RUNPOD_KEY_FILE (default:
~/.config/runpod/api_key) and is never printed. A throwaway SSH key and the pod
state live in STATE_DIR, not in ~/.ssh.
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Each scan folder's vol*/ subfolders are uploaded as books named <prefix>_<vol>.
SCANS = {"waseda": ROOT / "童絵解万国噺 (1861) - Waseda 文庫11 a0380",
         "ndl": ROOT / "童絵解万国噺 (1861) - NDL 207-1695"}
NDL_MANIFESTS = [f"https://dl.ndl.go.jp/api/iiif/{pid}/manifest.json"
                 for pid in (2559375, 2559376, 2559377, 2559378)]
WASEDA_BASE = "https://archive.wul.waseda.ac.jp/kosho/bunko11/bunko11_a0380/"
OUT = ROOT / "ocr" / "ndl_v3"
KEY_FILE = Path(os.environ.get("RUNPOD_KEY_FILE",
                               "~/.config/runpod/api_key")).expanduser()
STATE_DIR = Path(os.environ.get("STATE_DIR", ROOT / "tools" / "runpod")).expanduser()
STATE = STATE_DIR / "pod.json"
SSH_KEY = STATE_DIR / "id_ed25519"

POD_NAME = "ndl-kotenocr-v3"
IMAGE = "runpod/pytorch:2.1.1-py3.10-cuda12.1.1-devel-ubuntu22.04"
# torch 2.1.1 supports up to Hopper (sm_90); Blackwell cards (5090, PRO 6000) won't work.
GPUS = ["NVIDIA RTX A4000", "NVIDIA RTX A5000", "NVIDIA GeForce RTX 3090",
        "NVIDIA GeForce RTX 4090", "NVIDIA L4", "NVIDIA RTX A6000", "NVIDIA A40"]

SETUP = r"""
set -euxo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq && apt-get install -y -qq libgl1 libglib2.0-0 zip unzip git wget >/dev/null
cd /root
[ -d kotenocr_cli ] || git clone --depth 1 https://github.com/ndl-lab/ndlkotenocr_cli.git kotenocr_cli
cd kotenocr_cli
pip install -q torch==2.1.1 torchvision==0.16.1 torchaudio==2.1.1 torchtext==0.16.1 \
    --index-url https://download.pytorch.org/whl/cu121
pip install -q -r requirements.txt
pip install -q mmcv==2.1.0 -f https://download.openmmlab.com/mmcv/dist/cu121/torch2.1/index.html
wget -q -nc https://lab.ndl.go.jp/dataset/ndlkotensekiocr/trocr/model-ver2.zip -P src/text_kotenseki_recognition/
wget -q -nc https://lab.ndl.go.jp/dataset/ndlkotensekiocr/layoutmodel/ndl_kotenseki_layout_ver3.pth -P src/ndl_kotenseki_layout/models/
(cd src/text_kotenseki_recognition && unzip -o -q model-ver2.zip)
python -c "import torch, mmcv, mmdet; print('torch', torch.__version__, 'cuda', torch.cuda.is_available(), torch.cuda.get_device_name(0)); print('mmcv', mmcv.__version__, 'mmdet', mmdet.__version__)"
echo SETUP_OK
"""

RUN = r"""
set -euxo pipefail
cd /root/kotenocr_cli
rm -rf /root/out
time python main.py infer /root/in /root/out -s b -a
find /root/out -name '*.txt' | wc -l
"""


def api_key() -> str:
    return KEY_FILE.read_text().strip()


def gql(query: str, variables: dict | None = None) -> dict:
    req = urllib.request.Request(
        "https://api.runpod.io/graphql",
        data=json.dumps({"query": query, "variables": variables or {}}).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {api_key()}",
                 "User-Agent": "ndl-kotenocr-runner"})
    with urllib.request.urlopen(req, timeout=60) as r:
        body = json.load(r)
    if body.get("errors"):
        raise RuntimeError("; ".join(e.get("message", str(e)) for e in body["errors"]))
    return body["data"]


def load_state() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def save_state(s: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(s, indent=2))


def ensure_ssh_key() -> str:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if not SSH_KEY.exists():
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", POD_NAME,
                        "-f", str(SSH_KEY)], check=True)
    return SSH_KEY.with_suffix(".pub").read_text().strip()


def pod_info(pod_id: str) -> dict | None:
    q = """query($id: String!) { pod(input: {podId: $id}) {
        id desiredStatus costPerHr machine { gpuDisplayName }
        runtime { uptimeInSeconds ports { ip isIpPublic privatePort publicPort type } } } }"""
    return gql(q, {"id": pod_id})["pod"]


def ssh_addr(pod: dict) -> tuple[str, int] | None:
    for p in ((pod or {}).get("runtime") or {}).get("ports") or []:
        if p["privatePort"] == 22 and p["isIpPublic"]:
            return p["ip"], p["publicPort"]
    return None


def ssh_cmd(extra: list[str] | None = None) -> list[str]:
    s = load_state()
    return ["ssh", "-i", str(SSH_KEY), "-p", str(s["port"]),
            "-o", "StrictHostKeyChecking=accept-new",
            "-o", f"UserKnownHostsFile={STATE_DIR / 'known_hosts'}",
            "-o", "ServerAliveInterval=30", "-o", "BatchMode=yes",
            # macOS ssh drops long uploads with "ssh_packet_write_poll: Result too large"
            # unless QoS marking is off.
            "-o", "IPQoS=none",
            *(extra or []), f"root@{s['ip']}"]


def remote(script: str) -> None:
    subprocess.run(ssh_cmd() + ["bash -s"], input=script.encode(), check=True)


def up() -> None:
    if load_state().get("pod_id"):
        sys.exit("A pod is already recorded in state; run `status` or `down` first.")
    pub = ensure_ssh_key()
    mutation = "mutation($input: PodFindAndDeployOnDemandInput) { podFindAndDeployOnDemand(input: $input) { id costPerHr } }"
    pod = None
    for cloud in ("COMMUNITY", "SECURE"):
        for gpu in GPUS:
            inp = {"cloudType": cloud, "gpuTypeId": gpu, "gpuCount": 1, "name": POD_NAME,
                   "imageName": IMAGE, "ports": "22/tcp", "containerDiskInGb": 40,
                   "volumeInGb": 0, "supportPublicIp": True, "startSsh": True,
                   "env": [{"key": "PUBLIC_KEY", "value": pub}]}
            try:
                pod = gql(mutation, {"input": inp})["podFindAndDeployOnDemand"]
            except RuntimeError as e:
                print(f"  {cloud} {gpu}: {e}")
                continue
            if pod:
                print(f"Deployed {pod['id']} on {cloud} {gpu} at ${pod['costPerHr']}/hr")
                save_state({"pod_id": pod["id"], "gpu": gpu, "cloud": cloud,
                            "cost_per_hr": pod["costPerHr"], "started": time.time()})
                break
        if pod:
            break
    if not pod:
        sys.exit("No GPU available in the list right now.")
    deadline = time.time() + 600
    while time.time() < deadline:
        info = pod_info(pod["id"])
        addr = ssh_addr(info)
        if addr:
            s = load_state()
            s.update(ip=addr[0], port=addr[1])
            save_state(s)
            # sshd may need a few more seconds after the port is published.
            for _ in range(30):
                if subprocess.run(ssh_cmd(["-o", "ConnectTimeout=10"]) + ["true"],
                                  capture_output=True).returncode == 0:
                    print(f"SSH ready at {addr[0]}:{addr[1]}")
                    return
                time.sleep(5)
        time.sleep(10)
    print("Pod did not become reachable in 10 min; terminating it.")
    down()
    sys.exit(1)


def setup() -> None:
    remote(SETUP)


def remote_fetch_script() -> str:
    """Shell script that makes the pod download the scans from the libraries.

    Uploading ~400 MB from the Mac kept dying with "ssh_packet_write_poll:
    Result too large", so the pod fetches the public images itself and only
    this small script crosses the SSH link. Layout: /root/in/img/<book>/pNNNN.jpg
    (input structure "b"), same file names as the local copies.
    """
    downloader = (ROOT / "scripts" / "download_iiif.py").read_text()
    lines = ["set -euo pipefail", "rm -rf /root/in && mkdir -p /root/in/img",
             "cat > /root/download_iiif.py <<'PYEOF'", downloader, "PYEOF"]
    for i, man in enumerate(NDL_MANIFESTS, 1):
        lines.append(f"python3 /root/download_iiif.py {man} /root/in/img/ndl_vol{i}")
    for vol, wid in (("vol1", "0001"), ("vol2", "0002")):
        base = f"{WASEDA_BASE}bunko11_a0380_{wid}/bunko11_a0380_{wid}_p"
        n = len(list((SCANS["waseda"] / vol).glob("p*.jpg")))
        lines += [f"mkdir -p /root/in/img/waseda_{vol}",
                  f"for i in $(seq -f %04g 1 {n}); do "
                  f"curl -sSf --retry 3 -o /root/in/img/waseda_{vol}/p$i.jpg {base}$i.jpg; sleep 0.3; done"]
    lines.append("for d in /root/in/img/*; do echo \"$d $(ls $d | wc -l)\"; done")
    return "\n".join(lines) + "\n"


def run() -> None:
    remote(remote_fetch_script())
    remote(RUN)
    fetch()


def fetch() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pull = subprocess.Popen(ssh_cmd() + ["tar czf - -C /root/out ."], stdout=subprocess.PIPE)
    subprocess.run(["tar", "xzf", "-", "-C", str(OUT)], stdin=pull.stdout, check=True)
    pull.wait()
    print(f"Results in {OUT}")


def down() -> None:
    s = load_state()
    if not s.get("pod_id"):
        print("No pod recorded.")
        return
    gql('mutation { podTerminate(input: {podId: "%s"}) }' % s["pod_id"])
    hrs = (time.time() - s.get("started", time.time())) / 3600
    print(f"Terminated {s['pod_id']} after {hrs:.2f} h (~${hrs * float(s.get('cost_per_hr') or 0):.2f})")
    STATE.unlink()


def status() -> None:
    s = load_state()
    if not s.get("pod_id"):
        print("No pod recorded.")
        return
    info = pod_info(s["pod_id"])
    hrs = (time.time() - s.get("started", time.time())) / 3600
    print(json.dumps({"pod": s["pod_id"], "gpu": s.get("gpu"), "cloud": s.get("cloud"),
                      "status": (info or {}).get("desiredStatus"), "ssh": ssh_addr(info),
                      "hours": round(hrs, 2), "cost_so_far": round(hrs * float(s.get("cost_per_hr") or 0), 2)},
                     indent=2))


if __name__ == "__main__":
    cmds = {"up": up, "setup": setup, "run": run, "fetch": fetch, "down": down, "status": status}
    if len(sys.argv) != 2 or sys.argv[1] not in cmds:
        sys.exit(__doc__)
    cmds[sys.argv[1]]()
