module axis_regional_detector (
  input  logic        aclk,
  input  logic        aresetn,

  input  logic        cfg_evaluate_center,
  input  logic [1:0]  cfg_pfa_select,

  input  logic        s_axis_tvalid,
  output logic        s_axis_tready,
  input  logic [57:0] s_axis_tdata,
  input  logic        s_axis_tlast,
  input  logic [11:0] s_axis_tuser_index,

  output logic        m_axis_tvalid,
  input  logic        m_axis_tready,
  output logic [57:0] m_axis_tdata,
  output logic        m_axis_tlast,
  output logic [11:0] m_axis_tuser_natural_index,
  output logic [11:0] m_axis_tuser_shifted_index,
  output logic [58:0] m_axis_tuser_median_twice,
  output logic [57:0] m_axis_tuser_noise,
  output logic [61:0] m_axis_tuser_threshold,
  output logic        m_axis_tuser_evaluated,
  output logic        m_axis_tuser_detected,
  output logic [1:0]  m_axis_tuser_pfa_select,
  output logic        m_axis_tuser_evaluate_center,

  output logic        status_frame_error_sticky
);
  import phase06g_pkg::*;

  typedef enum logic [3:0] {
    ST_COLLECT,
    ST_RESYNC,
    ST_SELECT_SETUP,
    ST_SELECT_READ,
    ST_SELECT_COUNT,
    ST_SELECT_DECIDE,
    ST_COEFF_NOISE,
    ST_COEFF_THRESHOLD,
    ST_COEFF_STORE,
    ST_OUTPUT_READ,
    ST_OUTPUT_PRESENT
  } state_t;

  state_t state;
  (* ram_style = "block" *) logic [57:0] frame_memory [0:4095];
  logic [57:0] frame_read_data;
  logic [58:0] region_median_twice [0:15];
  logic [57:0] region_noise [0:15];
  logic [61:0] region_threshold [0:15];

  logic [11:0] expected_input_index;
  logic [1:0]  frame_pfa_select;
  logic        frame_evaluate_center;

  logic [3:0]  selection_region;
  logic [5:0]  selection_bit;
  logic [7:0]  selection_scan_index;
  logic [57:0] selection_mask;
  logic [57:0] lower_prefix;
  logic [57:0] upper_prefix;
  logic [7:0]  lower_rank;
  logic [7:0]  upper_rank;
  logic [8:0]  lower_zero_count;
  logic [8:0]  upper_zero_count;
  logic [57:0] lower_decided_prefix;
  logic [57:0] upper_decided_prefix;

  logic [58:0] median_twice_work;
  logic [28:0] multiplier_coefficient;
  logic [87:0] multiplier_result;
  logic [87:0] multiplier_register;
  logic [11:0] output_index;
  logic [11:0] output_shifted_index;
  logic [3:0]  output_region;
  logic        output_evaluated;

  assign s_axis_tready = (state == ST_COLLECT) || (state == ST_RESYNC);
  assign m_axis_tvalid = state == ST_OUTPUT_PRESENT;
  assign output_shifted_index = output_index ^ 12'h800;
  assign output_region = output_shifted_index[11:8];
  assign output_evaluated = (output_shifted_index >= 12'd20) &&
                            (output_shifted_index < 12'd4076) &&
                            (frame_evaluate_center || output_shifted_index != 12'd2048);

  assign m_axis_tdata = frame_read_data;
  assign m_axis_tlast = output_index == 12'd4095;
  assign m_axis_tuser_natural_index = output_index;
  assign m_axis_tuser_shifted_index = output_shifted_index;
  assign m_axis_tuser_median_twice = region_median_twice[output_region];
  assign m_axis_tuser_noise = output_evaluated ? region_noise[output_region] : 58'd0;
  assign m_axis_tuser_threshold = output_evaluated ? region_threshold[output_region] : 62'd0;
  assign m_axis_tuser_evaluated = output_evaluated;
  assign m_axis_tuser_detected = output_evaluated &&
                                 ({4'd0, frame_read_data} > region_threshold[output_region]);
  assign m_axis_tuser_pfa_select = frame_pfa_select;
  assign m_axis_tuser_evaluate_center = frame_evaluate_center;

  always_comb begin
    lower_decided_prefix = lower_prefix;
    upper_decided_prefix = upper_prefix;
    lower_decided_prefix[selection_bit] = lower_rank >= lower_zero_count;
    upper_decided_prefix[selection_bit] = upper_rank >= upper_zero_count;
  end

  always_comb begin
    case (frame_pfa_select)
      2'd0: multiplier_coefficient = C_COMBINED_PFA_1E3_Q24;
      2'd1: multiplier_coefficient = C_COMBINED_PFA_1E4_Q24;
      default: multiplier_coefficient = C_COMBINED_PFA_1E5_Q24;
    endcase
    if (state == ST_COEFF_NOISE)
      multiplier_coefficient = {3'd0, C_NOISE_Q24};
  end

  assign multiplier_result = median_twice_work * multiplier_coefficient;

  always_ff @(posedge aclk) begin
    if (!aresetn) begin
      state <= ST_COLLECT;
      expected_input_index <= 12'd0;
      frame_pfa_select <= 2'd1;
      frame_evaluate_center <= 1'b1;
      status_frame_error_sticky <= 1'b0;
      frame_read_data <= 58'd0;
      selection_region <= 4'd0;
      selection_bit <= 6'd57;
      selection_scan_index <= 8'd0;
      selection_mask <= 58'd0;
      lower_prefix <= 58'd0;
      upper_prefix <= 58'd0;
      lower_rank <= 8'd127;
      upper_rank <= 8'd128;
      lower_zero_count <= 9'd0;
      upper_zero_count <= 9'd0;
      median_twice_work <= 59'd0;
      multiplier_register <= 88'd0;
      output_index <= 12'd0;
    end else begin
      case (state)
        ST_COLLECT: begin
          if (s_axis_tvalid && s_axis_tready) begin
            if ((s_axis_tuser_index != expected_input_index) ||
                (s_axis_tlast != (expected_input_index == 12'd4095)) ||
                ((expected_input_index == 12'd0) && (cfg_pfa_select == 2'd3))) begin
              status_frame_error_sticky <= 1'b1;
              expected_input_index <= 12'd0;
              if (s_axis_tlast || (expected_input_index == 12'd4095))
                state <= ST_COLLECT;
              else
                state <= ST_RESYNC;
            end else begin
              frame_memory[expected_input_index] <= s_axis_tdata;
              if (expected_input_index == 12'd0) begin
                frame_pfa_select <= cfg_pfa_select;
                frame_evaluate_center <= cfg_evaluate_center;
              end
              if (expected_input_index == 12'd4095) begin
                expected_input_index <= 12'd0;
                selection_region <= 4'd0;
                state <= ST_SELECT_SETUP;
              end else begin
                expected_input_index <= expected_input_index + 1'b1;
              end
            end
          end
        end

        ST_RESYNC: begin
          if (s_axis_tvalid && s_axis_tready && s_axis_tlast) begin
            expected_input_index <= 12'd0;
            state <= ST_COLLECT;
          end
        end

        ST_SELECT_SETUP: begin
          selection_bit <= 6'd57;
          selection_scan_index <= 8'd0;
          selection_mask <= 58'd0;
          lower_prefix <= 58'd0;
          upper_prefix <= 58'd0;
          lower_rank <= 8'd127;
          upper_rank <= 8'd128;
          lower_zero_count <= 9'd0;
          upper_zero_count <= 9'd0;
          state <= ST_SELECT_READ;
        end

        ST_SELECT_READ: begin
          frame_read_data <= frame_memory[{(selection_region ^ 4'h8), selection_scan_index}];
          state <= ST_SELECT_COUNT;
        end

        ST_SELECT_COUNT: begin
          if (((frame_read_data & selection_mask) == (lower_prefix & selection_mask)) &&
              !frame_read_data[selection_bit])
            lower_zero_count <= lower_zero_count + 1'b1;
          if (((frame_read_data & selection_mask) == (upper_prefix & selection_mask)) &&
              !frame_read_data[selection_bit])
            upper_zero_count <= upper_zero_count + 1'b1;
          if (selection_scan_index == 8'd255) begin
            state <= ST_SELECT_DECIDE;
          end else begin
            selection_scan_index <= selection_scan_index + 1'b1;
            state <= ST_SELECT_READ;
          end
        end

        ST_SELECT_DECIDE: begin
          lower_prefix <= lower_decided_prefix;
          upper_prefix <= upper_decided_prefix;
          selection_mask[selection_bit] <= 1'b1;
          if (lower_rank >= lower_zero_count)
            lower_rank <= lower_rank - lower_zero_count;
          if (upper_rank >= upper_zero_count)
            upper_rank <= upper_rank - upper_zero_count;
          if (selection_bit == 6'd0) begin
            median_twice_work <= {1'b0, lower_decided_prefix} + {1'b0, upper_decided_prefix};
            state <= ST_COEFF_NOISE;
          end else begin
            selection_bit <= selection_bit - 1'b1;
            selection_scan_index <= 8'd0;
            lower_zero_count <= 9'd0;
            upper_zero_count <= 9'd0;
            state <= ST_SELECT_READ;
          end
        end

        ST_COEFF_NOISE: begin
          multiplier_register <= multiplier_result;
          state <= ST_COEFF_THRESHOLD;
        end

        ST_COEFF_THRESHOLD: begin
          region_noise[selection_region] <=
              (multiplier_register + (88'd1 << 24)) >> 25;
          multiplier_register <= multiplier_result;
          state <= ST_COEFF_STORE;
        end

        ST_COEFF_STORE: begin
          region_median_twice[selection_region] <= median_twice_work;
          region_threshold[selection_region] <=
              (multiplier_register + (88'd1 << 24)) >> 25;
          if (selection_region == 4'd15) begin
            output_index <= 12'd0;
            state <= ST_OUTPUT_READ;
          end else begin
            selection_region <= selection_region + 1'b1;
            state <= ST_SELECT_SETUP;
          end
        end

        ST_OUTPUT_READ: begin
          frame_read_data <= frame_memory[output_index];
          state <= ST_OUTPUT_PRESENT;
        end

        ST_OUTPUT_PRESENT: begin
          if (m_axis_tvalid && m_axis_tready) begin
            if (output_index == 12'd4095) begin
              output_index <= 12'd0;
              state <= ST_COLLECT;
            end else begin
              output_index <= output_index + 1'b1;
              state <= ST_OUTPUT_READ;
            end
          end
        end

        default: state <= ST_COLLECT;
      endcase
    end
  end
endmodule
