# C4004 core PDN: 11 M1 row pairs + 4 TAP2 column pairs.
#
# The upstream TR-1um C4004 core (jun1okamura/TR-1um_C4004) does not draw its
# power grid in the DEF: `scripts/def2gds_chip.py` paints it into the GDS after
# the standard cells are merged.  This file expresses the same topology through
# pdngen, and `post_pdn.tcl` then rewrites the eight M2 straps and adds the
# SRAM128 rails with the exact upstream coordinates.
#
# Geometry (all in um, DBU = 1000/um):
#
#   * 11 rows at y = 27.0 + 145.8*r, 59.4 um tall.  Each compact cell carries
#     its GND band at local y 1.1..3.7 and its VDD band at 55.7..58.3, so the
#     row rails are:
#         GND centre y + 1.7   (rail y .. y + 3.4)
#         VDD centre y + 57.4  (rail y + 55.7 .. y + 59.1)
#     Centre distance = width 3.4 + spacing 52.3 = 55.7 um.
#   * 4 TAP2 columns at x = 21.6 / 615.6 / 1215.0 / 1809.0.  TAP2 puts GND at
#     x + 1.0..4.4 and VDD at x + 6.4..9.8 on M2, full cell height, so each
#     column is a GND/VDD strap pair 3.4 um wide with a 2.0 um gap:
#         column GND centre = tap_x + 2.7, VDD centre = tap_x + 8.1
#
# pdngen cannot emit a fixed number of stripes (`-number_of_stripes` does not
# exist in OpenROAD 26Q4), so every row and every column gets its own
# one-shot stripe pair: `-pitch 1840` (the die width) makes each spec place a
# single GND/VDD pair.  `-starts_with GROUND` on every spec is what keeps the
# pair polarity identical for all 11 rows and all 4 columns.
#
# `-pins M2` turns the M2 straps into VDD/GND block terminals.  Without block
# terminals PSM reports "does not contain any terminals" (PSM-0025) and the
# IR-drop step aborts (PSM-0069).
#
# No core/die ring: the IO pins sit on the die edge and a ring would either
# collide with them or cross the compact cells' full-cell M1/V1 obstruction.

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

# --- 11 row rails (one GND/VDD pair per row, 145.8 um pitch) ---------------
set row_y 27.0
for {set row 0} {$row < 11} {incr row} {
    add_pdn_stripe -grid core -layer M1 -width 3.4 \
        -offset [expr {$row_y + 1.7}] -pitch 1840 -spacing 52.3 \
        -starts_with GROUND
    set row_y [expr {$row_y + 145.8}]
}

# --- 4 TAP2 column strap pairs (one pair per column) -----------------------
foreach gnd_centre {24.3 618.3 1217.7 1811.7} {
    add_pdn_stripe -grid core -layer M2 -width 3.4 -offset $gnd_centre \
        -pitch 1840 -spacing 2.0 -starts_with GROUND
}

add_pdn_connect -grid core -layers {M1 M2}
