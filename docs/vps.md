 free -h
               total        used        free      shared  buff/cache   available
Mem:           954Mi       340Mi       129Mi       5.0Mi       636Mi       613Mi
Swap:             0B          0B          0B
ubuntu@instance-20260829-0025:~$ nproc
2
ubuntu@instance-20260829-0025:~$ df -h /
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        45G  1.4G   43G   3% /
ubuntu@instance-20260829-0025:~$ free -h
               total        used        free      shared  buff/cache   available
Mem:           954Mi       340Mi       128Mi       5.0Mi       637Mi       613Mi
Swap:             0B          0B          0B
ubuntu@instance-20260829-0025:~$ sudo fallocate -l 2G /swapfile
ubuntu@instance-20260829-0025:~$ sudo chmod 600 /swapfile
ubuntu@instance-20260829-0025:~$ sudo mkswap /swapfile
Setting up swapspace version 1, size = 2 GiB (2147479552 bytes)
no label, UUID=67eddb38-60a2-47ff-a945-df8e38d69f2a
ubuntu@instance-20260829-0025:~$ sudo swapon /swapfile
ubuntu@instance-20260829-0025:~$ free -h
               total        used        free      shared  buff/cache   available
Mem:           954Mi       341Mi       126Mi       5.0Mi       638Mi       612Mi
Swap:          2.0Gi          0B       2.0Gi
ubuntu@instance-20260829-0025:~$ echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
/swapfile none swap sw 0 0
ubuntu@instance-20260829-0025:~$ sudo swapon --show
NAME      TYPE SIZE USED PRIO
/swapfile file   2G   0B   -2
ubuntu@instance-20260829-0025:~$ sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
free -h
fallocate: fallocate failed: Text file busy
mkswap: error: /swapfile is mounted; will not make swapspace
swapon: /swapfile: swapon failed: Device or resource busy
               total        used        free      shared  buff/cache   available
Mem:           954Mi       341Mi       126Mi       5.0Mi       638Mi       612Mi
Swap:          2.0Gi          0B       2.0Gi
ubuntu@instance-20260829-0025:~$ free -h
               total        used        free      shared  buff/cache   available
Mem:           954Mi       341Mi       126Mi       5.0Mi       638Mi       612Mi
Swap:          2.0Gi          0B       2.0Gi
ubuntu@instance-20260829-0025:~$ sudo swapon --show
NAME      TYPE SIZE USED PRIO
/swapfile file   2G   0B   -2
ubuntu@instance-20260829-0025:~$ grep swapfile /etc/fstab
/swapfile none swap sw 0 0
ubuntu@instance-20260829-0025:~$ sudo apt update
Get:1 http://security.ubuntu.com/ubuntu noble-security InRelease [126 kB]
Hit:2 http://ap-hyderabad-1-ad-1.clouds.archive.ubuntu.com/ubuntu noble InRelease
Get:3 http://ap-hyderabad-1-ad-1.clouds.archive.ubuntu.com/ubuntu noble-updates InRelease [126 kB]
Get:4 http://ap-hyderabad-1-ad-1.clouds.archive.ubuntu.com/ubuntu noble-backports InRelease [126 kB]
Fetched 378 kB in 4s (105 kB/s)
Reading package lists... Done
Building dependency tree... Done
Reading state information... Done
18 packages can be upgraded. Run 'apt list --upgradable' to see them.
ubuntu@instance-20260829-0025:~$ sudo apt upgrade -y
Reading package lists... Done
Building dependency tree... Done
Reading state information... Done
Calculating upgrade... Done
The following packages will be upgraded:
  curl libcurl3t64-gnutls libcurl4t64 libp11-kit0 libpam-modules libpam-modules-bin libpam-runtime libpam0g libproc2-0
  libpython3.12-minimal libpython3.12-stdlib libssl3t64 openssl perl-base procps python3.12 python3.12-minimal xxd
