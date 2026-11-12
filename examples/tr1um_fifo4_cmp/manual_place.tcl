# Connectivity-aware deterministic placement for the TR10_cmp_sc 59.4 um
# cell row.  RePlAce (global_placement -disable_pin_density_adjust) is run
# first to get a wirelength-optimized seed: it clusters connected cells,
# so the rows below pack *logically adjacent* cells next to each other
# instead of the alphabetical order that left DRT with long crossing
# wires.  The seed coordinates are only used as a hint — every cell is
# then snapped onto a legal N row so the all-R0, WN-legal floorplan is
# preserved.
#
# The cmp_sc cells carry a full-cell M1/V1 obstruction, so the only place
# TritonRoute can drop a V1 landing pad is *outside* the cell footprint —
# i.e. in the inter-cell gap.  That makes the horizontal gap, not the
# inter-row channel, the scarce resource: a 1-site (5.4 um) gap has room
# for barely one via, and pin-access congestion at the M2 pin band is what
# the residual DRT violations are made of.
#
# Both knobs are sweepable from the environment without touching this
# file (librelane exports env vars into the OpenROAD process):
#   TR10_GAP_UM    – inter-cell gap in um (default 10.8, two site columns)
#   TR10_PITCH_EVERY – use every Nth R0 row (default 2 -> 237.6 um pitch)
set GAP  [expr {[info exists ::env(TR10_GAP_UM)] ? int($::env(TR10_GAP_UM) * 1000) : 10800}]
set PITCH_EVERY [expr {[info exists ::env(TR10_PITCH_EVERY)] ? $::env(TR10_PITCH_EVERY) : 2}]

set block [ord::get_db_block]

set core [$block getCoreArea]
set x_min [expr {[$core xMin] > 10800 ? [$core xMin] : 10800}]
set x_min [expr {int(ceil(($x_min - 10800) / 5400.0)) * 5400 + 10800}]
set x_max [$core xMax]

# --- stage 1: connectivity-aware seed via RePlAce --------------------------
# -disable_pin_density_adjust is the TR10 workaround (see flow/patches/
# librelane/README.md): the pin-density term diverges on these tall cells.
set seed_ok 0
if { [catch {
    global_placement -density 0.3 -disable_pin_density_adjust \
        -pad_left 1 -pad_right 1
} _gpl_err] } {
    puts "\[WARNING\] TR10_cmp_sc seed GPL failed ($_gpl_err); falling back to alphabetical order"
} else {
    set seed_ok 1
}

# Collect fixed TAP2 welltap obstacles as {row_base, xmin, xmax} so the
# packer can step over them.
set fixed {}
foreach inst [$block getInsts] {
    if {[$inst isFixed]} {
        set name [[$inst getMaster] getName]
        if {[string match "TAP*" $name]} {
            set bb [$inst getBBox]
            lappend fixed [list [lindex [$inst getLocation] 1] [$bb xMin] [$bb xMax]]
        }
    }
}

# Row pitch.  ``TR10_PITCH_EVERY`` selects every Nth *N row* (the old
# behaviour: 2 -> 237.6 um, 1 -> 118.8 um).  ``TR10_ROW_STEP`` selects every
# Nth *physical* row instead, which also brings in the MX (flipped) rows:
# 3 -> 178.2 um, a tighter pitch that has not been available before.
# MX rows are placed with the cell mirrored (setOrient MX) and their pins
# mirror with them, so the router sees the same geometry rotated 180 about x.
set all_rows {}
foreach row [$block getRows] {
    set orient [$row getOrient]
    if {[info exists ::env(TR10_ROW_STEP)]} {
        if {[string equal $orient "R0"] || [string equal $orient "MX"]} {
            lappend all_rows [list [lindex [$row getOrigin] 1] $orient]
        }
    } elseif {[string equal $orient "R0"] || [string equal $orient "N"]} {
        lappend all_rows [list [lindex [$row getOrigin] 1] "R0"]
    }
}
set all_rows [lsort -integer -index 0 $all_rows]
set usable_rows {}
if {[info exists ::env(TR10_ROW_STEP)]} {
    # physical-row step: 3 -> 178.2 um (N and MX rows), 4 -> 237.6 um
    set row_step $::env(TR10_ROW_STEP)
} else {
    # legacy R0-only list: every PITCH_EVERY-th N row
    set row_step $PITCH_EVERY
}
for {set i 0} {$i < [llength $all_rows]} {incr i $row_step} {
    lappend usable_rows [lindex $all_rows $i]
}
set n_rows [llength $usable_rows]

# --- stage 2: bin cells into rows by their GPL seed-y, ordered by seed-x ---
# Seed-y tells us which logical "band" a cell belongs to; we quantize that
# onto the usable rows and sort each row by seed-x so nets stay local.
set row_of_inst [dict create]
set x_of_inst [dict create]
set movable {}
foreach inst [$block getInsts] {
    if {[$inst isFixed]} { continue }
    set nm [$inst getName]
    lappend movable $inst
    if {$seed_ok} {
        lassign [$inst getLocation] sx sy
    } else {
        set sx 0
        set sy 0
    }
    dict set x_of_inst $nm $sx
    dict set row_of_inst $nm $sy
}

# Assign each cell to a row: sort by seed-y, split into n_rows buckets so
# each row ends up with a similar cell count, then order within a row by
# seed-x.  This preserves GPL's clustering far better than name order.
# sort insts by seed-y then seed-x so each row keeps GPL's clustering
proc cmp_inst {a b} {
    set ay [dict get $::row_of_inst [$a getName]]
    set by [dict get $::row_of_inst [$b getName]]
    if {$ay == $by} {
        set ax [dict get $::x_of_inst [$a getName]]
        set bx [dict get $::x_of_inst [$b getName]]
        return [expr {$ax < $bx ? -1 : ($ax > $bx ? 1 : 0)}]
    }
    return [expr {$ay < $by ? -1 : 1}]
}
set sorted [lsort -command cmp_inst $movable]
set total [llength $sorted]
set per_row [expr {int(ceil(double($total) / $n_rows))}]

set index 0
set rows_used 0
for {set r 0} {$r < $n_rows && $index < $total} {incr r} {
    lassign [lindex $usable_rows $r] y row_orient
    set x $x_min
    set placed 0
    # Fill this row with up to per_row cells, in GPL (y, x) order.  If the
    # next cell in that order no longer fits, it simply moves to the next
    # row instead of aborting — cell widths vary 2x across the library.
    while {$placed < $per_row && $index < $total} {
        set inst [lindex $sorted $index]
        set width [[$inst getMaster] getWidth]
        # Step over any tap cell that collides with [x, x+width).
        foreach obs $fixed {
            lassign $obs oby oxmin oxmax
            if {$oby == $y && $x < $oxmax && [expr {$x + $width}] > $oxmin} {
                set x $oxmax
            }
        }
        if {[expr {$x + $width}] > $x_max} { break }
        set px [expr {int(ceil(($x - 10800) / 5400.0)) * 5400 + 10800}]
        $inst setOrient $row_orient
        $inst setLocation $px $y
        $inst setPlacementStatus FIRM
        set x [expr {$px + $width + $GAP}]
        incr index
        incr placed
    }
    incr rows_used
}

if {$index < $total} {
    error "TR10_cmp_sc placement: only $index of $total cells fit in $n_rows used rows; enlarge DIE_AREA"
}

puts "\[INFO\] TR10_cmp_sc GPL-seeded placement: $total cells across $rows_used rows (seed_ok=$seed_ok gap=$GAP pitch_every=$PITCH_EVERY)"
