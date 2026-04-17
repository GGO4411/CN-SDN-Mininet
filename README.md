# SDN Packet Drop Simulator

**SRN:** PES1UG24CS167 &nbsp;|&nbsp; **Name:** Gandhar Gokhale &nbsp;|&nbsp; **Course:** Computer Networks

A Software Defined Networking project that simulates selective packet loss using OpenFlow flow rules installed via a custom POX controller. Built and tested on Mininet with Open vSwitch.

---

## Project Overview

This project demonstrates how an SDN controller can programmatically install drop rules on a virtual switch to selectively block traffic between specific hosts — while allowing all other traffic to flow normally. It covers rule installation, packet loss measurement, behavioral evaluation, and regression testing.

### What Was Built

| Component | Description |
|-----------|-------------|
| `packet_drop.py` | Custom POX controller with L2 MAC learning and selective drop rules |
| `measure_topo.py` | Automated Mininet test harness that measures loss, evaluates behavior, and runs regression checks |

---

## Network Topology

```
    h1 (10.0.0.1)
         |
    [s1] OVS Switch  ←→  POX Controller (port 6633)
         |
    h2 (10.0.0.2)
         |
    h3 (10.0.0.3)
```

Single switch, 3 hosts, remote POX controller.

---

## How It Works

### Flow Rule Priority Hierarchy

| Priority | Match | Action |
|----------|-------|--------|
| 210 | h1 → h2, ICMP echo reply (type 0) | FLOOD (allow replies) |
| 200 | h1 → h2, ICMP echo request (type 8) | **DROP** |
| 50 | Everything else (per learned MAC pair) | Forward to specific port |

The drop rule targets only ICMP echo **requests** from h1 to h2. A separate allow rule at higher priority permits h1's echo **replies** back to h2, so h2→h1 traffic still works correctly. All other traffic is handled by an L2 MAC learning mechanism via `PacketIn` events.

### Regression Test

After the ping measurements, the test script dumps the OVS flow table using `ovs-ofctl dump-flows s1` and verifies that the drop rule is still present — confirming it persists correctly across the test run.

---

## Setup & Prerequisites

