PLL experiment - transistor VCO vs a 2 MHz reference
* NOTE: the loop acquires through 2.000 MHz but overshoots to a rail;
* this netlist documents the experiment, it is not a passing test.
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/libs.tech/ngspice/models/ip62_models_rf
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/examples/rf_iq_receiver/spice/vco.lib
Vdd vdd 0 dc 5

* free-running kick
Ikick vco_p 0 PULSE(0 0.5m 20n 5n 5n 50n 1s)

XVCO vco_p vco_n vtune vdd 0 RX_VCO

* AC-couple the VCO output into the phase detector
Cpd vco_p pd_ac 10n
Rpd pd_ac 0 100k

* multiplier phase detector against the 2 MHz reference
Bpd pd 0 V = v(pd_ac)*sin(2*pi*2meg*time)

* loop filter: 1.6 kHz low-pass, then an integrator (G into C)
Rf pd n1 10k
Cf n1 0 10n
* proportional-only loop: the PD low-pass output directly sets vtune
* Gint 0 int n1 0 1m
Cint int 0 100n
Rint int 0 10meg
* vtune = 0.5 V + integral, clamped to the varactor's useful 0.05..0.95 V
* smooth clamp to the varactor range; max/min steps would stall the solver
Bvt vtune 0 V = 0.5 + 0.45*tanh(-2*v(n1)/0.45)

.options reltol=1e-3 abstol=1e-9 vntol=1e-5 method=gear
.tran 2n 500u 0 2n
.control
run
meas tran vtmax max v(vtune) from=150u to=200u
meas tran vtmin min v(vtune) from=150u to=200u
set wr_singlescale
set wr_vecnames
wrdata tb_pll.dat v(vco_p) v(vtune) v(pd) v(int)
.endc
.end
