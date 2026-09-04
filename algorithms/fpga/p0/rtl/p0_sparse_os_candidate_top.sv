`timescale 1ns/1ps

module p0_sparse_os_candidate_top (
  input  logic        aclk,
  input  logic        aresetn,
  input  logic        s_axis_tvalid,
  output logic        s_axis_tready,
  input  logic [57:0] s_axis_tdata,
  input  logic        s_axis_tlast,
  input  logic [11:0] s_axis_tuser_index,
  output logic        m_axis_tvalid,
  input  logic        m_axis_tready,
  output logic [57:0] m_axis_tdata,
  output logic        m_axis_tlast,
  output logic [11:0] m_axis_tuser_start_shifted_bin,
  output logic [11:0] m_axis_tuser_end_shifted_bin,
  output logic [11:0] m_axis_tuser_peak_shifted_bin,
  output logic [11:0] m_axis_tuser_coarse_span_bins,
  output logic [57:0] m_axis_tuser_noise,
  output logic [61:0] m_axis_tuser_threshold,
  output logic [1:0]  m_axis_tuser_pfa_select,
  output logic        m_axis_tuser_evaluate_center,
  output logic        m_axis_tuser_candidate_valid,
  output logic [15:0] completed_frame_count,
  output logic [2:0]  status_sticky
);
  logic decision_valid;
  logic decision_ready;
  logic [57:0] decision_power;
  logic decision_last;
  logic [11:0] decision_shifted_index;
  logic [57:0] decision_order_statistic;
  logic decision_detected;
  logic decision_weak_nominated;
  logic [15:0] decision_completed_frame_count;
  logic decision_frame_error;
  logic grouping_frame_error;
  logic grouping_candidate_overflow;

  p0_os_cfar_decision_engine decision_engine_i (
    .aclk,
    .aresetn,
    .s_axis_tvalid,
    .s_axis_tready,
    .s_axis_tdata,
    .s_axis_tlast,
    .s_axis_tuser_index,
    .m_axis_tvalid(decision_valid),
    .m_axis_tready(decision_ready),
    .m_axis_tdata(decision_power),
    .m_axis_tlast(decision_last),
    .m_axis_tuser_shifted_index(decision_shifted_index),
    .m_axis_tuser_order_statistic(decision_order_statistic),
    .m_axis_tuser_detected(decision_detected),
    .m_axis_tuser_weak_nominated(decision_weak_nominated),
    .completed_frame_count(decision_completed_frame_count),
    .status_frame_error_sticky(decision_frame_error)
  );

  p0_os_candidate_grouping candidate_grouping_i (
    .aclk,
    .aresetn,
    .s_axis_tvalid(decision_valid),
    .s_axis_tready(decision_ready),
    .s_axis_tdata(decision_power),
    .s_axis_tlast(decision_last),
    .s_axis_tuser_shifted_index(decision_shifted_index),
    .s_axis_tuser_order_statistic(decision_order_statistic),
    .s_axis_tuser_detected(decision_detected),
    .m_axis_tvalid,
    .m_axis_tready,
    .m_axis_tdata,
    .m_axis_tlast,
    .m_axis_tuser_start_shifted_bin,
    .m_axis_tuser_end_shifted_bin,
    .m_axis_tuser_peak_shifted_bin,
    .m_axis_tuser_coarse_span_bins,
    .m_axis_tuser_noise,
    .m_axis_tuser_threshold,
    .m_axis_tuser_pfa_select,
    .m_axis_tuser_evaluate_center,
    .m_axis_tuser_candidate_valid,
    .completed_frame_count,
    .status_frame_error_sticky(grouping_frame_error),
    .status_candidate_overflow_sticky(grouping_candidate_overflow)
  );

  assign status_sticky = {
    grouping_candidate_overflow,
    grouping_frame_error,
    decision_frame_error
  };

  logic unused_decision_count;
  assign unused_decision_count = ^decision_completed_frame_count ^ decision_weak_nominated;
endmodule
