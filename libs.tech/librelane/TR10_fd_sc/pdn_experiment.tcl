# TR10 PDN experiment A (R0 + MX), 2026-10-24.
#
# Principle:
#   - M1 is horizontal: one rail per standard-cell row, intersecting the
#     actual in-cell VDD/GND M1 access conductors.
#   - M2 is vertical: this candidate uses only two edge straps, not the
#     tested 54 um-pitch set that shorted an M2 signal pin.  Edge straps still
#     require placement-specific signal/OBS clearance checks; a conflicting
#     right-edge instance can overlap the GND strap.
#
# This is NOT a production PDN.  It requires:
#   - rows in R0 or MX orientation only; native row pitch comes from the site;
#   - VDD/GND pin names VDD/GND (the LibreLane nets are taken from
#     VDD_NETS/GND_NETS);
#   - actual M1 PG conductors intersecting the 3.4 um buses at GND y=0..3.4
#     and VDD y=54.2..57.6 in R0, with native mirrored positions in MX.
#     FD access spans GND y=0..3.4/VDD y=54.2..57.6. Gen VDD remains
#     y=55..57.6; its GND expands from y=0..2.6 to 0..3.4 with the
#     70.2 um row-boundary repair. The same buses cover both revisions;
#   - die extending at least 1.7 um above the top row boundary when MX
#     rows exist, to work around OpenROAD issue #3724 (PDN-0185).
#
# OpenROAD issue #3724 workaround:
#   The MX GND rail is exactly centered at y = row_base + row_pitch - 1.7.
#   For the 75.6 um row: y = 149.5, rail = 147.8..151.2, V1 center = 149.5.
#   OpenROAD's conservative top-edge check rejects this as
#   offset + width > grid height.  With -allow_out_of_core it checks the die
#   boundary instead, so the stripe is accepted when die > core.
#
# All add_pdn_stripe offsets below are relative to the PDN grid origin
# (core lower-left).  The precheck uses absolute die/row coordinates.
#
# Adjacent same-net rails are merged.  At an MX/R0 boundary the MX GND rail
# [147.8,151.2] and the next R0 GND rail [151.2,154.6] touch.  OpenROAD
# drops one of two separate add_pdn_stripe calls in that case, so the
# candidate emits one merged 6.8 um GND stripe centered at 151.2.  The
# merged stripe still covers both PG rails; the generated V1 may be a via
# array, which must be DRC-checked.

source $::env(SCRIPTS_DIR)/openroad/common/set_global_connections.tcl
set_global_connections

# Synthesis exposes PG ports as SIGNAL unless the library declares pg_pin.
# Type the logical ports before pdngen so I/O placement does not move them
# away from the physical grid pins created on M2.
foreach {net sigtype} [list $::env(VDD_NET) POWER $::env(GND_NET) GROUND] {
    set term [[ord::get_db_block] findBTerm $net]
    if {$term != "NULL"} {
        $term setSigType $sigtype
        $term setIoType INOUT
    }
}

set_voltage_domain -name CORE -power $::env(VDD_NET) -ground $::env(GND_NET)
define_pdn_grid -name core -voltage_domains {CORE} -starts_with POWER -pins {M2}

set block [ord::get_db_block]
set core [$block getCoreArea]
set die [$block getDieArea]
set core_xmin [expr {[$core xMin] / 1000.0}]
set core_xmax [expr {[$core xMax] / 1000.0}]
set core_ymin [expr {[$core yMin] / 1000.0}]
set core_ymax [expr {[$core yMax] / 1000.0}]
set core_height [expr {$core_ymax - $core_ymin}]
set die_ymax [expr {[$die yMax] / 1000.0}]
set rail_width 3.4
set rows [$block getRows]
if {[llength $rows] == 0} { error "TR10 PDN experiment: no rows" }
set site [[lindex $rows 0] getSite]
set row_pitch [expr {[$site getHeight] / 1000.0}]

set gnd_intervals [list]
set vdd_intervals [list]
set top_row_boundary 0.0

foreach row $rows {
    set orient [$row getOrient]
    set origin [$row getOrigin]
    # PDN offsets are relative to the core origin.
    set base [expr {([lindex $origin 1] / 1000.0) - $core_ymin}]
    set top [expr {$core_ymin + $base + $row_pitch}]
    if {$top > $top_row_boundary} { set top_row_boundary $top }

    if {[string equal $orient "R0"]} {
        set gnd [expr {$base + 1.7}]
        set vdd [expr {$base + 55.9}]
    } elseif {[string equal $orient "MX"]} {
        set gnd [expr {$base + $row_pitch - 1.7}]
        set vdd [expr {$base + $row_pitch - 55.9}]
    } else {
        error "TR10 PDN experiment: unsupported row orientation '$orient'"
    }
    lappend gnd_intervals [list [expr {$gnd - 1.7}] [expr {$gnd + 1.7}]]
    lappend vdd_intervals [list [expr {$vdd - 1.7}] [expr {$vdd + 1.7}]]
}

if {$die_ymax < ($top_row_boundary + 1.7)} {
    error "TR10 PDN experiment: die top $die_ymax < top row boundary + 1.7 ($top_row_boundary + 1.7); OpenROAD issue #3724 workaround requires die margin"
}

proc merge_intervals {intervals} {
    set sorted [lsort -real -index 0 $intervals]
    set merged [list]
    foreach iv $sorted {
        set s [lindex $iv 0]
        set e [lindex $iv 1]
        if {[llength $merged] == 0} {
            lappend merged [list $s $e]
        } else {
            set last [lindex $merged end]
            set ls [lindex $last 0]
            set le [lindex $last 1]
            if {$s <= $le + 1e-6} {
                lset merged end [list $ls [expr {max($le, $e)}]]
            } else {
                lappend merged [list $s $e]
            }
        }
    }
    return $merged
}

proc add_merged_rails {grid net intervals core_height row_pitch} {
    foreach iv [merge_intervals $intervals] {
        set s [lindex $iv 0]
        set e [lindex $iv 1]
        set width [expr {$e - $s}]
        set center [expr {($s + $e) / 2.0}]
        set extra [list]
        # Only the interval reaching the top edge needs the issue #3724
        # workaround; check by the actual interval end, not by row count.
        if {$e >= $core_height - 1e-6} {
            lappend extra -allow_out_of_core
        }
        add_pdn_stripe -grid $grid -layer M1 -nets [list $net] \
            -width $width -pitch $row_pitch -offset $center -number_of_straps 1 {*}$extra
    }
}

add_merged_rails core $::env(GND_NET) $gnd_intervals $core_height $row_pitch
add_merged_rails core $::env(VDD_NET) $vdd_intervals $core_height $row_pitch

# M2 edge straps: one VDD at the left edge, one GND near the right edge.
# The right strap is pulled inward to keep its cross-section off the core edge.
# This is not a per-cell clearance guarantee: validate the realized edge
# placement against each macro's actual M2 signal and OBS geometry.
# Offsets are relative to the core origin.
set core_width [expr {$core_xmax - $core_xmin}]
set m2_left [expr {$rail_width / 2.0}]
set m2_right [expr {$core_width - (2.0 * $rail_width)}]
add_pdn_stripe -grid core -layer M2 -nets [list $::env(VDD_NET)] \
    -width $rail_width -pitch $core_width -offset $m2_left -number_of_straps 1
add_pdn_stripe -grid core -layer M2 -nets [list $::env(GND_NET)] \
    -width $rail_width -pitch $core_width -offset $m2_right -number_of_straps 1

add_pdn_connect -grid core -layers {M1 M2}
