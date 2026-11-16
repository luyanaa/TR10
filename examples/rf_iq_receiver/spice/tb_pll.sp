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

* Loop filter.  The VCO gain is small (~10 kHz/V), so a type-II zero would
* sit at a very low frequency and the loop was only marginally stable.
* This is a type-I loop: the charge pump drives the integrator C1 directly
* (R1 is a 1 ohm placeholder), with C2 smoothing the pump pulses.
* wn = sqrt(Kphi*Kv/(N*C1)) ~ 4.5 kHz for Kv ~ 10 kHz/V.
R1 vtune n1 1
C1 n1 0 2.2n
C2 vtune 0 22p

* bias tee: the VCO's tuning range is 0..5 V and the lock point is near
* 3 V, so the filter is biased there; 1 Mohm is transparent to the loop
Vb vb 0 dc 2.65
Rb vtune vb 10meg
* clamp the filter to the VCO's sensitive tuning window.  Below 2.5 V the
* NMOS varactor is in accumulation and Kv collapses to zero, so the loop
* would integrate a phase error without a frequency response and limit
* cycle.  Above 4.2 V the charge pump's source side runs out of headroom.
Dc1 vcl1 vtune DCL
Vc1 vcl1 0 dc 2.0
Dc2 vtune vcl2 DCL
Vc2 vcl2 0 dc 4.2
Dcg 0 vtune DCL
.model DCL D(is=1e-12 n=0.02)

.options reltol=1e-3 abstol=1e-9 vntol=1e-5 method=gear
.tran 5n 1000u 0 5n
.control
run
meas tran vt_avg avg v(vtune) from=700u to=1000u
meas tran vt_ripple pp v(vtune) from=700u to=1000u
set wr_singlescale
set wr_vecnames
wrdata tb_pll.dat v(vco_p) v(vtune) v(fb) v(ref) v(up) v(dn)
.endc
.end
