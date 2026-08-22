module axis_ci8_frame_stats (
  input  logic         aclk,
  input  logic         aresetn,

  input  logic         s_axis_tvalid,
  output logic         s_axis_tready,
  input  logic [15:0]  s_axis_tdata,
  input  logic         s_axis_tlast,

  output logic         m_result_tvalid,
  input  logic         m_result_tready,
  output logic [27:0]  m_result_total_energy,
  output logic [15:0]  m_result_peak_power,
  output logic [11:0]  m_result_peak_index,
  output logic [12:0]  m_result_sample_count,
  output logic         m_result_protocol_error,
  output logic [1:0]   m_result_error_code
);
  import phase06a_pkg::*;

  logic        buffered_valid;
  logic        buffered_ready;
  logic [16:0] buffered_payload;
  logic [15:0] buffered_data;
  logic        buffered_last;

  logic signed [8:0]  i_value;
  logic signed [8:0]  q_value;
  logic signed [17:0] i_square_signed;
  logic signed [17:0] q_square_signed;
  logic [16:0]        power_sum;
  logic [15:0]        sample_power;

  logic [11:0] sample_index;
  logic [27:0] energy_accumulator;
  logic [15:0] peak_power_accumulator;
  logic [11:0] peak_index_accumulator;
  logic        dropping_late_frame;

  logic        accepted_transfer;
  logic [27:0] next_energy;
  logic [15:0] next_peak_power;
  logic [11:0] next_peak_index;
  logic [12:0] next_sample_count;
  logic        expected_last;

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

  assign buffered_last = buffered_payload[16];
  assign buffered_data = buffered_payload[15:0];
  assign i_value = {buffered_data[7], buffered_data[7:0]};
  assign q_value = {buffered_data[15], buffered_data[15:8]};
  assign i_square_signed = i_value * i_value;
  assign q_square_signed = q_value * q_value;
  assign power_sum = {1'b0, i_square_signed[15:0]}
                   + {1'b0, q_square_signed[15:0]};
  assign sample_power = power_sum[15:0];

  assign buffered_ready = !m_result_tvalid || m_result_tready;
  assign accepted_transfer = buffered_valid && buffered_ready;
  assign next_energy = energy_accumulator + {{12{1'b0}}, sample_power};
  assign next_peak_power = (sample_power > peak_power_accumulator)
                         ? sample_power : peak_power_accumulator;
  assign next_peak_index = (sample_power > peak_power_accumulator)
                         ? sample_index : peak_index_accumulator;
  assign next_sample_count = {1'b0, sample_index} + 13'd1;
  assign expected_last = sample_index == 12'd4095;

  always_ff @(posedge aclk) begin
    if (!aresetn) begin
      sample_index             <= '0;
      energy_accumulator       <= '0;
      peak_power_accumulator   <= '0;
      peak_index_accumulator   <= '0;
      dropping_late_frame      <= 1'b0;
      m_result_tvalid          <= 1'b0;
      m_result_total_energy    <= '0;
      m_result_peak_power      <= '0;
      m_result_peak_index      <= '0;
      m_result_sample_count    <= '0;
      m_result_protocol_error  <= 1'b0;
      m_result_error_code      <= PHASE06A_ERROR_NONE;
    end else begin
      if (m_result_tvalid && m_result_tready) begin
        m_result_tvalid <= 1'b0;
      end

      if (accepted_transfer) begin
        if (dropping_late_frame) begin
          if (buffered_last) begin
            dropping_late_frame    <= 1'b0;
            sample_index           <= '0;
            energy_accumulator     <= '0;
            peak_power_accumulator <= '0;
            peak_index_accumulator <= '0;
          end
        end else if (buffered_last || expected_last) begin
          m_result_tvalid          <= 1'b1;
          m_result_total_energy    <= next_energy;
          m_result_peak_power      <= next_peak_power;
          m_result_peak_index      <= next_peak_index;
          m_result_sample_count    <= next_sample_count;
          m_result_protocol_error  <= buffered_last != expected_last;
          if (buffered_last && !expected_last) begin
            m_result_error_code <= PHASE06A_ERROR_EARLY_TLAST;
          end else if (!buffered_last && expected_last) begin
            m_result_error_code <= PHASE06A_ERROR_MISSING_TLAST;
          end else begin
            m_result_error_code <= PHASE06A_ERROR_NONE;
          end

          sample_index             <= '0;
          energy_accumulator       <= '0;
          peak_power_accumulator   <= '0;
          peak_index_accumulator   <= '0;
          if (!buffered_last && expected_last) begin
            dropping_late_frame <= 1'b1;
          end
        end else begin
          sample_index             <= sample_index + 12'd1;
          energy_accumulator       <= next_energy;
          peak_power_accumulator   <= next_peak_power;
          peak_index_accumulator   <= next_peak_index;
        end
      end
    end
  end
endmodule
