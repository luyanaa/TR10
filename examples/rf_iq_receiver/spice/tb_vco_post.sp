RX_VCO free-running test, POST-LAYOUT (PEX caps) - 2 MHz
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/libs.tech/ngspice/models/ip62_models_rf
* post-layout VCO (hybrid PEX): see scripts/gen_post_am.py
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/examples/rf_iq_receiver/spice/post_vco.lib
Vdd vdd 0 dc 5
* centre the varactors at 2.5 V
Vt vtune 0 dc 2.5

XVCO vco_p vco_n vtune vdd 0 RX_VCO

* start-up kick into the tank at t=20 ns
* differential kick: inject into one drain so the odd mode is excited
Ikick vco_p 0 PULSE(0 0.2m 20n 5n 5n 50n 1s)

.options reltol=1e-3 abstol=1e-9 vntol=1e-5 method=gear
.tran 2n 5u 0 2n
.control
run
meas tran vmax max v(vco_p) from=10u to=20u
meas tran vmin min v(vco_p) from=10u to=20u
meas tran vmaxn max v(vco_n) from=10u to=20u
meas tran vminn min v(vco_n) from=10u to=20u
set wr_singlescale
set wr_vecnames
wrdata vco_post.dat v(vco_p) v(vco_n) v(xvco.vct) v(xvco.tail) v(vtune)
.endc
.end
