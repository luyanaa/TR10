RX_FM_DEMOD test - 75 kHz deviation, 3 kHz audio, 100 mV I/Q
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/libs.tech/ngspice/models/ip62_models_rf
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/examples/rf_iq_receiver/spice/demod_fm.lib
Vdd vdd 0 dc 5

* FM I/Q baseband: phase = -(dev/fa)*cos(2*pi*fa*t), so phi' = 2*pi*dev*sin()
* 75 kHz deviation, 3 kHz audio, 100 mV amplitude, DC 1.55 V.
Bi i_in 0 V = 1.55 + 100m*cos(-25*cos(2*pi*3k*time))
Bq q_in 0 V = 1.55 + 100m*sin(-25*cos(2*pi*3k*time))

XDEM i_in q_in out_p out_n vdd 0 RX_FM_DEMOD
Bd bd 0 V = v(out_p) - v(out_n)

.options reltol=1e-3 abstol=1e-9 vntol=1e-5 method=gear
.tran 200n 3m 0 200n
.control
run
meas tran out_max max v(bd) from=2m to=3m
meas tran out_min min v(bd) from=2m to=3m
meas tran out_avg avg v(bd) from=2m to=3m
set wr_singlescale
set wr_vecnames
wrdata demod_fm.dat v(bd) v(out_p) v(out_n) v(xdem.di) v(xdem.dq)
.endc
.end
