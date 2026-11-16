RX_LNA test - gain, bandwidth, AGC
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/libs.tech/ngspice/models/ip62_models_rf
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/examples/rf_iq_receiver/spice/lna.lib
Vdd vdd 0 dc 5
Vagc agc 0 dc 5
Vsrc src 0 dc 0 ac 1
Rsrc src in 50
XRX in out vdd 0 agc RX_LNA
Cload out load 10u
Rload load 0 2.45k
.control
op
print v(xrx.d) v(xrx.s) v(out) i(vdd)
ac dec 200 10k 100meg
set wr_singlescale
set wr_vecnames
wrdata lna_ac.dat v(out) v(in)
.endc
.end
