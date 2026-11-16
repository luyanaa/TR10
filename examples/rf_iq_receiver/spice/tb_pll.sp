TR10 PLL - PFD + charge pump + loop filter locks the LC VCO to 1 MHz
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/libs.tech/ngspice/models/ip62_models_rf
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/examples/rf_iq_receiver/spice/lo_div.lib
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/examples/rf_iq_receiver/spice/vco.lib
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/examples/rf_iq_receiver/spice/pll.lib

Vdd vdd 0 dc 5

* 1 MHz reference square (the RF carrier in a real receiver)
Bref ref 0 V = 5/(1+exp(-200*sin(2*pi*1meg*time)))
* power-on reset: low for the first 2 us
Bpor por 0 V = 5*(1/(1+exp(-(time-2u)/2n)))

* VCO at 2*f_lo, divided by two to 1 MHz for the PFD
XVCO vco_p vco_n vtune vdd 0 RX_VCO
XDIV vco_p vdd 0 lo0 lo90 lo180 lo270 fb RX_LO_DIV
XPFD ref fb por up dn dnb vdd 0 PFD

* charge pump into the loop filter (200 uA, UP sinks / DN sources)
XCP up dnb vtune vdd 0 CP

* Loop filter: type-II with the zero below wn.
* C1 = Kphi*Kv/(N*wn^2), R1 = 2*zeta/(wn*C1), C2 = C1/10.
* Kv ~ 23 kHz/V and C1 = 1 nF give wn ~ 7.7 kHz; R1 = 50 k gives
* zeta ~ 1.2 and the zero at 3.2 kHz, which removes the slow limit cycle
* seen with the pure integrator.
R1 vtune n1 50k
C1 n1 0 1n
C2 vtune 0 100p

* bias tee: the VCO reaches 2.000 MHz near vtune = 2.05 V (measured ramp)
* and the charge pump is balanced there (rp=10k, rn=7k), so the filter is
* biased at that point; 10 Mohm is transparent to the loop
Vb vb 0 dc 2.05
Rb vtune vb 10meg
* clamp the filter to the VCO's sensitive tuning window.  Below 2.5 V the
* NMOS varactor is in accumulation and Kv collapses to zero, so the loop
* would integrate a phase error without a frequency response and limit
* cycle.  Above 4.2 V the charge pump's source side runs out of headroom.
Dc1 vcl1 vtune DCL
Vc1 vcl1 0 dc 1.7
Dc2 vtune vcl2 DCL
Vc2 vcl2 0 dc 4.2
Dcg 0 vtune DCL
.model DCL D(is=1e-12 n=0.02)

.options reltol=1e-3 abstol=1e-9 vntol=1e-5 method=gear
.tran 5n 2000u 0 5n
.control
run
meas tran vt_avg avg v(vtune) from=1700u to=2000u
meas tran vt_ripple pp v(vtune) from=1700u to=2000u
set wr_singlescale
set wr_vecnames
wrdata pll_lock.dat v(vco_p) v(vtune) v(fb) v(ref) v(up) v(dn)
.endc
.end
