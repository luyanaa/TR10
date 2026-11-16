RX_FM_DEMOD deviation sweep - output at 3 kHz vs peak deviation
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/libs.tech/ngspice/models/ip62_models_rf
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/examples/rf_iq_receiver/spice/demod_fm.lib
.param dev=75k fa=3k
Vdd vdd 0 dc 5

* phase = -(dev/fa)*cos(2*pi*fa*t); phi' = 2*pi*dev*sin(2*pi*fa*t)
Bi i_in 0 V = 1.55 + 100m*cos(-({dev}/{fa})*cos(2*pi*{fa}*time))
Bq q_in 0 V = 1.55 + 100m*sin(-({dev}/{fa})*cos(2*pi*{fa}*time))

XDEM i_in q_in out_p out_n vdd 0 RX_FM_DEMOD
Bd bd 0 V = v(out_p) - v(out_n)

.control
foreach d 5k 25k 50k 75k
  alterparam dev = $d
  reset
  tran 200n 2m 0 200n
  meas tran vmax max v(bd) from=1m to=2m
  meas tran vmin min v(bd) from=1m to=2m
  let a = (vmax - vmin)/2
  echo dev=$d amp=$&a
end
.endc
.end
