`timescale 1ns/1ps

module p0_parallel_region_median (
  input  logic        aclk,
  input  logic        aresetn,

  input  logic        s_axis_tvalid,
  output logic        s_axis_tready,
  input  logic [57:0] s_axis_tdata,
  input  logic        s_axis_tlast,
  input  logic [11:0] s_axis_tuser_index,

  output logic        result_valid,
  output logic [58:0] region_median_twice [0:15],
  output logic [15:0] completed_frame_count,
  output logic        status_frame_error_sticky
);
  import p0_candidate_reducer_pkg::*;

  typedef enum logic [2:0] {
    ST_COLLECT,
    ST_RESYNC,
    ST_SELECT_SETUP,
    ST_SELECT_READ,
    ST_SELECT_COUNT,
    ST_SELECT_DECIDE,
    ST_RESULT
  } state_t;

  state_t state;
  (* ram_style = "block" *) logic [POWER_WIDTH-1:0] region_memory [0:REGION_COUNT-1][0:REGION_SIZE-1];
  logic [POWER_WIDTH-1:0] region_read_data [0:REGION_COUNT-1];
  logic [POWER_WIDTH-1:0] lower_prefix [0:REGION_COUNT-1];
  logic [POWER_WIDTH-1:0] upper_prefix [0:REGION_COUNT-1];
  logic [7:0] lower_rank [0:REGION_COUNT-1];
  logic [7:0] upper_rank [0:REGION_COUNT-1];
  logic [8:0] lower_zero_count [0:REGION_COUNT-1];
  logic [8:0] upper_zero_count [0:REGION_COUNT-1];
  logic [POWER_WIDTH-1:0] lower_decided_prefix [0:REGION_COUNT-1];
  logic [POWER_WIDTH-1:0] upper_decided_prefix [0:REGION_COUNT-1];

  logic [11:0] expected_input_index;
  logic [5:0] selection_bit;
  logic [7:0] selection_scan_index;
  logic [POWER_WIDTH-1:0] selection_mask;
  logic [3:0] write_region;
  integer region;

  assign s_axis_tready = state == ST_COLLECT || state == ST_RESYNC;
  assign result_valid = state == ST_RESULT;
  assign write_region = expected_input_index[11:8] ^ 4'h8;

  always_comb begin
    for (region = 0; region < REGION_COUNT; region = region + 1) begin
      lower_decided_prefix[region] = lower_prefix[region];
      upper_decided_prefix[region] = upper_prefix[region];
      lower_decided_prefix[region][selection_bit] =
          lower_rank[region] >= lower_zero_count[region];
      upper_decided_prefix[region][selection_bit] =
          upper_rank[region] >= upper_zero_count[region];
    end
  end

  always_ff @(posedge aclk) begin
    if (!aresetn) begin
      state <= ST_COLLECT;
      expected_input_index <= 12'd0;
      selection_bit <= 6'd57;
      selection_scan_index <= 8'd0;
      selection_mask <= '0;
      completed_frame_count <= 16'd0;
      status_frame_error_sticky <= 1'b0;
      for (region = 0; region < REGION_COUNT; region = region + 1) begin
        region_read_data[region] <= '0;
        lower_prefix[region] <= '0;
        upper_prefix[region] <= '0;
        lower_rank[region] <= 8'd127;
        upper_rank[region] <= 8'd128;
        lower_zero_count[region] <= 9'd0;
        upper_zero_count[region] <= 9'd0;
        region_median_twice[region] <= '0;
      end
    end else begin
      case (state)
        ST_COLLECT: begin
          if (s_axis_tvalid && s_axis_tready) begin
            if (s_axis_tuser_index != expected_input_index ||
                s_axis_tlast != (expected_input_index == FRAME_LENGTH - 1)) begin
              status_frame_error_sticky <= 1'b1;
              expected_input_index <= 12'd0;
              if (!s_axis_tlast && expected_input_index != FRAME_LENGTH - 1)
                state <= ST_RESYNC;
            end else begin
              region_memory[write_region][expected_input_index[7:0]] <= s_axis_tdata;
              if (expected_input_index == FRAME_LENGTH - 1) begin
                expected_input_index <= 12'd0;
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
          selection_mask <= '0;
          for (region = 0; region < REGION_COUNT; region = region + 1) begin
            lower_prefix[region] <= '0;
            upper_prefix[region] <= '0;
            lower_rank[region] <= 8'd127;
            upper_rank[region] <= 8'd128;
            lower_zero_count[region] <= 9'd0;
            upper_zero_count[region] <= 9'd0;
          end
          state <= ST_SELECT_READ;
        end

        ST_SELECT_READ: begin
          for (region = 0; region < REGION_COUNT; region = region + 1)
            region_read_data[region] <= region_memory[region][selection_scan_index];
          state <= ST_SELECT_COUNT;
        end

        ST_SELECT_COUNT: begin
          for (region = 0; region < REGION_COUNT; region = region + 1) begin
            if ((region_read_data[region] & selection_mask) ==
                    (lower_prefix[region] & selection_mask) &&
                !region_read_data[region][selection_bit])
              lower_zero_count[region] <= lower_zero_count[region] + 1'b1;
            if ((region_read_data[region] & selection_mask) ==
                    (upper_prefix[region] & selection_mask) &&
                !region_read_data[region][selection_bit])
              upper_zero_count[region] <= upper_zero_count[region] + 1'b1;
          end
          if (selection_scan_index == REGION_SIZE - 1) begin
            state <= ST_SELECT_DECIDE;
          end else begin
            selection_scan_index <= selection_scan_index + 1'b1;
            state <= ST_SELECT_READ;
          end
        end

        ST_SELECT_DECIDE: begin
          for (region = 0; region < REGION_COUNT; region = region + 1) begin
            lower_prefix[region] <= lower_decided_prefix[region];
            upper_prefix[region] <= upper_decided_prefix[region];
            if (lower_rank[region] >= lower_zero_count[region])
              lower_rank[region] <= lower_rank[region] - lower_zero_count[region];
            if (upper_rank[region] >= upper_zero_count[region])
              upper_rank[region] <= upper_rank[region] - upper_zero_count[region];
            lower_zero_count[region] <= 9'd0;
            upper_zero_count[region] <= 9'd0;
            if (selection_bit == 0)
              region_median_twice[region] <=
                  {1'b0, lower_decided_prefix[region]} +
                  {1'b0, upper_decided_prefix[region]};
          end
          selection_mask[selection_bit] <= 1'b1;
          selection_scan_index <= 8'd0;
          if (selection_bit == 0) begin
            completed_frame_count <= completed_frame_count + 1'b1;
            state <= ST_RESULT;
          end else begin
            selection_bit <= selection_bit - 1'b1;
            state <= ST_SELECT_READ;
          end
        end

        ST_RESULT: state <= ST_COLLECT;

        default: state <= ST_COLLECT;
      endcase
    end
  end
endmodule
