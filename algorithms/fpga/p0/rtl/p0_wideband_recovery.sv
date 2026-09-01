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
    ST_REFERENCE_INITIALIZE,
    ST_REFERENCE_SCAN,
    ST_COEFFICIENT_INTEGRATED,
    ST_COEFFICIENT_NOISE,
    ST_COEFFICIENT_THRESHOLD,
    ST_COEFFICIENT_BROAD,
    ST_WINDOW_INITIALIZE,
    ST_WINDOW_ACCUMULATE,
    ST_EVALUATE_CENTER,
    ST_UPDATE_CAPTURE_OUTGOING,
    ST_UPDATE_APPLY,
    ST_FINALIZE_GROUP,
    ST_SUPPRESSION_INITIALIZE,
    ST_SUPPRESSION_SCAN,
    ST_APPEND_BROAD,
    ST_SORT_INITIALIZE,
    ST_SORT_SCAN,
    ST_PREPARE_RECOVERY,
    ST_PEAK_COMPARE,
    ST_PRESENT_OUTPUT
  } state_t;

  state_t state;
  logic [POWER_WIDTH-1:0] frame_memory_read_data;
  logic [11:0] frame_memory_read_address;
  logic frame_memory_write_enable;
  logic [POWER_WIDTH-1:0] outgoing_power;
  logic [11:0] expected_input_index;
  logic frame_range_error;

  logic [MEDIAN_TWICE_WIDTH-1:0] frame_median_twice [0:REGION_COUNT-1];
  logic [112:0] integrated_threshold_product [0:REGION_COUNT-1];
  logic [112:0] broad_integrated_threshold_product;
  logic [58:0] frame_reference_twice;
  logic [57:0] frame_region_noise [0:REGION_COUNT-1];
  logic [61:0] frame_region_threshold [0:REGION_COUNT-1];
  logic [REGION_INDEX_WIDTH-1:0] coefficient_region;
  logic [53:0] selected_coefficient;
  logic [58:0] coefficient_input;
  logic [112:0] coefficient_product;
  logic [112:0] rounded_coefficient_product;

  logic [62:0] window_sum;
  logic [11:0] window_read_index;
  logic [11:0] current_center;
  logic integrated_detected;
  logic regional_integrated_detected;
  logic broad_integrated_detected;
  logic [112:0] scaled_window_sum;
  logic scan_broad;

  logic [15:0] reference_selected_mask;
  logic [2:0] reference_selection_rank;
  logic [4:0] reference_scan_region;
  logic [3:0] reference_min_index;
  logic [58:0] reference_min_value;
  logic reference_current_better;
  logic [3:0] reference_selected_index;
  logic [58:0] reference_selected_value;

  logic group_active;
  logic [11:0] group_start;
  logic [11:0] group_end;
  logic group_qualified;
  logic broad_group_qualified;
  logic [11:0] group_support_start;
  logic [11:0] group_support_end;
  logic [58:0] broad_inside_median_twice;
  logic [58:0] broad_flank_median_twice;
  logic [3:0] broad_flank_region_index;
  logic [61:0] broad_inside_times_two;
  logic [61:0] broad_flank_times_five;
  logic broad_group_active;
  logic [11:0] broad_group_start;
  logic [11:0] broad_group_end;
  logic [11:0] broad_group_support_start;
  logic [11:0] broad_group_support_end;
  logic [58:0] broad_inside_max_tree [0:30];
  logic [58:0] broad_inside_stage_two [0:3];
  logic [58:0] broad_inside_stage_three_left;
  logic [58:0] broad_inside_stage_three_right;
  logic [58:0] broad_inside_maximum_next;
  logic [11:0] broad_recovery_start [0:MAXIMUM_BROAD_RECOVERY_CANDIDATES-1];
  logic [11:0] broad_recovery_end [0:MAXIMUM_BROAD_RECOVERY_CANDIDATES-1];
  logic [3:0] broad_recovery_noise_region [0:MAXIMUM_BROAD_RECOVERY_CANDIDATES-1];
  logic [4:0] broad_recovery_count;
  logic [4:0] append_broad_index;
  logic [6:0] sort_pass;
  logic [6:0] sort_index;
  logic sort_swapped;

  logic [11:0] recovery_start [0:MAXIMUM_RECOVERY_CANDIDATES-1];
  logic [11:0] recovery_end [0:MAXIMUM_RECOVERY_CANDIDATES-1];
  logic recovery_is_broad [0:MAXIMUM_RECOVERY_CANDIDATES-1];
  logic recovery_valid [0:MAXIMUM_RECOVERY_CANDIDATES-1];
  logic [3:0] recovery_noise_region [0:MAXIMUM_RECOVERY_CANDIDATES-1];
  logic [6:0] recovery_count;
  logic [6:0] recovery_index;
  logic [6:0] suppression_candidate_index;
  logic [6:0] suppression_broad_index;
  logic frame_overflow;
  logic later_recovery_valid;

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
  integer later_index;
  integer recovery_slot;
  integer broad_slot;

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

  assign frame_memory_write_enable =
      s_axis_tvalid && s_axis_tready &&
      (s_axis_tuser_index == expected_input_index) &&
      (s_axis_tlast == (expected_input_index == FRAME_LENGTH - 1));

  p0_region_bank #(
    .DATA_WIDTH(POWER_WIDTH),
    .ADDRESS_WIDTH(12),
    .DEPTH(FRAME_LENGTH)
  ) frame_memory_i (
    .aclk,
    .write_enable(frame_memory_write_enable),
    .write_address(expected_input_index),
    .write_data(s_axis_tdata),
    .read_address(frame_memory_read_address),
    .read_data(frame_memory_read_data)
  );

  always_comb begin
    frame_memory_read_address = 12'd0;
    case (state)
      ST_WINDOW_INITIALIZE:
        frame_memory_read_address = window_read_index ^ 12'h800;
      ST_WINDOW_ACCUMULATE:
        if (window_read_index != 12'd36)
          frame_memory_read_address = (window_read_index + 1'b1) ^ 12'h800;
      ST_EVALUATE_CENTER:
        if (current_center != 12'd4075)
          frame_memory_read_address = (current_center - INTEGRATION_LEFT) ^ 12'h800;
      ST_UPDATE_CAPTURE_OUTGOING:
        frame_memory_read_address =
            (current_center + INTEGRATION_RIGHT + 1'b1) ^ 12'h800;
      ST_PREPARE_RECOVERY:
        if (!frame_overflow && recovery_count != 0)
          frame_memory_read_address = recovery_start[recovery_index] ^ 12'h800;
      ST_PEAK_COMPARE:
        if (peak_scan_index != recovery_end[recovery_index])
          frame_memory_read_address = (peak_scan_index + 1'b1) ^ 12'h800;
      default: ;
    endcase
  end

  always_comb begin
    case (state)
      ST_COEFFICIENT_NOISE: selected_coefficient = {6'd0, NOISE_Q48};
      ST_COEFFICIENT_THRESHOLD: selected_coefficient = {5'd0, REGIONAL_THRESHOLD_Q48};
      default: selected_coefficient = INTEGRATED_THRESHOLD_Q48;
    endcase
    coefficient_input = state == ST_COEFFICIENT_BROAD
        ? frame_reference_twice : frame_median_twice[coefficient_region];
    coefficient_product = coefficient_input * selected_coefficient;
    rounded_coefficient_product = coefficient_product + (113'd1 << 47);
  end

  assign scaled_window_sum = {2'd0, window_sum, 48'd0};
  assign regional_integrated_detected =
      scaled_window_sum > integrated_threshold_product[current_center[11:8]];
  assign broad_integrated_detected =
      scaled_window_sum > broad_integrated_threshold_product;
  assign integrated_detected = regional_integrated_detected;
  assign group_qualified = group_active &&
      ({1'b0, group_end} >= ({1'b0, group_start} + 13'd71));
  assign group_support_start = group_start + INTEGRATION_LEFT;
  assign group_support_end = group_end - INTEGRATION_RIGHT;
  // FLANK_MEDIAN_RATIO_Q48 is exactly 2.5.  Cancel the common Q48
  // denominator and compare 2*inside against 5*flank.  This is bit-exact and
  // avoids an unregistered 59-by-50-bit DSP cascade in the decision path.
  assign broad_inside_times_two = {2'd0, broad_inside_median_twice, 1'b0};
  assign broad_flank_times_five =
      ({3'd0, broad_flank_median_twice} << 2) +
      {3'd0, broad_flank_median_twice};
  assign broad_group_support_start = broad_group_start + INTEGRATION_LEFT;
  assign broad_group_support_end = broad_group_end - INTEGRATION_RIGHT;
  assign broad_group_qualified = broad_group_active &&
      ({1'b0, broad_group_end} >= ({1'b0, broad_group_start} + 13'd287)) &&
      broad_group_support_start[11:8] != 4'd0 &&
      broad_group_support_end[11:8] != REGION_COUNT - 1 &&
      broad_inside_times_two > broad_flank_times_five;

  // Balance the sixteen 59-bit comparisons over four levels.  The former
  // procedural reduction formed a sixteen-deep priority chain and could not
  // meet the 50 MHz clock constraint after synthesis.
  genvar broad_leaf;
  generate
    for (broad_leaf = 0; broad_leaf < REGION_COUNT; broad_leaf = broad_leaf + 1) begin : g_broad_inside_leaf
      localparam logic [3:0] BROAD_REGION_INDEX = broad_leaf;
      assign broad_inside_max_tree[15 + broad_leaf] =
          BROAD_REGION_INDEX >= broad_group_support_start[11:8] &&
          BROAD_REGION_INDEX <= broad_group_support_end[11:8]
              ? frame_median_twice[broad_leaf] : 59'd0;
    end
  endgenerate

  genvar broad_node;
  generate
    for (broad_node = 3; broad_node < REGION_COUNT - 1; broad_node = broad_node + 1) begin : g_broad_inside_node
      assign broad_inside_max_tree[broad_node] =
          broad_inside_max_tree[(2 * broad_node) + 1] >=
          broad_inside_max_tree[(2 * broad_node) + 2]
              ? broad_inside_max_tree[(2 * broad_node) + 1]
              : broad_inside_max_tree[(2 * broad_node) + 2];
    end
  endgenerate

  assign broad_inside_stage_three_left =
      broad_inside_stage_two[0] >= broad_inside_stage_two[1]
          ? broad_inside_stage_two[0] : broad_inside_stage_two[1];
  assign broad_inside_stage_three_right =
      broad_inside_stage_two[2] >= broad_inside_stage_two[3]
          ? broad_inside_stage_two[2] : broad_inside_stage_two[3];
  assign broad_inside_maximum_next =
      broad_inside_stage_three_left >= broad_inside_stage_three_right
          ? broad_inside_stage_three_left : broad_inside_stage_three_right;
  assign current_peak_better = frame_memory_read_data > peak_power;
  assign final_peak_index = current_peak_better ? peak_scan_index : peak_index;
  assign final_peak_power = current_peak_better ? frame_memory_read_data : peak_power;

  assign reference_current_better =
      !reference_selected_mask[reference_scan_region[3:0]] &&
      frame_median_twice[reference_scan_region[3:0]] < reference_min_value;
  assign reference_selected_index = reference_current_better
      ? reference_scan_region[3:0] : reference_min_index;
  assign reference_selected_value = reference_current_better
      ? frame_median_twice[reference_scan_region[3:0]] : reference_min_value;

  always_comb begin
    broad_flank_median_twice = 59'd0;
    broad_flank_region_index = 4'd0;
    if (broad_group_support_start[11:8] != 4'd0 &&
        broad_group_support_end[11:8] != REGION_COUNT - 1) begin
      if (frame_median_twice[broad_group_support_start[11:8] - 1'b1] >=
          frame_median_twice[broad_group_support_end[11:8] + 1'b1]) begin
        broad_flank_median_twice = frame_median_twice[broad_group_support_start[11:8] - 1'b1];
        broad_flank_region_index = broad_group_support_start[11:8] - 1'b1;
      end else begin
        broad_flank_median_twice = frame_median_twice[broad_group_support_end[11:8] + 1'b1];
        broad_flank_region_index = broad_group_support_end[11:8] + 1'b1;
      end
    end
  end

  always_comb begin
    later_recovery_valid = 1'b0;
    for (later_index = 0; later_index < MAXIMUM_RECOVERY_CANDIDATES; later_index = later_index + 1) begin
      if (later_index > recovery_index && later_index < recovery_count && recovery_valid[later_index])
        later_recovery_valid = 1'b1;
    end
  end

  always_ff @(posedge aclk) begin
    if (!aresetn) begin
      state <= ST_COLLECT;
      expected_input_index <= 12'd0;
      outgoing_power <= 58'd0;
      frame_range_error <= 1'b0;
      coefficient_region <= 4'd0;
      broad_integrated_threshold_product <= 113'd0;
      frame_reference_twice <= 59'd0;
      scan_broad <= 1'b0;
      reference_selected_mask <= 16'd0;
      reference_selection_rank <= 3'd0;
      reference_scan_region <= 5'd0;
      reference_min_index <= 4'd0;
      reference_min_value <= {59{1'b1}};
      window_sum <= 63'd0;
      window_read_index <= 12'd0;
      current_center <= 12'd20;
      group_active <= 1'b0;
      group_start <= 12'd0;
      group_end <= 12'd0;
      broad_group_active <= 1'b0;
      broad_group_start <= 12'd0;
      broad_group_end <= 12'd0;
      broad_inside_stage_two[0] <= 59'd0;
      broad_inside_stage_two[1] <= 59'd0;
      broad_inside_stage_two[2] <= 59'd0;
      broad_inside_stage_two[3] <= 59'd0;
      broad_inside_median_twice <= 59'd0;
      broad_recovery_count <= 5'd0;
      append_broad_index <= 5'd0;
      sort_pass <= 7'd0;
      sort_index <= 7'd0;
      sort_swapped <= 1'b0;
      recovery_count <= 7'd0;
      recovery_index <= 7'd0;
      suppression_candidate_index <= 7'd0;
      suppression_broad_index <= 7'd0;
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
      for (recovery_slot = 0; recovery_slot < MAXIMUM_RECOVERY_CANDIDATES;
           recovery_slot = recovery_slot + 1) begin
        recovery_start[recovery_slot] <= 12'd0;
        recovery_end[recovery_slot] <= 12'd0;
        recovery_is_broad[recovery_slot] <= 1'b0;
        recovery_valid[recovery_slot] <= 1'b0;
        recovery_noise_region[recovery_slot] <= 4'd0;
      end
      for (broad_slot = 0; broad_slot < MAXIMUM_BROAD_RECOVERY_CANDIDATES;
           broad_slot = broad_slot + 1) begin
        broad_recovery_start[broad_slot] <= 12'd0;
        broad_recovery_end[broad_slot] <= 12'd0;
        broad_recovery_noise_region[broad_slot] <= 4'd0;
      end
    end else begin
      broad_inside_stage_two[0] <= broad_inside_max_tree[3];
      broad_inside_stage_two[1] <= broad_inside_max_tree[4];
      broad_inside_stage_two[2] <= broad_inside_max_tree[5];
      broad_inside_stage_two[3] <= broad_inside_max_tree[6];
      broad_inside_median_twice <= broad_inside_maximum_next;
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
            broad_recovery_count <= 5'd0;
            frame_overflow <= 1'b0;
            group_active <= 1'b0;
            broad_group_active <= 1'b0;
            scan_broad <= 1'b0;
            output_candidate_valid <= 1'b0;
            coefficient_region <= 4'd0;
            if (frame_range_error) begin
              status_input_range_error_sticky <= 1'b1;
              output_last <= 1'b1;
              state <= ST_PRESENT_OUTPUT;
            end else begin
              state <= ST_REFERENCE_INITIALIZE;
            end
          end
        end

        ST_REFERENCE_INITIALIZE: begin
          reference_selected_mask <= 16'd0;
          reference_selection_rank <= 3'd0;
          reference_scan_region <= 5'd0;
          reference_min_index <= 4'd0;
          reference_min_value <= {59{1'b1}};
          state <= ST_REFERENCE_SCAN;
        end

        ST_REFERENCE_SCAN: begin
          if (reference_scan_region == REGION_COUNT - 1) begin
            if (reference_selection_rank == BROAD_REFERENCE_REGION_RANK - 1) begin
              frame_reference_twice <= reference_selected_value;
              coefficient_region <= 4'd0;
              state <= ST_COEFFICIENT_INTEGRATED;
            end else begin
              reference_selected_mask[reference_selected_index] <= 1'b1;
              reference_selection_rank <= reference_selection_rank + 1'b1;
              reference_scan_region <= 5'd0;
              reference_min_index <= 4'd0;
              reference_min_value <= {59{1'b1}};
            end
          end else begin
            if (reference_current_better) begin
              reference_min_index <= reference_scan_region[3:0];
              reference_min_value <= frame_median_twice[reference_scan_region[3:0]];
            end
            reference_scan_region <= reference_scan_region + 1'b1;
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
            state <= ST_COEFFICIENT_BROAD;
          end else begin
            coefficient_region <= coefficient_region + 1'b1;
            state <= ST_COEFFICIENT_INTEGRATED;
          end
        end

        ST_COEFFICIENT_BROAD: begin
          broad_integrated_threshold_product <= coefficient_product;
          window_sum <= 63'd0;
          window_read_index <= 12'd5;
          current_center <= 12'd20;
          group_active <= 1'b0;
          scan_broad <= 1'b0;
          state <= ST_WINDOW_INITIALIZE;
        end

        ST_WINDOW_INITIALIZE: begin
          state <= ST_WINDOW_ACCUMULATE;
        end

        ST_WINDOW_ACCUMULATE: begin
          window_sum <= window_sum + frame_memory_read_data;
          if (window_read_index == 12'd36) begin
            state <= ST_EVALUATE_CENTER;
          end else begin
            window_read_index <= window_read_index + 1'b1;
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
                  recovery_is_broad[recovery_count] <= 1'b0;
                  recovery_valid[recovery_count] <= 1'b1;
                  recovery_noise_region[recovery_count] <= broad_flank_region_index;
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
                recovery_is_broad[recovery_count] <= 1'b0;
                recovery_valid[recovery_count] <= 1'b1;
                recovery_noise_region[recovery_count] <= broad_flank_region_index;
                recovery_count <= recovery_count + 1'b1;
              end else begin
                frame_overflow <= 1'b1;
                status_candidate_overflow_sticky <= 1'b1;
              end
            end
            group_active <= 1'b0;
          end

          if (broad_integrated_detected) begin
            if (!broad_group_active) begin
              broad_group_active <= 1'b1;
              broad_group_start <= current_center;
              broad_group_end <= current_center;
            end else if ((current_center - broad_group_end) <= MAXIMUM_GAP_BINS + 1) begin
              broad_group_end <= current_center;
            end else begin
              if (broad_group_qualified) begin
                if (broad_recovery_count < MAXIMUM_BROAD_RECOVERY_CANDIDATES) begin
                  broad_recovery_start[broad_recovery_count] <= broad_group_support_start;
                  broad_recovery_end[broad_recovery_count] <= broad_group_support_end;
                  broad_recovery_noise_region[broad_recovery_count] <= broad_flank_region_index;
                  broad_recovery_count <= broad_recovery_count + 1'b1;
                end else begin
                  frame_overflow <= 1'b1;
                  status_candidate_overflow_sticky <= 1'b1;
                end
              end
              broad_group_start <= current_center;
              broad_group_end <= current_center;
            end
          end else if (broad_group_active &&
                       (current_center - broad_group_end) > MAXIMUM_GAP_BINS + 1) begin
            if (broad_group_qualified) begin
              if (broad_recovery_count < MAXIMUM_BROAD_RECOVERY_CANDIDATES) begin
                broad_recovery_start[broad_recovery_count] <= broad_group_support_start;
                broad_recovery_end[broad_recovery_count] <= broad_group_support_end;
                broad_recovery_noise_region[broad_recovery_count] <= broad_flank_region_index;
                broad_recovery_count <= broad_recovery_count + 1'b1;
              end else begin
                frame_overflow <= 1'b1;
                status_candidate_overflow_sticky <= 1'b1;
              end
            end
            broad_group_active <= 1'b0;
          end

          if (current_center == 12'd4075) begin
            state <= ST_FINALIZE_GROUP;
          end else begin
            state <= ST_UPDATE_CAPTURE_OUTGOING;
          end
        end

        ST_UPDATE_CAPTURE_OUTGOING: begin
          outgoing_power <= frame_memory_read_data;
          state <= ST_UPDATE_APPLY;
        end

        ST_UPDATE_APPLY: begin
          window_sum <= window_sum - outgoing_power + frame_memory_read_data;
          current_center <= current_center + 1'b1;
          state <= ST_EVALUATE_CENTER;
        end

        ST_FINALIZE_GROUP: begin
          if (group_qualified) begin
            if (recovery_count < MAXIMUM_RECOVERY_CANDIDATES) begin
              recovery_start[recovery_count] <= group_support_start;
              recovery_end[recovery_count] <= group_support_end;
              recovery_is_broad[recovery_count] <= 1'b0;
              recovery_valid[recovery_count] <= 1'b1;
              recovery_noise_region[recovery_count] <= broad_flank_region_index;
              recovery_count <= recovery_count + 1'b1;
            end else begin
              frame_overflow <= 1'b1;
              status_candidate_overflow_sticky <= 1'b1;
            end
          end
          group_active <= 1'b0;
          if (broad_group_qualified) begin
            if (broad_recovery_count < MAXIMUM_BROAD_RECOVERY_CANDIDATES) begin
              broad_recovery_start[broad_recovery_count] <= broad_group_support_start;
              broad_recovery_end[broad_recovery_count] <= broad_group_support_end;
              broad_recovery_noise_region[broad_recovery_count] <= broad_flank_region_index;
              broad_recovery_count <= broad_recovery_count + 1'b1;
            end else begin
              frame_overflow <= 1'b1;
              status_candidate_overflow_sticky <= 1'b1;
            end
          end
          broad_group_active <= 1'b0;
          state <= ST_SUPPRESSION_INITIALIZE;
        end

        ST_SUPPRESSION_INITIALIZE: begin
          suppression_candidate_index <= 7'd0;
          suppression_broad_index <= 7'd0;
          state <= ST_SUPPRESSION_SCAN;
        end

        ST_SUPPRESSION_SCAN: begin
          if (suppression_candidate_index >= recovery_count) begin
            append_broad_index <= 5'd0;
            state <= ST_APPEND_BROAD;
          end else if (!recovery_valid[suppression_candidate_index]) begin
            suppression_candidate_index <= suppression_candidate_index + 1'b1;
            suppression_broad_index <= 7'd0;
          end else if (suppression_broad_index >= broad_recovery_count) begin
            suppression_candidate_index <= suppression_candidate_index + 1'b1;
            suppression_broad_index <= 7'd0;
          end else if (
                       recovery_start[suppression_candidate_index] <=
                           broad_recovery_end[suppression_broad_index] &&
                       broad_recovery_start[suppression_broad_index] <=
                           recovery_end[suppression_candidate_index]) begin
            recovery_valid[suppression_candidate_index] <= 1'b0;
            suppression_candidate_index <= suppression_candidate_index + 1'b1;
            suppression_broad_index <= 7'd0;
          end else begin
            suppression_broad_index <= suppression_broad_index + 1'b1;
          end
        end

        ST_APPEND_BROAD: begin
          if (frame_overflow || append_broad_index >= broad_recovery_count) begin
            state <= ST_SORT_INITIALIZE;
          end else if (recovery_count >= MAXIMUM_RECOVERY_CANDIDATES) begin
            frame_overflow <= 1'b1;
            status_candidate_overflow_sticky <= 1'b1;
            recovery_index <= 7'd0;
            state <= ST_PREPARE_RECOVERY;
          end else begin
            recovery_start[recovery_count] <= broad_recovery_start[append_broad_index];
            recovery_end[recovery_count] <= broad_recovery_end[append_broad_index];
            recovery_is_broad[recovery_count] <= 1'b1;
            recovery_valid[recovery_count] <= 1'b1;
            recovery_noise_region[recovery_count] <= broad_recovery_noise_region[append_broad_index];
            recovery_count <= recovery_count + 1'b1;
            append_broad_index <= append_broad_index + 1'b1;
          end
        end

        ST_SORT_INITIALIZE: begin
          sort_pass <= 7'd0;
          sort_index <= 7'd0;
          sort_swapped <= 1'b0;
          state <= ST_SORT_SCAN;
        end

        ST_SORT_SCAN: begin
          if (frame_overflow || recovery_count < 2) begin
            recovery_index <= 7'd0;
            state <= ST_PREPARE_RECOVERY;
          end else if (sort_index + 1'b1 >= recovery_count - sort_pass) begin
            if (!sort_swapped || sort_pass + 1'b1 >= recovery_count - 1'b1) begin
              recovery_index <= 7'd0;
              state <= ST_PREPARE_RECOVERY;
            end else begin
              sort_pass <= sort_pass + 1'b1;
              sort_index <= 7'd0;
              sort_swapped <= 1'b0;
            end
          end else begin
            if (recovery_start[sort_index] > recovery_start[sort_index + 1'b1] ||
                (recovery_start[sort_index] == recovery_start[sort_index + 1'b1] &&
                 recovery_end[sort_index] > recovery_end[sort_index + 1'b1])) begin
              recovery_start[sort_index] <= recovery_start[sort_index + 1'b1];
              recovery_start[sort_index + 1'b1] <= recovery_start[sort_index];
              recovery_end[sort_index] <= recovery_end[sort_index + 1'b1];
              recovery_end[sort_index + 1'b1] <= recovery_end[sort_index];
              recovery_is_broad[sort_index] <= recovery_is_broad[sort_index + 1'b1];
              recovery_is_broad[sort_index + 1'b1] <= recovery_is_broad[sort_index];
              recovery_valid[sort_index] <= recovery_valid[sort_index + 1'b1];
              recovery_valid[sort_index + 1'b1] <= recovery_valid[sort_index];
              recovery_noise_region[sort_index] <= recovery_noise_region[sort_index + 1'b1];
              recovery_noise_region[sort_index + 1'b1] <= recovery_noise_region[sort_index];
              sort_swapped <= 1'b1;
            end
            sort_index <= sort_index + 1'b1;
          end
        end

        ST_PREPARE_RECOVERY: begin
          if (frame_overflow || recovery_count == 0 || recovery_index >= recovery_count) begin
            output_candidate_valid <= 1'b0;
            output_last <= 1'b1;
            state <= ST_PRESENT_OUTPUT;
          end else if (!recovery_valid[recovery_index]) begin
            if (recovery_index + 1'b1 >= recovery_count) begin
              output_candidate_valid <= 1'b0;
              output_last <= 1'b1;
              state <= ST_PRESENT_OUTPUT;
            end else begin
              recovery_index <= recovery_index + 1'b1;
            end
          end else begin
            peak_scan_index <= recovery_start[recovery_index];
            peak_index <= recovery_start[recovery_index];
            peak_power <= 58'd0;
            state <= ST_PEAK_COMPARE;
          end
        end

        ST_PEAK_COMPARE: begin
          if (peak_scan_index == recovery_end[recovery_index]) begin
            output_candidate_valid <= 1'b1;
            output_last <= !later_recovery_valid;
            output_start <= recovery_start[recovery_index];
            output_end <= recovery_end[recovery_index];
            output_peak <= final_peak_index;
            output_peak_power <= final_peak_power;
            output_noise <= recovery_is_broad[recovery_index]
                ? frame_region_noise[recovery_noise_region[recovery_index]]
                : frame_region_noise[final_peak_index[11:8]];
            output_threshold <= recovery_is_broad[recovery_index]
                ? frame_region_threshold[recovery_noise_region[recovery_index]]
                : frame_region_threshold[final_peak_index[11:8]];
            state <= ST_PRESENT_OUTPUT;
          end else begin
            if (current_peak_better) begin
              peak_index <= peak_scan_index;
              peak_power <= frame_memory_read_data;
            end
            peak_scan_index <= peak_scan_index + 1'b1;
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
              output_candidate_valid <= 1'b0;
              state <= ST_PREPARE_RECOVERY;
            end
          end
        end

        default: state <= ST_COLLECT;
      endcase
    end
  end
endmodule
