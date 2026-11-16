Full FM receiver at 1 MHz - LNA -> balun -> mixer -> TIA -> LPF -> FM demod
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/libs.tech/ngspice/models/ip62_models_rf
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/examples/rf_iq_receiver/spice/lna.lib
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/examples/rf_iq_receiver/spice/mixer_tia.lib
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/examples/rf_iq_receiver/spice/demod_fm.lib

Vdd vdd 0 dc 5
Vagc agc 0 dc 5

* FM source: 1 mV carrier at 1 MHz, 75 kHz deviation, 10 kHz audio
* phase = 2*pi*fc*t - (dev/fa)*cos(2*pi*fa*t), dev/fa = 7.5
Bsrc src 0 V = 1m*sin(2*pi*1meg*time - 7.5*cos(2*pi*10k*time))
Rsrc src lna_in 50

* FM wide needs the tank bandwidth: q=5 -> 200 kHz, covers +-75 kHz
XRX lna_in lna_out vdd 0 agc RX_LNA q=5

Clna lna_out rf_in 100n
Rbias rf_in vcm 1meg
Vcm vcm 0 dc 2.5

Bp bp 0 V = 1.354 + 0.5*(v(rf_in)-2.5)
Rp bp rf_p 25
Bn bn 0 V = 1.354 - 0.5*(v(rf_in)-2.5)
Rn bn rf_n 25

Vlo0   lo0   0 PULSE(0 5 0    5n 5n 245n 1000n)
Vlo90  lo90  0 PULSE(0 5 250n 5n 5n 245n 1000n)
Vlo180 lo180 0 PULSE(0 5 500n 5n 5n 245n 1000n)
Vlo270 lo270 0 PULSE(0 5 750n 5n 5n 245n 1000n)

XMIX rf_p rf_n lo0 lo90 lo180 lo270 out_i out_q vdd 0 RX_MIXER
* FM wide TIA: 22k / 80 pF -> 90 kHz corner, 4.7x more gain than 4.7k/375p
XTIAI out_i tia_i vdd 0 RX_TIA rf=22k cf=80p
XTIAQ out_q tia_q vdd 0 RX_TIA rf=22k cf=80p

* reject the 2*f_lo image left by the single-ended passive mixer
XLPI tia_i tia_q lpf_i lpf_q 0 RX_FM_LPF

XDEM lpf_i lpf_q audio_p audio_n vdd 0 RX_FM_DEMOD
Bd audio 0 V = v(audio_p) - v(audio_n)

.options reltol=1e-3 abstol=1e-9 vntol=1e-5 method=gear gmin=1e-10
.tran 20n 0.2m 0 20n
.control
run
meas tran audio_max max v(audio) from=0.1m to=0.2m
meas tran audio_min min v(audio) from=0.1m to=0.2m
meas tran audio_avg avg v(audio) from=0.1m to=0.2m
meas tran tia_max max v(tia_i) from=0.1m to=0.2m
meas tran tia_min min v(tia_i) from=0.1m to=0.2m
set wr_singlescale
set wr_vecnames
wrdata tb_fm_1m.dat v(audio) v(tia_i) v(tia_q) v(lpf_i) v(lpf_q)
.endc
.end
