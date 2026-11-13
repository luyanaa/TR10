/* Verilog module written by vlog2Verilog (qflow) */
/* With explicit power connections */

module tr1um_fifo4_cmp(
    inout VDD,
    inout GND,
    input clk,
    input push,
    input pop,
    input [3:0] data_in,
    output [3:0] data_out,
    output empty,
    output full
);

wire _60_ ;
wire _19_ ;
wire _57_ ;
wire _95_ ;
wire _16_ ;
wire _54_ ;
wire _92_ ;
wire _89_ ;
wire _13_ ;
wire _51_ ;
wire _7_ ;
wire _48_ ;
wire _86_ ;
wire _10_ ;
wire _4_ ;
wire _45_ ;
wire _83_ ;
wire _1_ ;
wire _42_ ;
wire _80_ ;
wire _39_ ;
wire clk ;
wire _77_ ;
wire _36_ ;
wire _74_ ;
wire _33_ ;
wire _71_ ;
wire _68_ ;
wire _30_ ;
wire _27_ ;
wire _100_ ;
wire _65_ ;
wire _24_ ;
wire _62_ ;
wire _59_ ;
wire [3:0] data_out ;
wire _97_ ;
wire _21_ ;
wire [3:0] data_in ;
wire _18_ ;
wire _56_ ;
wire _94_ ;
wire empty ;
wire _15_ ;
wire _53_ ;
wire _91_ ;
wire _9_ ;
wire _88_ ;
wire _12_ ;
wire _50_ ;
wire _6_ ;
wire _47_ ;
wire _85_ ;
wire _3_ ;
wire _44_ ;
wire _82_ ;
wire _79_ ;
wire _0_ ;
wire _41_ ;
wire _38_ ;
wire _76_ ;
wire _35_ ;
wire _73_ ;
wire [1:0] wr_ptr ;
wire full ;
wire _32_ ;
wire _70_ ;
wire _29_ ;
wire _67_ ;
wire _26_ ;
wire [0:0] _64_ ;
wire [3:0] _99_ ;
wire [2:0] count ;
wire _23_ ;
wire _61_ ;
wire pop ;
wire _58_ ;
wire [0:0] _96_ ;
wire [3:0] mem0 ;
wire [3:0] mem1 ;
wire [3:0] mem2 ;
wire [3:0] mem3 ;
wire _20_ ;
wire _17_ ;
wire _55_ ;
wire _93_ ;
wire _14_ ;
wire _52_ ;
wire _90_ ;
wire _8_ ;
wire _49_ ;
wire _87_ ;
wire push ;
wire _11_ ;
wire _5_ ;
wire _46_ ;
wire _84_ ;
wire _2_ ;
wire _43_ ;
wire [0:0] _81_ ;
wire _78_ ;
wire _40_ ;
wire _37_ ;
wire _75_ ;
wire _34_ ;
wire _72_ ;
wire _69_ ;
wire _31_ ;
wire _28_ ;
wire _66_ ;
wire _25_ ;
wire _63_ ;
wire _98_ ;
wire [1:0] rd_ptr ;
wire _22_ ;

MUX2 _168_ (
    .GND(GND),
    .VDD(VDD),
    .A(mem3[2]),
    .B(data_in[2]),
    .S(_80_),
    .Y(_47_)
);

NOR2 _130_ (
    .GND(GND),
    .VDD(VDD),
    .A(_72_),
    .B(_75_),
    .Y(_77_)
);

FILL1 FILL483300x62100 (
    .GND(GND),
    .VDD(VDD)
);

OR2 _127_ (
    .GND(GND),
    .VDD(VDD),
    .A(count[0]),
    .B(count[1]),
    .Y(_74_)
);

MUX2 _165_ (
    .GND(GND),
    .VDD(VDD),
    .A(wr_ptr[0]),
    .B(_96_[0]),
    .S(_62_),
    .Y(_39_)
);

NAND2 _124_ (
    .GND(GND),
    .VDD(VDD),
    .A(count[0]),
    .B(count[1]),
    .Y(_71_)
);

INV_X1 _162_ (
    .GND(GND),
    .VDD(VDD),
    .A(count[0]),
    .Y(_1_)
);

FILL1 FILL483300x359100 (
    .GND(GND),
    .VDD(VDD)
);

AOI21 _159_ (
    .GND(GND),
    .VDD(VDD),
    .A1(_74_),
    .A2(_71_),
    .B(_97_),
    .Y(_100_)
);

DFF _197_ (
    .GND(GND),
    .VDD(VDD),
    .CK(clk),
    .D(_43_),
    .Q(mem1[2]),
    .QB(_19_)
);

