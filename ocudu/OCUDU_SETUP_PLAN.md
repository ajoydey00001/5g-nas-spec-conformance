# OCUDU Setup Plan (Linux laptop)

Source: https://docs.ocudu.org/user_manual/installation/ (fetched 2026-10-12)
Repo: https://gitlab.com/ocudu/ocudu.git

## 0. Goal and chosen path

Build the OCUDU 5G gNB from source and prove it works end to end on one laptop,
with no radio hardware:

```
Open5GS core (docker)  <-->  OCUDU gNB  <--ZMQ virtual radio-->  srsUE
```

- ZMQ replaces the SDR, so no USRP is needed.
- Recommended OS: **Ubuntu 24.04 LTS** (22.04 also supported).
- Work directory used below: `~/ocudu-lab`

Total time: about 2-4 hours, mostly compile time.

---

## 1. Pre-flight checks

```bash
lsb_release -a          # Ubuntu 22.04 or later
uname -r                # kernel version
nproc                   # CPU cores
free -h                 # RAM: 8 GB min, 16 GB better
df -h ~                 # need ~20 GB free
gcc --version           # docs require gcc >= 15.2.0 OR clang >= 14
```

Compiler decision:
- gcc 15.2 or newer: use the default build commands.
- older gcc (Ubuntu 22.04 = gcc 11, 24.04 = gcc 13): use **clang** (step 2b).

Realtime kernel: the docs say OCUDU "requires a Linux-based OS with realtime kernel support".
For a ZMQ test on a laptop the normal kernel is fine. For real radios later, install a
low-latency/RT kernel (Ubuntu: `sudo apt install linux-lowlatency`, or Ubuntu Pro `realtime` kernel).

```bash
mkdir -p ~/ocudu-lab && cd ~/ocudu-lab
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y git
```

---

## 2. Build tools and dependencies

### 2a. Core packages (from docs)

```bash
sudo apt-get install -y cmake make gcc g++ pkg-config libmbedtls-dev libsctp-dev libyaml-cpp-dev libgtest-dev
```

Optional but useful:

```bash
sudo apt-get install -y ccache            # faster rebuilds
sudo apt-get install -y libeigen3-dev     # only for DOA estimation (off by default)
```

### 2b. Compiler fallback (only if gcc < 15.2)

```bash
sudo apt-get install -y clang
clang --version        # must be >= 14
```

Then add this to every OCUDU `cmake` command in step 5:
`-DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++`

### 2c. FFT library (pick one, FFTW is simplest)

```bash
sudo apt-get install -y libfftw3-dev
```

Alternatives in the docs: Intel oneMKL (Intel CPUs), AOCL-FFTZ 5.2 (AMD), ARMPL 24.10 (ARM).
Not needed for this assignment.

---

## 3. ZeroMQ (virtual radio)

ZMQ is **off by default** in OCUDU. Install it **before** building OCUDU.

```bash
sudo apt-get install -y libzmq3-dev
```

If the package is missing or too old, build from source instead:

```bash
cd ~/ocudu-lab
git clone https://github.com/zeromq/libzmq.git
cd libzmq && ./autogen.sh && ./configure && make -j$(nproc) && sudo make install && sudo ldconfig
cd ~/ocudu-lab
git clone https://github.com/zeromq/czmq.git
cd czmq && ./autogen.sh && ./configure && make -j$(nproc) && sudo make install && sudo ldconfig
```

(Source build needs `sudo apt-get install -y autoconf automake libtool`.)

UHD (USRP driver, v4.6.0.0) is only for real Split 8 radios. **Skip it.**

---

## 4. Clone OCUDU

```bash
cd ~/ocudu-lab
git clone https://gitlab.com/ocudu/ocudu.git
cd ocudu
git log -1 --oneline     # record the commit for your report
```

---

## 5. Build OCUDU with ZMQ

