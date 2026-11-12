# TR10_cmp_sc PDN: followpin rails only.
#
# The 59.4 um compact cells put their M1 PG bands at y=1.1..3.7 (GND) and
# y=55.7..58.3 (VDD) relative to an R0 row base.  pdngen's -followpins emits
# a stripe at every row boundary, which lands directly on those bands:
#   * N-row base (GND): stripe 0..3.4 covers the 1.1..3.7 band;
#   * N-row top (VDD): stripe at the next row's base spans 57.7..61.1,
#     covering the 55.7..58.3 band at its top 0.6 um.
# So followpins alone connect every placed cell's PG pins.
#
# Explicit dbSBox band rails and die-margin straps are deliberately NOT
# used:
#   * a rail that touches a same-net followpin stripe makes pdngen report
#     an empty grid (PDN-0233);
#   * a die-edge strap collides with the IO pins this flow places on the
#     die edges (observed as M1 shorts in detailed routing).
#
# Vertical continuity between rows comes from TAP2's M2 PG straps
# (GND x+1.0..4.4, VDD x+6.4..9.8, full cell height) at each tap column.

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
define_pdn_grid -name core -voltage_domain CORE -starts_with POWER
add_pdn_stripe -grid core -layer M1 -width 3.4 -followpins
