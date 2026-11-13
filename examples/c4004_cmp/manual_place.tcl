# C4004 core reproduction -- deterministic upstream placement.
#
# Sourced by the patched LibreLane ``gpl.tcl`` when the design directory
# contains this file (same hook as examples/tr1um_fifo4/manual_place.tcl).
#
# The upstream TR-1um C4004 floorplan cannot be produced by
# ``initialize_floorplan``:
#
#   * the 59.4 um compact cells are 145.8 um apart vertically
#     (y = 27 + 145.8 * r, r = 0..10), not at the 59.4 um site pitch;
#   * the 340-site rows stop at x = 1836 um, leaving the IO escape bands;
#   * every cell sits at a hand-optimised x, and the macro/SRAM/TAP
#     coordinates are part of the upstream design intent.
#
# So the automatic rows are destroyed and the upstream rows are rebuilt
# with ``odb::dbRow_create``.  ``placements.tcl`` is generated from
# ``openroad/c4004_core_placed.def`` by
# ``flow/scripts/gen_c4004_placement.py`` (637 stdcells + 129 FILL3/FILL2 +
# 44 TAP2 + SRAM128 = the upstream 811 components).  The fillers are
# placed here rather than by ``RUN_FILL_INSERTION`` so the row is byte-for-
# byte the upstream physical intent; they also merge the N-well islands
# that a 16.2 um cell gap would otherwise split (WN.S1/WN.S7).
#
# Everything is marked FIRM (this OpenROAD binding rejects FIXED) so
# ``OpenROAD.DetailedPlacement`` can only legalise/verify, never move cells.

set block [ord::get_db_block]

# placements.tcl holds $C4004_ROWS / $C4004_PLACE (generated).  Sourced here
# rather than from gpl.tcl so the hook stays self-contained.
source [file join $::env(DESIGN_DIR) placements.tcl]

# The site is needed to rebuild the rows.  ``initialize_floorplan`` created
# the automatic rows, so take the site from one of them; fall back to a
# library master if a previous step removed every row.
if {[llength [$block getRows]] > 0} {
    set place_site [[lindex [$block getRows] 0] getSite]
} else {
    set place_site [[[ord::get_db] findMaster INV_X1] getSite]
}
if {$place_site == "NULL"} {
    error "C4004 placement: no TR1UM site found"
}
set site_width  [$place_site getWidth]
set site_height [$place_site getHeight]
if {$site_width != 5400 || $site_height != 59400} {
    error "C4004 placement: unexpected site geometry $site_width x $site_height"
}

foreach row [$block getRows] {
    odb::dbRow_destroy $row
}

set row_index 0
foreach row_def $C4004_ROWS {
    lassign $row_def y count
    odb::dbRow_create $block ROW_$row_index $place_site 0 $y R0 HORIZONTAL $count 5400
    incr row_index
}
puts "\[INFO\] C4004: rebuilt $row_index rows (pitch 145.8 um, 340 sites each)"

set placed 0
set created 0
set sram_seen 0
foreach item $C4004_PLACE {
    lassign $item name master x y orient
    set inst [$block findInst $name]
    if {$inst == "NULL"} {
        set m [[ord::get_db] findMaster $master]
        if {$m == "NULL"} {
            error "C4004 placement: master $master not found (instance $name)"
        }
        set inst [odb::dbInst_create $block $m $name]
        incr created
    }
    # The SRAM and the standard cells already exist (netlist); FILL3/FILL2
    # and TAP2 do not, and are materialised here.
    $inst setOrient $orient
    $inst setLocation $x $y
    $inst setPlacementStatus FIRM
    incr placed
    if {[string equal $master "SRAM128"]} { incr sram_seen }
}

if {$sram_seen != 1} {
    error "C4004 placement: expected exactly one SRAM128 instance, placed $sram_seen"
}
puts "\[INFO\] C4004: placed $placed objects ($created created) from the upstream DEF"

# Give the newly created TAP2 instances their VDD/GND connections.  The
# cells/AIOs that came from the netlist were already connected by
# Odb.SetPowerConnections; a second call is idempotent for them.
source $::env(SCRIPTS_DIR)/openroad/common/set_power_nets.tcl
set_global_connections

# Sanity: every instance must now be fixed and on a row.
set movable 0
foreach inst [$block getInsts] {
    if {![$inst isFixed]} { incr movable }
}
if {$movable != 0} {
    error "C4004 placement: $movable instances are still movable"
}
puts "\[INFO\] C4004: tip-free hand placement applied (all instances FIRM)"
