RX_TIA with the extracted layout parasitics - ideal vs PEX v1 vs PEX v2
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/libs.tech/ngspice/models/ip62_models_rf
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/examples/rf_iq_receiver/spice/mixer_tia.lib
Vdd vdd 0 dc 5

* ideal: no layout capacitance
I0 0 n0 dc 0 ac 1
X0 n0 o0 vdd 0 RX_TIA

* PEX v1: 30x30 um pads (IN 65.45 fF, OUT 74.25 fF, VSS 76.28 fF)
I1 0 n1 dc 0 ac 1
X1 n1 o1 vdd 0 RX_TIA
Cin1 n1 0 65.45f
Cout1 o1 0 74.25f
Cvss1 vdd 0 76.28f

* PEX v2: 16x16 um pads (IN 39.10 fF, OUT 46.21 fF, VSS 53.29 fF)
I2 0 n2 dc 0 ac 1
X2 n2 o2 vdd 0 RX_TIA
Cin2 n2 0 39.10f
Cout2 o2 0 46.21f
Cvss2 vdd 0 53.29f

.control
ac dec 200 1k 1g
set wr_singlescale
set wr_vecnames
wrdata tia_pex.dat mag(v(o0)) mag(v(o1)) mag(v(o2)) mag(v(n0)) mag(v(n1)) mag(v(n2))
.endc
.end
