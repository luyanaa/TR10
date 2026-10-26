# Common LibreLane configuration for the TR10 open_pdk libraries.
set ::env(PROCESS) 1000
set ::env(DEF_UNITS_PER_MICRON) 1000
set ::env(VDD_PIN) "VDD"
set ::env(GND_PIN) "GND"
set ::env(SCL_POWER_PINS) [list VDD]
set ::env(SCL_GROUND_PINS) [list GND]

if { [info exists ::env(STD_CELL_LIBRARY_OPT)] && $::env(STD_CELL_LIBRARY_OPT) != "" } {
    set ::env(STD_CELL_LIBRARY) $::env(STD_CELL_LIBRARY_OPT)
} elseif { ![info exists ::env(STD_CELL_LIBRARY)] } {
    set ::env(STD_CELL_LIBRARY) TR10_fd_sc
}

set lib $::env(STD_CELL_LIBRARY)
set ref "$::env(PDK_ROOT)/$::env(PDK)/libs.ref/$lib"
set antenna_library TR10_fd_pr
if {$lib eq "TR10_gen_sc"} {
    set antenna_library TR10_gen_pr
}
set antenna_ref "$::env(PDK_ROOT)/$::env(PDK)/libs.ref/$antenna_library"

set ::env(LIB) [dict create]
dict set ::env(LIB) "*_typ_5p0V_25C" [list "$ref/lib/${lib}__typ_5p0V_25C.lib" "$antenna_ref/lib/TR10_antenna.lib"]
set ::env(TECH_LEFS) [dict create]
dict set ::env(TECH_LEFS) "*" "$ref/techlef/TR10_tech.tlef"
set ::env(CELL_LEFS) [list "$ref/lef/$lib.lef" "$antenna_ref/lef/TR10_antenna.lef"]
set ::env(CELL_GDS) [list "$ref/gds/$lib.gds" "$antenna_ref/gds/TR10_antenna.gds"]
set ::env(CELL_VERILOG_MODELS) [list "$ref/verilog/$lib.v" "$antenna_ref/verilog/TR10_antenna.v"]
set ::env(CELL_SPICE_MODELS) [list "$ref/spice/$lib.spice" "$antenna_ref/spice/TR10_antenna.spice"]
set ::env(CELL_CDLS) [list "$ref/cdl/$lib.cdl" "$antenna_ref/cdl/TR10_antenna.cdl"]

set ::env(DEFAULT_CORNER) "nom_typ_5p0V_25C"
set ::env(STA_CORNERS) "nom_typ_5p0V_25C"
set ::env(TIMING_VIOLATION_CORNERS) "*"
set ::env(PRIMARY_GDSII_STREAMOUT_TOOL) "klayout"
set ::env(KLAYOUT_TECH) "$::env(PDK_ROOT)/$::env(PDK)/libs.tech/klayout/tech/TR10.lyt"
set ::env(KLAYOUT_PROPERTIES) "$::env(PDK_ROOT)/$::env(PDK)/libs.tech/klayout/tech/TR10.lyp"
set ::env(KLAYOUT_DRC_RUNSET) "$::env(PDK_ROOT)/$::env(PDK)/libs.tech/klayout/tech/drc/run.drc"
set ::env(KLAYOUT_DEF_LAYER_MAP) "$::env(PDK_ROOT)/$::env(PDK)/libs.tech/klayout/tech/def_layer_map.map"

set ::env(MAGICRC) "$::env(PDK_ROOT)/$::env(PDK)/libs.tech/magic/TR10.magicrc"
set ::env(MAGIC_TECH) "$::env(PDK_ROOT)/$::env(PDK)/libs.tech/magic/TR10.tech"
set ::env(MAGIC_PDK_SETUP) "$::env(PDK_ROOT)/$::env(PDK)/libs.tech/magic/TR10.tcl"
set ::env(NETGEN_SETUP) "$::env(PDK_ROOT)/$::env(PDK)/libs.tech/netgen/TR10_setup.tcl"
set ::env(PDN_MULTILAYER) 0
if {[info exists ::env(TR10_PDN_EXPERIMENT)] && $::env(TR10_PDN_EXPERIMENT) == 1} {
    set ::env(PDN_CFG) "$::env(PDK_ROOT)/$::env(PDK)/libs.tech/librelane/TR10_fd_sc/pdn_experiment.tcl"
}
set ::env(KLAYOUT_CONFLICT_RESOLUTION) AddToCell
set ::env(FP_SIZING) absolute
set ::env(BOTTOM_MARGIN_MULT) 0
set ::env(TOP_MARGIN_MULT) 0
set ::env(LEFT_MARGIN_MULT) 0
set ::env(RIGHT_MARGIN_MULT) 0

set ::env(FP_TRACKS_INFO) "$::env(PDK_ROOT)/$::env(PDK)/libs.tech/librelane/$lib/tracks.info"
# Source-bound experimental geometry RCX, qualified against native Magic and heldout v4.
set geometry_model "$::env(PDK_ROOT)/$::env(PDK)/libs.tech/librelane/openrcx/TR10_magic_nom.geometry.json"
set ::env(RCX_RULESETS) [dict create]
dict set ::env(RCX_RULESETS) "nom_*" $geometry_model

# ANT views are an engineering prior, not foundry or ESD signoff.
set ::env(DIODE_CELL) "ANTENNAN_X1/ANT"

# Library-specific defaults live in ./$STD_CELL_LIBRARY/config.tcl.
source "$::env(PDK_ROOT)/$::env(PDK)/libs.tech/librelane/$lib/config.tcl"