INV_X1 _121_ (
    .GND(GND),
    .VDD(VDD),
    .A(pop),
    .Y(_69_)
);

INV_X1 _118_ (
    .GND(GND),
    .VDD(VDD),
    .A(wr_ptr[1]),
    .Y(_67_)
);

NAND2 _156_ (
    .GND(GND),
    .VDD(VDD),
    .A(_71_),
    .B(_74_),
    .Y(_94_)
);

DFF _194_ (
    .GND(GND),
    .VDD(VDD),
    .CK(clk),
    .D(_40_),
    .Q(count[0]),
    .QB(_81_[0])
);

MUX2 _115_ (
    .GND(GND),
    .VDD(VDD),
    .A(mem0[0]),
    .B(data_in[0]),
    .S(_66_),
    .Y(_59_)
);

NAND2 _153_ (
    .GND(GND),
    .VDD(VDD),
    .A(_70_),
    .B(_65_),
    .Y(_91_)
);

DFF _209_ (
    .GND(GND),
    .VDD(VDD),
    .CK(clk),
    .D(_55_),
    .Q(mem1[3]),
    .QB(_32_)
);

DFF _191_ (
    .GND(GND),
    .VDD(VDD),
    .CK(clk),
    .D(_37_),
    .Q(mem3[1]),
    .QB(_30_)
);

DFF _188_ (
    .GND(GND),
    .VDD(VDD),
    .CK(clk),
    .D(_47_),
    .Q(mem3[2]),
    .QB(_31_)
);

MUX2 _112_ (
    .GND(GND),
    .VDD(VDD),
    .A(data_in[2]),
    .B(mem2[2]),
    .S(_63_),
    .Y(_60_)
);

INV_X1 _150_ (
    .GND(GND),
    .VDD(VDD),
    .A(count[1]),
    .Y(_88_)
);

DFF _206_ (
    .GND(GND),
    .VDD(VDD),
    .CK(clk),
    .D(_52_),
    .Q(mem0[1]),
    .QB(_28_)
);

NOR3 _109_ (
    .GND(GND),
    .VDD(VDD),
    .A(count[0]),
    .B(count[1]),
    .C(_84_),
    .Y(_0_)
);

MUX2 _147_ (
    .GND(GND),
    .VDD(VDD),
    .A(rd_ptr[0]),
    .B(_64_[0]),
    .S(_70_),
    .Y(_45_)
);

AOI22 _185_ (
    .GND(GND),
    .VDD(VDD),
    .A1(_85_),
    .A2(mem1[3]),
    .B1(_9_),
    .B2(mem2[3]),
    .Y(_16_)
);

DFF _203_ (
    .GND(GND),
    .VDD(VDD),
    .CK(clk),
    .D(_50_),
    .Q(mem0[2]),
    .QB(_26_)
);

BUF_X1 _106_ (
    .GND(GND),
    .VDD(VDD),
    .A(_0_),
    .Y(full)
);

NAND2 _144_ (
    .GND(GND),
    .VDD(VDD),
    .A(rd_ptr[0]),
    .B(_85_),
    .Y(_86_)
);

OAI21 _182_ (
    .GND(GND),
    .VDD(VDD),
    .A1(_12_),
    .A2(_87_),
    .B(_13_),
    .Y(_14_)
);

FILL2 FILL477900x240300 (
    .GND(GND),
    .VDD(VDD)
);

MUX2 _179_ (
    .GND(GND),
    .VDD(VDD),
    .A(_11_),
    .B(mem0[1]),
    .S(_4_),
    .Y(_99_[1])
);

DFF _200_ (
    .GND(GND),
    .VDD(VDD),
    .CK(clk),
    .D(_46_),
    .Q(rd_ptr[1]),
    .QB(_23_)
);

FILL2 FILL477900x2700 (
    .GND(GND),
    .VDD(VDD)
);

BUF_X1 _103_ (
    .GND(GND),
    .VDD(VDD),
    .A(_99_[1]),
    .Y(data_out[1])
);

INV_X1 _141_ (
    .GND(GND),
    .VDD(VDD),
    .A(rd_ptr[0]),
    .Y(_82_)
);

NAND2 _138_ (
    .GND(GND),
    .VDD(VDD),
    .A(_68_),
    .B(_79_),
    .Y(_49_)
);

NOR2 _176_ (
    .GND(GND),
    .VDD(VDD),
    .A(rd_ptr[0]),
    .B(_85_),
    .Y(_9_)
);

