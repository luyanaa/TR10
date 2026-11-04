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

Config notes:
  - DIE_AREA 300x310 with core snapped to 3x 75.6 um rows; die top must be
    >= top row boundary + 1.7 um for the PDN issue-#3724 workaround.
  - PDN_CFG points at libs.tech/librelane/TR10_fd_sc/pdn_experiment.tcl
    (-followpins M1 rail grid; see that file's header for the residual
    within-row-flip power gap).
  - RUN_FILL_INSERTION/RUN_IRDROP_REPORT are off: the smallest filler is
    5.4 um so tiny gaps can't fill, and the rail-only grid is not a full
    connectivity grid for IR analysis.
  - IGNORE_DISCONNECTED_MODULES=inv: the top module has no power pins.

Known signoff status: all signal nets LVS-match; residual LVS errors are
power-pin fragments on cells the placer vertically flips within a row
(FN) -- those land on the mirror band the single -followpins rail cannot
reach (documented in pdn_experiment.tcl).
