TR10 PFD characteristic - average UP/DN vs phase error
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/libs.tech/ngspice/models/ip62_models_rf
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/examples/rf_iq_receiver/spice/lo_div.lib
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/examples/rf_iq_receiver/spice/pll.lib
.param ph=0
Vdd vdd 0 dc 5

* 1 MHz reference and feedback squares, FB delayed by `ph` degrees
Bref ref 0 V = 5/(1+exp(-200*sin(2*pi*1meg*time)))
Bfb  fb  0 V = 5/(1+exp(-200*sin(2*pi*1meg*time - {ph}*pi/180)))
* power-on reset: low until 700 ns, after both clocks have been low once
Bpor por 0 V = 5*(1/(1+exp(-(time-700n)/2n)))

XPFD ref fb por up dn dnb vdd 0 PFD

.control
foreach d -170 -135 -90 -45 -10 0 10 45 90 135 170
  alterparam ph = $d
  reset
  tran 2n 4u 0 2n
  let u = 0
  let n = 0
  meas tran u avg v(up) from=2u to=4u
  meas tran n avg v(dn) from=2u to=4u
  echo ph=$d up=$&u dn=$&n
end
.endc
.end
