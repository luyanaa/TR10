RX_LO_GEN test - four 25 % duty phases at 1 MHz
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/libs.tech/ngspice/models/ip62_models_rf
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/examples/rf_iq_receiver/spice/lo_gen.lib
Vdd vdd 0 dc 5
XG vdd 0 lo0 lo90 lo180 lo270 RX_LO_GEN flo=1meg
.control
tran 2n 6u 0 2n
set wr_singlescale
set wr_vecnames
wrdata lo_gen.dat v(lo0) v(lo90) v(lo180) v(lo270)
.endc
.end
