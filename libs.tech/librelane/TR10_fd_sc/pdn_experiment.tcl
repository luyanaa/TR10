# TR10 PDN (M1 rails at the true cell PG bands + margin tie straps).
#
# Why this is not the stock pdngen flow:
#   TR10 stdcells are 75.6 um tall but their VDD pin sits at y=54.2..57.6 and
#   GND at y=0..3.4 inside the cell -- i.e. VDD is 18 um BELOW the row top.
#   pdngen's -followpins places rails at the row BOUNDARIES (y=1.7 and
#   y=73.9), so the VDD rail never touches the cell VDD pin; explicit
#   -offset stripes are dropped at PDN time as "floating" because placement
#   has not run yet.  The only reliable route is to emit the rails directly
#   with the odb API at the PG bands the cells actually expose.
#
# Topology:
#   For every row, one full-width M1 rail per net at the orientation-correct
#   band:
#     R0 row: GND [base+0    .. base+3.4 ]  VDD [base+54.2 .. base+57.6]
#     MX row: GND [base+72.2 .. base+75.6]  VDD [base+18.0 .. base+21.4]
#   Cell signal pins are on M2 (A/B/Y) with V1 to M1, so full-width M1 rails
#   do not short signals; the cell M1 OBS stops at the PG bands, which is
#   exactly where the rails live.
#
#   Multi-row tie: VDD rails are extended to the die's LEFT edge and GND
#   rails to the RIGHT edge.  A vertical M2 strap in each die margin (outside
#   the core, so it never blocks placement or signal routing) ties every rail
#   of its net through a V1 cut at each crossing.  Rails of the opposite net
#   stop at the core boundary, so they cannot reach the other margin strap.
#   This requires a die margin of at least ~6 um on each side; the example
#   config sets LEFT/RIGHT_MARGIN_MULT accordingly.
#
#   -followpins is still configured so the LibreLane pdn step's pdngen call
#   succeeds (an empty grid makes pdngen error out); its boundary rails are
#   same-net overlaps or harmless floating metal.

source $::env(SCRIPTS_DIR)/openroad/common/set_global_connections.tcl
set_global_connections

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

# Keep pdngen happy: it must produce at least one shape/via or it exits with
# PDN-0232/PDN-0233.  -followpins is net-agnostic and always emits rails.
set_voltage_domain -name CORE -power $::env(VDD_NET) -ground $::env(GND_NET)
define_pdn_grid -name core -voltage_domain CORE -starts_with POWER
add_pdn_stripe -grid core -layer M1 -width 3.4 -followpins

# One special wire per net; every rail/strap/via box is added to it.  Using
# a separate wire per box (in particular V1-only wires) makes OpenRCX crash.
proc new_pg_swire {net} {
    return [odb::dbSWire_create $net "ROUTED"]
}
proc add_sbox {sw layer_name x1 y1 x2 y2} {
    set block [ord::get_db_block]
    set layer [[$block getTech] findLayer $layer_name]
    odb::dbSBox_create $sw $layer $x1 $y1 $x2 $y2 "STRIPE"
}

set block [ord::get_db_block]
set core [$block getCoreArea]
set die [$block getDieArea]
set core_xmin [$core xMin]
set core_xmax [$core xMax]
set core_ymin [$core yMin]
set core_ymax [$core yMax]
set die_xmin [$die xMin]
set die_xmax [$die xMax]

set sw_vdd [new_pg_swire $vdd_net]
set sw_gnd [new_pg_swire $gnd_net]

set strap_w 3400
# Tie straps live in the die margins; require room for them plus a 2 um gap.
if {($core_xmin - $die_xmin) < 2 * $strap_w} {
    error "TR10 PDN: left die margin too small for the VDD tie strap (need >= 6.8 um)"
}
if {($die_xmax - $core_xmax) < 2 * $strap_w} {
    error "TR10 PDN: right die margin too small for the GND tie strap (need >= 6.8 um)"
}

# Band offsets from the row base, in DBU (0.001 um units).
set GND_R0_LO 0      ; set GND_R0_HI 3400
set VDD_R0_LO 54200  ; set VDD_R0_HI 57600
set GND_MX_LO 72200  ; set GND_MX_HI 75600
set VDD_MX_LO 18000  ; set VDD_MX_HI 21400
set via_size 1400


foreach row [$block getRows] {
    set orient [$row getOrient]
    set oy [lindex [$row getOrigin] 1]
    if {[string equal $orient "R0"]} {
        set gnd_lo [expr {$oy + $GND_R0_LO}]
        set gnd_hi [expr {$oy + $GND_R0_HI}]
        set vdd_lo [expr {$oy + $VDD_R0_LO}]
        set vdd_hi [expr {$oy + $VDD_R0_HI}]
    } elseif {[string equal $orient "MX"]} {
        set gnd_lo [expr {$oy + $GND_MX_LO}]
        set gnd_hi [expr {$oy + $GND_MX_HI}]
        set vdd_lo [expr {$oy + $VDD_MX_LO}]
        set vdd_hi [expr {$oy + $VDD_MX_HI}]
    } else {
        error "TR10 PDN: unsupported row orientation '$orient'"
    }
    # VDD rail reaches the left margin strap; GND rail reaches the right one.
    add_sbox $sw_vdd M1 $die_xmin $vdd_lo $core_xmax $vdd_hi
    add_sbox $sw_gnd M1 $core_xmin $gnd_lo $die_xmax $gnd_hi
}

# Margin tie straps on M1: VDD left, GND right, spanning the core height.
# M1 is preferred-horizontal but geometry on it may be vertical (the reference
# flow's DEF has vertical M1 tie wires).  Keeping the tie on the same layer
# as the rails means no V1/M2 is needed, which also keeps OpenRCX happy.
add_sbox $sw_vdd M1 $die_xmin $core_ymin [expr {$die_xmin + $strap_w}] $core_ymax
add_sbox $sw_gnd M1 [expr {$die_xmax - $strap_w}] $core_ymin $die_xmax $core_ymax
