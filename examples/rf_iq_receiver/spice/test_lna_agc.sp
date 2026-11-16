RX_LNA AGC sweep - gain at 1 MHz vs agc control voltage
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/libs.tech/ngspice/models/ip62_models_rf
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/examples/rf_iq_receiver/spice/lna.lib
Vdd vdd 0 dc 5
Vagc agc 0 dc 5
Vsrc src 0 dc 0 ac 1
Rsrc src in 50
XRX in out vdd 0 agc RX_LNA
Cload out load 10u
Rload load 0 2.45k
.control
foreach a 0 0.5 1 1.5 2 2.5 3 3.5 4 4.5 5
  alter Vagc = $a
  ac lin 1 1meg 1meg
  let g = mag(v(out)/v(in))
  echo agc=$a gain=$&g
end
.endc
.end
