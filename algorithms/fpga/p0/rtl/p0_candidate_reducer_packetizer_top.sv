`timescale 1ns/1ps

// P0 final candidate reducer to the frozen PHASE-06I AXI4-Stream packet ABI.
// This is a transport-boundary integration top; DMA, PS ownership and board
// pin assignment remain outside this module.
module p0_candidate_reducer_packetizer_top (
  input  logic        aclk,
  input  logic        aresetn,
  input  logic        s_axis_tvalid,
  output logic        s_axis_tready,
  input  logic [57:0] s_axis_tdata,
  input  logic        s_axis_tlast,
  input  logic [11:0] s_axis_tuser_index,
  output logic        m_axis_tvalid,
  input  logic        m_axis_tready,
  output logic [63:0] m_axis_tdata,
  output logic [7:0]  m_axis_tkeep,
  output logic        m_axis_tlast,
  output logic [31:0] completed_frame_count,
  output logic        status_transport_error_sticky,
  output logic        status_candidate_overflow_sticky,
  output logic [8:0]  status_reducer_sticky
);
  logic reducer_tvalid;
  logic reducer_tready;
  logic [57:0] reducer_tdata;
  logic reducer_tlast;
  logic [11:0] reducer_start;
  logic [11:0] reducer_end;
  logic [11:0] reducer_peak;
  logic [11:0] reducer_span;
  logic [57:0] reducer_noise;
  logic [61:0] reducer_threshold;
  logic [1:0]  reducer_pfa;
  logic        reducer_evaluate_center;
  logic        reducer_candidate_valid;
  logic [15:0] reducer_completed_frame_count;

  p0_candidate_reducer_top reducer_i (
    .aclk,
    .aresetn,
    .s_axis_tvalid,
    .s_axis_tready,
    .s_axis_tdata,
    .s_axis_tlast,
    .s_axis_tuser_index,
    .m_axis_tvalid(reducer_tvalid),
    .m_axis_tready(reducer_tready),
    .m_axis_tdata(reducer_tdata),
    .m_axis_tlast(reducer_tlast),
    .m_axis_tuser_start_shifted_bin(reducer_start),
    .m_axis_tuser_end_shifted_bin(reducer_end),
    .m_axis_tuser_peak_shifted_bin(reducer_peak),
    .m_axis_tuser_coarse_span_bins(reducer_span),
    .m_axis_tuser_noise(reducer_noise),
    .m_axis_tuser_threshold(reducer_threshold),
    .m_axis_tuser_pfa_select(reducer_pfa),
    .m_axis_tuser_evaluate_center(reducer_evaluate_center),
    .m_axis_tuser_candidate_valid(reducer_candidate_valid),
    .completed_frame_count(reducer_completed_frame_count),
    .status_sticky(status_reducer_sticky)
  );

  axis_candidate_packetizer packetizer_i (
    .aclk,
    .aresetn,
    .s_axis_tvalid(reducer_tvalid),
    .s_axis_tready(reducer_tready),
    .s_axis_tdata(reducer_tdata),
    .s_axis_tlast(reducer_tlast),
    .s_axis_tuser_start_shifted_bin(reducer_start),
    .s_axis_tuser_end_shifted_bin(reducer_end),
    .s_axis_tuser_peak_shifted_bin(reducer_peak),
    .s_axis_tuser_coarse_span_bins(reducer_span),
    .s_axis_tuser_noise(reducer_noise),
    .s_axis_tuser_threshold(reducer_threshold),
    .s_axis_tuser_pfa_select(reducer_pfa),
    .s_axis_tuser_evaluate_center(reducer_evaluate_center),
    .s_axis_tuser_candidate_valid(reducer_candidate_valid),
    .m_axis_tvalid,
    .m_axis_tready,
    .m_axis_tdata,
    .m_axis_tkeep,
    .m_axis_tlast,
    .completed_frame_count,
    .status_transport_error_sticky,
    .status_candidate_overflow_sticky
  );

  // The packetizer owns the downstream backpressure boundary.  The reducer's
  // frame counter is intentionally retained only as an internal cross-check;
  // the ABI frame ID is owned by the packetizer.
  logic reducer_counter_use;
  assign reducer_counter_use = ^reducer_completed_frame_count;
endmodule
