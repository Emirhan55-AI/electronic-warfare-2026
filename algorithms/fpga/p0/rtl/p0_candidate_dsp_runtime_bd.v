// AXI module wrapper for the complete CI8-to-candidate packet path.
module p0_candidate_dsp_runtime_bd (
  input         aclk,
  input         aresetn,
  input         s_axis_tvalid,
  output        s_axis_tready,
  input  [15:0] s_axis_tdata,
  input  [1:0]  s_axis_tkeep,
  input         s_axis_tlast,
  output        m_axis_tvalid,
  input         m_axis_tready,
  output [63:0] m_axis_tdata,
  output [7:0]  m_axis_tkeep,
  output        m_axis_tlast
);
  wire        unused_configuration_done;
  wire [5:0]  unused_status_events;
  wire        unused_keep_error;
  wire [8:0]  unused_reducer_status;
  wire        unused_transport_error;
  wire        unused_candidate_overflow;
  wire [31:0] unused_completed_frames;

  p0_candidate_dsp_runtime_top core (
    .aclk(aclk),
    .aresetn(aresetn),
    .s_axis_tvalid(s_axis_tvalid),
    .s_axis_tready(s_axis_tready),
    .s_axis_tdata(s_axis_tdata),
    .s_axis_tkeep(s_axis_tkeep),
    .s_axis_tlast(s_axis_tlast),
    .m_axis_tvalid(m_axis_tvalid),
    .m_axis_tready(m_axis_tready),
    .m_axis_tdata(m_axis_tdata),
    .m_axis_tkeep(m_axis_tkeep),
    .m_axis_tlast(m_axis_tlast),
    .configuration_done(unused_configuration_done),
    .status_events_sticky(unused_status_events),
    .input_keep_error_sticky(unused_keep_error),
    .status_reducer_sticky(unused_reducer_status),
    .status_transport_error_sticky(unused_transport_error),
    .status_candidate_overflow_sticky(unused_candidate_overflow),
    .completed_frame_count(unused_completed_frames)
  );
endmodule
