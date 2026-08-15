create_clock -name phase06e_aclk -period 10.000 -waveform {0.000 5.000} [get_ports aclk]

set_input_delay -clock [get_clocks phase06e_aclk] 0.000 [get_ports {
  aresetn
  s_axis_tvalid
  s_axis_tdata[*]
  s_axis_tlast
  m_axis_tready
}]

set_output_delay -clock [get_clocks phase06e_aclk] 0.000 [get_ports {
  s_axis_tready
  m_axis_tvalid
  m_axis_tdata[*]
  m_axis_tlast
  m_axis_tuser_index[*]
  configuration_done
  status_events_sticky[*]
}]

# The wrapper output skid-buffer registers directly drive these payload ports.
# Pack them into IOB output registers without changing AXI behavior or latency.
set_property IOB TRUE [get_ports {
  m_axis_tdata[*]
  m_axis_tlast
  m_axis_tuser_index[*]
}]
