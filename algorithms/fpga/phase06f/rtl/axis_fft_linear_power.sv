module axis_fft_linear_power (
  input  logic        aclk,
  input  logic        aresetn,

  input  logic        s_axis_tvalid,
  output logic        s_axis_tready,
  input  logic [63:0] s_axis_tdata,
  input  logic        s_axis_tlast,
  input  logic [11:0] s_axis_tuser_index,

  output logic        m_axis_tvalid,
  input  logic        m_axis_tready,
  output logic [57:0] m_axis_tdata,
  output logic        m_axis_tlast,
  output logic [11:0] m_axis_tuser_index
);
  logic stage0_valid;
  logic stage1_valid;
  logic stage2_valid;
  logic stage0_ready;
  logic stage1_ready;
  logic stage2_ready;

  logic signed [28:0] stage0_i;
  logic signed [28:0] stage0_q;
  logic               stage0_last;
  logic [11:0]        stage0_index;

  logic [56:0] stage1_i_square;
  logic [56:0] stage1_q_square;
  logic        stage1_last;
  logic [11:0] stage1_index;

  logic [57:0] stage2_power;
  logic        stage2_last;
  logic [11:0] stage2_index;

  logic [28:0] stage0_i_magnitude;
  logic [28:0] stage0_q_magnitude;
  logic [57:0] stage0_i_square_full;
  logic [57:0] stage0_q_square_full;

  function automatic logic [28:0] magnitude29(input logic signed [28:0] value);
    logic [28:0] bits;
    begin
      bits = value;
      magnitude29 = value[28] ? (~bits + 29'd1) : bits;
    end
  endfunction

  assign stage0_i_magnitude = magnitude29(stage0_i);
  assign stage0_q_magnitude = magnitude29(stage0_q);
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
          // A 29-bit magnitude square is at most 2^56, so bit 57 is provably zero.
          stage1_i_square <= stage0_i_square_full[56:0];
          stage1_q_square <= stage0_q_square_full[56:0];
          stage1_last <= stage0_last;
          stage1_index <= stage0_index;
        end
      end

      if (stage0_ready) begin
        stage0_valid <= s_axis_tvalid;
        if (s_axis_tvalid) begin
          // Extract the numerical 29-bit fields; do not square 32-bit lane padding.
          stage0_i <= $signed(s_axis_tdata[28:0]);
          stage0_q <= $signed(s_axis_tdata[60:32]);
          stage0_last <= s_axis_tlast;
          stage0_index <= s_axis_tuser_index;
        end
      end
    end
  end
endmodule
