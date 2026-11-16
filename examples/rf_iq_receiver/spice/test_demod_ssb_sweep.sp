RX_SSB_DEMOD sideband rejection vs audio frequency
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/libs.tech/ngspice/models/ip62_models_rf
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/examples/rf_iq_receiver/spice/demod_ssb.lib
.param freq=3k
Vdd vdd 0 dc 5

* USB: Q = +sin.  LSB: Q = -sin.  10 mV I/Q, DC 1.55 V.
Bi i_in 0 V = 1.55 + 10m*cos(2*pi*{freq}*time)
Bqu usb_q 0 V = 1.55 + 10m*sin(2*pi*{freq}*time)
Bql lsb_q 0 V = 1.55 - 10m*sin(2*pi*{freq}*time)

XU i_in usb_q usb_p usb_n vdd 0 RX_SSB_DEMOD
XL i_in lsb_q lsb_p lsb_n vdd 0 RX_SSB_DEMOD

Bdu usb_d 0 V = v(usb_p) - v(usb_n)
Bdl lsb_d 0 V = v(lsb_p) - v(lsb_n)

.control
foreach f 0.3k 1k 2k 3k 5k 8k
  alterparam freq = $f
  reset
  tran 1u 3m 0 1u
  meas tran umax max v(usb_d) from=2m to=3m
  meas tran umin min v(usb_d) from=2m to=3m
  meas tran lmax max v(lsb_d) from=2m to=3m
  meas tran lmin min v(lsb_d) from=2m to=3m
  let ua = (umax - umin)/2
  let la = (lmax - lmin)/2
  echo freq=$f usb=$&ua lsb=$&la
end
.endc
.end
