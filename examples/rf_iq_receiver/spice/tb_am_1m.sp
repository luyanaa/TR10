Full AM receiver at 1 MHz - LNA -> balun -> mixer -> TIA -> AM demod
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/libs.tech/ngspice/models/ip62_models_rf
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/examples/rf_iq_receiver/spice/lna.lib
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/examples/rf_iq_receiver/spice/mixer_tia.lib
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/examples/rf_iq_receiver/spice/demod_am.lib

Vdd vdd 0 dc 5
Vagc agc 0 dc 5

* AM source: 1 mV carrier at 1 MHz, m=0.5, 3 kHz audio
Bsrc src 0 V = 1m*(1+0.5*sin(2*pi*3k*time))*sin(2*pi*1meg*time)
Rsrc src lna_in 50

* narrowband LNA, 19.9 dB at 1 MHz, 50 ohm input
XRX lna_in lna_out vdd 0 agc RX_LNA

* AC couple into the balun and rebias at 2.5 V
Clna lna_out rf_in 100n
Rbias rf_in vcm 1meg
Vcm vcm 0 dc 2.5

* ideal balun, 25 ohm per side, common mode at the TIA input bias
Bp bp 0 V = 1.354 + 0.5*(v(rf_in)-2.5)
Rp bp rf_p 25
Bn bn 0 V = 1.354 - 0.5*(v(rf_in)-2.5)
Rn bn rf_n 25

* 4-phase 25 % duty LO at 1 MHz
Vlo0   lo0   0 PULSE(0 5 0    5n 5n 245n 1000n)
Vlo90  lo90  0 PULSE(0 5 250n 5n 5n 245n 1000n)
Vlo180 lo180 0 PULSE(0 5 500n 5n 5n 245n 1000n)
Vlo270 lo270 0 PULSE(0 5 750n 5n 5n 245n 1000n)

XMIX rf_p rf_n lo0 lo90 lo180 lo270 out_i out_q vdd 0 RX_MIXER
XTIAI out_i tia_i vdd 0 RX_TIA rf=10k cf=3.5n
XTIAQ out_q tia_q vdd 0 RX_TIA rf=10k cf=3.5n

* AM demodulator: I/Q rectifier + sum, 4.5 kHz audio low-pass
XDEM tia_i tia_q audio vdd 0 RX_AM_DEMOD

.options reltol=1e-3 abstol=1e-9 vntol=1e-5 method=gear gmin=1e-10
.tran 20n 1m 0 20n
.control
run
meas tran audio_max max v(audio) from=0.667m to=1m
meas tran audio_min min v(audio) from=0.667m to=1m
meas tran audio_avg avg v(audio) from=0.667m to=1m
meas tran tia_max max v(tia_i) from=0.667m to=1m
meas tran tia_min min v(tia_i) from=0.667m to=1m
set wr_singlescale
set wr_vecnames
wrdata tb_am_1m.dat v(audio) v(tia_i) v(tia_q) v(lna_out) v(rf_in)
.endc
.end
