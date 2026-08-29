`timescale 1ns/1ps

module tb_p0_candidate_reducer_packetizer;
  localparam int FRAME_LENGTH = 4096;
  localparam int FRAME_COUNT = 5;
  localparam int INPUT_RECORDS = FRAME_LENGTH * FRAME_COUNT;
  localparam int EXPECTED_BEATS = 345;

  logic aclk = 0;
  always #5 aclk = ~aclk;
  logic aresetn = 0;
  logic [70:0] input_memory [0:INPUT_RECORDS-1];
  logic [64:0] expected_memory [0:EXPECTED_BEATS-1];
  integer input_count = 0;
  integer output_count = 0;
  integer cycle_count = 0;
  integer output_stalls = 0;
  integer payload_stability_checks = 0;
  integer completed_packets = 0;
  logic stalled_previous = 0;
  logic [72:0] stalled_payload = 0;

  wire source_valid = input_count < INPUT_RECORDS;
  wire [70:0] source_word = source_valid ? input_memory[input_count] : 71'd0;
  wire s_axis_tready;
  wire m_axis_tvalid;
  wire [63:0] m_axis_tdata;
  wire [7:0] m_axis_tkeep;
  wire m_axis_tlast;
  wire [31:0] completed_frame_count;
  wire status_transport_error_sticky;
  wire status_candidate_overflow_sticky;
  wire [8:0] status_reducer_sticky;
  logic m_axis_tready;

  always_comb begin
    m_axis_tready = ((cycle_count % 17) != 5) && ((cycle_count % 29) != 11);
  end

  p0_candidate_reducer_packetizer_top dut (
    .aclk,
    .aresetn,
    .s_axis_tvalid(source_valid),
    .s_axis_tready,
    .s_axis_tdata(source_word[57:0]),
    .s_axis_tlast(source_word[70]),
    .s_axis_tuser_index(source_word[69:58]),
    .m_axis_tvalid,
    .m_axis_tready,
    .m_axis_tdata,
    .m_axis_tkeep,
    .m_axis_tlast,
    .completed_frame_count,
    .status_transport_error_sticky,
    .status_candidate_overflow_sticky,
    .status_reducer_sticky
  );

  always @(posedge aclk) begin
    if (!aresetn) begin
      input_count <= 0;
      output_count <= 0;
      cycle_count <= 0;
      output_stalls <= 0;
      payload_stability_checks <= 0;
      completed_packets <= 0;
      stalled_previous <= 0;
    end else begin
      cycle_count <= cycle_count + 1;
      if (source_valid && s_axis_tready)
        input_count <= input_count + 1;
      if (m_axis_tvalid && !m_axis_tready)
        output_stalls <= output_stalls + 1;
      if (stalled_previous) begin
        if (!m_axis_tvalid || {m_axis_tlast, m_axis_tkeep, m_axis_tdata} !== stalled_payload) begin
          $display("P0_PACKETIZER_ERROR stalled output changed");
          $fatal(1);
        end
        payload_stability_checks <= payload_stability_checks + 1;
      end
      stalled_previous <= m_axis_tvalid && !m_axis_tready;
      if (m_axis_tvalid && !m_axis_tready)
        stalled_payload <= {m_axis_tlast, m_axis_tkeep, m_axis_tdata};
      if (m_axis_tvalid && m_axis_tready) begin
        if (m_axis_tkeep !== 8'hFF) begin
          $display("P0_PACKETIZER_ERROR TKEEP mismatch");
          $fatal(1);
        end
        if (output_count >= EXPECTED_BEATS ||
            {m_axis_tlast, m_axis_tdata} !== expected_memory[output_count]) begin
          $display("P0_PACKETIZER_ERROR beat=%0d observed=%017x expected=%017x",
                   output_count, {m_axis_tlast, m_axis_tdata}, expected_memory[output_count]);
          $fatal(1);
        end
        output_count <= output_count + 1;
        if (m_axis_tlast)
          completed_packets <= completed_packets + 1;
      end
    end
  end

  initial begin
    $readmemh("datasets/fixtures/p0_wideband_recovery/axis-power-input.mem", input_memory);
    $readmemh("datasets/fixtures/p0_candidate_reducer_packetizer/transport-axis64-expected.mem", expected_memory);
    repeat (4) @(posedge aclk);
    aresetn = 1;
    wait (input_count == INPUT_RECORDS && output_count == EXPECTED_BEATS);
    wait (!m_axis_tvalid);
    if (completed_frame_count != FRAME_COUNT || completed_packets != FRAME_COUNT) begin
      $display("P0_PACKETIZER_ERROR packets=%0d frame_count=%0d", completed_packets, completed_frame_count);
      $fatal(1);
    end
    if (status_transport_error_sticky || status_candidate_overflow_sticky || status_reducer_sticky) begin
      $display("P0_PACKETIZER_ERROR status transport=%0d overflow=%0d reducer=%03x",
               status_transport_error_sticky, status_candidate_overflow_sticky, status_reducer_sticky);
      $fatal(1);
    end
    $display("P0_PACKETIZER_PASS frames=%0d candidates=61 beats=%0d output_stalls=%0d stability_checks=%0d",
             completed_packets, output_count, output_stalls, payload_stability_checks);
    $finish;
  end

  initial begin
    #20000000;
    $display("P0_PACKETIZER_ERROR timeout input=%0d output=%0d", input_count, output_count);
    $fatal(1);
  end
endmodule
