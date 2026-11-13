set_units -time ns
create_clock -name vclk -period 10
set_input_delay 1 -clock vclk [all_inputs]
set_output_delay 1 -clock vclk [all_outputs]
