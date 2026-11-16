PLL lock test - transistor VCO locked to a 2 MHz reference
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
Gint 0 int n1 0 10m
Cint int 0 100n
Rint int 0 10meg
* vtune = 0.5 V + integral, clamped to the varactor's useful 0.05..0.95 V
Bvt vtune 0 V = max(0.05, min(0.95, 0.5 + v(int)))

.options reltol=1e-3 abstol=1e-9 vntol=1e-5 method=gear
.tran 2n 60u 0 2n
.control
run
meas tran vtmax max v(vtune) from=40u to=60u
meas tran vtmin min v(vtune) from=40u to=60u
set wr_singlescale
set wr_vecnames
wrdata tb_pll.dat v(vco_p) v(vtune) v(pd) v(int)
.endc
.end
