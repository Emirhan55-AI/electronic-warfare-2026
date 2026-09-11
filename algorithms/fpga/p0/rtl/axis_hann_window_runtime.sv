module axis_hann_window_runtime #(
  parameter COEFFICIENT_FILE_4096 = "hann-runtime-coefficients-4096.mem",
  parameter COEFFICIENT_FILE_8192 = "hann-runtime-coefficients-8192.mem",
  parameter COEFFICIENT_FILE_16384 = "hann-runtime-coefficients-16384.mem"
) (
  input  logic        aclk,
  input  logic        aresetn,
  input  logic [3:0]  active_fft_log2,

  input  logic        s_axis_tvalid,
  output logic        s_axis_tready,
  input  logic [15:0] s_axis_tdata,
  input  logic        s_axis_tlast,

  output logic        m_axis_tvalid,
  input  logic        m_axis_tready,
  output logic [31:0] m_axis_tdata,
  output logic        m_axis_tlast,
  output logic        status_frame_error_sticky
);
  logic        buffered_valid;
  logic        buffered_ready;
  logic [16:0] buffered_payload;
  logic [15:0] buffered_data;
  logic        buffered_last;

  logic [13:0] sample_index;
  logic [14:0] frame_length;
  (* rom_style = "block" *)
  logic [15:0] coefficient_rom_4096 [0:4095];
  (* rom_style = "block" *)
  logic [15:0] coefficient_rom_8192 [0:8191];
  (* rom_style = "block" *)
  logic [15:0] coefficient_rom_16384 [0:16383];
  logic        coefficient_valid;
  logic        coefficient_ready;
  logic [15:0] coefficient_data;
  logic        coefficient_last;
  logic [15:0] coefficient;
  logic signed [7:0] i_value;
  logic signed [7:0] q_value;
  logic signed [16:0] coefficient_signed;
  logic signed [24:0] i_product;
  logic signed [24:0] q_product;
  logic signed [15:0] rounded_i;
  logic signed [15:0] rounded_q;
  logic processing_transfer;
  logic output_ready;
  logic expected_last;
  logic valid_fft_size;

  initial begin
    $readmemh(COEFFICIENT_FILE_4096, coefficient_rom_4096);
    $readmemh(COEFFICIENT_FILE_8192, coefficient_rom_8192);
    $readmemh(COEFFICIENT_FILE_16384, coefficient_rom_16384);
  end

  function automatic logic signed [15:0] round_product(
    input logic signed [24:0] value
  );
    logic [24:0] magnitude;
    logic [24:0] rounded_magnitude;
    begin
      magnitude = value[24] ? (~value) + 25'd1 : value;
      rounded_magnitude = (magnitude + 25'd64) >> 7;
      round_product = value[24]
                    ? (~rounded_magnitude[15:0]) + 16'd1
                    : rounded_magnitude[15:0];
    end
  endfunction

  axis_skid_buffer #(.PAYLOAD_WIDTH(17)) input_buffer (
    .aclk(aclk), .aresetn(aresetn),
    .s_valid(s_axis_tvalid), .s_ready(s_axis_tready),
    .s_payload({s_axis_tlast, s_axis_tdata}),
    .m_valid(buffered_valid), .m_ready(buffered_ready),
    .m_payload(buffered_payload)
  );

  always_comb begin
    valid_fft_size = 1'b1;
    case (active_fft_log2)
      4'd12: frame_length = 15'd4096;
      4'd13: frame_length = 15'd8192;
      4'd14: frame_length = 15'd16384;
      default: begin frame_length = 15'd4096; valid_fft_size = 1'b0; end
    endcase
  end

  assign buffered_data = buffered_payload[15:0];
  assign buffered_last = buffered_payload[16];
  assign output_ready = !m_axis_tvalid || m_axis_tready;
  assign coefficient_ready = !coefficient_valid || output_ready;
  assign buffered_ready = coefficient_ready;
  assign processing_transfer = buffered_valid && buffered_ready;
  assign expected_last = sample_index == frame_length - 1'b1;
  assign i_value = $signed(coefficient_data[7:0]);
  assign q_value = $signed(coefficient_data[15:8]);
  assign coefficient_signed = $signed({1'b0, coefficient});
  assign i_product = i_value * coefficient_signed;
  assign q_product = q_value * coefficient_signed;
  assign rounded_i = round_product(i_product);
  assign rounded_q = round_product(q_product);

  always_ff @(posedge aclk) begin
    if (!aresetn) begin
      sample_index <= '0;
      coefficient_valid <= 1'b0;
      coefficient_data <= '0;
      coefficient_last <= 1'b0;
      coefficient <= '0;
      m_axis_tvalid <= 1'b0;
      m_axis_tdata <= '0;
      m_axis_tlast <= 1'b0;
      status_frame_error_sticky <= 1'b0;
    end else begin
      if (!valid_fft_size)
        status_frame_error_sticky <= 1'b1;
      if (output_ready) begin
        m_axis_tvalid <= coefficient_valid;
        if (coefficient_valid) begin
          m_axis_tdata <= {rounded_q, rounded_i};
          m_axis_tlast <= coefficient_last;
        end
      end
      if (coefficient_ready)
        coefficient_valid <= buffered_valid;
      if (processing_transfer) begin
        coefficient_data <= buffered_data;
        coefficient_last <= buffered_last;
        case (active_fft_log2)
          4'd13: coefficient <= coefficient_rom_8192[sample_index[12:0]];
          4'd14: coefficient <= coefficient_rom_16384[sample_index[13:0]];
          default: coefficient <= coefficient_rom_4096[sample_index[11:0]];
        endcase
        if (buffered_last != expected_last)
          status_frame_error_sticky <= 1'b1;
        sample_index <= buffered_last || expected_last ? '0 : sample_index + 1'b1;
      end
    end
  end
endmodule
