// SRAM128 blackbox for the pinned C4004 gate-level netlist.
//
// The synthesised netlist instantiates ``SRAM128`` (32x4-bit 6T SRAM).  The
// real views live in ``libs.ref/TR10_SRAM128`` and are attached through
// LibreLane's ``MACROS``; Yosys only needs the port contract to elaborate the
// netlist (``SYNTH_ELABORATE_ONLY``).
//
// The upstream macro keeps its supplies (VDD/GND) out of the Verilog model:
// LEF pins + Liberty ``pg_pin`` records carry them, and
// ``PDN_MACRO_CONNECTIONS`` hooks them to the top-level grid.

(* blackbox *)
module SRAM128 (
    input  A0,
    input  A1,
    input  A2,
    input  A3,
    input  A4,
    input  CE,
    input  [3:0] DIN,
    input  WR,
    output [3:0] DO
);
endmodule
