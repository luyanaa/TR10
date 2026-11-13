#!/bin/tcsh
# TR10_cmp_sc / qflow technology setup
set leffile=TR10_cmp_sc_qflow.lef
set techleffile=TR10_tech_qflow.tlef
set libertyfile=/grid/TR-1um_stdcell/flow/pdk_root/TR10/flow/experiments/qflow_ppa/tech/tr10cmp/TR10_cmp_sc_qflow.lib
set spicefile=/grid/TR-1um_stdcell/flow/pdk_root/TR10/libs.ref/TR10_cmp_sc/cdl/TR10_cmp_sc.cdl
set gdsfile=/grid/TR-1um_stdcell/flow/pdk_root/TR10/libs.ref/TR10_cmp_sc/gds/TR10_cmp_sc.gds
set verilogfile=/grid/TR-1um_stdcell/flow/pdk_root/TR10/libs.ref/TR10_cmp_sc/verilog/TR10_cmp_sc.v
set techfile=/grid/TR-1um_stdcell/flow/pdk_root/TR10/libs.tech/magic/TR10.tech
set magicrc=/grid/TR-1um_stdcell/flow/pdk_root/TR10/libs.tech/magic/TR10.magicrc
set netgen_setup=/grid/TR-1um_stdcell/flow/pdk_root/TR10/libs.tech/netgen/TR10_setup.tcl

set flopcell=DFF
set floppinout=Q
set floppinin=D
set floppinclk=CK
set flopsetreset=""
set setpin=""
set resetpin=""
set setpininvert=0
set resetpininvert=0

set bufcell=BUF_X1
set bufpin_in=A
set bufpin_out=Y
set clkbufcell=BUF_X1
set clkbufpin_in=A
set clkbufpin_out=Y
set inverter=INV_X1
set invertpin_in=A
set invertpin_out=Y
set norgate=NOR2
set norpin_in1=A
set norpin_in2=B
set norpin_out=Y
set nandgate=NAND2
set nandpin_in1=A
set nandpin_in2=B
set nandpin_out=Y

set fillcell=FILL
set decapcell=""
set antennacell=""
set antennapin_in=""
set bodytiecell=TAP2

set tiehi=TIEHI
set tiehipin_out=HI
set tielo=TIELO
set tielopin_out=LO
set separator=""
set gndnet=GND
set vddnet=VDD

set postproc_options=""
set route_layers=2
set fill_ratios="0,70,10,20"
set fanout_options="-l 200 -c 20"
set addspacers_options="-stripe 2.5 50.0 PG"
set xspice_options="-io_time=500p -time=50p -idelay=5p -odelay=50p -cload=250f"

# qflow tool selection (route-only experiment; DRC/LVS not run here)
set lvs_tool=netgen_lvs
set drc_tool=magic_drc
set gds_tool=magic_gds
set display_tool=magic_view
set migrate_tool=magic_db
