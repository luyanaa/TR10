# TR10_cmp_sc: 59.4 um compact standard cell library.
#
# Geometry facts that drive this configuration:
#   * cell height 59.4 um, site 5.4 x 59.4; signal pins live on M2
#     (y 28..31.4, on the 5.4 um M2 track grid).  The DRT LEF carries a
#     full-cell M1/V1 OBS (the compact cells' internal M1 fills every
#     track), so V1 landing happens in the empty channels between rows.
#   * 59.4 um vertical abutment is NOT DRC-legal (WN.AN < 10, AP.WN < 7,
#     CO.WD on the tap contacts).  Legal row pitches: >= 75.6 um, or
#     multiples of 59.4 starting at 118.8.  examples/*/manual_place.tcl
#     uses 237.6 um (every fourth R0 row), which measured best.
#   * auto-generated rows at 59.4 um pitch would abut WN illegally, so
#     PLACE_SITE rows are used only as anchors; deterministic placement is
#     done by manual_place.tcl (GPL hook, same mechanism as TR10_fd_sc).
set ::env(STD_CELL_LIBRARY) TR10_cmp_sc
# The shared TR10_fd_pr/TR10_gen_pr antenna cells are fd_sc-height (75.6 um)
# and would collide with the 59.4 um compact rows.  Drop them from the
# view lists; physical cells only.
set ::env(CELL_LEFS) [list [lindex $::env(CELL_LEFS) 0]]
set ::env(CELL_GDS) [list [lindex $::env(CELL_GDS) 0]]
set ::env(CELL_VERILOG_MODELS) [list [lindex $::env(CELL_VERILOG_MODELS) 0]]
set ::env(CELL_SPICE_MODELS) [list [lindex $::env(CELL_SPICE_MODELS) 0]]
set ::env(CELL_CDLS) [list [lindex $::env(CELL_CDLS) 0]]
unset -nocomplain ::env(DIODE_CELL)
set ::env(PLACE_SITE) TR1UM
set ::env(GPL_CELL_PADDING) 0
set ::env(DPL_CELL_PADDING) 0
set ::env(CELL_PAD_EXCLUDE) [list]

set ::env(FILL_CELLS) [list FILL3 FILL2 FILL1]
set ::env(DECAP_CELLS) [list]
set ::env(WELLTAP_CELL) TAP2
set ::env(FP_TAPCELL_DIST) 216

set ::env(RT_MIN_LAYER) "M1"
set ::env(RT_MAX_LAYER) "M2"
set ::env(IO_PIN_V_LAYER) "M2"
set ::env(IO_PIN_H_LAYER) "M1"
# LibreLane derives a north/south pin's length from the routing layer's LEF
# AREA when no length is given.  Our tech LEF carries AREA 9.0 on M2 (the
# same way TR10_fd_sc does), but that AREA is stored in dbu^2 by OpenDB while
# io_place.py multiplies by DATABASE MICRONS^2 again -- the result is a
# 1,323,529 um long M2 pin bar per I/O.  Those bars leave only 0.3 um to the
# neighbouring M2 tracks across the whole die and are the source of the
# residual DRT violations.  Pin length is a PDK-level knob; pin it to the
# conventional 2x min width (6.8 um), which is what TR10_fd_sc ends up with
# (its M2 has no AREA, so the buggy term is zero there).
set ::env(IO_PIN_V_LENGTH) 6.8
set ::env(IO_PIN_H_LENGTH) 6.8
set ::env(FP_TRACKS_INFO) "$::env(PDK_ROOT)/$::env(PDK)/libs.tech/librelane/TR10_cmp_sc/tracks.info"

set ::env(SYNTH_DRIVING_CELL) "BUF_X2/A"
set ::env(SYNTH_BUFFER_CELL) "BUF_X2/A/Y"
set ::env(SYNTH_TIEHI_CELL) "TIEHI/HI"
set ::env(SYNTH_TIELO_CELL) "TIELO/LO"
set ::env(CTS_ROOT_BUFFER) "BUF_X2"
set ::env(CTS_CLK_BUFFERS) [list "BUF_X2"]

set ::env(PDN_RAIL_LAYER) "M1"
set ::env(PDN_RAIL_WIDTH) 5
set ::env(PDN_RAIL_OFFSET) 0
set ::env(PDN_CORE_RING_HWIDTH) 5
set ::env(PDN_CORE_RING_VWIDTH) 5
set ::env(PDN_CORE_RING_HSPACING) 5
set ::env(PDN_CORE_RING_VSPACING) 5
set ::env(PDN_VERTICAL_LAYER) "M2"
set ::env(PDN_HORIZONTAL_LAYER) "M1"
set ::env(PDN_HOFFSET) 30
set ::env(PDN_VWIDTH) 5
set ::env(PDN_HWIDTH) 5
set ::env(PDN_VPITCH) 120
set ::env(PDN_HPITCH) 120
set ::env(PDN_VSPACING) 5
set ::env(PDN_HSPACING) 5
set ::env(PDN_CORE_RING_VOFFSET) 10
set ::env(PDN_CORE_RING_HOFFSET) 10
set ::env(PDN_VOFFSET) 30
set ::env(GRT_LAYER_ADJUSTMENTS) "0.3,0.3"
set ::env(IO_DELAY_CONSTRAINT) 5
set ::env(OUTPUT_CAP_LOAD) 0.5
set ::env(MAX_FANOUT_CONSTRAINT) 10
set ::env(CLOCK_UNCERTAINTY_CONSTRAINT) 2
set ::env(CLOCK_TRANSITION_CONSTRAINT) 2
set ::env(TIME_DERATING_CONSTRAINT) 0.5
set ::env(SYNTH_EXCLUDED_CELL_FILE) "/dev/null"
set ::env(PNR_EXCLUDED_CELL_FILE) "/dev/null"
set ::env(PDN_MULTILAYER) 0
