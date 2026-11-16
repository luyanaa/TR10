TR10 PFD frequency-direction test - UP for a slow FB, DN for a fast FB
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/libs.tech/ngspice/models/ip62_models_rf
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/examples/rf_iq_receiver/spice/lo_div.lib
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/examples/rf_iq_receiver/spice/pll.lib
.param ffb=1.000meg
Vdd vdd 0 dc 5

Bref ref 0 V = 5/(1+exp(-200*sin(2*pi*1.000meg*time)))
Bfb  fb  0 V = 5/(1+exp(-200*sin(2*pi*{ffb}*time)))
Bpor por 0 V = 5*(1/(1+exp(-(time-700n)/2n)))

XPFD ref fb por up dn dnb vdd 0 PFD

.control
foreach f 0.995meg 1.000meg 1.005meg
  alterparam ffb = $f
  reset
  tran 5n 100u 0 5n
  let u = 0
  let n = 0
  meas tran u avg v(up) from=10u to=100u
  meas tran n avg v(dn) from=10u to=100u
  let net = (n - u)/5
  echo ffb=$f up=$&u dn=$&n net_dn_duty=$&net
end
.endc
.end
