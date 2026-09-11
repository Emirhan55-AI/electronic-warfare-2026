module amd_xfft_runtime_adapter (
  input  logic        aclk,
  input  logic        aresetn,

  input  logic        s_axis_config_tvalid,
  output logic        s_axis_config_tready,
  input  logic [15:0] s_axis_config_tdata,

  input  logic        s_axis_data_tvalid,
  output logic        s_axis_data_tready,
  input  logic [31:0] s_axis_data_tdata,
  input  logic        s_axis_data_tlast,

  output logic        m_axis_data_tvalid,
  input  logic        m_axis_data_tready,
  output logic [63:0] m_axis_data_tdata,
  output logic        m_axis_data_tlast,
  output logic [13:0] m_axis_data_tuser_index,

  output logic        event_frame_started,
  output logic        event_tlast_unexpected,
  output logic        event_tlast_missing,
  output logic        event_status_channel_halt,
  output logic        event_data_in_channel_halt,
  output logic        event_data_out_channel_halt
);
  logic [63:0] amd_m_axis_data_tdata;
  logic [15:0] amd_m_axis_data_tuser;

  // The max-16384 unscaled core exposes signed 31-bit components in two
  // byte-aligned 32-bit lanes. Keep the external lanes sign-extended.
  assign m_axis_data_tdata = {
    {amd_m_axis_data_tdata[62], amd_m_axis_data_tdata[62:32]},
    {amd_m_axis_data_tdata[30], amd_m_axis_data_tdata[30:0]}
  };
  assign m_axis_data_tuser_index = amd_m_axis_data_tuser[13:0];

  st06_fft_runtime_16384 fft_ip (
    .aclk(aclk), .aresetn(aresetn),
    .s_axis_config_tdata(s_axis_config_tdata),
    .s_axis_config_tvalid(s_axis_config_tvalid),
    .s_axis_config_tready(s_axis_config_tready),
    .s_axis_data_tdata(s_axis_data_tdata),
    .s_axis_data_tvalid(s_axis_data_tvalid),
    .s_axis_data_tready(s_axis_data_tready),
    .s_axis_data_tlast(s_axis_data_tlast),
    .m_axis_data_tdata(amd_m_axis_data_tdata),
    .m_axis_data_tuser(amd_m_axis_data_tuser),
    .m_axis_data_tvalid(m_axis_data_tvalid),
    .m_axis_data_tready(m_axis_data_tready),
    .m_axis_data_tlast(m_axis_data_tlast),
    .event_frame_started(event_frame_started),
    .event_tlast_unexpected(event_tlast_unexpected),
    .event_tlast_missing(event_tlast_missing),
    .event_status_channel_halt(event_status_channel_halt),
    .event_data_in_channel_halt(event_data_in_channel_halt),
    .event_data_out_channel_halt(event_data_out_channel_halt)
  );
endmodule
