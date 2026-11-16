RX_LO_DIV test - ideal 2 MHz clock, check divide-by-2 and 25 % duty
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/libs.tech/ngspice/models/ip62_models_rf
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/examples/rf_iq_receiver/spice/lo_div.lib
Vdd vdd 0 dc 5
* 2 MHz sine, 1.2 Vpp around 2.5 V, like the VCO output
Bclk clk 0 V = 2.5 + 0.6*sin(2*pi*2meg*time)

* startup kick to break the latch symmetry
Ist m 0 PULSE(0 1m 50n 5n 5n 20n 1s)

XDIV clk vdd 0 lo0 lo90 lo180 lo270 fb RX_LO_DIV

.options reltol=1e-3 abstol=1e-9 vntol=1e-5 method=gear
.tran 2n 12u 0 2n
.control
run
set wr_singlescale
set wr_vecnames
wrdata lo_div.dat v(lo0) v(lo90) v(lo180) v(lo270) v(xdiv.m) v(xdiv.s) v(xdiv.ck) v(xdiv.ckb) v(xdiv.clk_b) v(xdiv.mb) v(xdiv.sb)
.endc
.end
