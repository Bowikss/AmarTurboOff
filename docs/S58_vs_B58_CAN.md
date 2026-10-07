# S58 (M4) vs B58 (M240i) DME – CAN comparison

Source files (Autotuner bench backups):

| | A: M4 "amar" | B: M240i "moja" |
|---|---|---|
| Software | `MG1CS049_S58_F4C2L8R5B` | `MG1CS201_BX8TUE_R4C2L8PCB` |
| Hardware | `DME8XT0_35UP`, DME 8.6T | same |
| Bootloader | `MDG1_I35UP-CB_011_253.23` | same |
| CAN table (file offset) | `0x6E23E0`, 98 RX + 58 TX | `0x6E02B4`, 92 RX + 73 TX |

Reproduce with `python3 tools/can_matrix.py <A iflash0.bin> <B iflash0.bin>`.

## What was found

* Flash is mapped at `0x80000000`. The processor is an Infineon AURIX TC2xx with
  MultiCAN (registers at `0xF0018000` / `0xF0028000`).
* No code or config was found that sets up the on-chip FlexRay controller. All vehicle
  communication goes through CAN (the controllers listed below).
* CAN controllers in both files: one at 1 Mbit and three at 500 kbit. The message objects
  sit on controllers 1, 2 and 3 ("bus1/2/3" below). Which physical car network each one
  is has **not** been identified yet.
* RX/TX is taken from the AUTOSAR rule that all receive objects are numbered before
  transmit objects. This fits the object counts stored in the config. It hasn't been
  confirmed in the code.

## Differences

Only in S58 (A):

| Bus | Dir | IDs |
|---|---|---|
| bus1 | TX | `261 300 34A 37C 383 3BD 404 42F` |
| bus1 | RX | `194` |
| bus3 | TX | `021 023 025 027 041 043 045 047` |
| bus3 | RX | `010 020 022 024 026 040 042 044 046 384` |

Only in B58 (B):

| Bus | Dir | IDs |
|---|---|---|
| bus1 | TX | `2E9 352 3E4` |
| bus2 | TX | `08D 0AD 108 112 13E 192 1D9 1FA 239 2A5 2B7 2DB 2E7 2E8 32F 331 368 3A4 3B4 3CD 3D4 3E8 3E9 3EC 409 429 431 432` |
| bus2 | RX | `4FC 4FD 4FE 7EA 7FE` |

114 bus/direction/ID entries are the same in both.

## Interpretation (to be confirmed on the car)

* **Best candidates for the "M signals": the 8 bus1 TX IDs** that only the S58
  sends (`261 300 34A 37C 383 3BD 404 42F`). The S58 also listens to `194` on bus1,
  probably a request from an M module (for example the selected M mode).
* The bus3 pairs `020/021 … 046/047` look like request/response traffic with
  S58-specific engine devices. They are probably not needed on a B58 and should not be
  emulated without knowing what they are.
* IDs that exist in both files can still carry **different content** (signal layout,
  values for M modes). This table doesn't show that. Car logs are needed.

## Next steps

1. Find out which physical network bus1 is: put a CAN sniffer on the DME's CAN pairs
   and check where `0CF 181 1B3 228 …` (common bus1 TX IDs) appear.
2. Log a real S58 car (G80/G82 M3/M4 or G87 M2) on that network. Capture the 8 IDs
   in every mode (ignition, idle, M1/M2, Sport/Sport+, Drivelogic, xDrive modes) and
   note their cycle times.
3. Log your car with the M modules fitted. Read the ISTA faults and record which IDs
   the M modules expect but don't get.
4. Decode byte layout, alive counters and CRC (BMW E2E protection). The per-message
   CRC data IDs may be found in the S58 file.
5. Build a 2-channel CAN gateway between the B58 DME and that network: forward
   everything, add the missing M messages with content worked out from the B58's own
   messages. Start with mode and display signals only. Never fake torque or brake data.
