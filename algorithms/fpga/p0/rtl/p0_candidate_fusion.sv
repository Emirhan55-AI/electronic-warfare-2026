`timescale 1ns/1ps

module p0_candidate_fusion (
  input  logic        aclk,
  input  logic        aresetn,

  input  logic        s_os_tvalid,
  output logic        s_os_tready,
  input  logic [57:0] s_os_tdata,
  input  logic        s_os_tlast,
  input  logic [11:0] s_os_start,
  input  logic [11:0] s_os_end,
  input  logic [11:0] s_os_peak,
  input  logic [57:0] s_os_noise,
  input  logic [61:0] s_os_threshold,
  input  logic [1:0]  s_os_pfa_select,
  input  logic        s_os_evaluate_center,
  input  logic        s_os_weak_evidence,
  input  logic        s_os_single_frame_confident,
  input  logic        s_os_candidate_valid,

  input  logic        s_recovery_tvalid,
  output logic        s_recovery_tready,
  input  logic [57:0] s_recovery_tdata,
  input  logic        s_recovery_tlast,
  input  logic [11:0] s_recovery_start,
  input  logic [11:0] s_recovery_end,
  input  logic [11:0] s_recovery_peak,
  input  logic [57:0] s_recovery_noise,
  input  logic [61:0] s_recovery_threshold,
  input  logic [1:0]  s_recovery_pfa_select,
  input  logic        s_recovery_evaluate_center,
  input  logic        s_recovery_candidate_valid,
  input  logic        s_recovery_frame_invalid,

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
  output logic        status_input_error_sticky,
  output logic        status_candidate_overflow_sticky
);
  import p0_sparse_os_candidate_pkg::*;
  import p0_wideband_recovery_pkg::*;

  typedef enum logic [3:0] {
    ST_COLLECT,
    ST_INITIALIZE_MERGE,
    ST_REQUEST_MERGE,
    ST_LOAD_MERGE,
    ST_DECIDE_MERGE,
    ST_INITIALIZE_OUTPUT,
    ST_REQUEST_OUTPUT,
    ST_LOAD_OUTPUT,
    ST_PRESENT_OUTPUT
  } state_t;

  state_t state;
  logic os_done;
  logic recovery_done;
  logic frame_invalid;
  logic [10:0] os_count;
  logic [6:0] recovery_count;
  logic [10:0] fused_count;
  logic [11:0] previous_os_start;
  logic [11:0] previous_recovery_start;
  logic os_seen;
  logic recovery_seen;

  logic os_write_enable;
  logic [10:0] os_write_address;
  logic [215:0] os_write_data;
  logic [10:0] os_read_address;
  logic [215:0] os_read_data;
  logic recovery_write_enable;
  logic [6:0] recovery_write_address;
  logic [215:0] recovery_write_data;
  logic [6:0] recovery_read_address;
  logic [215:0] recovery_read_data;
  logic fused_write_enable;
  logic [10:0] fused_write_address;
  logic [215:0] fused_write_data;
  logic [10:0] fused_read_address;
  logic [215:0] fused_read_data;

  logic [10:0] os_index;
  logic [6:0] recovery_index;
  logic [215:0] current_os;
  logic [215:0] current_recovery;
  logic [10:0] output_index;
  logic [215:0] output_record;
  logic output_candidate_valid;
  logic output_last;

  logic os_input_error;
  logic recovery_input_error;
  logic os_exhausted;
  logic recovery_exhausted;
  logic os_before_recovery;
  logic recovery_before_os;

  function automatic logic [215:0] pack_candidate(
    input logic [11:0] start_index,
    input logic [11:0] end_index,
    input logic [11:0] peak_index,
    input logic [57:0] peak_power,
    input logic [57:0] noise,
    input logic [61:0] threshold,
    input logic weak_evidence,
    input logic single_frame_confident
  );
    pack_candidate = {weak_evidence, single_frame_confident,
                      threshold, noise, peak_power, peak_index, end_index, start_index};
  endfunction

  p0_candidate_record_ram #(
    .DEPTH(MAXIMUM_OS_CANDIDATES), .ADDRESS_WIDTH(11), .DATA_WIDTH(216)
  ) os_ram_i (
    .aclk,
    .write_enable(os_write_enable),
    .write_address(os_write_address),
    .write_data(os_write_data),
    .read_address(os_read_address),
    .read_data(os_read_data)
  );
  p0_candidate_record_ram #(
    .DEPTH(MAXIMUM_RECOVERY_CANDIDATES),
    .ADDRESS_WIDTH(7),
    .DATA_WIDTH(216)
  ) recovery_ram_i (
    .aclk,
    .write_enable(recovery_write_enable),
    .write_address(recovery_write_address),
    .write_data(recovery_write_data),
    .read_address(recovery_read_address),
    .read_data(recovery_read_data)
  );
  p0_candidate_record_ram #(
    .DEPTH(MAXIMUM_OS_CANDIDATES), .ADDRESS_WIDTH(11), .DATA_WIDTH(216)
  ) fused_ram_i (
    .aclk,
    .write_enable(fused_write_enable),
    .write_address(fused_write_address),
    .write_data(fused_write_data),
    .read_address(fused_read_address),
    .read_data(fused_read_data)
  );

  assign s_os_tready = state == ST_COLLECT && !os_done;
  assign s_recovery_tready = state == ST_COLLECT && !recovery_done;
  assign m_axis_tvalid = state == ST_PRESENT_OUTPUT;
  assign os_input_error = s_os_tvalid && s_os_tready &&
      ((!s_os_candidate_valid && !s_os_tlast) ||
       (s_os_candidate_valid &&
        (s_os_start > s_os_end || s_os_peak < s_os_start || s_os_peak > s_os_end ||
         s_os_pfa_select != 2'd1 || s_os_evaluate_center ||
         (os_seen && s_os_start < previous_os_start))));
  assign recovery_input_error = s_recovery_tvalid && s_recovery_tready &&
      ((!s_recovery_candidate_valid && !s_recovery_tlast) ||
       (s_recovery_candidate_valid &&
        (s_recovery_start > s_recovery_end ||
         s_recovery_peak < s_recovery_start || s_recovery_peak > s_recovery_end ||
         s_recovery_pfa_select != 2'd1 || s_recovery_evaluate_center ||
         (recovery_seen && s_recovery_start < previous_recovery_start))));

  assign os_exhausted = os_index >= os_count;
  assign recovery_exhausted = recovery_index >= recovery_count;
  assign os_before_recovery = current_os[23:12] < current_recovery[11:0];
  assign recovery_before_os = current_recovery[23:12] < current_os[11:0];

  assign m_axis_tdata = output_candidate_valid ? output_record[93:36] : 58'd0;
  assign m_axis_tlast = output_last;
  assign m_axis_tuser_start_shifted_bin =
      output_candidate_valid ? output_record[11:0] : 12'd0;
  assign m_axis_tuser_end_shifted_bin =
      output_candidate_valid ? output_record[23:12] : 12'd0;
  assign m_axis_tuser_peak_shifted_bin =
      output_candidate_valid ? output_record[35:24] : 12'd0;
  assign m_axis_tuser_coarse_span_bins = output_candidate_valid ?
      (output_record[23:12] - output_record[11:0] + 1'b1) : 12'd0;
  assign m_axis_tuser_noise = output_candidate_valid ? output_record[151:94] : 58'd0;
  assign m_axis_tuser_threshold = output_candidate_valid ? output_record[213:152] : 62'd0;
  assign m_axis_tuser_pfa_select = output_candidate_valid ? 2'd1 : 2'd0;
  assign m_axis_tuser_evaluate_center = 1'b0;
  assign m_axis_tuser_weak_evidence = output_candidate_valid && output_record[215];
  assign m_axis_tuser_single_frame_confident =
      output_candidate_valid && output_record[214];
  assign m_axis_tuser_candidate_valid = output_candidate_valid;

  always_comb begin
    os_write_enable = s_os_tvalid && s_os_tready && s_os_candidate_valid &&
        !os_input_error && os_count < MAXIMUM_OS_CANDIDATES;
    os_write_address = os_count;
    os_write_data = pack_candidate(
      s_os_start, s_os_end, s_os_peak, s_os_tdata, s_os_noise, s_os_threshold,
      s_os_weak_evidence, s_os_single_frame_confident
    );
    recovery_write_enable =
        s_recovery_tvalid && s_recovery_tready && s_recovery_candidate_valid &&
        !recovery_input_error && recovery_count < MAXIMUM_RECOVERY_CANDIDATES;
    recovery_write_address = recovery_count;
    recovery_write_data = pack_candidate(
      s_recovery_start,
      s_recovery_end,
      s_recovery_peak,
      s_recovery_tdata,
      s_recovery_noise,
      s_recovery_threshold,
      1'b0,
      1'b0
    );
    os_read_address = os_index;
    recovery_read_address = recovery_index;
    fused_write_enable = 1'b0;
    fused_write_address = fused_count;
    fused_write_data = 216'd0;
    fused_read_address = output_index;
    if (state == ST_DECIDE_MERGE && !frame_invalid) begin
      if (os_exhausted && !recovery_exhausted) begin
        fused_write_enable = fused_count < MAXIMUM_OS_CANDIDATES;
        fused_write_data = current_recovery;
      end else if (!os_exhausted && recovery_exhausted) begin
        fused_write_enable = fused_count < MAXIMUM_OS_CANDIDATES;
        fused_write_data = current_os;
      end else if (!os_exhausted && !recovery_exhausted) begin
        if (os_before_recovery) begin
          fused_write_enable = fused_count < MAXIMUM_OS_CANDIDATES;
          fused_write_data = current_os;
        end else if (recovery_before_os) begin
          fused_write_enable = fused_count < MAXIMUM_OS_CANDIDATES;
          fused_write_data = current_recovery;
        end
      end
    end
  end

  always_ff @(posedge aclk) begin
    if (!aresetn) begin
      state <= ST_COLLECT;
      os_done <= 1'b0;
      recovery_done <= 1'b0;
      frame_invalid <= 1'b0;
      os_count <= 11'd0;
      recovery_count <= 7'd0;
      fused_count <= 11'd0;
      previous_os_start <= 12'd0;
      previous_recovery_start <= 12'd0;
      os_seen <= 1'b0;
      recovery_seen <= 1'b0;
      os_index <= 11'd0;
      recovery_index <= 7'd0;
      current_os <= 214'd0;
      current_recovery <= 214'd0;
      output_index <= 11'd0;
      output_record <= 216'd0;
      output_candidate_valid <= 1'b0;
      output_last <= 1'b0;
      completed_frame_count <= 16'd0;
      status_input_error_sticky <= 1'b0;
      status_candidate_overflow_sticky <= 1'b0;
    end else begin
      case (state)
        ST_COLLECT: begin
          if (s_os_tvalid && s_os_tready) begin
            if (os_input_error) begin
              frame_invalid <= 1'b1;
              status_input_error_sticky <= 1'b1;
            end else if (s_os_candidate_valid) begin
              if (os_count < MAXIMUM_OS_CANDIDATES) begin
                os_count <= os_count + 1'b1;
                previous_os_start <= s_os_start;
                os_seen <= 1'b1;
              end else begin
                frame_invalid <= 1'b1;
                status_candidate_overflow_sticky <= 1'b1;
              end
            end
            if (s_os_tlast)
              os_done <= 1'b1;
          end
          if (s_recovery_tvalid && s_recovery_tready) begin
            if (s_recovery_frame_invalid)
              frame_invalid <= 1'b1;
            if (recovery_input_error) begin
              frame_invalid <= 1'b1;
              status_input_error_sticky <= 1'b1;
            end else if (s_recovery_candidate_valid) begin
              if (recovery_count < MAXIMUM_RECOVERY_CANDIDATES) begin
                recovery_count <= recovery_count + 1'b1;
                previous_recovery_start <= s_recovery_start;
                recovery_seen <= 1'b1;
              end else begin
                frame_invalid <= 1'b1;
                status_candidate_overflow_sticky <= 1'b1;
              end
            end
            if (s_recovery_tlast)
              recovery_done <= 1'b1;
          end
          if ((os_done || (s_os_tvalid && s_os_tready && s_os_tlast)) &&
              (recovery_done ||
               (s_recovery_tvalid && s_recovery_tready && s_recovery_tlast)))
            state <= ST_INITIALIZE_MERGE;
        end

        ST_INITIALIZE_MERGE: begin
          os_index <= 11'd0;
          recovery_index <= 7'd0;
          fused_count <= 11'd0;
          if (frame_invalid || (os_count == 0 && recovery_count == 0))
            state <= ST_INITIALIZE_OUTPUT;
          else
            state <= ST_REQUEST_MERGE;
        end

        ST_REQUEST_MERGE: state <= ST_LOAD_MERGE;

        ST_LOAD_MERGE: begin
          current_os <= os_read_data;
          current_recovery <= recovery_read_data;
          state <= ST_DECIDE_MERGE;
        end

        ST_DECIDE_MERGE: begin
          if (os_exhausted && recovery_exhausted) begin
            state <= ST_INITIALIZE_OUTPUT;
          end else begin
            if (os_exhausted) begin
              recovery_index <= recovery_index + 1'b1;
              if (fused_count < MAXIMUM_OS_CANDIDATES)
                fused_count <= fused_count + 1'b1;
              else begin
                frame_invalid <= 1'b1;
                status_candidate_overflow_sticky <= 1'b1;
              end
            end else if (recovery_exhausted) begin
              os_index <= os_index + 1'b1;
              if (fused_count < MAXIMUM_OS_CANDIDATES)
                fused_count <= fused_count + 1'b1;
              else begin
                frame_invalid <= 1'b1;
                status_candidate_overflow_sticky <= 1'b1;
              end
            end else if (os_before_recovery) begin
              os_index <= os_index + 1'b1;
              if (fused_count < MAXIMUM_OS_CANDIDATES)
                fused_count <= fused_count + 1'b1;
              else begin
                frame_invalid <= 1'b1;
                status_candidate_overflow_sticky <= 1'b1;
              end
            end else if (recovery_before_os) begin
              recovery_index <= recovery_index + 1'b1;
              if (fused_count < MAXIMUM_OS_CANDIDATES)
                fused_count <= fused_count + 1'b1;
              else begin
                frame_invalid <= 1'b1;
                status_candidate_overflow_sticky <= 1'b1;
              end
            end else begin
              os_index <= os_index + 1'b1;
            end
            state <= ST_REQUEST_MERGE;
          end
        end

        ST_INITIALIZE_OUTPUT: begin
          output_index <= 11'd0;
          if (frame_invalid || fused_count == 0) begin
            output_record <= 216'd0;
            output_candidate_valid <= 1'b0;
            output_last <= 1'b1;
            state <= ST_PRESENT_OUTPUT;
          end else begin
            state <= ST_REQUEST_OUTPUT;
          end
        end

        ST_REQUEST_OUTPUT: state <= ST_LOAD_OUTPUT;

        ST_LOAD_OUTPUT: begin
          output_record <= fused_read_data;
          output_candidate_valid <= 1'b1;
          output_last <= output_index + 1'b1 == fused_count;
          state <= ST_PRESENT_OUTPUT;
        end

        ST_PRESENT_OUTPUT: begin
          if (m_axis_tvalid && m_axis_tready) begin
            if (output_last) begin
              completed_frame_count <= completed_frame_count + 1'b1;
              os_done <= 1'b0;
              recovery_done <= 1'b0;
              frame_invalid <= 1'b0;
              os_count <= 11'd0;
              recovery_count <= 7'd0;
              os_seen <= 1'b0;
              recovery_seen <= 1'b0;
              output_candidate_valid <= 1'b0;
              state <= ST_COLLECT;
            end else begin
              output_index <= output_index + 1'b1;
              state <= ST_REQUEST_OUTPUT;
            end
          end
        end

        default: state <= ST_COLLECT;
      endcase
    end
  end
endmodule