```bash
cd ~/ocudu-lab/ocudu
mkdir build && cd build
cmake ../ -DENABLE_EXPORT=ON -DENABLE_ZEROMQ=ON
# clang users: cmake ../ -DENABLE_EXPORT=ON -DENABLE_ZEROMQ=ON -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++
```

**Check the cmake output** for a line saying ZeroMQ was found. If it is missing, fix step 3,
delete `build/`, and run cmake again.

```bash
make -j$(nproc)
```

RAM tip: if the build gets killed or the laptop freezes, use `make -j2` or `make -j4`.

Other build variants from the docs (not needed here):
- Split 7.2 only: `cmake -DDU_SPLIT_TYPE=SPLIT_7_2 ../`
- Split 8 only: `cmake -DDU_SPLIT_TYPE=SPLIT_8 ../`

---

## 6. Verify the build

```bash
cd ~/ocudu-lab/ocudu/build
make test -j$(nproc)
ls -l apps/gnb/gnb          # the gNB binary
./apps/gnb/gnb --help | head
```

Optional system-wide install (lets you run `gnb` from anywhere):

```bash
sudo make install
```

Save the `make test` summary line for your report.

---

## 7. Docker + Open5GS core

Install docker (Ubuntu packages):

```bash
sudo apt-get install -y docker.io docker-compose-v2
sudo usermod -aG docker $USER
newgrp docker               # or log out and back in
docker run hello-world
```

