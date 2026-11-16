RX_LNA band scaling - 0.1 / 1 / 10 / 100 MHz, same 50 ohm interface
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/libs.tech/ngspice/models/ip62_models_rf
.include /grid/TR-1um_stdcell/flow/pdk_root/TR10/examples/rf_iq_receiver/spice/lna.lib
Vdd vdd 0 dc 5
Vagc agc 0 dc 5

V1 s1 0 dc 0 ac 1
R1 s1 i1 50
X1 i1 o1 vdd 0 agc RX_LNA fc=100k
C1 o1 l1 10u
RL1 l1 0 2.45k

V2 s2 0 dc 0 ac 1
R2 s2 i2 50
X2 i2 o2 vdd 0 agc RX_LNA fc=1meg
C2 o2 l2 10u
RL2 l2 0 2.45k

V3 s3 0 dc 0 ac 1
R3 s3 i3 50
X3 i3 o3 vdd 0 agc RX_LNA fc=10meg
C3 o3 l3 10u
RL3 l3 0 2.45k

V4 s4 0 dc 0 ac 1
R4 s4 i4 50
X4 i4 o4 vdd 0 agc RX_LNA fc=100meg
C4 o4 l4 10u
RL4 l4 0 2.45k

.control
ac dec 200 10k 500meg
set wr_singlescale
set wr_vecnames
wrdata lna_bands.dat mag(v(o1)/v(i1)) mag(v(o2)/v(i2)) mag(v(o3)/v(i3)) mag(v(o4)/v(i4))
.endc
.end
