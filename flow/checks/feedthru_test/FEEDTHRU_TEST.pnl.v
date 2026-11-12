module FEEDTHRU_TEST (A, Y, VDD, GND, VSS);
  input A;
  output Y;
  inout VDD;
  inout GND;
  inout VSS;
  INV_X1 u0 (.A(A), .Y(Y), .VDD(VDD), .GND(GND));
  FEEDTHRU u1 (.A(Y), .VDD(VDD), .GND(GND));
endmodule
