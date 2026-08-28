create_clock -name p0_aclk -period 20.000 -waveform {0.000 10.000} [get_ports aclk]

set_input_delay -clock [get_clocks p0_aclk] 0.000 [get_ports {
  aresetn
  s_axis_tvalid
  s_axis_tdata[*]
  s_axis_tlast
  m_axis_tready
}]

set_output_delay -clock [get_clocks p0_aclk] 0.000 [get_ports {
  s_axis_tready
  m_axis_tvalid
  m_axis_tdata[*]
  m_axis_tlast
  m_axis_tuser_index[*]
  configuration_done
  status_events_sticky[*]
}]
