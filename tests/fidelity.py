"""Fidelity check: runs Krux simulator sequences on the official desktop
simulator and on the web simulator core, and compares LCD screenshots.

    python3 tests/fidelity.py <krux-dir> <work-dir> seq1 seq2 ...
"""
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from compare import compare  # noqa: E402

SEEDS = (
    '{"d668b8b7": {"version": 0, "key_iterations": 100000, "data": "haAyMxF'
    'mOVkBE5QixIeJl7P0dYKVeOiuhNodO+qyI2lA+veFUxcXben1OZvKOqTbWNI2Oj8SROTpooiS/4WJdA=="}, "a56dfd6c": '
    '{"version": 0, "key_iterations": 100000, "data": "PY9fBDrqtv2ZyZF47CsZ5QucxzXmOxaJJtjkngEQTfH'
    'LyLgHTQ3oX8AbZR6+UXBXZUB+eSOHwJZm1jCO8AaBxQ=="}}'
)
SETTINGS = '{"settings": {"i18n": {"locale": "en-US"}}}'
NO_SD = {"logo", "sign-message-at-address"}


def run_official(krux, seq, out):
    sim = os.path.join(krux, "simulator")
    shutil.rmtree(os.path.join(sim, "sd"), ignore_errors=True)
    shutil.rmtree(os.path.join(sim, "flash"), ignore_errors=True)
    os.makedirs(os.path.join(sim, "sd"))
    with open(os.path.join(sim, "sd", "settings.json"), "w") as f:
        f.write(SETTINGS + "\n")
    with open(os.path.join(sim, "sd", "seeds.json"), "w") as f:
        f.write(SEEDS + "\n")
    env = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy",
               PYTHONPATH=os.path.join(krux, "src") + ":" + sim)
    args = [os.path.join(krux, ".venv", "bin", "python"), os.path.join(HERE, "official_dump.py"), out,
            "--device", "maixpy_amigo", "--sequence", "sequences/%s.txt" % seq]
    if seq not in NO_SD:
        args.append("--sd")
    t = time.time()
    p = subprocess.run(args, cwd=sim, env=env, capture_output=True, text=True, timeout=900)
    return p.returncode, time.time() - t, p.stdout[-2000:] + p.stderr[-2000:]


def run_web(krux, seq, out):
    t = time.time()
    p = subprocess.run(["node", os.path.join(HERE, "run_one.mjs"),
                        os.path.join(krux, "simulator", "sequences", seq + ".txt"), out,
                        "en-US", "" if seq in NO_SD else "sd"],
                       capture_output=True, text=True, timeout=900)
    return p.returncode, time.time() - t, p.stdout[-3000:] + p.stderr[-2000:]


def main():
    krux, work = sys.argv[1], sys.argv[2]
    summary = {}
    for seq in sys.argv[3:]:
        ref, web = os.path.join(work, "ref", seq), os.path.join(work, "web", seq)
        shutil.rmtree(ref, ignore_errors=True)
        shutil.rmtree(web, ignore_errors=True)
        rc1, t1, log1 = run_official(krux, seq, ref)
        rc2, t2, log2 = run_web(krux, seq, web)
        res = compare(ref, web, os.path.join(work, "diff", seq)) if os.path.isdir(ref) else []
        same = sum(1 for _, n, _ in res if n == 0)
        print("%-34s official %3.0fs rc=%s | web %3.0fs rc=%s | %d/%d identical"
              % (seq, t1, rc1, t2, rc2, same, len(res)), flush=True)
        for name, n, bbox in res:
            if n != 0:
                print("      %-40s %s %s" % (name, n, bbox or ""), flush=True)
        if "CRASH" in log2 or '"crash":"' in log2:
            print("      web crash:", log2[-1500:])
        summary[seq] = {"identical": same, "total": len(res)}
    with open(os.path.join(work, "summary-%d.json" % int(time.time())), "w") as f:
        json.dump(summary, f, indent=1)


if __name__ == "__main__":
    main()
