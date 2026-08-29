`timescale 1ns/1ps

// Complete PL candidate path: CI8 input through FFT/power into the
// multi-scale candidate reducer and the frozen PHASE-06I packet ABI.
// DMA, PS ownership and board pin assignment remain outside this module.
module p0_candidate_dsp_runtime_top (
  input  logic        aclk,
  input  logic        aresetn,

  input  logic        s_axis_tvalid,
  output logic        s_axis_tready,
  input  logic [15:0] s_axis_tdata,
  input  logic [1:0]  s_axis_tkeep,
  input  logic        s_axis_tlast,

  output logic        m_axis_tvalid,
  input  logic        m_axis_tready,
  output logic [63:0] m_axis_tdata,
  output logic [7:0]  m_axis_tkeep,
  output logic        m_axis_tlast,

  output logic        configuration_done,
  output logic [5:0]  status_events_sticky,
  output logic        input_keep_error_sticky,
  output logic [8:0]  status_reducer_sticky,
  output logic        status_transport_error_sticky,
  output logic        status_candidate_overflow_sticky,
  output logic [31:0] completed_frame_count
);
  logic        hann_valid;
  logic        hann_ready;
  logic [31:0] hann_data;
  logic        hann_last;
  logic        fft_valid;
  logic        fft_ready;
  logic [63:0] fft_data;
  logic        fft_last;
  logic [11:0] fft_index;
  logic        power_valid;
  logic        power_ready;
  logic [57:0] power_data;
  logic        power_last;
  logic [11:0] power_index;

  logic        fft_s_axis_config_tvalid;
  logic        fft_s_axis_config_tready;
  logic [7:0]  fft_s_axis_config_tdata;
  logic        fft_s_axis_data_tvalid;
  logic        fft_s_axis_data_tready;
  logic [31:0] fft_s_axis_data_tdata;
  logic        fft_s_axis_data_tlast;
  logic        fft_m_axis_data_tvalid;
  logic        fft_m_axis_data_tready;
  logic [63:0] fft_m_axis_data_tdata;
  logic        fft_m_axis_data_tlast;
  logic [11:0] fft_m_axis_data_tuser_index;
  logic        fft_event_frame_started;
  logic        fft_event_tlast_unexpected;
  logic        fft_event_tlast_missing;
  logic        fft_event_status_channel_halt;
  logic        fft_event_data_in_channel_halt;
  logic        fft_event_data_out_channel_halt;
  logic        input_keep_error_sticky_reg;

  assign input_keep_error_sticky = input_keep_error_sticky_reg;

  axis_hann_window #(
    .COEFFICIENT_FILE("datasets/fixtures/phase06b/hann-coefficients.mem")
  ) hann (
    .aclk(aclk),
    .aresetn(aresetn),
    .s_axis_tvalid(s_axis_tvalid),
    .s_axis_tready(s_axis_tready),
    .s_axis_tdata(s_axis_tdata),
    .s_axis_tlast(s_axis_tlast),
    .m_axis_tvalid(hann_valid),
    .m_axis_tready(hann_ready),
    .m_axis_tdata(hann_data),
    .m_axis_tlast(hann_last)
  );

  axis_fft_wrapper fft_wrapper (
    .aclk(aclk), .aresetn(aresetn),
    .s_axis_tvalid(hann_valid), .s_axis_tready(hann_ready),
    .s_axis_tdata(hann_data), .s_axis_tlast(hann_last),
    .m_axis_tvalid(fft_valid), .m_axis_tready(fft_ready),
    .m_axis_tdata(fft_data), .m_axis_tlast(fft_last), .m_axis_tuser_index(fft_index),
    .fft_s_axis_config_tvalid(fft_s_axis_config_tvalid),
    .fft_s_axis_config_tready(fft_s_axis_config_tready),
    .fft_s_axis_config_tdata(fft_s_axis_config_tdata),
    .fft_s_axis_data_tvalid(fft_s_axis_data_tvalid),
    .fft_s_axis_data_tready(fft_s_axis_data_tready),
    .fft_s_axis_data_tdata(fft_s_axis_data_tdata),
    .fft_s_axis_data_tlast(fft_s_axis_data_tlast),
    .fft_m_axis_data_tvalid(fft_m_axis_data_tvalid),
    .fft_m_axis_data_tready(fft_m_axis_data_tready),
    .fft_m_axis_data_tdata(fft_m_axis_data_tdata),
    .fft_m_axis_data_tlast(fft_m_axis_data_tlast),
    .fft_m_axis_data_tuser_index(fft_m_axis_data_tuser_index),
    .fft_event_frame_started(fft_event_frame_started),
    .fft_event_tlast_unexpected(fft_event_tlast_unexpected),
    .fft_event_tlast_missing(fft_event_tlast_missing),
    .fft_event_status_channel_halt(fft_event_status_channel_halt),
    .fft_event_data_in_channel_halt(fft_event_data_in_channel_halt),
    .fft_event_data_out_channel_halt(fft_event_data_out_channel_halt),
    .configuration_done(configuration_done),
    .status_events_sticky(status_events_sticky)
  );

  amd_xfft_adapter fft (
    .aclk(aclk), .aresetn(aresetn),
    .s_axis_config_tvalid(fft_s_axis_config_tvalid),
    .s_axis_config_tready(fft_s_axis_config_tready),
    .s_axis_config_tdata(fft_s_axis_config_tdata),
    .s_axis_data_tvalid(fft_s_axis_data_tvalid),
    .s_axis_data_tready(fft_s_axis_data_tready),
    .s_axis_data_tdata(fft_s_axis_data_tdata),
    .s_axis_data_tlast(fft_s_axis_data_tlast),
    .m_axis_data_tvalid(fft_m_axis_data_tvalid),
    .m_axis_data_tready(fft_m_axis_data_tready),
    .m_axis_data_tdata(fft_m_axis_data_tdata),
    .m_axis_data_tlast(fft_m_axis_data_tlast),
    .m_axis_data_tuser_index(fft_m_axis_data_tuser_index),
    .event_frame_started(fft_event_frame_started),
    .event_tlast_unexpected(fft_event_tlast_unexpected),
    .event_tlast_missing(fft_event_tlast_missing),
    .event_status_channel_halt(fft_event_status_channel_halt),
    .event_data_in_channel_halt(fft_event_data_in_channel_halt),
    .event_data_out_channel_halt(fft_event_data_out_channel_halt)
  );

  axis_fft_linear_power power (
    .aclk(aclk), .aresetn(aresetn),
    .s_axis_tvalid(fft_valid), .s_axis_tready(fft_ready),
    .s_axis_tdata(fft_data), .s_axis_tlast(fft_last), .s_axis_tuser_index(fft_index),
    .m_axis_tvalid(power_valid), .m_axis_tready(power_ready),
    .m_axis_tdata(power_data), .m_axis_tlast(power_last), .m_axis_tuser_index(power_index)
  );

  p0_candidate_reducer_packetizer_top candidate_path (
    .aclk(aclk), .aresetn(aresetn),
    .s_axis_tvalid(power_valid), .s_axis_tready(power_ready),
    .s_axis_tdata(power_data), .s_axis_tlast(power_last),
    .s_axis_tuser_index(power_index),
    .m_axis_tvalid(m_axis_tvalid), .m_axis_tready(m_axis_tready),
    .m_axis_tdata(m_axis_tdata), .m_axis_tkeep(m_axis_tkeep), .m_axis_tlast(m_axis_tlast),
    .completed_frame_count(completed_frame_count),
    .status_transport_error_sticky(status_transport_error_sticky),
    .status_candidate_overflow_sticky(status_candidate_overflow_sticky),
    .status_reducer_sticky(status_reducer_sticky)
  );

  always_ff @(posedge aclk) begin
    if (!aresetn) begin
      input_keep_error_sticky_reg <= 1'b0;
    end else if (s_axis_tvalid && s_axis_tready && s_axis_tkeep != 2'b11) begin
      input_keep_error_sticky_reg <= 1'b1;
    end
  end
endmodule
