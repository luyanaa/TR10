# C4004 core -- STA constraints matching the upstream measurement.
#
# The upstream sign-off (apr/simulation/VERIFICATION_SUMMARY.md of
# jun1okamura/TR-1um_C4004) characterises the core at 28.50 MHz with a 1 pF
# load per output in ngspice.  The same operating point is used here so the
# LibreLane and qflow numbers are comparable:
#
#   35.088 ns period  (1 / 28.50 MHz)
#   0.5 ns setup/hold uncertainty
#   2.0 ns input and output delay (the upstream testbench drives/monitors
#   through a pad-like 2 ns budget; it is also the qflow run's convention)
#   1 pF output load  (the Liberty capacitive_load_unit is 1 ff -> 1000)

create_clock -period 35.088 -name clk [get_ports clk]
set_clock_uncertainty 0.500 [get_clocks clk]

set_input_delay -clock clk 2.000 [all_inputs]
set_output_delay -clock clk 2.000 [all_outputs]

set_load 1000.0 [all_outputs]