MUX2 _135_ (
    .GND(GND),
    .VDD(VDD),
    .A(data_in[0]),
    .B(mem1[0]),
    .S(_68_),
    .Y(_51_)
);

FILL1 FILL483300x121500 (
    .GND(GND),
    .VDD(VDD)
);

OAI22 _173_ (
    .GND(GND),
    .VDD(VDD),
    .A1(_82_),
    .A2(mem1[2]),
    .B1(_6_),
    .B2(_85_),
    .Y(_7_)
);

NOR2 _132_ (
    .GND(GND),
    .VDD(VDD),
    .A(_76_),
    .B(_78_),
    .Y(_54_)
);

NOR2 _170_ (
    .GND(GND),
    .VDD(VDD),
    .A(rd_ptr[1]),
    .B(rd_ptr[0]),
    .Y(_4_)
);

NOR3 _129_ (
    .GND(GND),
    .VDD(VDD),
    .A(count[2]),
    .B(_72_),
    .C(_75_),
    .Y(_76_)
);

MUX2 _167_ (
    .GND(GND),
    .VDD(VDD),
    .A(mem3[1]),
    .B(data_in[1]),
    .S(_80_),
    .Y(_37_)
);

INV_X1 _126_ (
    .GND(GND),
    .VDD(VDD),
    .A(count[2]),
    .Y(_73_)
);

OAI21 _164_ (
    .GND(GND),
    .VDD(VDD),
    .A1(_1_),
    .A2(_92_),
    .B(_2_),
    .Y(_40_)
);

DFF _199_ (
    .GND(GND),
    .VDD(VDD),
    .CK(clk),
    .D(_45_),
    .Q(rd_ptr[0]),
    .QB(_64_[0])
);

NOR2 _123_ (
    .GND(GND),
    .VDD(VDD),
    .A(_69_),
    .B(_98_),
    .Y(_70_)
);

MUX2 _161_ (
    .GND(GND),
    .VDD(VDD),
    .A(data_in[0]),
    .B(mem2[0]),
    .S(_63_),
    .Y(_41_)
);

NOR2 _158_ (
    .GND(GND),
    .VDD(VDD),
    .A(_62_),
    .B(_89_),
    .Y(_97_)
);

DFF _196_ (
    .GND(GND),
    .VDD(VDD),
    .CK(clk),
    .D(_42_),
    .Q(count[1]),
    .QB(_18_)
);

MUX2 _120_ (
    .GND(GND),
    .VDD(VDD),
    .A(data_in[3]),
    .B(mem1[3]),
    .S(_68_),
    .Y(_55_)
);

MUX2 _117_ (
    .GND(GND),
    .VDD(VDD),
    .A(data_in[3]),
    .B(mem2[3]),
    .S(_63_),
    .Y(_57_)
);

NOR2 _155_ (
    .GND(GND),
    .VDD(VDD),
    .A(_70_),
    .B(_65_),
    .Y(_93_)
);

DFF _193_ (
    .GND(GND),
    .VDD(VDD),
    .CK(clk),
    .D(_39_),
    .Q(wr_ptr[0]),
    .QB(_96_[0])
);

NOR3 _114_ (
    .GND(GND),
    .VDD(VDD),
    .A(wr_ptr[1]),
    .B(wr_ptr[0]),
    .C(_65_),
    .Y(_66_)
);

NAND2 _152_ (
    .GND(GND),
    .VDD(VDD),
    .A(_62_),
    .B(_89_),
    .Y(_90_)
);

DFF _208_ (
    .GND(GND),
    .VDD(VDD),
    .CK(clk),
    .D(_54_),
    .Q(count[2]),
    .QB(_84_)
);

DFF _190_ (
    .GND(GND),
    .VDD(VDD),
    .CK(clk),
    .D(_60_),
    .Q(mem2[2]),
    .QB(_36_)
);

MUX2 _149_ (
    .GND(GND),
    .VDD(VDD),
    .A(data_in[2]),
    .B(mem1[2]),
    .S(_68_),
    .Y(_43_)
);

MUX2 _187_ (
    .GND(GND),
    .VDD(VDD),
    .A(_17_),
    .B(mem0[3]),
    .S(_4_),
    .Y(_99_[3])
);

NAND3 _111_ (
    .GND(GND),
    .VDD(VDD),
    .A(wr_ptr[1]),
    .B(_56_),
    .C(_62_),
    .Y(_63_)
);

DFF _205_ (
    .GND(GND),
    .VDD(VDD),
    .CK(clk),
    .D(_51_),
    .Q(mem1[0]),
    .QB(_27_)
);

