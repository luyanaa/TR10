RX_SSB_DEMOD test - 3 kHz I/Q audio, USB then LSB
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/libs.tech/ngspice/models/ip62_models_rf
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/examples/rf_iq_receiver/spice/demod_ssb.lib
Vdd vdd 0 dc 5

* Two instances so USB and LSB run in one transient.
* USB: Q = +sin, LSB: Q = -sin.  10 mV I/Q, 3 kHz, DC 1.55 V.
Bi i_in 0 V = 1.55 + 10m*cos(2*pi*3k*time)
Bqu usb_q 0 V = 1.55 + 10m*sin(2*pi*3k*time)
Bql lsb_q 0 V = 1.55 - 10m*sin(2*pi*3k*time)

XU i_in usb_q usb_p usb_n vdd 0 RX_SSB_DEMOD
XL i_in lsb_q lsb_p lsb_n vdd 0 RX_SSB_DEMOD

Bdu usb_d 0 V = v(usb_p) - v(usb_n)
Bdl lsb_d 0 V = v(lsb_p) - v(lsb_n)

.options reltol=1e-3 abstol=1e-9 vntol=1e-5 method=gear
.tran 1u 3m 0 1u
.control
run
meas tran usb_dc avg v(usb_d) from=1m to=3m
meas tran lsb_dc avg v(lsb_d) from=1m to=3m
set wr_singlescale
set wr_vecnames
wrdata demod_ssb.dat v(usb_d) v(lsb_d) v(usb_p) v(lsb_p)
.endc
.end
