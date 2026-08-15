module axis_candidate_grouping (
  input  logic        aclk,
  input  logic        aresetn,
  input  logic        s_axis_tvalid,
  output logic        s_axis_tready,
  input  logic [57:0] s_axis_tdata,
  input  logic        s_axis_tlast,
  input  logic [11:0] s_axis_tuser_natural_index,
  input  logic [11:0] s_axis_tuser_shifted_index,
  input  logic [58:0] s_axis_tuser_median_twice,
  input  logic [57:0] s_axis_tuser_noise,
  input  logic [61:0] s_axis_tuser_threshold,
  input  logic        s_axis_tuser_evaluated,
  input  logic        s_axis_tuser_detected,
  input  logic [1:0]  s_axis_tuser_pfa_select,
  input  logic        s_axis_tuser_evaluate_center,
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
  output logic        status_frame_error_sticky,
  output logic        status_candidate_overflow_sticky
);
  import phase06h_pkg::*;

  typedef enum logic [3:0] {
    ST_COLLECT,
    ST_RESYNC,
    ST_FINALIZE_LOW,
    ST_PREPARE_BOUNDARY,
    ST_CHECK_BOUNDARY,
    ST_INITIALIZE_OUTPUT,
    ST_REQUEST_OUTPUT,
    ST_LOAD_OUTPUT,
    ST_PRESENT_OUTPUT
  } state_t;

  state_t state;
  logic [57:0] frame_region_noise [0:15];
  logic [61:0] frame_region_threshold [0:15];
  logic [11:0] expected_input_index;
  logic [1:0] frame_pfa_select;
  logic frame_evaluate_center;
  logic frame_overflow;
  logic pending_valid;
  logic [11:0] pending_start;
  logic [11:0] pending_end;
  logic [11:0] pending_peak;
  logic [57:0] pending_peak_power;
  logic [9:0] low_candidate_count;
  logic [9:0] high_candidate_count;

  logic low_write_enable;
  logic [9:0] low_write_address;
  logic [93:0] low_write_data;
  logic [9:0] low_read_address;
  logic [93:0] low_read_data;
  logic high_write_enable;
  logic [9:0] high_write_address;
  logic [93:0] high_write_data;
  logic [9:0] high_read_address;
  logic [93:0] high_read_data;

  logic [9:0] output_index;
  logic output_from_low;
  logic output_sentinel;
  logic [9:0] high_output_start_index;
  logic [93:0] output_record;
  logic output_last;
  logic output_candidate_valid;

  logic input_center_policy;
  logic expected_evaluated;
  logic input_contract_error;
  logic separated_detection;
  logic boundary_merge;
  logic [93:0] boundary_merged_record;
  logic [11:0] output_start;
  logic [11:0] output_end;
  logic [11:0] output_peak;
  logic [57:0] output_peak_power;

  function automatic logic [93:0] pack_candidate(
    input logic [11:0] start_index,
    input logic [11:0] end_index,
    input logic [11:0] peak_index,
    input logic [57:0] peak_power
  );
    pack_candidate = {peak_power, peak_index, end_index, start_index};
  endfunction

  phase06h_candidate_ram low_ram_i (
    .aclk,
    .write_enable(low_write_enable),
    .write_address(low_write_address),
    .write_data(low_write_data),
    .read_address(low_read_address),
    .read_data(low_read_data)
  );
  phase06h_candidate_ram high_ram_i (
    .aclk,
    .write_enable(high_write_enable),
    .write_address(high_write_address),
    .write_data(high_write_data),
    .read_address(high_read_address),
    .read_data(high_read_data)
  );

  assign s_axis_tready = (state == ST_COLLECT) || (state == ST_RESYNC);
  assign m_axis_tvalid = state == ST_PRESENT_OUTPUT;
  assign input_center_policy = (expected_input_index == 12'd0) ?
                               s_axis_tuser_evaluate_center : frame_evaluate_center;
  assign expected_evaluated = (s_axis_tuser_shifted_index >= 12'd20) &&
                              (s_axis_tuser_shifted_index < 12'd4076) &&
                              (input_center_policy || s_axis_tuser_shifted_index != 12'd2048);
  assign input_contract_error =
      (s_axis_tuser_natural_index != expected_input_index) ||
      (s_axis_tuser_shifted_index != (s_axis_tuser_natural_index ^ 12'h800)) ||
      (s_axis_tlast != (expected_input_index == 12'd4095)) ||
      (s_axis_tuser_pfa_select == 2'd3) ||
      ((expected_input_index != 12'd0) &&
       ((s_axis_tuser_pfa_select != frame_pfa_select) ||
        (s_axis_tuser_evaluate_center != frame_evaluate_center))) ||
      (s_axis_tuser_evaluated != expected_evaluated) ||
      (s_axis_tuser_detected && !s_axis_tuser_evaluated) ||
      (!s_axis_tuser_evaluated &&
       ((s_axis_tuser_noise != 58'd0) || (s_axis_tuser_threshold != 62'd0)));
  assign separated_detection = s_axis_tuser_detected && pending_valid &&
                               ((s_axis_tuser_shifted_index - pending_end) > 12'd2);
  assign boundary_merge = (low_candidate_count != 0) && (high_candidate_count != 0) &&
                          ((high_read_data[11:0] - low_read_data[23:12]) <= 12'd2);
  assign boundary_merged_record = {
    (high_read_data[93:36] > low_read_data[93:36]) ? high_read_data[93:36] : low_read_data[93:36],
    (high_read_data[93:36] > low_read_data[93:36]) ? high_read_data[35:24] : low_read_data[35:24],
    high_read_data[23:12],
    low_read_data[11:0]
  };

  always_comb begin
    low_write_enable = 1'b0;
    low_write_address = 10'd0;
    low_write_data = 94'd0;
    high_write_enable = 1'b0;
    high_write_address = 10'd0;
    high_write_data = 94'd0;
    low_read_address = output_index;
    high_read_address = output_index;

    if ((state == ST_COLLECT) && s_axis_tvalid && s_axis_tready && !input_contract_error) begin
      if (separated_detection) begin
        if (pending_end[11]) begin
          high_write_enable = high_candidate_count < HALF_MAX_CANDIDATES;
          high_write_address = high_candidate_count;
          high_write_data = pack_candidate(pending_start, pending_end, pending_peak, pending_peak_power);
        end else begin
          low_write_enable = low_candidate_count < HALF_MAX_CANDIDATES;
          low_write_address = low_candidate_count;
          low_write_data = pack_candidate(pending_start, pending_end, pending_peak, pending_peak_power);
        end
      end else if ((expected_input_index == 12'd2047) && pending_valid) begin
        high_write_enable = high_candidate_count < HALF_MAX_CANDIDATES;
        high_write_address = high_candidate_count;
        high_write_data = pack_candidate(pending_start, pending_end, pending_peak, pending_peak_power);
      end
    end else if ((state == ST_FINALIZE_LOW) && pending_valid) begin
      low_write_enable = low_candidate_count < HALF_MAX_CANDIDATES;
      low_write_address = low_candidate_count;
      low_write_data = pack_candidate(pending_start, pending_end, pending_peak, pending_peak_power);
    end else if ((state == ST_CHECK_BOUNDARY) && boundary_merge) begin
      low_write_enable = 1'b1;
      low_write_address = low_candidate_count - 1'b1;
      low_write_data = boundary_merged_record;
    end

    if (state == ST_PREPARE_BOUNDARY) begin
      low_read_address = low_candidate_count - 1'b1;
      high_read_address = 10'd0;
    end else if (state == ST_REQUEST_OUTPUT) begin
      low_read_address = output_index;
      high_read_address = output_index;
    end
  end

  assign output_start = output_record[11:0];
  assign output_end = output_record[23:12];
  assign output_peak = output_record[35:24];
  assign output_peak_power = output_record[93:36];
  assign m_axis_tdata = output_candidate_valid ? output_peak_power : 58'd0;
  assign m_axis_tlast = output_last;
  assign m_axis_tuser_start_shifted_bin = output_candidate_valid ? output_start : 12'd0;
  assign m_axis_tuser_end_shifted_bin = output_candidate_valid ? output_end : 12'd0;
  assign m_axis_tuser_peak_shifted_bin = output_candidate_valid ? output_peak : 12'd0;
  assign m_axis_tuser_coarse_span_bins = output_candidate_valid ? (output_end - output_start + 1'b1) : 12'd0;
  assign m_axis_tuser_noise = output_candidate_valid ? frame_region_noise[output_peak[11:8]] : 58'd0;
  assign m_axis_tuser_threshold = output_candidate_valid ? frame_region_threshold[output_peak[11:8]] : 62'd0;
  assign m_axis_tuser_pfa_select = output_candidate_valid ? frame_pfa_select : 2'd0;
  assign m_axis_tuser_evaluate_center = output_candidate_valid ? frame_evaluate_center : 1'b0;
  assign m_axis_tuser_candidate_valid = output_candidate_valid;

  always_ff @(posedge aclk) begin
    if (!aresetn) begin
      state <= ST_COLLECT;
      expected_input_index <= 12'd0;
      frame_pfa_select <= 2'd0;
      frame_evaluate_center <= 1'b0;
      frame_overflow <= 1'b0;
      pending_valid <= 1'b0;
      pending_start <= 12'd0;
      pending_end <= 12'd0;
      pending_peak <= 12'd0;
      pending_peak_power <= 58'd0;
      low_candidate_count <= 10'd0;
      high_candidate_count <= 10'd0;
      output_index <= 10'd0;
      output_from_low <= 1'b0;
      output_sentinel <= 1'b0;
      high_output_start_index <= 10'd0;
      output_record <= 94'd0;
      output_last <= 1'b0;
      output_candidate_valid <= 1'b0;
      status_frame_error_sticky <= 1'b0;
      status_candidate_overflow_sticky <= 1'b0;
    end else begin
      case (state)
        ST_COLLECT: begin
          if (s_axis_tvalid && s_axis_tready) begin
            if (input_contract_error) begin
              status_frame_error_sticky <= 1'b1;
              expected_input_index <= 12'd0;
              pending_valid <= 1'b0;
              low_candidate_count <= 10'd0;
              high_candidate_count <= 10'd0;
              frame_overflow <= 1'b0;
              if (s_axis_tlast || expected_input_index == 12'd4095)
                state <= ST_COLLECT;
              else
                state <= ST_RESYNC;
            end else begin
              if (expected_input_index == 12'd0) begin
                frame_pfa_select <= s_axis_tuser_pfa_select;
                frame_evaluate_center <= s_axis_tuser_evaluate_center;
                frame_overflow <= 1'b0;
                low_candidate_count <= 10'd0;
                high_candidate_count <= 10'd0;
                pending_valid <= 1'b0;
              end
              if (s_axis_tuser_evaluated) begin
                frame_region_noise[s_axis_tuser_shifted_index[11:8]] <= s_axis_tuser_noise;
                frame_region_threshold[s_axis_tuser_shifted_index[11:8]] <= s_axis_tuser_threshold;
              end

              if (separated_detection) begin
                if (pending_end[11]) begin
                  if (high_candidate_count < HALF_MAX_CANDIDATES)
                    high_candidate_count <= high_candidate_count + 1'b1;
                  else begin
                    frame_overflow <= 1'b1;
                    status_candidate_overflow_sticky <= 1'b1;
                  end
                end else begin
                  if (low_candidate_count < HALF_MAX_CANDIDATES)
                    low_candidate_count <= low_candidate_count + 1'b1;
                  else begin
                    frame_overflow <= 1'b1;
                    status_candidate_overflow_sticky <= 1'b1;
                  end
                end
              end else if ((expected_input_index == 12'd2047) && pending_valid) begin
                if (high_candidate_count < HALF_MAX_CANDIDATES)
                  high_candidate_count <= high_candidate_count + 1'b1;
                else begin
                  frame_overflow <= 1'b1;
                  status_candidate_overflow_sticky <= 1'b1;
                end
              end

              if (s_axis_tuser_detected) begin
                if (!pending_valid || separated_detection) begin
                  pending_valid <= 1'b1;
                  pending_start <= s_axis_tuser_shifted_index;
                  pending_end <= s_axis_tuser_shifted_index;
                  pending_peak <= s_axis_tuser_shifted_index;
                  pending_peak_power <= s_axis_tdata;
                end else begin
                  pending_end <= s_axis_tuser_shifted_index;
                  if (s_axis_tdata > pending_peak_power) begin
                    pending_peak <= s_axis_tuser_shifted_index;
                    pending_peak_power <= s_axis_tdata;
                  end
                end
              end
              if (expected_input_index == 12'd2047)
                pending_valid <= 1'b0;

              if (expected_input_index == 12'd4095) begin
                expected_input_index <= 12'd0;
                state <= ST_FINALIZE_LOW;
              end else begin
                expected_input_index <= expected_input_index + 1'b1;
              end
            end
          end
        end

        ST_RESYNC: begin
          if (s_axis_tvalid && s_axis_tready && s_axis_tlast) begin
            expected_input_index <= 12'd0;
            pending_valid <= 1'b0;
            low_candidate_count <= 10'd0;
            high_candidate_count <= 10'd0;
            frame_overflow <= 1'b0;
            state <= ST_COLLECT;
          end
        end

        ST_FINALIZE_LOW: begin
          if (pending_valid) begin
            if (low_candidate_count < HALF_MAX_CANDIDATES)
              low_candidate_count <= low_candidate_count + 1'b1;
            else begin
              frame_overflow <= 1'b1;
              status_candidate_overflow_sticky <= 1'b1;
            end
          end
          pending_valid <= 1'b0;
          state <= ST_PREPARE_BOUNDARY;
        end

        ST_PREPARE_BOUNDARY: begin
          if (frame_overflow) begin
            low_candidate_count <= 10'd0;
            high_candidate_count <= 10'd0;
            state <= ST_COLLECT;
          end else begin
            state <= ST_CHECK_BOUNDARY;
          end
        end

        ST_CHECK_BOUNDARY: begin
          high_output_start_index <= boundary_merge ? 10'd1 : 10'd0;
          state <= ST_INITIALIZE_OUTPUT;
        end

        ST_INITIALIZE_OUTPUT: begin
          output_candidate_valid <= 1'b0;
          if (low_candidate_count != 0) begin
            output_from_low <= 1'b1;
            output_sentinel <= 1'b0;
            output_index <= 10'd0;
          end else if (high_candidate_count != high_output_start_index) begin
            output_from_low <= 1'b0;
            output_sentinel <= 1'b0;
            output_index <= high_output_start_index;
          end else begin
            output_from_low <= 1'b0;
            output_sentinel <= 1'b1;
            output_index <= 10'd0;
          end
          state <= ST_REQUEST_OUTPUT;
        end

        ST_REQUEST_OUTPUT: state <= ST_LOAD_OUTPUT;

        ST_LOAD_OUTPUT: begin
          output_record <= output_sentinel ? 94'd0 : (output_from_low ? low_read_data : high_read_data);
          output_candidate_valid <= !output_sentinel;
          if (output_sentinel)
            output_last <= 1'b1;
          else if (output_from_low)
            output_last <= (output_index + 1'b1 == low_candidate_count) &&
                           (high_candidate_count == high_output_start_index);
          else
            output_last <= output_index + 1'b1 == high_candidate_count;
          state <= ST_PRESENT_OUTPUT;
        end

        ST_PRESENT_OUTPUT: begin
          if (m_axis_tvalid && m_axis_tready) begin
            if (output_last) begin
              low_candidate_count <= 10'd0;
              high_candidate_count <= 10'd0;
              output_candidate_valid <= 1'b0;
              state <= ST_COLLECT;
            end else begin
              if (output_from_low && (output_index + 1'b1 == low_candidate_count)) begin
                output_from_low <= 1'b0;
                output_index <= high_output_start_index;
              end else begin
                output_index <= output_index + 1'b1;
              end
              state <= ST_REQUEST_OUTPUT;
            end
          end
        end

        default: state <= ST_COLLECT;
      endcase
    end
  end

  logic unused_median;
  assign unused_median = ^s_axis_tuser_median_twice;
endmodule
