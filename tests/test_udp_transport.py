import pytest

from python.udp_transport import DatagramHeader, FrameAssembler, FramePacketizer, HEADER_SIZE


def test_header_is_eight_bytes_and_preserves_offset_metadata():
    header = DatagramHeader(1, 1, 42, 4, 0, 2)
    encoded = header.encode()
    assert len(encoded) == 8 == HEADER_SIZE
    decoded = DatagramHeader.decode(encoded)
    assert decoded.frame_sequence == 42
    assert decoded.offset == 64
    assert decoded.is_roi


def test_packetizer_reassembles_out_of_order_udp_packets():
    payload = bytes(range(250)) * 8
    packets = FramePacketizer(mtu=128).packetize(payload, sequence=7, roi=True)
    assembler = FrameAssembler()
    result = None
    for packet in reversed(packets):
        result = assembler.add_datagram(packet) or result
    assert result is not None
    assert result.sequence == 7
    assert result.payload == payload
    assert result.roi_packets == len(packets)


def test_incomplete_frames_expire_instead_of_accumulating_latency():
    packet = FramePacketizer().packetize(b"x" * 1300, sequence=1)[0]
    assembler = FrameAssembler(frame_timeout=0.1)
    assembler.add_datagram(packet, now=0.0)
    assembler.expire(now=0.2)
    assert assembler.dropped_frames == 1


def test_invalid_packet_count_is_rejected():
    with pytest.raises(ValueError):
        DatagramHeader(1, 0, 1, 0, 0, 0).encode()
