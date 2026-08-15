module phase06g_detector_synthesis_top (
  input  logic        aclk,
  input  logic        aresetn,
  input  logic        cfg_evaluate_center,
  input  logic [1:0]  cfg_pfa_select,

  input  logic        s_axis_tvalid,
  output logic        s_axis_tready,
  input  logic [31:0] s_axis_tdata,
  input  logic        s_axis_tlast,

  output logic        m_axis_tvalid,
  input  logic        m_axis_tready,
  output logic [57:0] m_axis_tdata,
  output logic        m_axis_tlast,
  output logic [11:0] m_axis_tuser_natural_index,
  output logic [11:0] m_axis_tuser_shifted_index,
  output logic [58:0] m_axis_tuser_median_twice,
  output logic [57:0] m_axis_tuser_noise,
  output logic [61:0] m_axis_tuser_threshold,
  output logic        m_axis_tuser_evaluated,
  output logic        m_axis_tuser_detected,
  output logic [1:0]  m_axis_tuser_pfa_select,
  output logic        m_axis_tuser_evaluate_center,
  output logic        configuration_done,
  output logic [6:0]  status_events_sticky
);
  logic        fft_valid;
  logic        fft_ready;
  logic [63:0] fft_data;
  logic        fft_last;
  logic [11:0] fft_index;
  logic [5:0]  fft_status;
  logic        power_valid;
  logic        power_ready;
  logic [57:0] power_data;
  logic        power_last;
  logic [11:0] power_index;
  logic        detector_frame_error;

  phase06e_fft_implementation_top fft_chain (
    .aclk(aclk), .aresetn(aresetn),
    .s_axis_tvalid(s_axis_tvalid), .s_axis_tready(s_axis_tready),
    .s_axis_tdata(s_axis_tdata), .s_axis_tlast(s_axis_tlast),
    .m_axis_tvalid(fft_valid), .m_axis_tready(fft_ready),
    .m_axis_tdata(fft_data), .m_axis_tlast(fft_last),
    .m_axis_tuser_index(fft_index),
    .configuration_done(configuration_done),
    .status_events_sticky(fft_status)
  );

  axis_fft_linear_power power (
    .aclk(aclk), .aresetn(aresetn),
    .s_axis_tvalid(fft_valid), .s_axis_tready(fft_ready),
    .s_axis_tdata(fft_data), .s_axis_tlast(fft_last),
    .s_axis_tuser_index(fft_index),
    .m_axis_tvalid(power_valid), .m_axis_tready(power_ready),
    .m_axis_tdata(power_data), .m_axis_tlast(power_last),
    .m_axis_tuser_index(power_index)
  );

  axis_regional_detector detector (
    .aclk(aclk), .aresetn(aresetn),
    .cfg_evaluate_center(cfg_evaluate_center), .cfg_pfa_select(cfg_pfa_select),
    .s_axis_tvalid(power_valid), .s_axis_tready(power_ready),
    .s_axis_tdata(power_data), .s_axis_tlast(power_last),
    .s_axis_tuser_index(power_index),
    .m_axis_tvalid(m_axis_tvalid), .m_axis_tready(m_axis_tready),
    .m_axis_tdata(m_axis_tdata), .m_axis_tlast(m_axis_tlast),
    .m_axis_tuser_natural_index(m_axis_tuser_natural_index),
    .m_axis_tuser_shifted_index(m_axis_tuser_shifted_index),
    .m_axis_tuser_median_twice(m_axis_tuser_median_twice),
    .m_axis_tuser_noise(m_axis_tuser_noise),
    .m_axis_tuser_threshold(m_axis_tuser_threshold),
    .m_axis_tuser_evaluated(m_axis_tuser_evaluated),
    .m_axis_tuser_detected(m_axis_tuser_detected),
    .m_axis_tuser_pfa_select(m_axis_tuser_pfa_select),
    .m_axis_tuser_evaluate_center(m_axis_tuser_evaluate_center),
    .status_frame_error_sticky(detector_frame_error)
  );

  assign status_events_sticky = {detector_frame_error, fft_status};
endmodule
