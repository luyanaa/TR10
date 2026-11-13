module feedthru_route (input wire A, output wire Y);
  wire n;
  assign n = ~A;
  assign Y = n;
  (* keep *) FEEDTHRU u1 (.A(n));
endmodule
