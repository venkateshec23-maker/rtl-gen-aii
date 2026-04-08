import subprocess
import sys
import re

DOCKER_IMAGE = "efabless/openlane:latest"
PDK_WIN = r"C:\pdk"

REQUIRED = {
    "TECH_LEF":    "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.tlef",
    "CELL_LEF":    "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef",
    "LIB_TT":      "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib",
    "LIB_SS":      "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__ss_100C_1v60.lib",
    "CELL_GDS":    "/pdk/sky130A/libs.ref/sky130_fd_sc_hd/gds/sky130_fd_sc_hd.gds",
    "MAGIC_TECH":  "/pdk/sky130A/libs.tech/magic/sky130A.tech",
    "MAGIC_RC":    "/pdk/sky130A/libs.tech/magic/sky130A.magicrc",
    "NETGEN_SETUP":"/pdk/sky130A/libs.tech/netgen/sky130A_setup.tcl",
    "YOSYS":       "/usr/bin/yosys",
    "OPENROAD":    "/usr/bin/openroad",
    "MAGIC":       "/usr/bin/magic",
}


def win_to_docker(p):
    m = re.match(r"^([A-Za-z]):\\(.*)", p.replace("/", "\\"))
    return f"/{m.group(1).lower()}/{m.group(2).replace(chr(92), '/')}" if m else p


def main():
    print("\n=== RTL-Gen AI: OpenROAD Path Validator ===\n")

    try:
        r = subprocess.run(["docker", "info"],
                           capture_output=True, timeout=10)
        if r.returncode != 0:
            print("ERROR: Docker daemon is not running.")
            print("  Start Docker Desktop from the Windows Start Menu.")
            print("  Wait for the whale icon in the taskbar to stop animating.")
            sys.exit(1)
        print("Docker:  RUNNING")
    except FileNotFoundError:
        print("ERROR: docker command not found in PATH.")
        sys.exit(1)

    r2 = subprocess.run(["docker", "image", "inspect", DOCKER_IMAGE],
                        capture_output=True, timeout=10)
    if r2.returncode != 0:
        print(f"ERROR: Image {DOCKER_IMAGE} not found.")
        print(f"  Run: docker pull {DOCKER_IMAGE}")
        sys.exit(1)
    print(f"Image:   {DOCKER_IMAGE} PRESENT")
    print(f"\nChecking {len(REQUIRED)} paths inside Docker...\n")

    cmds = " ; ".join(
        f'[ -e "{p}" ] && echo "OK:{n}" || echo "MISS:{n}"'
        for n, p in REQUIRED.items()
    )
    docker_pdk = win_to_docker(PDK_WIN)
    cmd = ["docker", "run", "--rm",
           "-v", f"{docker_pdk}:/pdk",
           DOCKER_IMAGE, "/bin/sh", "-c", cmds]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    output = result.stdout + result.stderr

    missing = []
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("OK:"):
            print(f"  OK    {line[3:]}")
        elif line.startswith("MISS:"):
            name = line[5:]
            print(f"  MISS  {name}  <- {REQUIRED.get(name, '?')}")
            missing.append(name)

    print()
    if missing:
        print(f"RESULT: {len(missing)} path(s) missing.")
        print("Fix:    volare enable --pdk sky130 --pdk-root C:\\pdk bdc9412b")
        sys.exit(1)
    else:
        print("RESULT: ALL PATHS OK")
        print("\nRun the pipeline:")
        print("  python validate_pipeline.py")


if __name__ == "__main__":
    main()
