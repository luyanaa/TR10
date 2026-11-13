# C4004: finish the upstream power mesh right after pdngen.
#
# Sourced by the patched LibreLane `scripts/openroad/pdn.tcl` (see
# flow/patches/librelane/pdn.tcl) when the design ships this file.  It runs
# after `pdngen` and before `write_views`/`check_power_grid`, so the shapes
# below are part of the design's SPECIALNETS for every later step.
#
# Why this is needed
# ------------------
# `pdn_c4004.tcl` gives pdngen the right *topology*, but pdngen clips every
# strap to the block core area, which OpenROAD snaps to the row grid
# (0,0,1836,1782) instead of the 1840x1840 die, and it trims the M1 row rails
# to x = 1813.4 (one site short of the east TAP2 column).  The upstream core
# (jun1okamura/TR-1um_C4004) needs:
#
#   * row rails and outer column straps out to the 1818.8 um TAP2 column;
#   * the north VDD bus and the SRAM128 rails up to y = 1840 (SRAM128 sits
#     at y = 1614.6..1800.2, i.e. entirely outside the row bbox);
#   * columns 1 and 2 stopped at y = 1544.4 (top of row 10), because they
#     pass *under* SRAM128 and would otherwise run through its M2 obstruction.
#
# So every strap pdngen made is deleted and re-created with the exact
# upstream extents, the SRAM128 M1 rails / north VDD M1 bus are added, and
# the VDD/GND block-terminal geometry is rebuilt from the new straps (pdngen
# sizes the pin boxes from the clipped straps, so a trimmed column would
# otherwise leave a pin shape sticking through SRAM128).
#
# Every coordinate is copied from `scripts/def2gds_chip.py`
# (build_core_and_power_shapes) of the upstream repository, in DBU (1000/um).
#
# Geometry map (upstream, um):
#   rows y = 27.0 + 145.8*r : GND y .. y+3.4, VDD y+55.7 .. y+59.1, x 0..1818.8
#   col0 tap_x 21.6  : GND 22.6..26.0   (y 0..1840)      VDD 28.0..31.4   (y 3.6..1834)
#   col1 tap_x 615.6 : GND 616.6..620.0 (y 0..1544.4)    VDD 622.0..625.4 (y 27..1544.4)
#   col2 tap_x 1215.0: GND 1216.0..1219.4 (y 0..1544.4)  VDD 1221.4..1224.8 (y 27..1544.4)
#   col3 tap_x 1809.0: GND 1810.0..1813.4 (y 0..1840)    VDD 1815.4..1818.8 (y 3.6..1834)
#
# SRAM128 at (340.2, 1614.6), 1166.1 x 185.6 um.  Its only power pins are
# 3.4 x 3.4 M1 squares in the four corners (VDD at local y 5.4/176.8, GND at
# 0.0/182.2), so the rails below reach from the outer TAP2 columns to the
# corner pins.  The V1 vias land on the 3.4 um M1/M2 overlaps exactly where
# the upstream GDS places them.

set block [ord::get_db_block]
set m1 [[ord::get_db_tech] findLayer M1]
set m2 [[ord::get_db_tech] findLayer M2]
set via_m1m2 [[ord::get_db_tech] findVia M1M2_V1]

if {$m1 == "NULL" || $m2 == "NULL" || $via_m1m2 == "NULL"} {
    error "C4004 post_pdn: M1/M2/M1M2_V1 missing from the technology"
}

set ::c4004_vdd [$block findNet $::env(VDD_NET)]
set ::c4004_gnd [$block findNet $::env(GND_NET)]
if {$::c4004_vdd == "NULL" || $::c4004_gnd == "NULL"} {
    error "C4004 post_pdn: VDD/GND nets not found"
}

proc c4004_net {name} {
    if {$name eq "VDD"} {
        return $::c4004_vdd
    }
    return $::c4004_gnd
}

proc c4004_swire {net} {
    set swires [$net getSWires]
    if {[llength $swires] > 0} {
        return [lindex $swires 0]
    }
    return [odb::dbSWire_create $net ROUTED]
}

proc c4004_strap {net layer x1 y1 x2 y2} {
    return [odb::dbSBox_create [c4004_swire $net] $layer $x1 $y1 $x2 $y2 STRIPE]
}

proc c4004_via {net tech_via x y} {
    return [odb::dbSBox_create [c4004_swire $net] $tech_via $x $y STRIPE]
}

# --- 1. drop everything pdngen drew (straps *and* its V1 arrays) ----------
# pdngen's `add_pdn_connect` fills every strap crossing with a 1.4 x 1.4 V1
# array on a 2.6 um pitch.  On TR10 that is illegal twice over: the PDK
# requires V1 spacing >= 1.5 um (`V1.S1`), and the row rails carry the TAP2
# substrate contacts (CO, 1.0 x 2.0 um in the middle of a 3.4 um rail), so a
# rail-centred V1 overlaps CO (`V1.CO`).  KLayout sign-off DRC reported 132
# such violations, 88 on CO and 44 on spacing.
#
# The upstream core has no V1 on the row-rail/column-strap crossings at all
# (`scripts/def2gds_chip.py` only paints V1 at the SRAM rails, the north bus
# and the frame bridges); the crossings are connected by the V1 that the TAP2
# cell itself carries.  Section 6 below reproduces exactly those TAP2 vias as
# special-net vias, so PSM -- which cannot see cell internals -- still finds a
# connected network, while the geometry stays DRC clean.
foreach net [list $::c4004_vdd $::c4004_gnd] {
    set stale {}
    foreach shape [[c4004_swire $net] getWires] {
        lappend stale $shape
    }
    foreach shape $stale {
        odb::dbSBox_destroy $shape
    }
    puts "\[INFO\] C4004 post_pdn: removed [llength $stale] pdngen shape(s) on [$net getName]"
}

