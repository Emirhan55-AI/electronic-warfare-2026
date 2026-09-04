`timescale 1ns/1ps

module p0_candidate_reducer_top (
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
  output logic        m_axis_tuser_weak_evidence,
  output logic        m_axis_tuser_single_frame_confident,
  output logic        m_axis_tuser_candidate_valid,
  output logic [15:0] completed_frame_count,
  output logic [8:0]  status_sticky
);
  logic shared_valid;
  logic os_input_ready;
  logic median_input_ready;
  logic recovery_input_ready;

  logic os_valid;
  logic os_ready;
  logic [57:0] os_power;
  logic os_last;
  logic [11:0] os_start;
  logic [11:0] os_end;
  logic [11:0] os_peak;
  logic [11:0] os_span;
  logic [57:0] os_noise;
  logic [61:0] os_threshold;
  logic [1:0] os_pfa;
  logic os_evaluate_center;
  logic os_weak_evidence;
  logic os_single_frame_confident;
  logic os_candidate_valid;
  logic [15:0] os_completed_frame_count;
  logic [1:0] os_status;

  logic median_valid;
  logic [58:0] region_median_twice [0:15];
  logic [15:0] median_completed_frame_count;
  logic median_frame_error;

  logic recovery_valid;
  logic recovery_ready;
  logic [57:0] recovery_power;
  logic recovery_last;
  logic [11:0] recovery_start;
  logic [11:0] recovery_end;
  logic [11:0] recovery_peak;
  logic [11:0] recovery_span;
  logic [57:0] recovery_noise;
  logic [61:0] recovery_threshold;
  logic [1:0] recovery_pfa;
  logic recovery_evaluate_center;
  logic recovery_candidate_valid;
  logic [15:0] recovery_completed_frame_count;
  logic recovery_frame_error;
  logic recovery_range_error;
  logic recovery_overflow;
  logic fusion_input_error;
  logic fusion_overflow;

  assign s_axis_tready = os_input_ready && median_input_ready && recovery_input_ready;
  assign shared_valid = s_axis_tvalid && s_axis_tready;

  p0_weak_nomination_top sparse_os_i (
    .aclk,
    .aresetn,
    .s_axis_tvalid(shared_valid),
    .s_axis_tready(os_input_ready),
    .s_axis_tdata,
    .s_axis_tlast,
    .s_axis_tuser_index,
    .m_axis_tvalid(os_valid),
    .m_axis_tready(os_ready),
    .m_axis_tdata(os_power),
    .m_axis_tlast(os_last),
    .m_axis_tuser_start_shifted_bin(os_start),
    .m_axis_tuser_end_shifted_bin(os_end),
    .m_axis_tuser_peak_shifted_bin(os_peak),
    .m_axis_tuser_coarse_span_bins(os_span),
    .m_axis_tuser_order_statistic(os_noise),
    .m_axis_tuser_threshold(os_threshold),
    .m_axis_tuser_pfa_select(os_pfa),
    .m_axis_tuser_evaluate_center(os_evaluate_center),
    .m_axis_tuser_weak_evidence(os_weak_evidence),
    .m_axis_tuser_single_frame_confident(os_single_frame_confident),
    .m_axis_tuser_candidate_valid(os_candidate_valid),
    .completed_frame_count(os_completed_frame_count),
    .status_sticky(os_status)
  );

  p0_parallel_region_median median_i (
    .aclk,
    .aresetn,
    .s_axis_tvalid(shared_valid),
    .s_axis_tready(median_input_ready),
    .s_axis_tdata,
    .s_axis_tlast,
    .s_axis_tuser_index,
    .result_valid(median_valid),
    .region_median_twice,
    .completed_frame_count(median_completed_frame_count),
    .status_frame_error_sticky(median_frame_error)
  );

  p0_wideband_recovery recovery_i (
    .aclk,
    .aresetn,
    .s_axis_tvalid(shared_valid),
    .s_axis_tready(recovery_input_ready),
    .s_axis_tdata,
    .s_axis_tlast,
    .s_axis_tuser_index,
    .median_valid,
    .region_median_twice,
    .m_axis_tvalid(recovery_valid),
    .m_axis_tready(recovery_ready),
    .m_axis_tdata(recovery_power),
    .m_axis_tlast(recovery_last),
    .m_axis_tuser_start_shifted_bin(recovery_start),
    .m_axis_tuser_end_shifted_bin(recovery_end),
    .m_axis_tuser_peak_shifted_bin(recovery_peak),
    .m_axis_tuser_coarse_span_bins(recovery_span),
    .m_axis_tuser_noise(recovery_noise),
    .m_axis_tuser_threshold(recovery_threshold),
    .m_axis_tuser_pfa_select(recovery_pfa),
    .m_axis_tuser_evaluate_center(recovery_evaluate_center),
    .m_axis_tuser_candidate_valid(recovery_candidate_valid),
    .completed_frame_count(recovery_completed_frame_count),
    .status_frame_error_sticky(recovery_frame_error),
    .status_input_range_error_sticky(recovery_range_error),
    .status_candidate_overflow_sticky(recovery_overflow)
  );

  p0_candidate_fusion fusion_i (
    .aclk,
    .aresetn,
    .s_os_tvalid(os_valid),
    .s_os_tready(os_ready),
    .s_os_tdata(os_power),
    .s_os_tlast(os_last),
    .s_os_start(os_start),
    .s_os_end(os_end),
    .s_os_peak(os_peak),
    .s_os_noise(os_noise),
    .s_os_threshold(os_threshold),
    .s_os_pfa_select(os_pfa),
    .s_os_evaluate_center(os_evaluate_center),
    .s_os_weak_evidence(os_weak_evidence),
    .s_os_single_frame_confident(os_single_frame_confident),
    .s_os_candidate_valid(os_candidate_valid),
    .s_recovery_tvalid(recovery_valid),
    .s_recovery_tready(recovery_ready),
    .s_recovery_tdata(recovery_power),
    .s_recovery_tlast(recovery_last),
    .s_recovery_start(recovery_start),
    .s_recovery_end(recovery_end),
    .s_recovery_peak(recovery_peak),
    .s_recovery_noise(recovery_noise),
    .s_recovery_threshold(recovery_threshold),
    .s_recovery_pfa_select(recovery_pfa),
    .s_recovery_evaluate_center(recovery_evaluate_center),
    .s_recovery_candidate_valid(recovery_candidate_valid),
    .s_recovery_frame_invalid(
      recovery_frame_error || recovery_range_error || recovery_overflow
    ),
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
    .m_axis_tuser_weak_evidence,
    .m_axis_tuser_single_frame_confident,
    .m_axis_tuser_candidate_valid,
    .completed_frame_count,
    .status_input_error_sticky(fusion_input_error),
    .status_candidate_overflow_sticky(fusion_overflow)
  );

  assign status_sticky = {
    1'b0,
    fusion_overflow,
    fusion_input_error,
    recovery_overflow,
    recovery_range_error,
    recovery_frame_error,
    median_frame_error,
    os_status
  };

  logic unused_counts_and_spans;
  assign unused_counts_and_spans = ^{
    os_completed_frame_count,
    median_completed_frame_count,
    recovery_completed_frame_count,
    os_span,
    recovery_span
  };
endmodule
