# C4004: restore the upstream FILL3/FILL2 instances after detailed placement.
#
# Sourced by the patched LibreLane `scripts/openroad/dpl.tcl` (see
# flow/patches/librelane/dpl.tcl) between `detailed_placement` and the final
# `check_placement`.
#
# Why this is needed
# ------------------
# `scripts/openroad/common/dpl.tcl` begins with `remove_fillers`, so the 129
# upstream FILL3/FILL2 cells placed by manual_place.tcl are gone by the time
# the views are written.  That is fine for legalisation -- the cells are not
# logic -- but not for signoff:
#
#   * the upstream layout puts consecutive logic cells 16.2 um apart in
#     places and fills the gap with one FILL3 (and 10.8 um gaps with
#     FILL2).  Without the filler, the two N-wells are 3.6 um apart and
#     fail WN.S1 (< 4.0) and WN.S7 (< 12.0);
#   * the upstream GRT/DRT runs see 811 components, not 682, so routing
#     congestion and wirelength are only comparable if the fillers are
#     present during routing.
#
# The coordinates and masters come from the same generated data the GPL hook
# uses (`placements.tcl`), so this is a replay, not a second source of truth.

set block [ord::get_db_block]

source [file join $::env(DESIGN_DIR) placements.tcl]

set fill_masters {FILL1 FILL2 FILL3}
set recreated 0
foreach item $C4004_PLACE {
    lassign $item name master x y orient
    if {[lsearch -exact $fill_masters $master] < 0} {
        continue
    }
    if {[$block findInst $name] != "NULL"} {
        error "C4004 post_dpl: filler $name already exists"
    }
    set m [[ord::get_db] findMaster $master]
    if {$m == "NULL"} {
        error "C4004 post_dpl: master $master not found"
    }
    set inst [odb::dbInst_create $block $m $name]
    $inst setOrient $orient
    $inst setLocation $x $y
    $inst setPlacementStatus FIRM
    incr recreated
}
puts "\[INFO\] C4004 post_dpl: re-inserted $recreated filler cell(s)"

# The fillers are new instances, so they need the generic VDD/GND rule.
source $::env(SCRIPTS_DIR)/openroad/common/set_power_nets.tcl
set_global_connections
