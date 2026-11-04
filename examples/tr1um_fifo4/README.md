# tr1um_fifo4 — multi-cell RTL-to-GDS regression

4-deep FIFO taken from the TR-1um use cases, used to exercise LibreLane on a
100-instance design through detailed routing and KLayout signoff.

Verified status (run tag `ci`): flow exits 0, detailed routing 0 violations
(empty `*-openroad-detailedrouting/tr1um_fifo4.drc`), KLayout DRC 0 errors,
and the PDK KLayout LVS deck reports `TR10_LVS PASS` via
`flow/checks/test_klayout_lvs.sh`.

Run inside the tools container with the GPL patch mounted (see
`flow/patches/librelane/README.md`):

    docker run --rm \
      -v /grid/TR-1um_stdcell:/grid/TR-1um_stdcell \
      -v $PDK/flow/patches/librelane/gpl.tcl:/usr/local/lib/python3.12/dist-packages/librelane/scripts/openroad/gpl.tcl:ro \
      -w $PDK -e PDK_ROOT=$(dirname $PDK) -e PDK=TR10 \
      hpretl/iic-osic-tools:latest --skip \
      bash -lc 'bash flow/checks/run_librelane_lvs.sh tr1um_fifo4 tr1um_fifo4 ci'

## Why this design needs the special placement

The 1 um TR10 cells are 75.6 um tall and draw the n-well per cell (layer
140/0).  The deck enforces WN.S1 (>= 4 um) and WN.S7 (>= 12 um) spacing
between separate well polygons, so a normally spread placement that leaves
0 < gap < 12 um between cells violates them.  The reference TR-1um flow
(`flow/designs/tr1um_fifo4/manual_place_access.tcl`) solves this with a
deterministic sparse placement: every second row, all cells R0, and a wide
horizontal gap.

`manual_place.tcl` implements the same recipe on the R0 rows (y = 0 +
k*151.2 um) so it stays consistent with this PDK's orientation-aware M1 PDN
rails.  The patched `gpl.tcl` sources it instead of running RePlAce whenever
the design ships that file.

The LEF carry-over from the reference flow (`make_routing_obstructions.py`)
is applied in `libs.ref/TR10_fd_sc/lef/TR10_fd_sc.lef`: TIELO's real M1
output strap and the NOR2/NAND2/NAND3/NAND4 gate keep-outs are OBS so the
router cannot violate M1/V1 spacing next to them.

## Ports

All top-level signal pins are constrained to the North edge
(`pin_order.cfg`), keeping the East/West die margins free for the PDN tie
straps.  The top module has no power ports, hence
`IGNORE_DISCONNECTED_MODULES`.

## Notes

- `ERROR_ON_LVS_ERROR` is false: LibreLane's Netgen LVS uses Magic
  extraction and the PDK netgen setup explicitly says TR10 Netgen LVS is
  unsupported.  The authoritative check is the KLayout LVS assertion run by
  `run_librelane_lvs.sh`.
- `RUN_POST_GPL_DESIGN_REPAIR`, `RUN_POST_GRT_RESIZER_TIMING` and
  `RUN_ANTENNA_REPAIR` are off so no later step moves/inserts cells and
  breaks the deterministic sparse placement.
