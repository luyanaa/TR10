// TR10_cmp_sc powered models (blackbox-compatible).

module AND2_X1 (VDD, GND, A, B, Y);
  inout VDD;
  inout GND;
  input A;
  input B;
  output Y;
endmodule

module AND3_X1 (VDD, GND, A, B, C, Y);
  inout VDD;
  inout GND;
  input A;
  input B;
  input C;
  output Y;
endmodule

module AND4_X1 (VDD, GND, A, B, C, D, Y);
  inout VDD;
  inout GND;
  input A;
  input B;
  input C;
  input D;
  output Y;
endmodule

module AOI21 (VDD, GND, A1, A2, B, Y);
  inout VDD;
  inout GND;
  input A1;
  input A2;
  input B;
  output Y;
endmodule

module AOI22 (VDD, GND, A1, A2, B1, B2, Y);
  inout VDD;
  inout GND;
  input A1;
  input A2;
  input B1;
  input B2;
  output Y;
endmodule

module BUFTH (VDD, GND, A, Y);
  inout VDD;
  inout GND;
  input A;
  output Y;
endmodule

module BUF_X1 (VDD, GND, A, Y);
  inout VDD;
  inout GND;
  input A;
  output Y;
endmodule

module BUF_X2 (VDD, GND, A, Y);
  inout VDD;
  inout GND;
  input A;
  output Y;
endmodule

module DEL1 (VDD, GND, A, Y);
  inout VDD;
  inout GND;
  input A;
  output Y;
endmodule

module DFF (VDD, GND, CK, D, Q, QB);
  inout VDD;
  inout GND;
  input CK;
  input D;
  output Q;
  output QB;
endmodule

module DFF2 (VDD, GND, CK, D0, Q0, QB0, D1, Q1, QB1);
  inout VDD;
  inout GND;
  input CK;
  input D0;
  output Q0;
  output QB0;
  input D1;
  output Q1;
  output QB1;
endmodule

module DFFRB (VDD, GND, CK, D, Q, QB, RSTB);
  inout VDD;
  inout GND;
  input CK;
  input D;
  output Q;
  output QB;
  input RSTB;
endmodule

module DFFS (VDD, GND, CK, D, Q, QB, SET);
  inout VDD;
  inout GND;
  input CK;
  input D;
  output Q;
  output QB;
  input SET;
endmodule

module EDFFRB (VDD, GND, CK, D, E, Q, QB, RSTB);
  inout VDD;
  inout GND;
  input CK;
  input D;
  input E;
  output Q;
  output QB;
  input RSTB;
endmodule

module EDFF (VDD, GND, CK, D, E, Q, QB, RSTB);
  inout VDD;
  inout GND;
  input CK;
  input D;
  input E;
  output Q;
  output QB;
  input RSTB;
endmodule

module FILL1 (VDD, GND);
  inout VDD;
  inout GND;
endmodule

module FILL2 (VDD, GND);
  inout VDD;
  inout GND;
endmodule

module FILL3 (VDD, GND);
  inout VDD;
  inout GND;
endmodule

module INV_X1 (VDD, GND, A, Y);
  inout VDD;
  inout GND;
  input A;
  output Y;
endmodule

module INV_X2 (VDD, GND, A, Y);
  inout VDD;
  inout GND;
  input A;
  output Y;
endmodule

module MUX2 (VDD, GND, A, B, S, Y);
  inout VDD;
  inout GND;
  input A;
  input B;
  input S;
  output Y;
endmodule

module MUXDFFRB (VDD, GND, A, B, CK, Q, QB, RSTB, S);
  inout VDD;
  inout GND;
  input A;
  input B;
  input CK;
  output Q;
  output QB;
  input RSTB;
  input S;
endmodule

module NAND2 (VDD, GND, A, B, Y);
  inout VDD;
  inout GND;
  input A;
  input B;
  output Y;
endmodule

module NAND3 (VDD, GND, A, B, C, Y);
  inout VDD;
  inout GND;
  input A;
  input B;
  input C;
  output Y;
endmodule

module NAND4 (VDD, GND, A, B, C, D, Y);
  inout VDD;
  inout GND;
  input A;
  input B;
  input C;
  input D;
  output Y;
endmodule

module NOR2 (VDD, GND, A, B, Y);
  inout VDD;
  inout GND;
  input A;
  input B;
  output Y;
endmodule

module NOR3 (VDD, GND, A, B, C, Y);
  inout VDD;
  inout GND;
  input A;
  input B;
  input C;
  output Y;
endmodule

module NOR4 (VDD, GND, A, B, C, D, Y);
  inout VDD;
  inout GND;
  input A;
  input B;
  input C;
  input D;
  output Y;
endmodule

module OAI21 (VDD, GND, A1, A2, B, Y);
  inout VDD;
  inout GND;
  input A1;
  input A2;
  input B;
  output Y;
endmodule

module OAI22 (VDD, GND, A1, A2, B1, B2, Y);
  inout VDD;
  inout GND;
  input A1;
  input A2;
  input B1;
  input B2;
  output Y;
endmodule

module OR2 (VDD, GND, A, B, Y);
  inout VDD;
  inout GND;
  input A;
  input B;
  output Y;
endmodule

module OR3 (VDD, GND, A, B, C, Y);
  inout VDD;
  inout GND;
  input A;
  input B;
  input C;
  output Y;
endmodule

module OR4 (VDD, GND, A, B, C, D, Y);
  inout VDD;
  inout GND;
  input A;
  input B;
  input C;
  input D;
  output Y;
endmodule

module RSLATCH (VDD, GND, Q, QB, R, S);
  inout VDD;
  inout GND;
  output Q;
  output QB;
  input R;
  input S;
endmodule

module TAP2 (VDD, GND);
  inout VDD;
  inout GND;
endmodule

module TAP3 (VDD, GND);
  inout VDD;
  inout GND;
endmodule

module TLAT (VDD, GND, D, Q, RD, RDB, WR, WRB);
  inout VDD;
  inout GND;
  output D;
  output Q;
  output RD;
  output RDB;
  output WR;
  output WRB;
endmodule

module XNOR2 (VDD, GND, A, B, Y);
  inout VDD;
  inout GND;
  input A;
  input B;
  output Y;
endmodule

module XOR2 (VDD, GND, A, B, Y);
  inout VDD;
  inout GND;
  input A;
  input B;
  output Y;
endmodule

module TIEHI (VDD, GND, HI);
  inout VDD;
  inout GND;
  output HI;
  assign HI = 1'b1;
endmodule

module TIELO (VDD, GND, LO);
  inout VDD;
  inout GND;
  output LO;
  assign LO = 1'b0;
endmodule

module FEEDTHRU (VDD, GND, A);
  inout VDD;
  inout GND;
  inout A;
endmodule

module MUXTG2 (A, B, Y, S, VDD, GND);
  input A;
  input B;
  input S;
  output Y;
  inout VDD;
  inout GND;
endmodule