18 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
12 standard LTS security updates
Need to get 6659 kB/13.1 MB of archives.
After this operation, 13.3 kB of additional disk space will be used.
Get:1 http://ap-hyderabad-1-ad-1.clouds.archive.ubuntu.com/ubuntu noble-updates/main amd64 python3.12 amd64 3.12.3-1ubuntu0.16 [651 kB]
Get:2 http://ap-hyderabad-1-ad-1.clouds.archive.ubuntu.com/ubuntu noble-updates/main amd64 libpython3.12-stdlib amd64 3.12.3-1ubuntu0.16 [2070 kB]
Get:3 http://ap-hyderabad-1-ad-1.clouds.archive.ubuntu.com/ubuntu noble-updates/main amd64 python3.12-minimal amd64 3.12.3-1ubuntu0.16 [2335 kB]
Get:4 http://ap-hyderabad-1-ad-1.clouds.archive.ubuntu.com/ubuntu noble-updates/main amd64 libpython3.12-minimal amd64 3.12.3-1ubuntu0.16 [838 kB]
Get:5 http://ap-hyderabad-1-ad-1.clouds.archive.ubuntu.com/ubuntu noble-updates/main amd64 libproc2-0 amd64 2:4.0.4-4ubuntu3.3 [58.9 kB]
Get:6 http://ap-hyderabad-1-ad-1.clouds.archive.ubuntu.com/ubuntu noble-updates/main amd64 procps amd64 2:4.0.4-4ubuntu3.3 [707 kB]
Fetched 6659 kB in 5s (1395 kB/s)
debconf: delaying package configuration, since apt-utils is not installed
(Reading database ... 49305 files and directories currently installed.)
Preparing to unpack .../perl-base_5.38.2-3.2ubuntu0.4_amd64.deb ...
Unpacking perl-base (5.38.2-3.2ubuntu0.4) over (5.38.2-3.2ubuntu0.3) ...
Setting up perl-base (5.38.2-3.2ubuntu0.4) ...
(Reading database ... 49305 files and directories currently installed.)
Preparing to unpack .../libpam0g_1.5.3-5ubuntu5.7_amd64.deb ...
Unpacking libpam0g:amd64 (1.5.3-5ubuntu5.7) over (1.5.3-5ubuntu5.6) ...
Setting up libpam0g:amd64 (1.5.3-5ubuntu5.7) ...
debconf: unable to initialize frontend: Dialog
debconf: (No usable dialog-like program is installed, so the dialog based frontend cannot be used. at /usr/share/perl5/Debconf/FrontEnd/Dialog.pm line 79.)
debconf: falling back to frontend: Readline
debconf: unable to initialize frontend: Readline
debconf: (Can't locate Term/ReadLine.pm in @INC (you may need to install the Term::ReadLine module) (@INC entries checked: /etc/perl /usr/local/lib/x86_64-linux-gnu/perl/5.38.2 /usr/local/share/perl/5.38.2 /usr/lib/x86_64-linux-gnu/perl5/5.38 /usr/share/perl5 /usr/lib/x86_64-linux-gnu/perl-base /usr/lib/x86_64-linux-gnu/perl/5.38 /usr/share/perl/5.38 /usr/local/lib/site_perl) at /usr/share/perl5/Debconf/FrontEnd/Readline.pm line 8.)
debconf: falling back to frontend: Teletype
(Reading database ... 49305 files and directories currently installed.)
Preparing to unpack .../libpam-modules-bin_1.5.3-5ubuntu5.7_amd64.deb ...
Unpacking libpam-modules-bin (1.5.3-5ubuntu5.7) over (1.5.3-5ubuntu5.6) ...
Setting up libpam-modules-bin (1.5.3-5ubuntu5.7) ...
pam_namespace.service is a disabled or a static unit not running, not starting it.
(Reading database ... 49305 files and directories currently installed.)
Preparing to unpack .../libpam-modules_1.5.3-5ubuntu5.7_amd64.deb ...
debconf: unable to initialize frontend: Dialog
debconf: (No usable dialog-like program is installed, so the dialog based frontend cannot be used. at /usr/share/perl5/Debconf/FrontEnd/Dialog.pm line 79.)
debconf: falling back to frontend: Readline
debconf: unable to initialize frontend: Readline
debconf: (Can't locate Term/ReadLine.pm in @INC (you may need to install the Term::ReadLine module) (@INC entries checked: /etc/perl /usr/local/lib/x86_64-linux-gnu/perl/5.38.2 /usr/local/share/perl/5.38.2 /usr/lib/x86_64-linux-gnu/perl5/5.38 /usr/share/perl5 /usr/lib/x86_64-linux-gnu/perl-base /usr/lib/x86_64-linux-gnu/perl/5.38 /usr/share/perl/5.38 /usr/local/lib/site_perl) at /usr/share/perl5/Debconf/FrontEnd/Readline.pm line 8.)
debconf: falling back to frontend: Teletype
Unpacking libpam-modules:amd64 (1.5.3-5ubuntu5.7) over (1.5.3-5ubuntu5.6) ...
Setting up libpam-modules:amd64 (1.5.3-5ubuntu5.7) ...
(Reading database ... 49305 files and directories currently installed.)
Preparing to unpack .../libssl3t64_3.0.13-0ubuntu3.15_amd64.deb ...
Unpacking libssl3t64:amd64 (3.0.13-0ubuntu3.15) over (3.0.13-0ubuntu3.12) ...
Setting up libssl3t64:amd64 (3.0.13-0ubuntu3.15) ...
(Reading database ... 49305 files and directories currently installed.)
Preparing to unpack .../python3.12_3.12.3-1ubuntu0.16_amd64.deb ...
Unpacking python3.12 (3.12.3-1ubuntu0.16) over (3.12.3-1ubuntu0.15) ...
Preparing to unpack .../libpython3.12-stdlib_3.12.3-1ubuntu0.16_amd64.deb ...
Unpacking libpython3.12-stdlib:amd64 (3.12.3-1ubuntu0.16) over (3.12.3-1ubuntu0.15) ...
Preparing to unpack .../python3.12-minimal_3.12.3-1ubuntu0.16_amd64.deb ...
Unpacking python3.12-minimal (3.12.3-1ubuntu0.16) over (3.12.3-1ubuntu0.15) ...
Preparing to unpack .../libpython3.12-minimal_3.12.3-1ubuntu0.16_amd64.deb ...
Unpacking libpython3.12-minimal:amd64 (3.12.3-1ubuntu0.16) over (3.12.3-1ubuntu0.15) ...
Preparing to unpack .../libpam-runtime_1.5.3-5ubuntu5.7_all.deb ...
Unpacking libpam-runtime (1.5.3-5ubuntu5.7) over (1.5.3-5ubuntu5.6) ...
Setting up libpam-runtime (1.5.3-5ubuntu5.7) ...
debconf: unable to initialize frontend: Dialog
debconf: (No usable dialog-like program is installed, so the dialog based frontend cannot be used. at /usr/share/perl5/Debconf/FrontEnd/Dialog.pm line 79.)
debconf: falling back to frontend: Readline
debconf: unable to initialize frontend: Readline
debconf: (Can't locate Term/ReadLine.pm in @INC (you may need to install the Term::ReadLine module) (@INC entries checked: /etc/perl /usr/local/lib/x86_64-linux-gnu/perl/5.38.2 /usr/local/share/perl/5.38.2 /usr/lib/x86_64-linux-gnu/perl5/5.38 /usr/share/perl5 /usr/lib/x86_64-linux-gnu/perl-base /usr/lib/x86_64-linux-gnu/perl/5.38 /usr/share/perl/5.38 /usr/local/lib/site_perl) at /usr/share/perl5/Debconf/FrontEnd/Readline.pm line 8.)
debconf: falling back to frontend: Teletype
(Reading database ... 49305 files and directories currently installed.)
Preparing to unpack .../libp11-kit0_0.25.3-4ubuntu2.2_amd64.deb ...
Unpacking libp11-kit0:amd64 (0.25.3-4ubuntu2.2) over (0.25.3-4ubuntu2.1) ...
Setting up libp11-kit0:amd64 (0.25.3-4ubuntu2.2) ...
(Reading database ... 49305 files and directories currently installed.)
Preparing to unpack .../0-libproc2-0_2%3a4.0.4-4ubuntu3.3_amd64.deb ...
Unpacking libproc2-0:amd64 (2:4.0.4-4ubuntu3.3) over (2:4.0.4-4ubuntu3.2) ...
Preparing to unpack .../1-procps_2%3a4.0.4-4ubuntu3.3_amd64.deb ...
Unpacking procps (2:4.0.4-4ubuntu3.3) over (2:4.0.4-4ubuntu3.2) ...
Preparing to unpack .../2-openssl_3.0.13-0ubuntu3.15_amd64.deb ...
Unpacking openssl (3.0.13-0ubuntu3.15) over (3.0.13-0ubuntu3.12) ...
Preparing to unpack .../3-xxd_2%3a9.1.0016-1ubuntu7.20_amd64.deb ...
Unpacking xxd (2:9.1.0016-1ubuntu7.20) over (2:9.1.0016-1ubuntu7.19) ...
Preparing to unpack .../4-curl_8.5.0-2ubuntu10.13_amd64.deb ...
Unpacking curl (8.5.0-2ubuntu10.13) over (8.5.0-2ubuntu10.12) ...
Preparing to unpack .../5-libcurl4t64_8.5.0-2ubuntu10.13_amd64.deb ...
Unpacking libcurl4t64:amd64 (8.5.0-2ubuntu10.13) over (8.5.0-2ubuntu10.12) ...
Preparing to unpack .../6-libcurl3t64-gnutls_8.5.0-2ubuntu10.13_amd64.deb ...
Unpacking libcurl3t64-gnutls:amd64 (8.5.0-2ubuntu10.13) over (8.5.0-2ubuntu10.12) ...
Setting up libcurl4t64:amd64 (8.5.0-2ubuntu10.13) ...
Setting up libpython3.12-minimal:amd64 (3.12.3-1ubuntu0.16) ...
Setting up libcurl3t64-gnutls:amd64 (8.5.0-2ubuntu10.13) ...
Setting up xxd (2:9.1.0016-1ubuntu7.20) ...
Setting up libproc2-0:amd64 (2:4.0.4-4ubuntu3.3) ...
Setting up procps (2:4.0.4-4ubuntu3.3) ...
Setting up curl (8.5.0-2ubuntu10.13) ...
Setting up openssl (3.0.13-0ubuntu3.15) ...
Setting up python3.12-minimal (3.12.3-1ubuntu0.16) ...
Setting up libpython3.12-stdlib:amd64 (3.12.3-1ubuntu0.16) ...
Setting up python3.12 (3.12.3-1ubuntu0.16) ...
Processing triggers for systemd (255.4-1ubuntu8.17) ...
Processing triggers for libc-bin (2.39-0ubuntu8.8) ...
ubuntu@instance-20260829-0025:~$ sudo apt autoremove -y
Reading package lists... Done
Building dependency tree... Done
Reading state information... Done
0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
ubuntu@instance-20260829-0025:~$ sudo apt autoclean
Reading package lists... Done
Building dependency tree... Done
Reading state information... Done
ubuntu@instance-20260829-0025:~$ [ -f /var/run/reboot-required ] && echo "REBOOT REQUIRED" || echo "NO REBOOT REQUIRED"
NO REBOOT REQUIRED
ubuntu@instance-20260829-0025:~$ timedatectl
               Local time: Sat 2026-08-29 20:31:16 UTC
           Universal time: Sat 2026-08-29 20:31:16 UTC
                 RTC time: Sat 2026-08-29 20:31:16
                Time zone: Etc/UTC (UTC, +0000)
System clock synchronized: yes
              NTP service: active
          RTC in local TZ: no
ubuntu@instance-20260829-0025:~$ sudo timedatectl set-timezone Asia/Dhaka
ubuntu@instance-20260829-0025:~$ timedatectl
               Local time: Sun 2026-08-30 02:32:14 +06
           Universal time: Sat 2026-08-29 20:32:14 UTC
                 RTC time: Sat 2026-08-29 20:32:14
                Time zone: Asia/Dhaka (+06, +0600)
System clock synchronized: yes
              NTP service: active
          RTC in local TZ: no
ubuntu@instance-20260829-0025:~$ date
Sun Aug 30 02:32:38 +06 2026
ubuntu@instance-20260829-0025:~$ sudo ufw status
sudo: ufw: command not found
ubuntu@instance-20260829-0025:~$ sudo ufw status
sudo: ufw: command not found
ubuntu@instance-20260829-0025:~$ sudo apt install ufw -y
Reading package lists... Done
Building dependency tree... Done
Reading state information... Done
Suggested packages:
  rsyslog
The following packages will be REMOVED:
  iptables-persistent netfilter-persistent
The following NEW packages will be installed:
  ufw
0 upgraded, 1 newly installed, 2 to remove and 0 not upgraded.
Need to get 169 kB of archives.
After this operation, 780 kB of additional disk space will be used.
Get:1 http://ap-hyderabad-1-ad-1.clouds.archive.ubuntu.com/ubuntu noble/main amd64 ufw all 0.36.2-6 [169 kB]
Fetched 169 kB in 1s (148 kB/s)
debconf: delaying package configuration, since apt-utils is not installed
(Reading database ... 49305 files and directories currently installed.)
Removing iptables-persistent (1.0.20) ...
Removing netfilter-persistent (1.0.20) ...
Selecting previously unselected package ufw.
(Reading database ... 49286 files and directories currently installed.)
Preparing to unpack .../archives/ufw_0.36.2-6_all.deb ...
Unpacking ufw (0.36.2-6) ...
Setting up ufw (0.36.2-6) ...
debconf: unable to initialize frontend: Dialog
debconf: (No usable dialog-like program is installed, so the dialog based frontend cannot be used. at /usr/share/perl5/Debconf/FrontEnd/Dialog.pm line 79.)
debconf: falling back to frontend: Readline
debconf: unable to initialize frontend: Readline
debconf: (Can't locate Term/ReadLine.pm in @INC (you may need to install the Term::ReadLine module) (@INC entries checked: /etc/perl /usr/local/lib/x86_64-linux-gnu/perl/5.38.2 /usr/local/share/perl/5.38.2 /usr/lib/x86_64-linux-gnu/perl5/5.38 /usr/share/perl5 /usr/lib/x86_64-linux-gnu/perl-base /usr/lib/x86_64-linux-gnu/perl/5.38 /usr/share/perl/5.38 /usr/local/lib/site_perl) at /usr/share/perl5/Debconf/FrontEnd/Readline.pm line 8.)
debconf: falling back to frontend: Teletype

Creating config file /etc/ufw/before.rules with new version

Creating config file /etc/ufw/before6.rules with new version

Creating config file /etc/ufw/after.rules with new version

Creating config file /etc/ufw/after6.rules with new version
Created symlink /etc/systemd/system/multi-user.target.wants/ufw.service → /usr/lib/systemd/system/ufw.service.
ubuntu@instance-20260829-0025:~$ sudo ufw status
Status: inactive
ubuntu@instance-20260829-0025:~$ sudo ufw allow OpenSSH
Rules updated
Rules updated (v6)
ubuntu@instance-20260829-0025:~$ sudo ufw allow 80/tcp
Rules updated
Rules updated (v6)
ubuntu@instance-20260829-0025:~$ sudo ufw allow 443/tcp
Rules updated
Rules updated (v6)
ubuntu@instance-20260829-0025:~$ sudo ufw enable
Command may disrupt existing ssh connections. Proceed with operation (y|n)? y
Firewall is active and enabled on system startup
ubuntu@instance-20260829-0025:~$ sudo ufw status verbose
Status: active
Logging: on (low)
Default: deny (incoming), allow (outgoing), disabled (routed)
New profiles: skip

To                         Action      From
--                         ------      ----
22/tcp (OpenSSH)           ALLOW IN    Anywhere
80/tcp                     ALLOW IN    Anywhere
443/tcp                    ALLOW IN    Anywhere
22/tcp (OpenSSH (v6))      ALLOW IN    Anywhere (v6)
80/tcp (v6)                ALLOW IN    Anywhere (v6)
443/tcp (v6)               ALLOW IN    Anywhere (v6)

ubuntu@instance-20260829-0025:~$ sudo ufw status verbose
Status: active
Logging: on (low)
Default: deny (incoming), allow (outgoing), disabled (routed)
New profiles: skip

To                         Action      From
--                         ------      ----
22/tcp (OpenSSH)           ALLOW IN    Anywhere
80/tcp                     ALLOW IN    Anywhere
443/tcp                    ALLOW IN    Anywhere
22/tcp (OpenSSH (v6))      ALLOW IN    Anywhere (v6)
80/tcp (v6)                ALLOW IN    Anywhere (v6)
443/tcp (v6)               ALLOW IN    Anywhere (v6)

ubuntu@instance-20260829-0025:~$ sudo apt install ufw -y
Reading package lists... Done
Building dependency tree... Done
Reading state information... Done
ufw is already the newest version (0.36.2-6).
0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.

---

## Application hosting (next steps)

VPS baseline is complete (swap, UFW, amd64). Application deploy SOP: `docs/steps/blueprint_production.md`.

| Step | Command / action |
|------|------------------|
| OCI Security List | Allow inbound **22, 80, 443** (in addition to UFW) |
| Install Docker | `sudo apt install -y docker.io docker-compose-v2` |
| Clone repo | `git clone … ~/guideagent && cd ~/guideagent` |
| Env | `cp .env.production.example .env.production` → fill hosted URLs/keys |
| DNS | Point `WANDR_API_HOST` → VPS public IP |
| Migrate | `./ops/migrate.sh` |
| Reindex | If 384→768 cutover: `docker run --rm --env-file .env.production $IMAGE python scripts/index_places.py …` |
| Deploy | `./ops/deploy.sh` or `./ops/deploy.sh <git-sha>` after GHCR push |
| Smoke | `./ops/health.sh` then planner SSE (§7 in blueprint) |

**CI/CD:** GitHub Actions `deploy` workflow (`workflow_dispatch`) — set secrets `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`, optional `VPS_APP_DIR`. VPS must `docker login ghcr.io` once.

**Do not** `docker build` on the 1GB VPS — pull from GHCR or transfer a prebuilt image.

**Staging FE on another origin** (e.g. Vercel → `api.exporaai.xyz`): production cookies must be `SameSite=None; Secure` (see blueprint §6). Env-only restarts are not enough — ship a new API image after that change; clear browser cookies after deploy.

---

## Geo upstream troubleshooting

Destination search and prepare depend on external geo APIs. Auth/Redis/Qdrant healthy does **not** mean search works.

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `GET /api/v1/destinations/search?q=London` → **502** `external_service_error` (service=`nominatim`) | Public Nominatim blocked UA or cloud IP | Set real `NOMINATIM_USER_AGENT` (email); if still 403, set `NOMINATIM_BASE_URL` + `NOMINATIM_API_KEY` to a Nominatim-compatible free tier |
| Search → **404** `not_found` | True miss or geocode timeout | Try a known city; check `SEARCH_GEOCODE_TIMEOUT_SECONDS` |
| Search 200 but prepare/places empty | Overpass 4xx from VPS | Set free `OPENTRIPMAP_API_KEY` / `GEOAPIFY_API_KEY`; prefer `PLACES_SOURCES=opentripmap,geoapify` |

Probe from the API container (after env change, restart API so process geocode cache clears):

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml exec api \
  python -c 'import httpx,os; u=os.environ["NOMINATIM_BASE_URL"]+"/search"; r=httpx.get(u,params={"q":"London","format":"json","limit":1},headers={"User-Agent":os.environ["NOMINATIM_USER_AGENT"]},timeout=10); print(r.status_code); print(r.text[:300])'
```
