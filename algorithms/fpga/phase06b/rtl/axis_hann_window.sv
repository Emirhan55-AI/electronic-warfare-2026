module axis_hann_window #(
  parameter COEFFICIENT_FILE = "datasets/fixtures/phase06b/hann-coefficients.mem"
) (
  input  logic        aclk,
  input  logic        aresetn,

  input  logic        s_axis_tvalid,
  output logic        s_axis_tready,
  input  logic [15:0] s_axis_tdata,
  input  logic        s_axis_tlast,

  output logic        m_axis_tvalid,
  input  logic        m_axis_tready,
  output logic [31:0] m_axis_tdata,
  output logic        m_axis_tlast
);
  import phase06b_pkg::*;

  logic        buffered_valid;
  logic        buffered_ready;
  logic [16:0] buffered_payload;
  logic [15:0] buffered_data;
  logic        buffered_last;

  logic [PHASE06B_INDEX_WIDTH-1:0] sample_index;
  logic [12:0] rom_index;
  logic [PHASE06B_COEFFICIENT_WIDTH-1:0] coefficient_rom [0:2048];
  logic [PHASE06B_COEFFICIENT_WIDTH-1:0] coefficient;
  logic signed [7:0] i_value;
  logic signed [7:0] q_value;
  logic signed [16:0] coefficient_signed;
  logic signed [PHASE06B_PRODUCT_WIDTH-1:0] i_product;
  logic signed [PHASE06B_PRODUCT_WIDTH-1:0] q_product;
  logic signed [PHASE06B_OUTPUT_COMPONENT_WIDTH-1:0] rounded_i;
  logic signed [PHASE06B_OUTPUT_COMPONENT_WIDTH-1:0] rounded_q;
  logic processing_transfer;
  logic expected_last;

  initial begin
    $readmemh(COEFFICIENT_FILE, coefficient_rom);
  end

  function automatic logic signed [15:0] round_product(
    input logic signed [PHASE06B_PRODUCT_WIDTH-1:0] value
  );
    logic [PHASE06B_PRODUCT_WIDTH-1:0] magnitude;
    logic [PHASE06B_PRODUCT_WIDTH-1:0] rounded_magnitude;
    begin
      magnitude = value[PHASE06B_PRODUCT_WIDTH-1]
                ? (~value) + {{(PHASE06B_PRODUCT_WIDTH-1){1'b0}}, 1'b1}
                : value;
      rounded_magnitude = (magnitude + 25'd64) >> PHASE06B_OUTPUT_SHIFT;
      round_product = value[PHASE06B_PRODUCT_WIDTH-1]
                    ? (~rounded_magnitude[15:0]) + 16'd1
                    : rounded_magnitude[15:0];
    end
  endfunction

  axis_skid_buffer #(
    .PAYLOAD_WIDTH(17)
  ) input_buffer (
    .aclk      (aclk),
    .aresetn   (aresetn),
    .s_valid   (s_axis_tvalid),
    .s_ready   (s_axis_tready),
    .s_payload ({s_axis_tlast, s_axis_tdata}),
    .m_valid   (buffered_valid),
    .m_ready   (buffered_ready),
    .m_payload (buffered_payload)
  );

  assign buffered_data = buffered_payload[15:0];
  assign buffered_last = buffered_payload[16];
  assign buffered_ready = !m_axis_tvalid || m_axis_tready;
  assign processing_transfer = buffered_valid && buffered_ready;
  assign expected_last = sample_index == 12'd4095;
  assign rom_index = sample_index <= 12'd2048
                   ? {1'b0, sample_index}
                   : 13'd4096 - {1'b0, sample_index};
  assign coefficient = coefficient_rom[rom_index];
  assign i_value = $signed(buffered_data[7:0]);
  assign q_value = $signed(buffered_data[15:8]);
  assign coefficient_signed = $signed({1'b0, coefficient});
  assign i_product = i_value * coefficient_signed;
  assign q_product = q_value * coefficient_signed;
  assign rounded_i = round_product(i_product);
  assign rounded_q = round_product(q_product);

  always_ff @(posedge aclk) begin
    if (!aresetn) begin
      sample_index  <= '0;
      m_axis_tvalid <= 1'b0;
      m_axis_tdata  <= '0;
      m_axis_tlast  <= 1'b0;
    end else begin
      if (m_axis_tvalid && m_axis_tready) begin
        m_axis_tvalid <= 1'b0;
      end
      if (processing_transfer) begin
        m_axis_tvalid <= 1'b1;
        m_axis_tdata  <= {rounded_q, rounded_i};
        m_axis_tlast  <= buffered_last;
        if (buffered_last || expected_last) begin
          sample_index <= '0;
        end else begin
          sample_index <= sample_index + 12'd1;
        end
      end
    end
  end
endmodule
