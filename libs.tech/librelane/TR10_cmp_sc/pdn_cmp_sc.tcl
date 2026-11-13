# TR10_cmp_sc PDN: M1 followpin rails + M2 vertical straps at the TAP2 columns.
#
# The 59.4 um compact cells put their M1 PG bands at y=1.1..3.7 (GND) and
# y=55.7..58.3 (VDD) relative to an R0 row base.  pdngen's -followpins emits
# a stripe at every row boundary, which lands directly on those bands:
#   * N-row base (GND): stripe 0..3.4 covers the 1.1..3.7 band;
#   * N-row top (VDD): stripe at the next row's base spans 57.7..61.1,
#     covering the 55.7..58.3 band at its top 0.6 um.
# FS rows mirror the cell, so the same alternating VDD/GND boundary rails
# connect them as well.
#
# Vertical continuity comes from TAP2's M2 PG straps (GND x+1.0..4.4, VDD
# x+6.4..9.8, full cell height).  `examples/tr1um_fifo4_cmp/manual_place.tcl`
# deletes the FS rows and places TAP2 at x = 226.8, 442.8 and 658.8 um on
# every remaining N row (tap insertion is disabled).  All placed cells are
# R0, so the TAP2 M2 straps stay on the same net at a fixed x.  We add
# explicit M2 stripes on those exact columns so the top-level power pins and
# the PSM/IR-drop source model have a real M2 shape to attach to:
#   GND centres 229.5 / 445.5 / 661.5 um
#   VDD centres 234.9 / 450.9 / 666.9 um
# The core starts at x=10.8 um, so the first GND centre is offset 218.7 um.
# The 2.0 um spacing between GND and VDD is the TAP2 strap gap.  The M2
# stripes overlap the TAP2 M2 pins.  `add_pdn_connect` adds M1M2_V1 vias at
# same-net M1/M2 crossings; a via inside a TAP2 cell may be blocked by its
# full-cell V1 obstruction, but the crossings in the empty FS rows and the
# TAP2 internal M1<->M2 connection keep the grid connected (PSM-0040).
#
# `-pins M2` turns the M2 stripes into VDD/GND block terminals.  Without
# terminals PSM fails with "PSM-0025 ... does not contain any terminals",
# which in turn makes the IR-drop step abort with PSM-0069.
#
# No core/die ring is used: a die-edge M1 ring collides with the IO pins this
# flow places on the die edges, and a ring inside the core would cross the
# compact cells' full-cell M1/V1 obstruction.
#
# Explicit dbSBox band rails are deliberately NOT used: a rail that touches
# a same-net followpin stripe makes pdngen report an empty grid (PDN-0233).

proc ensure_pg_net {name sigtype} {
    set block [ord::get_db_block]
    set net [$block findNet $name]
    if {$net == "NULL"} {
        set net [odb::dbNet_create $block $name]
    }
    $net setSpecial
    $net setSigType $sigtype
    return $net
}

set vdd_net [ensure_pg_net $::env(VDD_NET) POWER]
set gnd_net [ensure_pg_net $::env(GND_NET) GROUND]

set_voltage_domain -name CORE -power $::env(VDD_NET) -ground $::env(GND_NET)
define_pdn_grid -name core -voltage_domain CORE -starts_with POWER -pins M2
add_pdn_stripe -grid core -layer M1 -width 3.4 -followpins
add_pdn_stripe -grid core -layer M2 -width 3.4 -pitch 216 -offset 218.7 \
    -spacing 2.0 -starts_with GROUND
add_pdn_connect -grid core -layers {M1 M2}
