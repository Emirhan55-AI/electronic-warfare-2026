`timescale 1ns/1ps

// Sparse grouping for the ADR-0040 weak OS-CFAR nomination stream. Each record
// carries both the weak-evidence class and whether any cell also crossed the
// strict single-frame threshold; PS routes the two classes independently.
module p0_weak_candidate_grouping (
  input  logic        aclk,
  input  logic        aresetn,
  input  logic        s_axis_tvalid,
  output logic        s_axis_tready,
  input  logic [57:0] s_axis_tdata,
  input  logic        s_axis_tlast,
  input  logic [11:0] s_axis_tuser_shifted_index,
  input  logic [57:0] s_axis_tuser_order_statistic,
  input  logic        s_axis_tuser_detected,
  input  logic        s_axis_tuser_weak_nominated,
  output logic        m_axis_tvalid,
  input  logic        m_axis_tready,
  output logic [57:0] m_axis_tdata,
  output logic        m_axis_tlast,
  output logic [11:0] m_axis_tuser_start_shifted_bin,
  output logic [11:0] m_axis_tuser_end_shifted_bin,
  output logic [11:0] m_axis_tuser_peak_shifted_bin,
  output logic [11:0] m_axis_tuser_coarse_span_bins,
  output logic [57:0] m_axis_tuser_order_statistic,
  output logic [61:0] m_axis_tuser_threshold,
  output logic [1:0]  m_axis_tuser_pfa_select,
  output logic        m_axis_tuser_evaluate_center,
  output logic        m_axis_tuser_weak_evidence,
  output logic        m_axis_tuser_single_frame_confident,
  output logic        m_axis_tuser_candidate_valid,
  output logic [15:0] completed_frame_count,
  output logic        status_frame_error_sticky,
  output logic        status_candidate_overflow_sticky
);
  import p0_os_cfar_pkg::*;
  import p0_sparse_os_candidate_pkg::*;

  localparam int MAXIMUM_WEAK_CANDIDATES = 1352;

  typedef enum logic [2:0] {
    ST_COLLECT,
    ST_RESYNC,
    ST_FINALIZE,
    ST_INITIALIZE_OUTPUT,
    ST_LOAD_OUTPUT,
    ST_PRESENT_OUTPUT
  } state_t;

  state_t state;
  logic [11:0] expected_shifted_index;
  logic pending_valid;
  logic [11:0] pending_start;
  logic [11:0] pending_end;
  logic [11:0] pending_peak;
  logic [57:0] pending_peak_power;
  logic [57:0] pending_peak_noise;
  logic pending_strong;
  logic [10:0] candidate_count;
  logic frame_overflow;
  logic [10:0] output_index;
  logic [152:0] output_record;
  logic output_candidate_valid;
  logic output_last;
  (* ram_style = "block" *) logic [152:0] candidate_memory [0:MAXIMUM_WEAK_CANDIDATES-1];

  logic separated_detection;
  logic closed_by_gap;
  logic input_contract_error;
  logic write_pending;

  logic [109:0] threshold_product;
  logic [109:0] rounded_threshold_product;

  function automatic logic [152:0] pack_candidate(
    input logic [11:0] start_index,
    input logic [11:0] end_index,
    input logic [11:0] peak_index,
    input logic [57:0] peak_power,
    input logic [57:0] peak_noise,
    input logic strong_flag
  );
    pack_candidate = {strong_flag, peak_noise, peak_power, peak_index, end_index, start_index};
  endfunction

  assign s_axis_tready = state == ST_COLLECT || state == ST_RESYNC;
  assign m_axis_tvalid = state == ST_PRESENT_OUTPUT;
  assign separated_detection = s_axis_tuser_weak_nominated && pending_valid &&
      ((s_axis_tuser_shifted_index - pending_end) > 12'd2);
  assign closed_by_gap = !s_axis_tuser_weak_nominated && pending_valid &&
      ((s_axis_tuser_shifted_index - pending_end) > 12'd2);
  assign input_contract_error =
      s_axis_tuser_shifted_index != expected_shifted_index ||
      (s_axis_tuser_detected && !s_axis_tuser_weak_nominated) ||
      s_axis_tlast != (expected_shifted_index == FRAME_LENGTH - RADIUS - 1);
  assign write_pending =
      (state == ST_COLLECT && s_axis_tvalid && s_axis_tready &&
       !input_contract_error && (separated_detection || closed_by_gap)) ||
      (state == ST_FINALIZE && pending_valid);

  assign m_axis_tdata = output_candidate_valid ? output_record[93:36] : 58'd0;
  assign m_axis_tlast = output_last;
  assign m_axis_tuser_start_shifted_bin =
      output_candidate_valid ? output_record[11:0] : 12'd0;
  assign m_axis_tuser_end_shifted_bin =
      output_candidate_valid ? output_record[23:12] : 12'd0;
  assign m_axis_tuser_peak_shifted_bin =
      output_candidate_valid ? output_record[35:24] : 12'd0;
  assign m_axis_tuser_coarse_span_bins = output_candidate_valid ?
      output_record[23:12] - output_record[11:0] + 1'b1 : 12'd0;
  assign m_axis_tuser_order_statistic =
      output_candidate_valid ? output_record[151:94] : 58'd0;
  assign threshold_product = output_record[151:94] *
      (output_record[152] ? OS_THRESHOLD_Q48 : WEAK_THRESHOLD_Q48);
  assign rounded_threshold_product = threshold_product + (110'd1 << 47);
  assign m_axis_tuser_threshold = output_candidate_valid ?
      rounded_threshold_product[109:48] : 62'd0;
  assign m_axis_tuser_pfa_select = output_candidate_valid ? 2'd1 : 2'd0;
  assign m_axis_tuser_evaluate_center = 1'b0;
  assign m_axis_tuser_weak_evidence = output_candidate_valid;
  assign m_axis_tuser_single_frame_confident =
      output_candidate_valid && output_record[152];
  assign m_axis_tuser_candidate_valid = output_candidate_valid;

  always_ff @(posedge aclk) begin
    if (!aresetn) begin
      state <= ST_COLLECT;
      expected_shifted_index <= RADIUS;
      pending_valid <= 1'b0;
      pending_start <= 12'd0;
      pending_end <= 12'd0;
      pending_peak <= 12'd0;
      pending_peak_power <= 58'd0;
      pending_peak_noise <= 58'd0;
      pending_strong <= 1'b0;
      candidate_count <= 11'd0;
      frame_overflow <= 1'b0;
      output_index <= 11'd0;
      output_record <= 153'd0;
      output_candidate_valid <= 1'b0;
      output_last <= 1'b0;
      completed_frame_count <= 16'd0;
      status_frame_error_sticky <= 1'b0;
      status_candidate_overflow_sticky <= 1'b0;
    end else begin
      if (write_pending) begin
        if (candidate_count < MAXIMUM_WEAK_CANDIDATES) begin
          candidate_memory[candidate_count] <= pack_candidate(
              pending_start, pending_end, pending_peak,
              pending_peak_power, pending_peak_noise, pending_strong);
          candidate_count <= candidate_count + 1'b1;
        end else begin
          frame_overflow <= 1'b1;
          status_candidate_overflow_sticky <= 1'b1;
        end
      end
      case (state)
        ST_COLLECT: begin
          if (s_axis_tvalid && s_axis_tready) begin
            if (input_contract_error) begin
              status_frame_error_sticky <= 1'b1;
              expected_shifted_index <= RADIUS;
              pending_valid <= 1'b0;
              pending_strong <= 1'b0;
              candidate_count <= 11'd0;
              frame_overflow <= 1'b0;
              if (!s_axis_tlast && expected_shifted_index != FRAME_LENGTH - RADIUS - 1)
                state <= ST_RESYNC;
            end else begin
              if (s_axis_tuser_weak_nominated) begin
                if (!pending_valid || separated_detection) begin
                  pending_valid <= 1'b1;
                  pending_start <= s_axis_tuser_shifted_index;
                  pending_end <= s_axis_tuser_shifted_index;
                  pending_peak <= s_axis_tuser_shifted_index;
                  pending_peak_power <= s_axis_tdata;
                  pending_peak_noise <= s_axis_tuser_order_statistic;
                  pending_strong <= s_axis_tuser_detected;
                end else begin
                  pending_end <= s_axis_tuser_shifted_index;
                  if (s_axis_tdata > pending_peak_power) begin
                    pending_peak <= s_axis_tuser_shifted_index;
                    pending_peak_power <= s_axis_tdata;
                    pending_peak_noise <= s_axis_tuser_order_statistic;
                  end
                  pending_strong <= pending_strong || s_axis_tuser_detected;
                end
              end else if (closed_by_gap) begin
                pending_valid <= 1'b0;
                pending_strong <= 1'b0;
              end
              if (expected_shifted_index == FRAME_LENGTH - RADIUS - 1) begin
                expected_shifted_index <= RADIUS;
                state <= ST_FINALIZE;
              end else begin
                expected_shifted_index <= expected_shifted_index + 1'b1;
              end
            end
          end
        end
        ST_RESYNC: begin
          if (s_axis_tvalid && s_axis_tready && s_axis_tlast) begin
            expected_shifted_index <= RADIUS;
            pending_valid <= 1'b0;
            pending_strong <= 1'b0;
            candidate_count <= 11'd0;
            frame_overflow <= 1'b0;
            state <= ST_COLLECT;
          end
        end
        ST_FINALIZE: begin
          pending_valid <= 1'b0;
          pending_strong <= 1'b0;
          state <= ST_INITIALIZE_OUTPUT;
        end
        ST_INITIALIZE_OUTPUT: begin
          output_index <= 11'd0;
          if (frame_overflow || candidate_count == 0) begin
            output_record <= 153'd0;
            output_candidate_valid <= 1'b0;
            output_last <= 1'b1;
            state <= ST_PRESENT_OUTPUT;
          end else begin
            state <= ST_LOAD_OUTPUT;
          end
        end
        ST_LOAD_OUTPUT: begin
          output_record <= candidate_memory[output_index];
          output_candidate_valid <= 1'b1;
          output_last <= output_index + 1'b1 == candidate_count;
          state <= ST_PRESENT_OUTPUT;
        end
        ST_PRESENT_OUTPUT: begin
          if (m_axis_tvalid && m_axis_tready) begin
            if (output_last) begin
              completed_frame_count <= completed_frame_count + 1'b1;
              candidate_count <= 11'd0;
              frame_overflow <= 1'b0;
              output_candidate_valid <= 1'b0;
              state <= ST_COLLECT;
            end else begin
              output_index <= output_index + 1'b1;
              state <= ST_LOAD_OUTPUT;
            end
          end
        end
        default: state <= ST_COLLECT;
      endcase
    end
  end
endmodule
