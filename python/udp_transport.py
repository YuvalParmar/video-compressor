"""Low-latency UDP transport for semantic video frames on a local mesh.

The transport deliberately drops incomplete frames instead of retransmitting
them. This bounds queueing latency when a Wi-Fi Direct or local-AP hop is
congested. The OS remains responsible for creating the hotspot/peer link.
"""

from __future__ import annotations

import socket
import struct
import time
from dataclasses import dataclass


MAGIC = 0x53
HEADER = struct.Struct("!BBHHBB")
HEADER_SIZE = HEADER.size  # 8 bytes
FLAG_ROI = 0x01
FLAG_KEYFRAME = 0x02
MAX_DATAGRAM = 1200


@dataclass(frozen=True)
class DatagramHeader:
    packet_type: int
    flags: int
    frame_sequence: int
    offset_units: int
    packet_index: int
    packet_count: int

    @property
    def offset(self) -> int:
        return self.offset_units * 16

    @property
    def is_roi(self) -> bool:
        return bool(self.flags & FLAG_ROI)

    def encode(self) -> bytes:
        if not 0 <= self.frame_sequence <= 0xFFFF:
            raise ValueError("frame sequence must fit in uint16")
        if not 0 <= self.offset <= 0xFFFF * 16 or self.offset % 16:
            raise ValueError("packet offset must be a multiple of 16 bytes")
        if not 0 <= self.packet_index < self.packet_count <= 0xFF:
            raise ValueError("packet index/count must fit in uint8")
        return HEADER.pack(
            MAGIC,
            ((self.packet_type & 0x0F) << 4) | (self.flags & 0x0F),
            self.frame_sequence,
            self.offset_units,
            self.packet_index,
            self.packet_count,
        )

    @classmethod
    def decode(cls, data: bytes) -> "DatagramHeader":
        if len(data) < HEADER_SIZE:
            raise ValueError("UDP datagram is shorter than its 8-byte header")
        magic, kind_flags, sequence, offset_units, index, count = HEADER.unpack_from(data)
        if magic != MAGIC:
            raise ValueError("invalid semantic UDP packet magic")
        if count == 0 or index >= count:
            raise ValueError("invalid packet index/count")
        return cls(
            packet_type=kind_flags >> 4,
            flags=kind_flags & 0x0F,
            frame_sequence=sequence,
            offset_units=offset_units,
            packet_index=index,
            packet_count=count,
        )


@dataclass(frozen=True)
class ReceivedFrame:
    sequence: int
    payload: bytes
    roi_packets: int
    packet_count: int


class FramePacketizer:
    def __init__(self, mtu: int = MAX_DATAGRAM) -> None:
        if mtu <= HEADER_SIZE or mtu > 65535:
            raise ValueError("MTU must be between 9 and 65535 bytes")
        self.payload_size = ((mtu - HEADER_SIZE) // 16) * 16
        if self.payload_size == 0:
            raise ValueError("MTU must leave at least 16 bytes for aligned payload")

    def packetize(
        self,
        payload: bytes,
        sequence: int,
        roi: bool = False,
        keyframe: bool = False,
        packet_type: int = 1,
    ) -> list[bytes]:
        if not payload:
            raise ValueError("cannot packetize an empty frame")
        packet_count = (len(payload) + self.payload_size - 1) // self.payload_size
        if packet_count > 255:
            raise ValueError("frame exceeds the 255-packet UDP frame limit")
        flags = (FLAG_ROI if roi else 0) | (FLAG_KEYFRAME if keyframe else 0)
        packets: list[bytes] = []
        for index in range(packet_count):
            offset = index * self.payload_size
            chunk = payload[offset:offset + self.payload_size]
            header = DatagramHeader(
                packet_type, flags, sequence & 0xFFFF, offset // 16, index, packet_count
            )
            packets.append(header.encode() + chunk)
        return packets


class FrameAssembler:
    """Reassemble only complete frames, evicting stale frames immediately."""

    def __init__(self, frame_timeout: float = 0.08, max_pending_frames: int = 2) -> None:
        if frame_timeout <= 0 or max_pending_frames < 1:
            raise ValueError("frame timeout and pending-frame limit must be positive")
        self.frame_timeout = frame_timeout
        self.max_pending_frames = max_pending_frames
        self._pending: dict[int, tuple[float, dict[int, bytes], int, int]] = {}
        self.dropped_frames = 0
        self.dropped_packets = 0

    def add_datagram(self, datagram: bytes, now: float | None = None) -> ReceivedFrame | None:
        timestamp = time.monotonic() if now is None else now
        self.expire(timestamp)
        try:
            header = DatagramHeader.decode(datagram)
        except ValueError:
            self.dropped_packets += 1
            return None
        payload = datagram[HEADER_SIZE:]
        if header.offset + len(payload) > 0xFFFF * 16:
            self.dropped_packets += 1
            return None
        if header.frame_sequence not in self._pending:
            if len(self._pending) >= self.max_pending_frames:
                oldest = min(self._pending, key=lambda sequence: self._pending[sequence][0])
                del self._pending[oldest]
                self.dropped_frames += 1
            self._pending[header.frame_sequence] = (timestamp, {}, header.packet_count, 0)
        created, packets, packet_count, roi_packets = self._pending[header.frame_sequence]
        if header.packet_count != packet_count:
            self.dropped_packets += 1
            return None
        if header.packet_index in packets:
            return None
        packets[header.packet_index] = payload
        if header.is_roi:
            roi_packets += 1
        self._pending[header.frame_sequence] = (created, packets, packet_count, roi_packets)
        if len(packets) != packet_count:
            return None
        assembled = b"".join(packets[index] for index in range(packet_count))
        del self._pending[header.frame_sequence]
        return ReceivedFrame(header.frame_sequence, assembled, roi_packets, packet_count)

    def expire(self, now: float | None = None) -> None:
        timestamp = time.monotonic() if now is None else now
        expired = [
            sequence for sequence, (created, *_rest) in self._pending.items()
            if timestamp - created >= self.frame_timeout
        ]
        for sequence in expired:
            del self._pending[sequence]
            self.dropped_frames += 1


class UdpFrameSender:
    def __init__(
        self,
        destination: tuple[str, int],
        mtu: int = MAX_DATAGRAM,
        socket_timeout: float = 0.0,
    ) -> None:
        self.destination = destination
        self.packetizer = FramePacketizer(mtu)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(socket_timeout)

    def send_frame(
        self, payload: bytes, sequence: int, roi: bool = False, keyframe: bool = False
    ) -> int:
        sent = 0
        for packet in self.packetizer.packetize(payload, sequence, roi, keyframe):
            try:
                self.socket.sendto(packet, self.destination)
                sent += 1
            except (BlockingIOError, OSError):
                # UDP has no retransmission path; skip the rest of this frame.
                break
        return sent

    def close(self) -> None:
        self.socket.close()


class UdpFrameReceiver:
    def __init__(self, bind: tuple[str, int], timeout: float = 0.0) -> None:
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1 << 20)
        self.socket.bind(bind)
        self.socket.settimeout(timeout)
        self.assembler = FrameAssembler()

    def receive(self) -> ReceivedFrame | None:
        try:
            datagram, _address = self.socket.recvfrom(MAX_DATAGRAM + 64)
        except socket.timeout:
            self.assembler.expire()
            return None
        return self.assembler.add_datagram(datagram)

    def close(self) -> None:
        self.socket.close()
