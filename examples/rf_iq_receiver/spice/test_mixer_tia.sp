RX_MIXER + RX_TIA transient test
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/libs.tech/ngspice/models/ip62_models_rf
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/examples/rf_iq_receiver/spice/mixer_tia.lib
Vdd vdd 0 dc 5

* AM RF source: 10 mV carrier at 1 MHz, m=0.5, 1 kHz audio
Bsrc src 0 V = 2.5 + 1m*(1+0.5*sin(2*pi*3k*time))*sin(2*pi*1meg*time)
Rsrc src rf_in 50

* ideal balun: 25 ohm per side, common mode matched to the TIA input bias
Bp bp 0 V = 1.354 + 0.5*(v(rf_in)-2.5)
Rp bp rf_p 25
Bn bn 0 V = 1.354 - 0.5*(v(rf_in)-2.5)
Rn bn rf_n 25

* 4-phase 25 % duty LO, 1 MHz
Vlo0   lo0   0 PULSE(0 5 0    5n 5n 245n 1000n)
Vlo90  lo90  0 PULSE(0 5 250n 5n 5n 245n 1000n)
Vlo180 lo180 0 PULSE(0 5 500n 5n 5n 245n 1000n)
Vlo270 lo270 0 PULSE(0 5 750n 5n 5n 245n 1000n)

XMIX rf_p rf_n lo0 lo90 lo180 lo270 out_i out_q vdd 0 RX_MIXER
XTIAI out_i tia_i vdd 0 RX_TIA rf=10k cf=3.5n
XTIAQ out_q tia_q vdd 0 RX_TIA rf=10k cf=3.5n

.options reltol=1e-3 abstol=1e-9 vntol=1e-5 method=gear gmin=1e-10
.tran 20n 600u 0 20n
.control
run
meas tran vmax_i max v(tia_i) from=267u to=600u
meas tran vmin_i min v(tia_i) from=267u to=600u
meas tran vmax_q max v(tia_q) from=267u to=600u
meas tran vmin_q min v(tia_q) from=267u to=600u
meas tran vdc_i avg v(tia_i) from=267u to=600u
meas tran vdc_q avg v(tia_q) from=267u to=600u
set wr_singlescale
set wr_vecnames
wrdata mixer_tia.dat v(tia_i) v(tia_q)
.endc
.end
