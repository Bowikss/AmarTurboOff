#!/usr/bin/env python3
"""Extract the CAN hardware-object table from a Bosch MG1 (BMW DME 8.6T, 35up)
iflash dump and optionally diff two dumps.

Usage:
    python3 can_matrix.py iflash0.bin                 # list one ECU
    python3 can_matrix.py s58_iflash0.bin b58_iflash0.bin   # diff A vs B

How the table is found:
  * Flash is mapped at 0x80000000.
  * The AUTOSAR Can driver config holds the controller baud-rate entries
    (1 Mbit + 3 x 500 kbit), preceded by 5 pointers. The last pointer is the
    hardware-object (HOH) table, the third points to the object counts.
  * Each HOH record is 20 bytes:
        u32 can_id, u32 mask, u16 hoh, u16 (ctrl<<8 | mo), u16 flags, u16 pdu, u16 flags2, u16 pad
  * AUTOSAR numbers all receive objects (HRH) before transmit objects (HTH),
    so hoh < rx_count is RX and the rest is TX.
"""
import struct
import sys

BASE = 0x80000000
BAUD_SIG = struct.pack("<IIII", 1000000, 1000000, 0x2F81, 0x2F81)


def load_table(path):
    b = open(path, "rb").read()
    sig = b.find(BAUD_SIG)
    if sig < 0:
        raise SystemExit(f"{path}: Can config signature not found")
    ptrs = struct.unpack_from("<5I", b, sig - 20)
    if not all(BASE <= p < BASE + len(b) for p in ptrs):
        raise SystemExit(f"{path}: unexpected Can config layout at {sig:#x}")
    rx_count, _, _, tx_count = struct.unpack_from("<4H", b, ptrs[2] - BASE)
    hoh_off = ptrs[4] - BASE
    rows = []
    for i in range(rx_count + tx_count):
        cid, mask, hoh, ctrl_mo, _flags, pdu = struct.unpack_from("<IIHHHH", b, hoh_off + 20 * i)
        rows.append({
            "id": cid,
            "ext": mask == 0x1FFFFFFF,
            "hoh": hoh,
            "bus": ctrl_mo >> 8,
            "dir": "RX" if hoh < rx_count else "TX",
            "pdu": pdu,
        })
    return rows, hoh_off, rx_count, tx_count


def fmt_id(r):
    return f"{r['id']:08X}" if r["ext"] else f"{r['id']:03X}"


def keyset(rows):
    return {(r["bus"], r["dir"], fmt_id(r)) for r in rows}


def main():
    if len(sys.argv) not in (2, 3):
        raise SystemExit(__doc__)
    tables = []
    for p in sys.argv[1:]:
        rows, off, rx, tx = load_table(p)
        print(f"{p}: HOH table @ file {off:#x}, {rx} RX + {tx} TX objects")
        tables.append(rows)
    if len(tables) == 1:
        for bus, d, cid in sorted(keyset(tables[0])):
            print(f"bus{bus} {d} {cid}")
        return
    a, b = (keyset(t) for t in tables)
    for title, s in (("only in A", a - b), ("only in B", b - a)):
        print(f"\n{title}:")
        for bus in sorted({k[0] for k in s}):
            for d in ("RX", "TX"):
                ids = sorted(k[2] for k in s if k[0] == bus and k[1] == d)
                if ids:
                    print(f"  bus{bus} {d}: {' '.join(ids)}")
    print(f"\ncommon: {len(a & b)}")


if __name__ == "__main__":
    main()
