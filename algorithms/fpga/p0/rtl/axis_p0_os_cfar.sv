`timescale 1ns/1ps

module axis_p0_os_cfar (
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
  output logic        m_axis_tlast,
  output logic [11:0] m_axis_tuser_index,

  output logic        status_frame_error_sticky
);
  import p0_os_cfar_pkg::*;

  typedef enum logic [4:0] {
    ST_COLLECT,
    ST_RESYNC,
    ST_INIT_RESET,
    ST_INIT_READ,
    ST_INIT_LOCATE,
    ST_INIT_APPLY,
    ST_RANK_ITERATE,
    ST_RANK_CAPTURE,
    ST_MULTIPLY,
    ST_DECIDE,
    ST_SLIDE_READ,
    ST_REMOVE_LOCATE,
    ST_REMOVE_APPLY,
    ST_INSERT_LOCATE,
    ST_INSERT_APPLY,
    ST_OUTPUT_READ,
    ST_OUTPUT_PRESENT
  } state_t;

  state_t state;
  (* ram_style = "block" *) logic [57:0] frame_memory [0:FRAME_LENGTH-1];
  (* ram_style = "distributed" *) logic [1:0] metadata_memory [0:FRAME_LENGTH-1];
  logic [57:0] frame_read_data;
  logic [1:0] metadata_read_data;

  logic [57:0] window [0:40];
  logic [57:0] left_sorted [0:15];
  logic [57:0] right_sorted [0:15];
  logic [57:0] left_init_next [0:15];
  logic [57:0] right_init_next [0:15];
  logic [57:0] left_compacted [0:14];
  logic [57:0] right_compacted [0:14];
  logic [57:0] left_update_next [0:15];
  logic [57:0] right_update_next [0:15];

  logic [11:0] expected_input_index;
  logic [5:0] init_index;
  logic [11:0] read_shifted_index;
  logic [11:0] cut_shifted_index;
  logic [11:0] output_index;

  logic [4:0] init_left_position;
  logic [4:0] init_right_position;
  logic [4:0] init_left_position_comb;
  logic [4:0] init_right_position_comb;
  logic init_left_found;
  logic init_right_found;

  logic [3:0] left_remove_index;
  logic [3:0] right_remove_index;
  logic [3:0] left_remove_index_comb;
  logic [3:0] right_remove_index_comb;
  logic left_remove_found_comb;
  logic right_remove_found_comb;

  logic [4:0] left_update_position;
  logic [4:0] right_update_position;
  logic [4:0] left_update_position_comb;
  logic [4:0] right_update_position_comb;
  logic left_update_found;
  logic right_update_found;

  logic [4:0] rank_low;
  logic [4:0] rank_high;
  logic [2:0] rank_iteration;
  logic [4:0] rank_partition_i;
  logic [4:0] rank_step_i;
  logic [4:0] rank_step_j;
  logic [4:0] rank_step_low;
  logic [4:0] rank_step_high;
  logic [4:0] rank_step_partition;
  logic rank_step_found;
  logic [57:0] rank_value;
  logic [93:0] rank_product_registered;
  logic [89:0] cut_scaled;

  integer init_scan_index;
  integer init_apply_index;
  integer remove_scan_index;
  integer compact_index;
  integer update_scan_index;
  integer update_apply_index;
  integer sequential_index;

  assign s_axis_tready = state == ST_COLLECT || state == ST_RESYNC;
  assign m_axis_tvalid = state == ST_OUTPUT_PRESENT;
  assign m_axis_tdata = {
    OUTPUT_MARKER,
    metadata_read_data[1],
    metadata_read_data[0],
    frame_read_data
  };
  assign m_axis_tlast = output_index == 12'd4095;
  assign m_axis_tuser_index = output_index;
  assign cut_scaled = {window[20], {COEFFICIENT_FRACTION_BITS{1'b0}}};

  always_comb begin
    init_left_position_comb = 5'd16;
    init_right_position_comb = 5'd16;
    init_left_found = 1'b0;
    init_right_found = 1'b0;
    for (init_scan_index = 0; init_scan_index < 16; init_scan_index = init_scan_index + 1) begin
      if (!init_left_found && frame_read_data <= left_sorted[init_scan_index]) begin
        init_left_position_comb = init_scan_index[4:0];
        init_left_found = 1'b1;
      end
      if (!init_right_found && frame_read_data <= right_sorted[init_scan_index]) begin
        init_right_position_comb = init_scan_index[4:0];
        init_right_found = 1'b1;
      end
    end
  end

  always_comb begin
    left_init_next[0] = init_left_position == 0 ? frame_read_data : left_sorted[0];
    right_init_next[0] = init_right_position == 0 ? frame_read_data : right_sorted[0];
    for (init_apply_index = 1; init_apply_index < 16; init_apply_index = init_apply_index + 1) begin
      if (init_apply_index < init_left_position)
        left_init_next[init_apply_index] = left_sorted[init_apply_index];
      else if (init_apply_index == init_left_position)
        left_init_next[init_apply_index] = frame_read_data;
      else
        left_init_next[init_apply_index] = left_sorted[init_apply_index-1];

      if (init_apply_index < init_right_position)
        right_init_next[init_apply_index] = right_sorted[init_apply_index];
      else if (init_apply_index == init_right_position)
        right_init_next[init_apply_index] = frame_read_data;
      else
        right_init_next[init_apply_index] = right_sorted[init_apply_index-1];
    end
  end

  always_comb begin
    left_remove_index_comb = 4'd0;
    right_remove_index_comb = 4'd0;
    left_remove_found_comb = 1'b0;
    right_remove_found_comb = 1'b0;
    for (remove_scan_index = 0; remove_scan_index < 16; remove_scan_index = remove_scan_index + 1) begin
      if (!left_remove_found_comb && left_sorted[remove_scan_index] == window[0]) begin
        left_remove_index_comb = remove_scan_index[3:0];
        left_remove_found_comb = 1'b1;
      end
      if (!right_remove_found_comb && right_sorted[remove_scan_index] == window[25]) begin
        right_remove_index_comb = remove_scan_index[3:0];
        right_remove_found_comb = 1'b1;
      end
    end
  end

  always_comb begin
    left_update_position_comb = 5'd15;
    right_update_position_comb = 5'd15;
    left_update_found = 1'b0;
    right_update_found = 1'b0;
    for (update_scan_index = 0; update_scan_index < 15; update_scan_index = update_scan_index + 1) begin
      if (!left_update_found && window[16] <= left_compacted[update_scan_index]) begin
        left_update_position_comb = update_scan_index[4:0];
        left_update_found = 1'b1;
      end
      if (!right_update_found && frame_read_data <= right_compacted[update_scan_index]) begin
        right_update_position_comb = update_scan_index[4:0];
        right_update_found = 1'b1;
      end
    end
  end

  always_comb begin
    left_update_next[0] = left_update_position == 0 ? window[16] : left_compacted[0];
    right_update_next[0] = right_update_position == 0 ? frame_read_data : right_compacted[0];
    for (update_apply_index = 1; update_apply_index < 15; update_apply_index = update_apply_index + 1) begin
      if (update_apply_index < left_update_position)
        left_update_next[update_apply_index] = left_compacted[update_apply_index];
      else if (update_apply_index == left_update_position)
        left_update_next[update_apply_index] = window[16];
      else
        left_update_next[update_apply_index] = left_compacted[update_apply_index-1];

      if (update_apply_index < right_update_position)
        right_update_next[update_apply_index] = right_compacted[update_apply_index];
      else if (update_apply_index == right_update_position)
        right_update_next[update_apply_index] = frame_read_data;
      else
        right_update_next[update_apply_index] = right_compacted[update_apply_index-1];
    end
    left_update_next[15] = left_update_position == 15 ? window[16] : left_compacted[14];
    right_update_next[15] = right_update_position == 15 ? frame_read_data : right_compacted[14];
  end

  always_comb begin
    rank_step_i = ({1'b0, rank_low} + {1'b0, rank_high}) >> 1;
    rank_step_j = ORDER_STATISTIC_RANK - rank_step_i;
    rank_step_low = rank_low;
    rank_step_high = rank_high;
    rank_step_partition = rank_step_i;
    rank_step_found = 1'b0;
    if (rank_step_j == 16) begin
      if (right_sorted[15] > left_sorted[rank_step_i])
        rank_step_low = rank_step_i + 1'b1;
      else
        rank_step_found = 1'b1;
    end else if (rank_step_i == 16) begin
      if (left_sorted[15] > right_sorted[rank_step_j])
        rank_step_high = rank_step_i - 1'b1;
      else
        rank_step_found = 1'b1;
    end else if (left_sorted[rank_step_i-1] > right_sorted[rank_step_j]) begin
      rank_step_high = rank_step_i - 1'b1;
    end else if (right_sorted[rank_step_j-1] > left_sorted[rank_step_i]) begin
      rank_step_low = rank_step_i + 1'b1;
    end else begin
      rank_step_found = 1'b1;
    end
  end

  always_ff @(posedge aclk) begin
    if (!aresetn) begin
      state <= ST_COLLECT;
      expected_input_index <= 12'd0;
      init_index <= 6'd0;
      read_shifted_index <= 12'd0;
      cut_shifted_index <= 12'd0;
      output_index <= 12'd0;
      frame_read_data <= 58'd0;
      metadata_read_data <= 2'd0;
      init_left_position <= 5'd16;
      init_right_position <= 5'd16;
      left_remove_index <= 4'd0;
      right_remove_index <= 4'd0;
      left_update_position <= 5'd15;
      right_update_position <= 5'd15;
      rank_low <= 5'd8;
      rank_high <= 5'd16;
      rank_iteration <= 3'd0;
      rank_partition_i <= 5'd12;
      rank_value <= 58'd0;
      rank_product_registered <= 94'd0;
      status_frame_error_sticky <= 1'b0;
      for (sequential_index = 0; sequential_index < 41; sequential_index = sequential_index + 1)
        window[sequential_index] <= 58'd0;
      for (sequential_index = 0; sequential_index < 16; sequential_index = sequential_index + 1) begin
        left_sorted[sequential_index] <= {58{1'b1}};
        right_sorted[sequential_index] <= {58{1'b1}};
      end
      for (sequential_index = 0; sequential_index < 15; sequential_index = sequential_index + 1) begin
        left_compacted[sequential_index] <= 58'd0;
        right_compacted[sequential_index] <= 58'd0;
      end
    end else begin
      case (state)
        ST_COLLECT: begin
          if (s_axis_tvalid && s_axis_tready) begin
            if (s_axis_tuser_index != expected_input_index ||
                s_axis_tlast != (expected_input_index == 12'd4095)) begin
              status_frame_error_sticky <= 1'b1;
              expected_input_index <= 12'd0;
              if (s_axis_tlast || expected_input_index == 12'd4095)
                state <= ST_COLLECT;
              else
                state <= ST_RESYNC;
            end else begin
              frame_memory[expected_input_index] <= s_axis_tdata;
              metadata_memory[expected_input_index ^ 12'h800] <= 2'b00;
              if (expected_input_index == 12'd4095) begin
                expected_input_index <= 12'd0;
                state <= ST_INIT_RESET;
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

        ST_INIT_RESET: begin
          init_index <= 6'd0;
          for (sequential_index = 0; sequential_index < 16; sequential_index = sequential_index + 1) begin
            left_sorted[sequential_index] <= {58{1'b1}};
            right_sorted[sequential_index] <= {58{1'b1}};
          end
          state <= ST_INIT_READ;
        end

        ST_INIT_READ: begin
          frame_read_data <= frame_memory[init_index ^ 12'h800];
          state <= ST_INIT_LOCATE;
        end

        ST_INIT_LOCATE: begin
          init_left_position <= init_left_position_comb;
          init_right_position <= init_right_position_comb;
          state <= ST_INIT_APPLY;
        end

        ST_INIT_APPLY: begin
          window[init_index] <= frame_read_data;
          if (init_index < 16)
            for (sequential_index = 0; sequential_index < 16; sequential_index = sequential_index + 1)
              left_sorted[sequential_index] <= left_init_next[sequential_index];
          else if (init_index >= 25)
            for (sequential_index = 0; sequential_index < 16; sequential_index = sequential_index + 1)
              right_sorted[sequential_index] <= right_init_next[sequential_index];
          if (init_index == 6'd40) begin
            cut_shifted_index <= 12'd20;
            rank_low <= 5'd8;
            rank_high <= 5'd16;
            rank_iteration <= 3'd0;
            state <= ST_RANK_ITERATE;
          end else begin
            init_index <= init_index + 1'b1;
            state <= ST_INIT_READ;
          end
        end

        ST_RANK_ITERATE: begin
          if (rank_step_found) begin
            rank_partition_i <= rank_step_partition;
            state <= ST_RANK_CAPTURE;
          end else if (rank_iteration == 3'd4) begin
            status_frame_error_sticky <= 1'b1;
            expected_input_index <= 12'd0;
            state <= ST_COLLECT;
          end else begin
            rank_low <= rank_step_low;
            rank_high <= rank_step_high;
            rank_iteration <= rank_iteration + 1'b1;
          end
        end

        ST_RANK_CAPTURE: begin
          rank_value <= left_sorted[rank_partition_i-1] >
                        right_sorted[ORDER_STATISTIC_RANK-rank_partition_i-1]
                          ? left_sorted[rank_partition_i-1]
                          : right_sorted[ORDER_STATISTIC_RANK-rank_partition_i-1];
          state <= ST_MULTIPLY;
        end

        ST_MULTIPLY: begin
          rank_product_registered <= rank_value * ALPHA_Q32;
          state <= ST_DECIDE;
        end

        ST_DECIDE: begin
          metadata_memory[cut_shifted_index] <= {
            {{4{1'b0}}, cut_scaled} > rank_product_registered,
            1'b1
          };
          if (cut_shifted_index == 12'd4075) begin
            output_index <= 12'd0;
            state <= ST_OUTPUT_READ;
          end else begin
            if (cut_shifted_index == 12'd20)
              read_shifted_index <= 12'd41;
            else
              read_shifted_index <= read_shifted_index + 1'b1;
            state <= ST_SLIDE_READ;
          end
        end

        ST_SLIDE_READ: begin
          frame_read_data <= frame_memory[read_shifted_index ^ 12'h800];
          state <= ST_REMOVE_LOCATE;
        end

        ST_REMOVE_LOCATE: begin
          if (!left_remove_found_comb || !right_remove_found_comb) begin
            status_frame_error_sticky <= 1'b1;
            expected_input_index <= 12'd0;
            state <= ST_COLLECT;
          end else begin
            left_remove_index <= left_remove_index_comb;
            right_remove_index <= right_remove_index_comb;
            state <= ST_REMOVE_APPLY;
          end
        end

        ST_REMOVE_APPLY: begin
          for (compact_index = 0; compact_index < 15; compact_index = compact_index + 1) begin
            left_compacted[compact_index] <=
                compact_index < left_remove_index
                  ? left_sorted[compact_index] : left_sorted[compact_index+1];
            right_compacted[compact_index] <=
                compact_index < right_remove_index
                  ? right_sorted[compact_index] : right_sorted[compact_index+1];
          end
          state <= ST_INSERT_LOCATE;
        end

        ST_INSERT_LOCATE: begin
          left_update_position <= left_update_position_comb;
          right_update_position <= right_update_position_comb;
          state <= ST_INSERT_APPLY;
        end

        ST_INSERT_APPLY: begin
          for (sequential_index = 0; sequential_index < 16; sequential_index = sequential_index + 1) begin
            left_sorted[sequential_index] <= left_update_next[sequential_index];
            right_sorted[sequential_index] <= right_update_next[sequential_index];
          end
          for (sequential_index = 0; sequential_index < 40; sequential_index = sequential_index + 1)
            window[sequential_index] <= window[sequential_index+1];
          window[40] <= frame_read_data;
          cut_shifted_index <= read_shifted_index - 12'd20;
          rank_low <= 5'd8;
          rank_high <= 5'd16;
          rank_iteration <= 3'd0;
          state <= ST_RANK_ITERATE;
        end

        ST_OUTPUT_READ: begin
          frame_read_data <= frame_memory[output_index];
          metadata_read_data <= metadata_memory[output_index ^ 12'h800];
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