INV_X1 _108_ (
    .GND(GND),
    .VDD(VDD),
    .A(push),
    .Y(_61_)
);

MUX2 _146_ (
    .GND(GND),
    .VDD(VDD),
    .A(rd_ptr[1]),
    .B(_87_),
    .S(_70_),
    .Y(_46_)
);

INV_X1 _184_ (
    .GND(GND),
    .VDD(VDD),
    .A(mem3[3]),
    .Y(_15_)
);

DFF _202_ (
    .GND(GND),
    .VDD(VDD),
    .CK(clk),
    .D(_49_),
    .Q(wr_ptr[1]),
    .QB(_25_)
);

BUF_X1 _105_ (
    .GND(GND),
    .VDD(VDD),
    .A(_98_),
    .Y(empty)
);

INV_X1 _143_ (
    .GND(GND),
    .VDD(VDD),
    .A(rd_ptr[1]),
    .Y(_85_)
);

AOI22 _181_ (
    .GND(GND),
    .VDD(VDD),
    .A1(_85_),
    .A2(mem1[0]),
    .B1(_9_),
    .B2(mem2[0]),
    .Y(_13_)
);

OAI21 _178_ (
    .GND(GND),
    .VDD(VDD),
    .A1(_8_),
    .A2(_87_),
    .B(_10_),
    .Y(_11_)
);

BUF_X1 _102_ (
    .GND(GND),
    .VDD(VDD),
    .A(_99_[2]),
    .Y(data_out[2])
);

MUX2 _140_ (
    .GND(GND),
    .VDD(VDD),
    .A(mem3[3]),
    .B(data_in[3]),
    .S(_80_),
    .Y(_48_)
);

OAI21 _137_ (
    .GND(GND),
    .VDD(VDD),
    .A1(_56_),
    .A2(_65_),
    .B(wr_ptr[1]),
    .Y(_79_)
);

INV_X1 _175_ (
    .GND(GND),
    .VDD(VDD),
    .A(mem3[1]),
    .Y(_8_)
);

MUX2 _134_ (
    .GND(GND),
    .VDD(VDD),
    .A(mem0[1]),
    .B(data_in[1]),
    .S(_66_),
    .Y(_52_)
);

AND2_X1 _172_ (
    .GND(GND),
    .VDD(VDD),
    .A(mem2[2]),
    .B(_82_),
    .Y(_6_)
);

INV_X1 _169_ (
    .GND(GND),
    .VDD(VDD),
    .A(mem0[2]),
    .Y(_3_)
);

NOR2 _131_ (
    .GND(GND),
    .VDD(VDD),
    .A(_73_),
    .B(_77_),
    .Y(_78_)
);

NOR4 _128_ (
    .GND(GND),
    .VDD(VDD),
    .A(_73_),
    .B(_69_),
    .C(_74_),
    .D(_62_),
    .Y(_75_)
);

MUX2 _166_ (
    .GND(GND),
    .VDD(VDD),
    .A(mem3[0]),
    .B(data_in[0]),
    .S(_80_),
    .Y(_38_)
);

NOR4 _125_ (
    .GND(GND),
    .VDD(VDD),
    .A(_61_),
    .B(_0_),
    .C(_71_),
    .D(_70_),
    .Y(_72_)
);

OAI21 _163_ (
    .GND(GND),
    .VDD(VDD),
    .A1(_97_),
    .A2(_93_),
    .B(_81_[0]),
    .Y(_2_)
);

DFF _198_ (
    .GND(GND),
    .VDD(VDD),
    .CK(clk),
    .D(_44_),
    .Q(mem2[1]),
    .QB(_20_)
);

NOR3 _122_ (
    .GND(GND),
    .VDD(VDD),
    .A(count[2]),
    .B(count[0]),
    .C(count[1]),
    .Y(_98_)
);

OAI22 _160_ (
    .GND(GND),
    .VDD(VDD),
    .A1(_100_),
    .A2(_95_),
    .B1(_92_),
    .B2(_88_),
    .Y(_42_)
);

NAND3 _119_ (
    .GND(GND),
    .VDD(VDD),
    .A(_67_),
    .B(wr_ptr[0]),
    .C(_62_),
    .Y(_68_)
);

NOR2 _157_ (
    .GND(GND),
    .VDD(VDD),
    .A(_94_),
    .B(_93_),
    .Y(_95_)
);

DFF _195_ (
    .GND(GND),
    .VDD(VDD),
    .CK(clk),
    .D(_41_),
    .Q(mem2[0]),
    .QB(_21_)
);

