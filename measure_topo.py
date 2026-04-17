from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.topo import SingleSwitchTopo
from mininet.log import setLogLevel
from mininet.cli import CLI
import time, re, datetime

LOG_FILE = f"drop_results_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

def parse_ping_loss(output):
    m = re.search(r'(\d+)% packet loss', output)
    return int(m.group(1)) if m else -1

def run_ping(src, dst_ip, count=20):
    out = src.cmd(f"ping -c {count} -i 0.2 {dst_ip}")
    return parse_ping_loss(out), out

def log(msg, f):
    print(msg)
    f.write(msg + "\n")

def main():
    setLogLevel('warning')
    net = Mininet(
        topo=SingleSwitchTopo(k=3),
        controller=lambda name: RemoteController(name, ip='127.0.0.1', port=6633)
    )
    net.start()
    print("Waiting for POX to install flow rules...")
    time.sleep(4)

    h1, h2, h3 = net.get('h1', 'h2', 'h3')

    # Warm up MAC table — let all hosts learn each other
    # before drop rules interfere with measurement order
    print("Warming up MAC table (h2->h3 and h3->h2 first)...")
    h2.cmd("ping -c 3 -i 0.2 " + h3.IP())
    h3.cmd("ping -c 3 -i 0.2 " + h2.IP())
    h2.cmd("ping -c 3 -i 0.2 " + h1.IP())
    h3.cmd("ping -c 3 -i 0.2 " + h1.IP())
    time.sleep(1)

    with open(LOG_FILE, 'w') as f:
        log("=" * 50, f)
        log("  SDN Packet Drop Simulator — Results", f)
        log(f"  {datetime.datetime.now()}", f)
        log("=" * 50, f)

        pairs = [
            (h1, h2.IP(), "h1 -> h2 [DROP RULE ACTIVE — expect 100% loss]"),
            (h2, h1.IP(), "h2 -> h1 [no rule     — expect   0% loss]"),
            (h1, h3.IP(), "h1 -> h3 [no rule     — expect   0% loss]"),
            (h3, h1.IP(), "h3 -> h1 [no rule     — expect   0% loss]"),
        ]

        log("\n[Phase 1] Ping measurements", f)
        results = {}
        for src, ip, label in pairs:
            loss, raw = run_ping(src, ip)
            results[label] = loss
            log(f"  {label}: {loss}% loss", f)

        log("\n[Phase 2] Pass/Fail", f)
        log("-" * 50, f)
        all_pass = True
        for label, loss in results.items():
            ok = loss >= 90 if "DROP" in label else loss == 0
            status = "PASS" if ok else "FAIL"
            if not ok:
                all_pass = False
            log(f"  [{status}]  {label}: {loss}%", f)

        log("\n[Phase 3] Regression — flow table dump", f)
        log("-" * 50, f)
        flows = net.get('s1').cmd('ovs-ofctl dump-flows s1')
        log(flows, f)
        drop_present = "nw_src=10.0.0.1,nw_dst=10.0.0.2" in flows or "nw_src=10.0.0.1" in flows
        log(f"  Drop rule present in flow table: {drop_present}", f)
        log(f"  Regression test: {'PASS' if drop_present else 'FAIL'}", f)

        log("\n[Overall] " + ("ALL TESTS PASSED" if all_pass and drop_present else "SOME TESTS FAILED"), f)
        log(f"\n[Done] Results saved to: {LOG_FILE}", f)

    print("\nEntering Mininet CLI. Type 'exit' when done.")
    CLI(net)
    net.stop()

if __name__ == '__main__':
    main()
