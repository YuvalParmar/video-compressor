import argparse

from python.udp_transport import UdpFrameReceiver


parser = argparse.ArgumentParser(description="Receive low-latency semantic UDP frames.")
parser.add_argument("--host", default="0.0.0.0")
parser.add_argument("--port", type=int, default=5000)
args = parser.parse_args()

receiver = UdpFrameReceiver((args.host, args.port), timeout=0.1)
print(f"Listening for semantic UDP frames on {args.host}:{args.port}")
try:
    while True:
        frame = receiver.receive()
        if frame is not None:
            print(
                f"frame={frame.sequence} packets={frame.packet_count} "
                f"roi_packets={frame.roi_packets} bytes={len(frame.payload)}"
            )
finally:
    receiver.close()