MUX2 _116_ (
    .GND(GND),
    .VDD(VDD),
    .A(mem0[3]),
    .B(data_in[3]),
    .S(_66_),
    .Y(_58_)
);

NAND2 _154_ (
    .GND(GND),
    .VDD(VDD),
    .A(_90_),
    .B(_91_),
    .Y(_92_)
);

DFF _192_ (
    .GND(GND),
    .VDD(VDD),
    .CK(clk),
    .D(_38_),
    .Q(mem3[0]),
    .QB(_22_)
);

DFF _189_ (
    .GND(GND),
    .VDD(VDD),
    .CK(clk),
    .D(_59_),
    .Q(mem0[0]),
    .QB(_35_)
);

DFF _210_ (
    .GND(GND),
    .VDD(VDD),
    .CK(clk),
    .D(_57_),
    .Q(mem2[3]),
    .QB(_33_)
);

INV_X1 _113_ (
    .GND(GND),
    .VDD(VDD),
    .A(_62_),
    .Y(_65_)
);

OAI21 _151_ (
    .GND(GND),
    .VDD(VDD),
    .A1(count[2]),
    .A2(_74_),
    .B(pop),
    .Y(_89_)
);

DFF _207_ (
    .GND(GND),
    .VDD(VDD),
    .CK(clk),
    .D(_53_),
    .Q(mem1[1]),
    .QB(_29_)
);

MUX2 _148_ (
    .GND(GND),
    .VDD(VDD),
    .A(data_in[1]),
    .B(mem2[1]),
    .S(_63_),
    .Y(_44_)
);

OAI21 _186_ (
    .GND(GND),
    .VDD(VDD),
    .A1(_15_),
    .A2(_87_),
    .B(_16_),
    .Y(_17_)
);

NOR2 _110_ (
    .GND(GND),
    .VDD(VDD),
    .A(_61_),
    .B(_0_),
    .Y(_62_)
);

DFF _204_ (
    .GND(GND),
    .VDD(VDD),
    .CK(clk),
    .D(_58_),
    .Q(mem0[3]),
    .QB(_34_)
);

INV_X1 _107_ (
    .GND(GND),
    .VDD(VDD),
    .A(wr_ptr[0]),
    .Y(_56_)
);

NAND2 _145_ (
    .GND(GND),
    .VDD(VDD),
    .A(_83_),
    .B(_86_),
    .Y(_87_)
);

MUX2 _183_ (
    .GND(GND),
    .VDD(VDD),
    .A(_14_),
    .B(mem0[0]),
    .S(_4_),
    .Y(_99_[0])
);

DFF _201_ (
    .GND(GND),
    .VDD(VDD),
    .CK(clk),
    .D(_48_),
    .Q(mem3[3]),
    .QB(_24_)
);

BUF_X1 _104_ (
    .GND(GND),
    .VDD(VDD),
    .A(_99_[0]),
    .Y(data_out[0])
);

NAND2 _142_ (
    .GND(GND),
    .VDD(VDD),
    .A(rd_ptr[1]),
    .B(_82_),
    .Y(_83_)
);

INV_X1 _180_ (
    .GND(GND),
    .VDD(VDD),
    .A(mem3[0]),
    .Y(_12_)
);

NOR3 _139_ (
    .GND(GND),
    .VDD(VDD),
    .A(_67_),
    .B(_56_),
    .C(_65_),
    .Y(_80_)
);

AOI22 _177_ (
    .GND(GND),
    .VDD(VDD),
    .A1(_85_),
    .A2(mem1[1]),
    .B1(_9_),
    .B2(mem2[1]),
    .Y(_10_)
);

BUF_X1 _101_ (
    .GND(GND),
    .VDD(VDD),
    .A(_99_[3]),
    .Y(data_out[3])
);

MUX2 _136_ (
    .GND(GND),
    .VDD(VDD),
    .A(mem0[2]),
    .B(data_in[2]),
    .S(_66_),
    .Y(_50_)
);

AOI22 _174_ (
    .GND(GND),
    .VDD(VDD),
    .A1(_3_),
    .A2(_4_),
    .B1(_7_),
    .B2(_5_),
    .Y(_99_[2])
);

MUX2 _133_ (
    .GND(GND),
    .VDD(VDD),
    .A(data_in[1]),
    .B(mem1[1]),
    .S(_68_),
    .Y(_53_)
);

NAND3 _171_ (
    .GND(GND),
    .VDD(VDD),
    .A(mem3[2]),
    .B(_83_),
    .C(_86_),
    .Y(_5_)
);

endmodule
