# Debug Session: Docker Desktop Out-of-Space Crash & Service Disabled

## Symptom
Docker Desktop crashed and fails to start with:
`write C:\Users\venka\AppData\Local\Docker\log\vm\init.log: There is not enough space on the disk.`

Running `docker ps` returns:
`Error response from daemon: Docker Desktop is unable to start` or connection refused on named pipe.

---

## Evidence Gathered
1. **Disk Space Check**: C: drive had exactly **0 B** of free space remaining (225.9 GB total).
2. **Docker WSL Virtual Disk Size**: `C:\Users\venka\AppData\Local\Docker\wsl\disk\docker_data.vhdx` is **66.88 GB** in size.
3. **Temp Directory Size**: `C:\Users\venka\AppData\Local\Temp` had **3.21 GB** of files.
4. **Large Leftover File**: Found a leftover PyTorch wheel installer `torch-2.5.1+cu121-cp312-cp312-win_amd64.whl` taking **2.33 GB** in the Temp directory.
5. **Past WebP Recordings**: Found **250 MB** of WebP recordings from past conversation IDs.
6. **Windows Service Status**: `com.docker.service` (Docker Desktop Service) is **Stopped** and its startup type is set to **Disabled**.
7. **WSL State**: `docker-desktop` distro is **Stopped**.

---

## Actions Taken & Space Reclaimed
We ran a cleanup script that successfully deleted:
1. The **2.33 GB** PyTorch Wheel in the Temp folder.
2. The **250 MB** of past WebP recordings.
3. Over **500 MB** of Remote Desktop trace logs (`RdClientAutoTrace-*.etl`).
4. Miscellaneous temporary pip directories.

**Result**: Reclaimed **3.12 GB** of free space on C: drive (now C: has **3.15 GB** free).

---

## Hypotheses & Troubleshooting

| # | Hypothesis | Likelihood | Status |
|---|------------|------------|--------|
| 1 | Running out of space caused Docker VM to crash and fail to write logs | 100% | CONFIRMED (Reclaimed 3.12 GB) |
| 2 | `com.docker.service` is Disabled, preventing Docker Desktop from launching | 100% | CONFIRMED (StartType is Disabled) |
| 3 | Re-enabling and starting `com.docker.service` will restore Docker | 100% | REQUIRES ELEVATION (User Action) |

---

## Resolution Plan & Next Steps
Since Windows service configuration changes require Administrator privileges:

1. **User Action**: Open PowerShell as **Administrator** and run:
   ```powershell
   Set-Service -Name com.docker.service -StartupType Manual
   Start-Service com.docker.service
   ```
2. **User Action**: Start Docker Desktop from the Start Menu.
3. Once Docker Desktop is running and healthy (showing green status), notify the agent to resume the validation suite!
