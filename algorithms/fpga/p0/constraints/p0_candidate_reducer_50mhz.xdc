create_clock -name p0_candidate_aclk -period 20.000 -waveform {0.000 10.000} [get_ports aclk]

set_input_delay -clock [get_clocks p0_candidate_aclk] 0.000 [get_ports {
  aresetn
  s_axis_tvalid
  s_axis_tdata[*]
  s_axis_tlast
  s_axis_tuser_index[*]
}]

set_output_delay -clock [get_clocks p0_candidate_aclk] 0.000 [get_ports {
  observable[*]
}]
