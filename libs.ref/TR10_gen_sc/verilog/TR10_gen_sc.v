// TR10 standard-cell behavioral models (synthesis only)
`timescale 1ns/1ps

module AND2_X1 (VDD, GND, Y, A, B);
  input A, B;
  output Y;
  inout VDD, GND;
  assign Y = &{A,B};
endmodule

module AND3_X1 (VDD, GND, Y, A, C, B);
  input A, C, B;
  output Y;
  inout VDD, GND;
  assign Y = &{A,C,B};
endmodule

module AND4_X1 (VDD, GND, Y, A, B, C, D);
  input A, B, C, D;
  output Y;
  inout VDD, GND;
  assign Y = &{A,B,C,D};
endmodule

module BUF_X1 (VDD, GND, Y, A);
  input A;
  output Y;
  inout VDD, GND;
  assign Y = A;
endmodule

module BUF_X12 (VDD, GND, Y, A);
  input A;
  output Y;
  inout VDD, GND;
  assign Y = A;
endmodule

module BUF_X16 (VDD, Y, A, GND);
  input A;
  output Y;
  inout VDD, GND;
  assign Y = A;
endmodule

module BUF_X2 (Y, A, VDD, GND);
  input A;
  output Y;
  inout VDD, GND;
  assign Y = A;
endmodule

module BUF_X4 (Y, A, VDD, GND);
  input A;
  output Y;
  inout VDD, GND;
  assign Y = A;
endmodule

module BUF_X8 (Y, A, VDD, GND);
  input A;
  output Y;
  inout VDD, GND;
  assign Y = A;
endmodule

module CLKBUF_X1 (VDD, A, GND, Y);
  input A;
  output Y;
  inout VDD, GND;
  assign Y = A;
endmodule

module CLKBUF_X12 (Y, VDD, GND, A);
  input A;
  output Y;
  inout VDD, GND;
  assign Y = A;
endmodule

module CLKBUF_X16 (A, Y, VDD, GND);
  input A;
  output Y;
  inout VDD, GND;
  assign Y = A;
endmodule

module CLKBUF_X2 (A, Y, VDD, GND);
  input A;
  output Y;
  inout VDD, GND;
  assign Y = A;
endmodule

module CLKBUF_X4 (Y, A, GND, VDD);
  input A;
  output Y;
  inout VDD, GND;
  assign Y = A;
endmodule

module CLKBUF_X8 (A, Y, VDD, GND);
  input A;
  output Y;
  inout VDD, GND;
  assign Y = A;
endmodule

module DEL1 (Y, A, VDD, GND);
  input A;
  output Y;
  inout VDD, GND;
  assign Y = A;
endmodule

module DEL2 (VDD, Y, A, GND);
  input A;
  output Y;
  inout VDD, GND;
  assign Y = A;
endmodule

module DEL4 (VDD, Y, A, GND);
  input A;
  output Y;
  inout VDD, GND;
  assign Y = A;
endmodule

module DFFR (D, RST, QB, Q, GND, CK, VDD);
  input D, RST, CK;
  output QB;
  output reg Q;
  inout VDD, GND;
  always @(posedge CK or posedge RST) if (RST) Q <= 1'b0; else Q <= D; assign QB = ~Q;
endmodule

module DFFS (SET, D, Q, QB, CK, GND, VDD);
  input SET, D, CK;
  output reg Q;
  output QB;
  inout VDD, GND;
  always @(posedge CK or negedge SET) if (!SET) Q <= 1'b1; else Q <= D; assign QB = ~Q;
endmodule

module INV_X1 (A, VDD, GND, Y);
  input A;
  output Y;
  inout VDD, GND;
  assign Y = ~A;
endmodule

module INV_X12 (Y, A, VDD, GND);
  input A;
  output Y;
  inout VDD, GND;
  assign Y = ~A;
endmodule

module INV_X16 (Y, A, VDD, GND);
  input A;
  output Y;
  inout VDD, GND;
  assign Y = ~A;
endmodule

module INV_X2 (A, Y, VDD, GND);
  input A;
  output Y;
  inout VDD, GND;
  assign Y = ~A;
endmodule

module INV_X4 (Y, A, VDD, GND);
  input A;
  output Y;
  inout VDD, GND;
  assign Y = ~A;
endmodule

module INV_X8 (Y, A, VDD, GND);
  input A;
  output Y;
  inout VDD, GND;
  assign Y = ~A;
endmodule

module MUX2 (S, B, Y, A, GND, VDD);
  input S, B, A;
  output Y;
  inout VDD, GND;
  assign Y = S ? B : A;
endmodule

module NAND2 (GND, Y, B, A, VDD);
  input B, A;
  output Y;
  inout VDD, GND;
  assign Y = ~(&{B,A});
endmodule

module NAND3 (Y, A, C, B, GND, VDD);
  input A, C, B;
  output Y;
  inout VDD, GND;
  assign Y = ~(&{A,C,B});
endmodule

module NAND4 (Y, A, B, C, D, VDD, GND);
  input A, B, C, D;
  output Y;
  inout VDD, GND;
  assign Y = ~(&{A,B,C,D});
endmodule

module NOR2 (A, B, Y, VDD, GND);
  input A, B;
  output Y;
  inout VDD, GND;
  assign Y = ~(|{A,B});
endmodule

module NOR3 (Y, A, B, C, VDD, GND);
  input A, B, C;
  output Y;
  inout VDD, GND;
  assign Y = ~(|{A,B,C});
endmodule

module NOR4 (VDD, C, Y, A, D, B, GND);
  input C, A, D, B;
  output Y;
  inout VDD, GND;
  assign Y = ~(|{C,A,D,B});
endmodule

module OR2 (Y, A, B, VDD, GND);
  input A, B;
  output Y;
  inout VDD, GND;
  assign Y = |{A,B};
endmodule

module OR3 (Y, A, B, C, GND, VDD);
  input A, B, C;
  output Y;
  inout VDD, GND;
  assign Y = |{A,B,C};
endmodule

module OR4 (A, B, C, D, Y, VDD, GND);
  input A, B, C, D;
  output Y;
  inout VDD, GND;
  assign Y = |{A,B,C,D};
endmodule

module XNOR2 (Y, A, B, VDD, GND);
  input A, B;
  output Y;
  inout VDD, GND;
  assign Y = ~(A ^ B);
endmodule

module XOR2 (Y, A, B, VDD, GND);
  input A, B;
  output Y;
  inout VDD, GND;
  assign Y = A ^ B;
endmodule

module TIEHI (HI, VDD, GND);
  output HI;
  inout VDD, GND;
  assign HI = 1'b1;
endmodule

module TIELO (LO, VDD, GND);
  output LO;
  inout VDD, GND;
  assign LO = 1'b0;
endmodule

module FILL_1(); endmodule
module FILL_2(); endmodule
