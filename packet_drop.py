from pox.core import core
from pox.lib.util import dpidToStr
import pox.openflow.libopenflow_01 as of
from pox.lib.addresses import IPAddr

log = core.getLogger()

class PacketDropController(object):

    def __init__(self):
        core.openflow.addListeners(self)
        self.mac_to_port = {}

    def _handle_ConnectionUp(self, event):
        log.info("Switch %s connected", dpidToStr(event.dpid))
        self.mac_to_port[event.dpid] = {}
        self._install_rules(event)

    def _install_rules(self, event):
        msg = of.ofp_flow_mod()
        msg.priority = 200
        msg.match.dl_type = 0x0800
        msg.match.nw_proto = 1
        msg.match.nw_src = IPAddr("10.0.0.1")
        msg.match.nw_dst = IPAddr("10.0.0.2")
        msg.match.tp_src = 8
        msg.match.tp_dst = 0
        event.connection.send(msg)
        log.info("DROP rule installed: h1->h2 ICMP echo requests only")
        msg2 = of.ofp_flow_mod()
        msg2.priority = 210
        msg2.match.dl_type = 0x0800
        msg2.match.nw_proto = 1
        msg2.match.nw_src = IPAddr("10.0.0.1")
        msg2.match.nw_dst = IPAddr("10.0.0.2")
        msg2.match.tp_src = 0
        msg2.match.tp_dst = 0
        msg2.actions.append(of.ofp_action_output(port=of.OFPP_FLOOD))
        event.connection.send(msg2)
        log.info("ALLOW rule installed: h1->h2 ICMP echo replies")

    def _handle_PacketIn(self, event):
        packet = event.parsed
        dpid = event.dpid
        in_port = event.port
        self.mac_to_port[dpid][packet.src] = in_port
        if packet.dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][packet.dst]
            msg = of.ofp_flow_mod()
            msg.priority = 50
            msg.idle_timeout = 60
            msg.match.in_port = in_port
            msg.match.dl_src = packet.src
            msg.match.dl_dst = packet.dst
            msg.actions.append(of.ofp_action_output(port=out_port))
            event.connection.send(msg)
        else:
            out_port = of.OFPP_FLOOD
        pkt_out = of.ofp_packet_out()
        pkt_out.data = event.ofp
        pkt_out.in_port = in_port
        pkt_out.actions.append(of.ofp_action_output(port=out_port))
        event.connection.send(pkt_out)

    def _handle_ConnectionDown(self, event):
        log.info("Switch %s disconnected", dpidToStr(event.dpid))
        self.mac_to_port.pop(event.dpid, None)

def launch():
    core.registerNew(PacketDropController)