(If those packages are unavailable, follow https://docs.docker.com/engine/install/ubuntu/.)

Check that the subscriber entry in `ocudu/docker/open5gs/open5gs.env` matches the UE:

```
SUBSCRIBER_DB=001010123456780,00112233445566778899aabbccddeeff,opc,63bfa50ee6523365ff14c1f45f88737d,8000,9,10.45.1.2
```

Start the core (terminal 1):

```bash
cd ~/ocudu-lab/ocudu/docker
docker compose up --build 5gc
```

---

## 8. Build srsUE (software UE)

srsUE comes from srsRAN_4G (version 23.11 or later). Build it **after** ZMQ is installed.

```bash
sudo apt-get install -y build-essential cmake libfftw3-dev libmbedtls-dev \
  libboost-program-options-dev libconfig++-dev libsctp-dev
cd ~/ocudu-lab
git clone https://github.com/srsran/srsRAN_4G.git
cd srsRAN_4G && mkdir build && cd build
cmake ../            # output should mention ZEROMQ found
make -j$(nproc)
ls srsue/src/srsue
```

If the build stops on compiler warnings with a newer gcc, retry with `cmake ../ -DENABLE_WERROR=OFF`.

---

## 9. Config files

Get both from the OCUDU docs tutorial "Using srsUE": https://docs.ocudu.org/tutorials/srsue/
(download links on that page). Also check `ls ~/ocudu-lab/ocudu/configs | grep -i zmq`.

```bash
mkdir -p ~/ocudu-lab/configs
# save gnb_zmq.yaml and ue_zmq.conf here
```

Key parts to confirm:

`gnb_zmq.yaml`
```yaml
ru_sdr:
  device_driver: zmq
  device_args: tx_port=tcp://127.0.0.1:2000,rx_port=tcp://127.0.0.1:2001,base_srate=11.52e6
  srate: 11.52
  tx_gain: 0
  rx_gain: 0
```

`ue_zmq.conf`
```
[rf]
freq_offset = 0
tx_gain = 50
rx_gain = 40
srate = 11.52e6
nof_antennas = 1
device_name = zmq
device_args = tx_port=tcp://127.0.0.1:2001,rx_port=tcp://127.0.0.1:2000,base_srate=11.52e6

[usim]
mode = soft
algo = milenage
opc  = 63BFA50EE6523365FF14C1F45F88737D
k    = 00112233445566778899aabbccddeeff
imsi = 001010123456780
imei = 353490069873319

[gw]
netns = ue1
ip_devname = tun_srsue
ip_netmask = 255.255.255.0
```

Ports must cross over: gNB tx 2000 = UE rx 2000, gNB rx 2001 = UE tx 2001.

---

## 10. Run end to end

Order matters: **core, then gNB, then UE.**

Once (before the UE):

```bash
sudo ip netns add ue1
sudo ip netns list
```

Terminal 1 - core (already running from step 7).

Terminal 2 - gNB:

```bash
cd ~/ocudu-lab/ocudu/build/apps/gnb
sudo ./gnb -c ~/ocudu-lab/configs/gnb_zmq.yaml
```

Wait until it connects to the AMF (N2/NG setup OK).

Terminal 3 - UE:

```bash
cd ~/ocudu-lab/srsRAN_4G/build/srsue/src
sudo ./srsue ~/ocudu-lab/configs/ue_zmq.conf
```

Success: UE console shows a PDU session IP like `10.45.1.2`.
In the gNB console, type `t` + Enter to show live per-UE metrics.

Terminal 4 - routes and ping:

```bash
sudo ip ro add 10.45.0.0/16 via 10.53.1.2
sudo ip netns exec ue1 ip route add default via 10.45.1.1 dev tun_srsue
sudo ip netns exec ue1 ping -c 10 10.45.1.1     # uplink: UE -> core
ping -c 10 10.45.1.2                            # downlink: core -> UE
```

Optional performance tuning (sets CPU governor to performance):

```bash
cd ~/ocudu-lab/ocudu && sudo ./scripts/ocudu_performance
```

Stop order: Ctrl+C the UE, then the gNB, then `docker compose down` in `ocudu/docker`.

---

## 11. Troubleshooting

| Problem | Fix |
|---|---|
| cmake: compiler too old | Use clang (step 2b), delete `build/`, rerun cmake |
| ZMQ not found in cmake output | Install `libzmq3-dev`, delete `build/`, rerun cmake |
| Build killed / laptop freezes | Out of RAM; use `make -j2` |
| gNB cannot reach AMF | Is the `5gc` container up? `docker ps`; check AMF addr in `gnb_zmq.yaml` |
| UE never attaches | Start order wrong, or ZMQ ports not crossed, or IMSI/K/OPc mismatch with `open5gs.env` |
| `tun_srsue` missing in ping | Namespace `ue1` not created before UE start |
| Ping fails | Check both routes; `sudo ip netns exec ue1 route -n` |

Docs troubleshooting page: https://docs.ocudu.org/user_manual/troubleshooting/

Limits of srsUE: FDD bands only (15 kHz SCS), 5/10/15/20 MHz, no handover. It is for proof-of-concept only.

---

## 12. Evidence to show Imtiaz sir

- [ ] `lsb_release -a`, `uname -r`, compiler version
- [ ] OCUDU commit hash (`git log -1 --oneline`)
- [ ] cmake output line showing ZeroMQ found
- [ ] `make test` summary (pass count)
- [ ] gNB console: NG setup with AMF successful
- [ ] UE console: attached with PDU session IP
- [ ] gNB `t` metrics screenshot
- [ ] Uplink and downlink ping output
- [ ] Short notes on problems hit and how they were fixed

---

## 13. References

- Installation: https://docs.ocudu.org/user_manual/installation/
- Running: https://docs.ocudu.org/user_manual/running/
- srsUE tutorial (ZMQ end to end): https://docs.ocudu.org/tutorials/srsue/
- Tuning: https://docs.ocudu.org/tutorials/tuning/
- Example configs: https://gitlab.com/ocudu/ocudu/-/tree/dev/configs
- srsRAN_4G: https://github.com/srsran/srsRAN_4G

## Moving this folder to the Linux laptop

Copy the whole `ocudu_setup/` folder by USB, or with
`scp -r ocudu_setup/ user@linux-laptop:~/`, then open `OCUDU_SETUP_PLAN.md` there.
