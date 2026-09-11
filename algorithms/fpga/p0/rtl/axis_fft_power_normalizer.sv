module axis_fft_power_normalizer (
  input  logic        aclk,
  input  logic        aresetn,
  input  logic [3:0]  active_fft_log2,
  input  logic        s_axis_tvalid,
  output logic        s_axis_tready,
  input  logic [61:0] s_axis_tdata,
  input  logic        s_axis_tlast,
  input  logic [13:0] s_axis_tuser_index,
  output logic        m_axis_tvalid,
  input  logic        m_axis_tready,
  output logic [57:0] m_axis_tdata,
  output logic        m_axis_tlast,
  output logic [13:0] m_axis_tuser_index,
  output logic        status_config_error_sticky
);
  logic [2:0] shift;
  logic valid_fft_size;
  logic [61:0] shifted_power;

  always_comb begin
    valid_fft_size = 1'b1;
    case (active_fft_log2)
      4'd12: shift = 3'd0;
      4'd13: shift = 3'd2;
      4'd14: shift = 3'd4;
      default: begin shift = 3'd0; valid_fft_size = 1'b0; end
    endcase
    shifted_power = s_axis_tdata >> shift;
  end

  assign s_axis_tready = !m_axis_tvalid || m_axis_tready;

  always_ff @(posedge aclk) begin
    if (!aresetn) begin
      m_axis_tvalid <= 1'b0;
      m_axis_tdata <= '0;
      m_axis_tlast <= 1'b0;
      m_axis_tuser_index <= '0;
      status_config_error_sticky <= 1'b0;
    end else begin
      if (!valid_fft_size)
        status_config_error_sticky <= 1'b1;
      if (s_axis_tready) begin
        m_axis_tvalid <= s_axis_tvalid;
        if (s_axis_tvalid) begin
          m_axis_tdata <= shifted_power[57:0];
          m_axis_tlast <= s_axis_tlast;
          m_axis_tuser_index <= s_axis_tuser_index;
        end
      end
    end
  end
endmodule