- Ubuntu VM (tested on Ubuntu 24 with Python 3.12)
- [Mininet](http://mininet.org/) installed
- [POX controller](https://github.com/noxrepo/pox) cloned to `~/pox`
- Open vSwitch (`ovs-ofctl` available)

---

## Running the Project

### Step 1 — Place the controller file

Copy `packet_drop.py` into POX's extensions directory:

```bash
cp packet_drop.py ~/pox/ext/packet_drop.py
```


### Step 2 — Start the POX controller (Terminal 1)

```bash
cd ~/pox && python3 pox.py packet_drop
```

<img width="802" height="177" alt="image" src="https://github.com/user-attachments/assets/fc6e19ee-b2b5-4879-91d0-4fa0fbcf7996" />

Expected output:
```
INFO:packet_drop:DROP rule installed: h1->h2 ICMP echo requests only
INFO:packet_drop:ALLOW rule installed: h1->h2 ICMP echo replies
INFO:core:POX 0.7.0 (gar) is up.
```

### Step 3 — Clean any existing Mininet state (Terminal 2)

```bash
sudo mn -c
```
<img width="1471" height="658" alt="image" src="https://github.com/user-attachments/assets/f3b10ccb-3c2c-4316-b902-2f9d953d399a" />


### Step 4 — Run the automated test (Terminal 2)

```bash
sudo mn --controller=remote --topo single,3
```
Terminal 2:
<img width="980" height="424" alt="image" src="https://github.com/user-attachments/assets/692e294c-8694-4934-80cc-0bb3e20cb67b" />
Terminal 1: 

<img width="807" height="309" alt="image" src="https://github.com/user-attachments/assets/a20fc7ea-2f44-46d5-8603-6852fc1235a1" />


This will run 20 pings across 4 host pairs, evaluate pass/fail, dump the flow table, and save results to a timestamped file.

### Step 5 — Manual verification (inside Mininet CLI)

After the automated tests complete, the script drops you into a Mininet CLI. Run:

```bash
pingall
h1 ping -c 5 h2        # Should show 100% loss
h1 ping -c 5 h3        # Should show 0% loss
h2 ping -c 5 h1        # Should show 0% loss
sh ovs-ofctl dump-flows s1
exit
```
<img width="722" height="264" alt="image" src="https://github.com/user-attachments/assets/e5a33815-7573-4e04-b194-29803bb2547e" />

<img width="736" height="263" alt="image" src="https://github.com/user-attachments/assets/bb21f4fc-cf4a-4f59-989a-3c6fdd338de0" />
<img width="734" height="639" alt="image" src="https://github.com/user-attachments/assets/6125c8a8-2fcb-4bf2-866f-58a6bd621b93" />

<img width="1475" height="139" alt="image" src="https://github.com/user-attachments/assets/b0dba7ac-a788-4b8d-9c14-e6af3202abe3" />


### Step 6 — View saved results

```bash
cat ~/drop_results_*.txt
```

---

## Test Results

### Expected Behavior

| Test | Expected Loss | Reason |
|------|--------------|--------|
| h1 → h2 | ~100% | Drop rule active (ICMP type 8 blocked) |
| h2 → h1 | 0% | No drop rule; MAC learned correctly |
| h1 → h3 | 0% | No rule for this pair |
| h3 → h1 | 0% | No rule for this pair |
| Regression | PASS | Drop rule present in flow table |

### Sample Output

```
==================================================
  SDN Packet Drop Simulator — Results
==================================================

[Phase 1] Ping measurements
  h1 -> h2 [DROP RULE ACTIVE — expect 100% loss]: 100% loss
  h2 -> h1 [no rule     — expect   0% loss]: 0% loss
  h1 -> h3 [no rule     — expect   0% loss]: 0% loss
  h3 -> h1 [no rule     — expect   0% loss]: 0% loss

[Phase 2] Pass/Fail
  [PASS]  h1 -> h2 [DROP RULE ACTIVE — expect 100% loss]: 100%
  [PASS]  h2 -> h1 [no rule     — expect   0% loss]: 0%
  [PASS]  h1 -> h3 [no rule     — expect   0% loss]: 0%
  [PASS]  h3 -> h1 [no rule     — expect   0% loss]: 0%

[Phase 3] Regression — flow table dump
  Drop rule present in flow table: True
  Regression test: PASS

[Overall] ALL TESTS PASSED
```
<img width="1480" height="688" alt="image" src="https://github.com/user-attachments/assets/4f0a10b5-03d6-45b4-8f2a-a9989aa8f83c" />


### Flow Table (from `ovs-ofctl dump-flows s1`)

```
priority=200,icmp,nw_src=10.0.0.1,nw_dst=10.0.0.2,icmp_type=8,icmp_code=0  actions=drop
priority=210,icmp,nw_src=10.0.0.1,nw_dst=10.0.0.2,icmp_type=0,icmp_code=0  actions=FLOOD
priority=50, in_port=s1-eth2, dl_src=..., dl_dst=...                         actions=output:s1-eth1
...
```
<img width="1475" height="139" alt="image" src="https://github.com/user-attachments/assets/05a9a6b7-966f-4c99-b4d2-e8073beb08e0" />

---

## Project Requirements Coverage

| Requirement | How It's Met |
|-------------|-------------|
| Install drop rules | `_install_rules()` in `packet_drop.py` installs ICMP type 8 drop at priority 200 on switch connect |
| Select specific flows | Rule targets only `nw_src=10.0.0.1, nw_dst=10.0.0.2` ICMP echo requests |
| Measure packet loss | `measure_topo.py` runs 20 pings per pair and parses `% packet loss` from output |
| Evaluate behavior | Phase 2 pass/fail logic checks expected vs actual loss for all 4 host pairs |
| Regression test | Phase 3 dumps OVS flow table and verifies drop rule string is present |

---

## Notes

- POX 0.7.0 runs with Python 3.12 warnings — these are harmless; functionality is unaffected.
- The drop rule targets ICMP type 8 specifically (echo request) rather than all IP traffic from h1 to h2. This is intentional: blocking all IP traffic would also block h1's echo replies to h2's pings, causing h2→h1 to appear broken even without a drop rule.
- To add more drop rules, modify the `_install_rules()` method in `packet_drop.py` and add additional `ofp_flow_mod` messages following the same pattern.
- Always run `sudo mn -c` between test runs to flush stale flow state.
