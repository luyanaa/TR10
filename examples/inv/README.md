# inv — minimal RTL->GDS smoke design

`inv` is a single inverter (`assign y = ~a`) used to smoke-test the TR10
LibreLane flow end to end.  Run inside the IIC-OSIC docker image:

    docker run --rm \
      -v /grid/TR-1um_stdcell:/grid/TR-1um_stdcell \
      -v $PWD:/design -w /design \
      -e PDK_ROOT=/grid/TR-1um_stdcell/flow/pdk_root -e PDK=TR10 \
      hpretl/iic-osic-tools:latest --skip \
      bash -lc 'librelane --pdk-root $PDK_ROOT --pdk $PDK --manual-pdk \
                --run-tag smoke config.json'

Last verified status: flow exits 0; Netgen LVS reports "Circuits match
uniquely"; KLayout DRC 0 across all rule categories; and the PDK KLayout LVS
deck reports `TR10_LVS PASS` via `flow/checks/test_klayout_lvs.sh`.

## Config notes

- `PDN_CFG` points at `libs.tech/librelane/TR10_fd_sc/pdn_experiment.tcl`,
  which builds the M1 rail grid at the true cell PG bands.  See that file's
  header: TR10 cells put VDD at row_base+54.2..57.6 (18 um below the row
  top), so pdngen's boundary-based `-followpins` cannot power them; the
  rails are emitted with the odb API instead.
- Die 300x310 gives three 75.6 um rows; the design itself only fills the
  first two.  Rails are tied per net by vertical M1 straps in the die
  margins (outside the core), so this works for any row count.
- `LEFT_MARGIN_MULT`/`RIGHT_MARGIN_MULT` = 70 -> 7 um margins (site width is
  0.1 um), enough for the 3.4 um tie straps plus clearance.
- `KLAYOUT_CONFLICT_RESOLUTION` = `OverwriteCell`.  LibreLane's default
  `RenameCell` keeps the empty DEF placeholder cells and renames the real
  library GDS cells, so the streamed KLayout GDS contains empty cell bodies
  and KLayout DRC/LVS become vacuous.  `OverwriteCell` merges the real cell
  geometry.
- `RUN_MAGIC_DRC` = false.  The magic tech's DRC rules are coarse
  approximations (lambda 0.5 um; e.g. AA width 3.0 um vs the actual cell's
  1.85 um) and are not the PDK signoff path -- KLayout is.  Magic stream-out
  is still run because Magic SPICE extraction feeds the flow's Netgen LVS.
- `RUN_FILL_INSERTION`/`RUN_IRDROP_REPORT` are off: the smallest filler is
  5.4 um so tiny gaps cannot fill, and the rail grid is not a full IR grid.
- `IGNORE_DISCONNECTED_MODULES` = ["inv"]: the top module has no power pins.
- `ERROR_ON_PDN_VIOLATIONS` = false: OpenROAD's PSM check runs before
  placement, so it reports "no terminals" for every grid; LVS proves the
  connectivity instead.
- `ERROR_ON_XOR_ERROR` = false: magic reads the GDS onto its 0.5 um lambda
  grid ("Input off lambda grid by 3/5"), so the magic and KLayout views can
  never be geometrically identical.  The KLayout view is the signoff view.

## Known limitations

- The flow's Netgen LVS uses Magic SPICE extraction.  The PDK's own netgen
  setup says TR10 Netgen LVS is unsupported and points at the KLayout LVS
  deck; the comparison still runs and matches, but the authoritative LVS is
  `libs.tech/klayout/tech/lvs/run.lvs` + `05_Compare.lvs`.
- Magic DRC is not calibrated for TR10 and is disabled for flow signoff.

## KLayout LVS assertion

`flow/checks/test_klayout_lvs.sh <run-dir> <top-cell>` builds a strict
transistor-level SPICE contract from the powered Verilog netlist plus the
checked-in cell CDL/Liberty, then runs the PDK KLayout LVS deck
(`libs.tech/klayout/tech/lvs/run.lvs`) and asserts `TR10_LVS PASS`.
`flow/checks/run_librelane_lvs.sh inv inv` runs the flow and the assertion
together; that is what `.github/workflows/pdk-regression.yml` invokes.

CI also runs `flow/checks/test_tr1um_fixtures_lvs.sh`: the TR-1um use-case
artifacts (`tr1um_alu8`, `tr1um_fifo4`, `tr1um_irqctrl` connected-power GDS
plus their strict SPICE contracts) are checked with the same KLayout LVS
deck.  These are real multi-hundred-instance cores, independent of whether
the RTL flow can place/route them.
