module axis_fft_runtime_linear_power (
  input  logic        aclk,
  input  logic        aresetn,

  input  logic        s_axis_tvalid,
  output logic        s_axis_tready,
  input  logic [63:0] s_axis_tdata,
  input  logic        s_axis_tlast,
  input  logic [13:0] s_axis_tuser_index,

  output logic        m_axis_tvalid,
  input  logic        m_axis_tready,
  output logic [61:0] m_axis_tdata,
  output logic        m_axis_tlast,
  output logic [13:0] m_axis_tuser_index
);
  logic stage0_valid, stage1_valid, stage2_valid;
  logic stage0_ready, stage1_ready, stage2_ready;
  logic signed [30:0] stage0_i, stage0_q;
  logic stage0_last;
  logic [13:0] stage0_index;
  logic [60:0] stage1_i_square, stage1_q_square;
  logic stage1_last;
  logic [13:0] stage1_index;
  logic [61:0] stage2_power;
  logic stage2_last;
  logic [13:0] stage2_index;
  logic [30:0] stage0_i_magnitude, stage0_q_magnitude;
  logic [61:0] stage0_i_square_full, stage0_q_square_full;

  function automatic logic [30:0] magnitude31(input logic signed [30:0] value);
    logic [30:0] bits;
    begin
      bits = value;
      magnitude31 = value[30] ? (~bits + 31'd1) : bits;
    end
  endfunction

  assign stage0_i_magnitude = magnitude31(stage0_i);
  assign stage0_q_magnitude = magnitude31(stage0_q);
  assign stage0_i_square_full = stage0_i_magnitude * stage0_i_magnitude;
  assign stage0_q_square_full = stage0_q_magnitude * stage0_q_magnitude;
  assign stage2_ready = !stage2_valid || m_axis_tready;
  assign stage1_ready = !stage1_valid || stage2_ready;
  assign stage0_ready = !stage0_valid || stage1_ready;
  assign s_axis_tready = stage0_ready;
  assign m_axis_tvalid = stage2_valid;
  assign m_axis_tdata = stage2_power;
  assign m_axis_tlast = stage2_last;
  assign m_axis_tuser_index = stage2_index;

  always_ff @(posedge aclk) begin
    if (!aresetn) begin
      stage0_valid <= 1'b0;
      stage1_valid <= 1'b0;
      stage2_valid <= 1'b0;
      stage0_i <= '0;
      stage0_q <= '0;
      stage0_last <= 1'b0;
      stage0_index <= '0;
      stage1_i_square <= '0;
      stage1_q_square <= '0;
      stage1_last <= 1'b0;
      stage1_index <= '0;
      stage2_power <= '0;
      stage2_last <= 1'b0;
      stage2_index <= '0;
    end else begin
      if (stage2_ready) begin
        stage2_valid <= stage1_valid;
        if (stage1_valid) begin
          stage2_power <= {1'b0, stage1_i_square} + {1'b0, stage1_q_square};
          stage2_last <= stage1_last;
          stage2_index <= stage1_index;
        end
      end
      if (stage1_ready) begin
        stage1_valid <= stage0_valid;
        if (stage0_valid) begin
          stage1_i_square <= stage0_i_square_full[60:0];
          stage1_q_square <= stage0_q_square_full[60:0];
          stage1_last <= stage0_last;
          stage1_index <= stage0_index;
        end
      end
      if (stage0_ready) begin
        stage0_valid <= s_axis_tvalid;
        if (s_axis_tvalid) begin
          stage0_i <= $signed(s_axis_tdata[30:0]);
          stage0_q <= $signed(s_axis_tdata[62:32]);
          stage0_last <= s_axis_tlast;
          stage0_index <= s_axis_tuser_index;
        end
      end
    end
  end
endmodule
