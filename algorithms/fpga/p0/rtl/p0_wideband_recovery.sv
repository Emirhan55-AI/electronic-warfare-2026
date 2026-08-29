`timescale 1ns/1ps

module p0_wideband_recovery (
  input  logic        aclk,
  input  logic        aresetn,

  input  logic        s_axis_tvalid,
  output logic        s_axis_tready,
  input  logic [57:0] s_axis_tdata,
  input  logic        s_axis_tlast,
  input  logic [11:0] s_axis_tuser_index,

  input  logic        median_valid,
  input  logic [58:0] region_median_twice [0:15],

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
  output logic        status_frame_error_sticky,
  output logic        status_input_range_error_sticky,
  output logic        status_candidate_overflow_sticky
);
  import p0_candidate_reducer_pkg::*;
  import p0_wideband_recovery_pkg::*;

  typedef enum logic [4:0] {
    ST_COLLECT,
    ST_RESYNC,
    ST_WAIT_MEDIAN,
    ST_COEFFICIENT_INTEGRATED,
    ST_COEFFICIENT_NOISE,
    ST_COEFFICIENT_THRESHOLD,
    ST_WINDOW_INITIALIZE,
    ST_WINDOW_ACCUMULATE,
    ST_EVALUATE_CENTER,
    ST_UPDATE_CAPTURE_OUTGOING,
    ST_UPDATE_APPLY,
    ST_FINALIZE_GROUP,
    ST_PREPARE_RECOVERY,
    ST_PEAK_COMPARE,
    ST_PRESENT_OUTPUT
  } state_t;

  state_t state;
  (* ram_style = "block" *) logic [POWER_WIDTH-1:0] frame_memory [0:FRAME_LENGTH-1];
  logic [POWER_WIDTH-1:0] frame_read_data;
  logic [POWER_WIDTH-1:0] outgoing_power;
  logic [11:0] expected_input_index;
  logic frame_range_error;

  logic [MEDIAN_TWICE_WIDTH-1:0] frame_median_twice [0:REGION_COUNT-1];
  logic [112:0] integrated_threshold_product [0:REGION_COUNT-1];
  logic [57:0] frame_region_noise [0:REGION_COUNT-1];
  logic [61:0] frame_region_threshold [0:REGION_COUNT-1];
  logic [REGION_INDEX_WIDTH-1:0] coefficient_region;
  logic [53:0] selected_coefficient;
  logic [112:0] coefficient_product;
  logic [112:0] rounded_coefficient_product;

  logic [62:0] window_sum;
  logic [11:0] window_read_index;
  logic [11:0] current_center;
  logic integrated_detected;
  logic [112:0] scaled_window_sum;

  logic group_active;
  logic [11:0] group_start;
  logic [11:0] group_end;
  logic group_qualified;
  logic [11:0] group_support_start;
  logic [11:0] group_support_end;

  logic [11:0] recovery_start [0:MAXIMUM_RECOVERY_CANDIDATES-1];
  logic [11:0] recovery_end [0:MAXIMUM_RECOVERY_CANDIDATES-1];
  logic [6:0] recovery_count;
  logic [6:0] recovery_index;
  logic frame_overflow;

  logic [11:0] peak_scan_index;
  logic [11:0] peak_index;
  logic [57:0] peak_power;
  logic current_peak_better;
  logic [11:0] final_peak_index;
  logic [57:0] final_peak_power;

  logic output_candidate_valid;
  logic output_last;
  logic [11:0] output_start;
  logic [11:0] output_end;
  logic [11:0] output_peak;
  logic [57:0] output_peak_power;
  logic [57:0] output_noise;
  logic [61:0] output_threshold;

  integer region;

  assign s_axis_tready = state == ST_COLLECT || state == ST_RESYNC;
  assign m_axis_tvalid = state == ST_PRESENT_OUTPUT;
  assign m_axis_tdata = output_candidate_valid ? output_peak_power : 58'd0;
  assign m_axis_tlast = output_last;
  assign m_axis_tuser_start_shifted_bin = output_candidate_valid ? output_start : 12'd0;
  assign m_axis_tuser_end_shifted_bin = output_candidate_valid ? output_end : 12'd0;
  assign m_axis_tuser_peak_shifted_bin = output_candidate_valid ? output_peak : 12'd0;
  assign m_axis_tuser_coarse_span_bins =
      output_candidate_valid ? (output_end - output_start + 1'b1) : 12'd0;
  assign m_axis_tuser_noise = output_candidate_valid ? output_noise : 58'd0;
  assign m_axis_tuser_threshold = output_candidate_valid ? output_threshold : 62'd0;
  assign m_axis_tuser_pfa_select = output_candidate_valid ? 2'd1 : 2'd0;
  assign m_axis_tuser_evaluate_center = 1'b0;
  assign m_axis_tuser_candidate_valid = output_candidate_valid;

  always_comb begin
    case (state)
      ST_COEFFICIENT_NOISE: selected_coefficient = {6'd0, NOISE_Q48};
      ST_COEFFICIENT_THRESHOLD: selected_coefficient = {5'd0, REGIONAL_THRESHOLD_Q48};
      default: selected_coefficient = INTEGRATED_THRESHOLD_Q48;
    endcase
    coefficient_product = frame_median_twice[coefficient_region] * selected_coefficient;
    rounded_coefficient_product = coefficient_product + (113'd1 << 47);
  end

  assign scaled_window_sum = {2'd0, window_sum, 48'd0};
  assign integrated_detected =
      scaled_window_sum > integrated_threshold_product[current_center[11:8]];
  assign group_qualified = group_active &&
      ({1'b0, group_end} >= ({1'b0, group_start} + 13'd71));
  assign group_support_start = group_start + INTEGRATION_LEFT;
  assign group_support_end = group_end - INTEGRATION_RIGHT;
  assign current_peak_better = frame_read_data > peak_power;
  assign final_peak_index = current_peak_better ? peak_scan_index : peak_index;
  assign final_peak_power = current_peak_better ? frame_read_data : peak_power;

  always_ff @(posedge aclk) begin
    if (!aresetn) begin
      state <= ST_COLLECT;
      expected_input_index <= 12'd0;
      frame_read_data <= 58'd0;
      outgoing_power <= 58'd0;
      frame_range_error <= 1'b0;
      coefficient_region <= 4'd0;
      window_sum <= 63'd0;
      window_read_index <= 12'd0;
      current_center <= 12'd20;
      group_active <= 1'b0;
      group_start <= 12'd0;
      group_end <= 12'd0;
      recovery_count <= 7'd0;
      recovery_index <= 7'd0;
      frame_overflow <= 1'b0;
      peak_scan_index <= 12'd0;
      peak_index <= 12'd0;
      peak_power <= 58'd0;
      output_candidate_valid <= 1'b0;
      output_last <= 1'b0;
      output_start <= 12'd0;
      output_end <= 12'd0;
      output_peak <= 12'd0;
      output_peak_power <= 58'd0;
      output_noise <= 58'd0;
      output_threshold <= 62'd0;
      completed_frame_count <= 16'd0;
      status_frame_error_sticky <= 1'b0;
      status_input_range_error_sticky <= 1'b0;
      status_candidate_overflow_sticky <= 1'b0;
      for (region = 0; region < REGION_COUNT; region = region + 1) begin
        frame_median_twice[region] <= 59'd0;
        integrated_threshold_product[region] <= 113'd0;
        frame_region_noise[region] <= 58'd0;
        frame_region_threshold[region] <= 62'd0;
      end
    end else begin
      case (state)
        ST_COLLECT: begin
          if (s_axis_tvalid && s_axis_tready) begin
            if (s_axis_tuser_index != expected_input_index ||
                s_axis_tlast != (expected_input_index == FRAME_LENGTH - 1)) begin
              status_frame_error_sticky <= 1'b1;
              expected_input_index <= 12'd0;
              frame_range_error <= 1'b0;
              if (!s_axis_tlast && expected_input_index != FRAME_LENGTH - 1)
                state <= ST_RESYNC;
            end else begin
              frame_memory[expected_input_index] <= s_axis_tdata;
              if (expected_input_index == 12'd0)
                frame_range_error <= s_axis_tdata > POWER_MAX_REACHABLE;
              else if (s_axis_tdata > POWER_MAX_REACHABLE)
                frame_range_error <= 1'b1;
              if (expected_input_index == FRAME_LENGTH - 1) begin
                expected_input_index <= 12'd0;
                state <= ST_WAIT_MEDIAN;
              end else begin
                expected_input_index <= expected_input_index + 1'b1;
              end
            end
          end
        end

        ST_RESYNC: begin
          if (s_axis_tvalid && s_axis_tready && s_axis_tlast) begin
            expected_input_index <= 12'd0;
            frame_range_error <= 1'b0;
            state <= ST_COLLECT;
          end
        end

        ST_WAIT_MEDIAN: begin
          if (median_valid) begin
            for (region = 0; region < REGION_COUNT; region = region + 1)
              frame_median_twice[region] <= region_median_twice[region];
            recovery_count <= 7'd0;
            recovery_index <= 7'd0;
            frame_overflow <= 1'b0;
            group_active <= 1'b0;
            output_candidate_valid <= 1'b0;
            coefficient_region <= 4'd0;
            if (frame_range_error) begin
              status_input_range_error_sticky <= 1'b1;
              output_last <= 1'b1;
              state <= ST_PRESENT_OUTPUT;
            end else begin
              state <= ST_COEFFICIENT_INTEGRATED;
            end
          end
        end

        ST_COEFFICIENT_INTEGRATED: begin
          integrated_threshold_product[coefficient_region] <= coefficient_product;
          state <= ST_COEFFICIENT_NOISE;
        end

        ST_COEFFICIENT_NOISE: begin
          frame_region_noise[coefficient_region] <= rounded_coefficient_product[105:48];
          state <= ST_COEFFICIENT_THRESHOLD;
        end

        ST_COEFFICIENT_THRESHOLD: begin
          frame_region_threshold[coefficient_region] <= rounded_coefficient_product[109:48];
          if (coefficient_region == REGION_COUNT - 1) begin
            window_sum <= 63'd0;
            window_read_index <= 12'd5;
            current_center <= 12'd20;
            state <= ST_WINDOW_INITIALIZE;
          end else begin
            coefficient_region <= coefficient_region + 1'b1;
            state <= ST_COEFFICIENT_INTEGRATED;
          end
        end

        ST_WINDOW_INITIALIZE: begin
          frame_read_data <= frame_memory[window_read_index ^ 12'h800];
          state <= ST_WINDOW_ACCUMULATE;
        end

        ST_WINDOW_ACCUMULATE: begin
          window_sum <= window_sum + frame_read_data;
          if (window_read_index == 12'd36) begin
            state <= ST_EVALUATE_CENTER;
          end else begin
            window_read_index <= window_read_index + 1'b1;
            frame_read_data <= frame_memory[(window_read_index + 1'b1) ^ 12'h800];
          end
        end

        ST_EVALUATE_CENTER: begin
          if (integrated_detected) begin
            if (!group_active) begin
              group_active <= 1'b1;
              group_start <= current_center;
              group_end <= current_center;
            end else if ((current_center - group_end) <= MAXIMUM_GAP_BINS + 1) begin
              group_end <= current_center;
            end else begin
              if (group_qualified) begin
                if (recovery_count < MAXIMUM_RECOVERY_CANDIDATES) begin
                  recovery_start[recovery_count] <= group_support_start;
                  recovery_end[recovery_count] <= group_support_end;
                  recovery_count <= recovery_count + 1'b1;
                end else begin
                  frame_overflow <= 1'b1;
                  status_candidate_overflow_sticky <= 1'b1;
                end
              end
              group_start <= current_center;
              group_end <= current_center;
            end
          end else if (group_active && (current_center - group_end) > MAXIMUM_GAP_BINS + 1) begin
            if (group_qualified) begin
              if (recovery_count < MAXIMUM_RECOVERY_CANDIDATES) begin
                recovery_start[recovery_count] <= group_support_start;
                recovery_end[recovery_count] <= group_support_end;
                recovery_count <= recovery_count + 1'b1;
              end else begin
                frame_overflow <= 1'b1;
                status_candidate_overflow_sticky <= 1'b1;
              end
            end
            group_active <= 1'b0;
          end

          if (current_center == 12'd4075) begin
            state <= ST_FINALIZE_GROUP;
          end else begin
            frame_read_data <= frame_memory[(current_center - INTEGRATION_LEFT) ^ 12'h800];
            state <= ST_UPDATE_CAPTURE_OUTGOING;
          end
        end

        ST_UPDATE_CAPTURE_OUTGOING: begin
          outgoing_power <= frame_read_data;
          frame_read_data <=
              frame_memory[(current_center + INTEGRATION_RIGHT + 1'b1) ^ 12'h800];
          state <= ST_UPDATE_APPLY;
        end

        ST_UPDATE_APPLY: begin
          window_sum <= window_sum - outgoing_power + frame_read_data;
          current_center <= current_center + 1'b1;
          state <= ST_EVALUATE_CENTER;
        end

        ST_FINALIZE_GROUP: begin
          if (group_qualified) begin
            if (recovery_count < MAXIMUM_RECOVERY_CANDIDATES) begin
              recovery_start[recovery_count] <= group_support_start;
              recovery_end[recovery_count] <= group_support_end;
              recovery_count <= recovery_count + 1'b1;
            end else begin
              frame_overflow <= 1'b1;
              status_candidate_overflow_sticky <= 1'b1;
            end
          end
          group_active <= 1'b0;
          state <= ST_PREPARE_RECOVERY;
        end

        ST_PREPARE_RECOVERY: begin
          if (frame_overflow || recovery_count == 0) begin
            output_candidate_valid <= 1'b0;
            output_last <= 1'b1;
            state <= ST_PRESENT_OUTPUT;
          end else begin
            recovery_index <= 7'd0;
            peak_scan_index <= recovery_start[0];
            peak_index <= recovery_start[0];
            peak_power <= 58'd0;
            frame_read_data <= frame_memory[recovery_start[0] ^ 12'h800];
            state <= ST_PEAK_COMPARE;
          end
        end

        ST_PEAK_COMPARE: begin
          if (peak_scan_index == recovery_end[recovery_index]) begin
            output_candidate_valid <= 1'b1;
            output_last <= recovery_index + 1'b1 == recovery_count;
            output_start <= recovery_start[recovery_index];
            output_end <= recovery_end[recovery_index];
            output_peak <= final_peak_index;
            output_peak_power <= final_peak_power;
            output_noise <= frame_region_noise[final_peak_index[11:8]];
            output_threshold <= frame_region_threshold[final_peak_index[11:8]];
            state <= ST_PRESENT_OUTPUT;
          end else begin
            if (current_peak_better) begin
              peak_index <= peak_scan_index;
              peak_power <= frame_read_data;
            end
            peak_scan_index <= peak_scan_index + 1'b1;
            frame_read_data <= frame_memory[(peak_scan_index + 1'b1) ^ 12'h800];
          end
        end

        ST_PRESENT_OUTPUT: begin
          if (m_axis_tvalid && m_axis_tready) begin
            if (output_last) begin
              completed_frame_count <= completed_frame_count + 1'b1;
              output_candidate_valid <= 1'b0;
              frame_range_error <= 1'b0;
              state <= ST_COLLECT;
            end else begin
              recovery_index <= recovery_index + 1'b1;
              peak_scan_index <= recovery_start[recovery_index + 1'b1];
              peak_index <= recovery_start[recovery_index + 1'b1];
              peak_power <= 58'd0;
              frame_read_data <=
                  frame_memory[recovery_start[recovery_index + 1'b1] ^ 12'h800];
              output_candidate_valid <= 1'b0;
              state <= ST_PEAK_COMPARE;
            end
          end
        end

        default: state <= ST_COLLECT;
      endcase
    end
  end
endmodule
