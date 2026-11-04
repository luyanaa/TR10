# TR10 PDN experiment A (R0 + MX), 2026-10-24.
#
# Principle:
#   - M1 is horizontal: one rail per standard-cell row, intersecting the
#     actual in-cell VDD/GND M1 access conductors.
#   - M2 is the ONLY vertical routing layer and must carry all signal
#     routing, so it cannot host a pdngen power-strap mesh -- any M2 strap
#     (even pitch 32.4 um) is a continuous placement/DPL blockage.  The
#     routed M2 power segments in the hand-crafted reference DEF
#     (connected_power.def) were emitted by the power router AFTER
#     placement, not by pdngen, so they are out of scope here.
#
# Mechanism:
#   -followpins drops an M1 rail on every row at the site's canonical PG
#   band.  It is the ONLY mechanism that emits M1 stripes on the degenerate
#   75.6x0.1 um site -- explicit -offset M1 stripes are silently dropped by
#   this OpenROAD build regardless of -pitch/-number_of_straps/-nets.
#
# Residual gap (documented, requires a library or placer fix):
#   TR10 cells are X/Y-symmetric, so a cell flipped vertically *within* a
#   row (FN/MY) exposes VDD/GND on the mirror band (e.g. VDD@~19.7 instead
#   of @~55.9).  -followpins covers only the canonical band, leaving such a
#   cell's PG pin unconnected (LVS power-pin fragment).  Full coverage needs
#   EITHER cells with flip-invariant PG bands (a stdcell-layout change) OR a
#   placer constraint forbidding within-row vertical flips -- neither is
#   expressible in pdngen.
#
# This is NOT a production PDN.  It requires:
#   - rows in R0 or MX orientation; cells kept to canonical-band
#     orientations for power to connect;
#   - VDD/GND pin names VDD/GND (the LibreLane nets are taken from
#     VDD_NETS/GND_NETS);
#   - in-cell M1 PG conductors intersecting the 3.4 um buses at GND y=0..3.4
#     and VDD y=54.2..57.6 in R0 (mirrored in flipped rows);
#   - die extending at least 1.7 um above the top row boundary when the top
#     rail reaches the core edge (OpenROAD issue #3724).

source $::env(SCRIPTS_DIR)/openroad/common/set_global_connections.tcl
set_global_connections

# Synthesis exposes PG ports as SIGNAL unless the library declares pg_pin.
# Type the logical ports before pdngen so I/O placement does not move them
# away from the physical grid pins.
foreach {net sigtype} [list $::env(VDD_NET) POWER $::env(GND_NET) GROUND] {
    set term [[ord::get_db_block] findBTerm $net]
    if {$term != "NULL"} {
        $term setSigType $sigtype
        $term setIoType INOUT
    }
}

set_voltage_domain -name CORE -power $::env(VDD_NET) -ground $::env(GND_NET)
# NB: the option is -voltage_domain (singular).  -voltage_domains is silently
# accepted but leaves the grid bound to no domain, so pdngen emits zero
# stripes and then segfaults PDNSim::checkConnectivity on the empty net.
define_pdn_grid -name core -voltage_domain CORE -starts_with POWER

set block [ord::get_db_block]
set core [$block getCoreArea]
set die [$block getDieArea]
set core_ymin [expr {[$core yMin] / 1000.0}]
set core_ymax [expr {[$core yMax] / 1000.0}]
set core_height [expr {$core_ymax - $core_ymin}]
set die_ymax [expr {[$die yMax] / 1000.0}]
set rail_width 3.4
set rows [$block getRows]
if {[llength $rows] == 0} { error "TR10 PDN experiment: no rows" }
set site [[lindex $rows 0] getSite]
set row_pitch [expr {[$site getHeight] / 1000.0}]

# Top-row margin for the issue #3724 workaround: the top rail's outer edge
# must be allowed to sit within 1.7 um of the die top.
set top_row_boundary 0.0
foreach row $rows {
    set oy [expr {[lindex [$row getOrigin] 1] / 1000.0}]
    set top [expr {$core_ymin + ($oy - $core_ymin) + $row_pitch}]
    if {$top > $top_row_boundary} { set top_row_boundary $top }
}
if {$die_ymax < ($top_row_boundary + 1.7)} {
    error "TR10 PDN experiment: die top $die_ymax < top row boundary + 1.7 ($top_row_boundary + 1.7); OpenROAD issue #3724 workaround requires die margin"
}
set reaches_top [expr {$top_row_boundary >= ($core_ymin + $core_height) - 1e-6}]
set rail_extra [list]
if {$reaches_top} { lappend rail_extra -allow_out_of_core }

# One M1 rail per net per row at the site's canonical PG band.
add_pdn_stripe -grid core -layer M1 -width $rail_width -followpins {*}$rail_extra
