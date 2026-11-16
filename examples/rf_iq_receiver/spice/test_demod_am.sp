RX_AM_DEMOD test - 3 kHz envelope on a 1.55 V bias, 1 MHz ripple
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/libs.tech/ngspice/models/ip62_models_rf
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/examples/rf_iq_receiver/spice/demod_am.lib
Vdd vdd 0 dc 5

* I channel: DC 1.55 V, 25 mV audio at 3 kHz, 50 mV of 1 MHz LO ripple.
* Q channel: reference only (phase-locked LO case).
Bi i_in 0 V = 1.55 + 25m*sin(2*pi*3k*time) + 50m*sin(2*pi*1meg*time)
Bq q_in 0 V = 1.55

XDEM i_in q_in out vdd 0 RX_AM_DEMOD

.options reltol=1e-3 abstol=1e-9 vntol=1e-5 method=gear
.tran 20n 1m 0 20n
.control
run
meas tran vout_max max v(out) from=0.5m to=1m
meas tran vout_min min v(out) from=0.5m to=1m
meas tran vout_avg avg v(out) from=0.5m to=1m
set wr_singlescale
set wr_vecnames
wrdata demod_am.dat v(out)
.endc
.end
