# Deterministic dense placement for the TR10_cmp_sc 59.4 um cell row.
#
# Row pitch is 118.8 um = 2 * 59.4: every used row is R0 and abuts its
# neighbours horizontally, leaving one empty 59.4 um channel between used
# rows.  Vertically this keeps >= 59.4 um between WN halos, so no
# WN.AN/AP.WN/CO.WD violations can occur (verified by the pitch scan in
# the P0 investigation: pitch 118.8 -> 0 real DRC items).
set block [ord::get_db_block]

set x_min 10800
set x_max 999999900
set y_min 0
set row_pitch 118800
set max_rows 1

set instance_names {}
foreach inst [$block getInsts] {
    # TAP/endcap/filler cells inserted by earlier steps are already FIXED;
    # only sortable, unplaced standard cells are positioned here.
    if {[$inst isFixed]} { continue }
    lappend instance_names [$inst getName]
}

set sorted_names [lsort $instance_names]
set cell_count [llength $sorted_names]
set cells_per_row [expr {int(ceil(double($cell_count) / $max_rows))}]

set index 0
set rows_used 0
for {set row 0} {$row < $max_rows && $index < $cell_count} {incr row} {
    set x $x_min
    set y [expr {$y_min + $row * $row_pitch}]
    for {set i 0} {$i < $cells_per_row && $index < $cell_count} {incr i} {
        set name [lindex $sorted_names $index]
        set inst [$block findInst $name]
        set width [[$inst getMaster] getWidth]
        $inst setOrient R0
        $inst setLocation $x $y
        $inst setPlacementStatus FIRM
        set x [expr {$x + $width}]
        incr index
    }
    incr rows_used
}

puts "\[INFO\] TR10_cmp_sc manual placement: $cell_count cells across $rows_used rows (pitch 118.8 um)"