# --- 2. 11 row rails x 2 nets, x = 0..1818.8 -----------------------------
# {net x1 y1 x2 y2}
set row_rails {}
set row_y 27.0
for {set row 0} {$row < 11} {incr row} {
    lappend row_rails [list GND 0 [expr {int(round(($row_y + 0.0) * 1000))}] 1818800 [expr {int(round(($row_y + 3.4) * 1000))}]]
    lappend row_rails [list VDD 0 [expr {int(round(($row_y + 55.7) * 1000))}] 1818800 [expr {int(round(($row_y + 59.1) * 1000))}]]
    set row_y [expr {$row_y + 145.8}]
}

# --- 3. the eight TAP2 column straps, upstream y-extents -----------------
set m2_straps {
    {GND 22600 0 26000 1840000}
    {VDD 28000 3600 31400 1834000}
    {GND 616600 0 620000 1544400}
    {VDD 622000 27000 625400 1544400}
    {GND 1216000 0 1219400 1544400}
    {VDD 1221400 27000 1224800 1544400}
    {GND 1810000 0 1813400 1840000}
    {VDD 1815400 3600 1818800 1834000}
}

# --- 4. SRAM128 M1 rails (left/right, bottom/top) -----------------------
set sram_rails {
    {GND 22600 1614600 343600 1618000}
    {VDD 28000 1620000 343600 1623400}
    {VDD 28000 1791400 343600 1794800}
    {GND 22600 1796800 343600 1800200}
    {GND 1502900 1614600 1813400 1618000}
    {VDD 1502900 1620000 1818800 1623400}
    {VDD 1502900 1791400 1818800 1794800}
    {GND 1502900 1796800 1813400 1800200}
}

foreach strap $m2_straps {
    lassign $strap name x1 y1 x2 y2
    c4004_strap [c4004_net $name] $m2 $x1 $y1 $x2 $y2
}
foreach rail $row_rails {
    lassign $rail name x1 y1 x2 y2
    c4004_strap [c4004_net $name] $m1 $x1 $y1 $x2 $y2
}
foreach rail $sram_rails {
    lassign $rail name x1 y1 x2 y2
    c4004_strap [c4004_net $name] $m1 $x1 $y1 $x2 $y2
}
# North VDD M1 bus: ties col0 and col3 together below the pad ring.
c4004_strap $::c4004_vdd $m1 28000 1826000 1818800 1834000
puts "\[INFO\] C4004 post_pdn: [llength $m2_straps] M2 straps, [llength $row_rails] row rails, [llength $sram_rails] SRAM rails + north bus"

# --- 5. rebuild the VDD/GND block terminals from the new M2 straps -------
foreach net [list $::c4004_vdd $::c4004_gnd] {
    set name [$net getName]
    set bterm [$block findBTerm $name]
    if {$bterm == "NULL"} {
        set bterm [odb::dbBTerm_create $net $name]
        $bterm setIoType INOUT
    }
    foreach bpin [$bterm getBPins] {
        odb::dbBPin_destroy $bpin
    }
    set bpin [odb::dbBPin_create $bterm]
    foreach strap $m2_straps {
        lassign $strap strap_net x1 y1 x2 y2
        if {$strap_net ne $name} {
            continue
        }
        odb::dbBox_create $bpin $m2 $x1 $y1 $x2 $y2
    }
    # PSM only counts placed terminals; a fresh dbBPin defaults to NONE and
    # `check_power_grid` then reports PSM-0025 "does not contain any terminals".
    $bpin setPlacementStatus FIRM
    puts "\[INFO\] C4004 post_pdn: [$bterm getName] terminal rebuilt on M2"
}

# --- 6. V1 vias: SRAM rails / north bus + every TAP2 strap crossing ------
# The first twelve are the upstream `add_via1()` calls for the SRAM128 rails
# and the north VDD M1 bus.
set vias {
    {GND 24300 1616300}
    {VDD 29700 1621700}
    {VDD 29700 1793100}
    {GND 24300 1798500}
    {GND 1811700 1616300}
    {VDD 1817100 1621700}
    {VDD 1817100 1793100}
    {GND 1811700 1798500}
    {VDD 29700 1828000}
    {VDD 29700 1832000}
    {VDD 1817100 1828000}
    {VDD 1817100 1832000}
}

# The row-rail x column-strap crossings: one via per net, at the position of
# the TAP2 cell's own V1 (local (2.0..3.4, 3.9..5.3) for GND and
# (7.4..8.8, 54.1..55.5) for VDD).  That spot clears the TAP2 CO by exactly
# the 1.0 um the deck requires, sits at least 1.0 um inside the cell's M1
# notch and inside the 3.4 um M2 strap, so these vias merge with the cell's
# own V1 instead of adding new geometry.
foreach tap_x {21600 615600 1215000 1809000} {
    set row_y 27.0
    for {set row 0} {$row < 11} {incr row} {
        lappend vias [list GND [expr {$tap_x + 2700}] [expr {int(round(($row_y + 4.6) * 1000))}]]
        lappend vias [list VDD [expr {$tap_x + 8100}] [expr {int(round(($row_y + 54.8) * 1000))}]]
        set row_y [expr {$row_y + 145.8}]
    }
}

foreach via $vias {
    lassign $via name x y
    c4004_via [c4004_net $name] $via_m1m2 $x $y
}
puts "\[INFO\] C4004 post_pdn: [llength $vias] V1 via(s) added"

unset -nocomplain block m1 m2 via_m1m2 row_rails m2_straps sram_rails vias
