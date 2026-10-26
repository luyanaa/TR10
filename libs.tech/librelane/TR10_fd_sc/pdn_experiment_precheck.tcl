# TR10 PDN experiment preconditions.
# Source after the floorplan/placement is loaded and before pdngen.
# The top row boundary is read from actual rows, not assumed from die height.

set block [ord::get_db_block]
set die [$block getDieArea]
set top_row_boundary 0.0
set row_count 0
set has_mx 0

foreach row [$block getRows] {
    incr row_count
    set orient [$row getOrient]
    if {[string equal $orient "MX"]} {
        set has_mx 1
    } elseif {![string equal $orient "R0"]} {
        error "TR10 PDN precondition: unsupported row orientation '$orient'"
    }
    set site [$row getSite]
    set h [expr {[$site getHeight] / 1000.0}]
    set y [expr {[lindex [$row getOrigin] 1] / 1000.0}]
    set top [expr {$y + $h}]
    if {$top > $top_row_boundary} {
        set top_row_boundary $top
    }
}

if {$row_count == 0} {
    error "TR10 PDN precondition: block has no rows"
}

set die_top [expr {[$die yMax] / 1000.0}]
set required_top [expr {$top_row_boundary + 1.7}]
puts "TR10 PDN precheck: rows=$row_count top_row_boundary=$top_row_boundary die_top=$die_top"
if {$die_top < $required_top} {
    error "TR10 PDN precondition: die top $die_top < top row boundary + 1.7 ($required_top); OpenROAD issue #3724 workaround requires die margin"
}
if {$has_mx} {
    puts "TR10 PDN precheck: MX rows present; exact MX GND center = row_base + row_height - 1.7"
}
