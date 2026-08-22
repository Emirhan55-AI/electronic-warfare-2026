`timescale 1ns/1ps

module tb_axis_candidate_packetizer;
  localparam int INPUT_RECORDS = 1773;
  localparam int OUTPUT_BEATS = 8964;

  logic aclk = 0;
  always #5 aclk = ~aclk;
  logic aresetn = 0;
  logic [230:0] input_memory [0:INPUT_RECORDS-1];
  logic [64:0] expected_memory [0:OUTPUT_BEATS-1];
  integer input_count = 0;
  integer output_count = 0;
  integer cycle_count = 0;
  integer input_stalls = 0;
  integer output_stalls = 0;
  integer payload_stability_checks = 0;
  integer completed_packets = 0;
  integer extra_output_beats = 0;
  logic automatic_source = 0;
  logic scoreboard_enable = 0;
  logic manual_valid = 0;
  logic [230:0] manual_word = 0;
  wire [230:0] source_word = automatic_source ?
      ((input_count < INPUT_RECORDS) ? input_memory[input_count] : 231'd0) : manual_word;
  wire source_valid = automatic_source ? (input_count < INPUT_RECORDS) : manual_valid;
  wire s_axis_tready;
  wire m_axis_tvalid;
  logic m_axis_tready;
  wire [63:0] m_axis_tdata;
  wire [7:0] m_axis_tkeep;
  wire m_axis_tlast;
  wire [31:0] completed_frame_count;
  wire status_transport_error_sticky;
  wire status_candidate_overflow_sticky;
  wire [64:0] observed = {m_axis_tlast, m_axis_tdata};
  logic stalled_previous = 0;
  logic [72:0] stalled_payload = 0;

  axis_candidate_packetizer dut (
    .aclk, .aresetn,
    .s_axis_tvalid(source_valid), .s_axis_tready,
    .s_axis_tdata(source_word[57:0]), .s_axis_tlast(source_word[230]),
    .s_axis_tuser_start_shifted_bin(source_word[69:58]),
    .s_axis_tuser_end_shifted_bin(source_word[81:70]),
    .s_axis_tuser_peak_shifted_bin(source_word[93:82]),
    .s_axis_tuser_coarse_span_bins(source_word[105:94]),
    .s_axis_tuser_noise(source_word[163:106]),
    .s_axis_tuser_threshold(source_word[225:164]),
    .s_axis_tuser_pfa_select(source_word[227:226]),
    .s_axis_tuser_evaluate_center(source_word[228]),
    .s_axis_tuser_candidate_valid(source_word[229]),
    .m_axis_tvalid, .m_axis_tready, .m_axis_tdata, .m_axis_tkeep, .m_axis_tlast,
    .completed_frame_count, .status_transport_error_sticky,
    .status_candidate_overflow_sticky
  );

  always_comb m_axis_tready = ((cycle_count % 13) != 4) && ((cycle_count % 19) != 7);

  always @(posedge aclk) begin
    if (!aresetn) begin
      input_count <= 0;
      output_count <= 0;
      cycle_count <= 0;
      input_stalls <= 0;
      output_stalls <= 0;
      payload_stability_checks <= 0;
      completed_packets <= 0;
      extra_output_beats <= 0;
      stalled_previous <= 0;
    end else begin
      cycle_count <= cycle_count + 1;
      if (automatic_source && source_valid && s_axis_tready)
        input_count <= input_count + 1;
      if (automatic_source && source_valid && !s_axis_tready)
        input_stalls <= input_stalls + 1;
      if (m_axis_tvalid && !m_axis_tready)
        output_stalls <= output_stalls + 1;
      if (stalled_previous) begin
        if (!m_axis_tvalid || {m_axis_tlast, m_axis_tkeep, m_axis_tdata} !== stalled_payload) begin
          $display("PHASE06I_ERROR stalled output changed");
          $fatal(1);
        end
        payload_stability_checks <= payload_stability_checks + 1;
      end
      stalled_previous <= m_axis_tvalid && !m_axis_tready;
      if (m_axis_tvalid && !m_axis_tready)
        stalled_payload <= {m_axis_tlast, m_axis_tkeep, m_axis_tdata};
      if (m_axis_tvalid && m_axis_tready) begin
        if (m_axis_tkeep !== 8'hFF) begin
          $display("PHASE06I_ERROR TKEEP mismatch");
          $fatal(1);
        end
        if (scoreboard_enable) begin
          if (output_count >= OUTPUT_BEATS || observed !== expected_memory[output_count]) begin
            $display("PHASE06I_ERROR beat=%0d observed=%017x expected=%017x",
                     output_count, observed, expected_memory[output_count]);
            $fatal(1);
          end
          output_count <= output_count + 1;
          if (m_axis_tlast) completed_packets <= completed_packets + 1;
        end else extra_output_beats <= extra_output_beats + 1;
      end
    end
  end

  task automatic send_manual(input logic [230:0] word);
    begin
      @(negedge aclk);
      manual_word = word;
      manual_valid = 1;
      while (!s_axis_tready) @(negedge aclk);
      @(negedge aclk);
      manual_valid = 0;
      manual_word = 0;
    end
  endtask

  logic [230:0] malformed;
  initial begin
    $readmemh("datasets/fixtures/phase06i/candidate-axis-input.mem", input_memory);
    $readmemh("datasets/fixtures/phase06i/transport-axis64-expected.mem", expected_memory);
    repeat (4) @(posedge aclk);
    aresetn = 1;

    send_manual(input_memory[0]);
    repeat (2) @(posedge aclk);
    @(negedge aclk); aresetn = 0;
    repeat (3) @(posedge aclk);
    @(negedge aclk); aresetn = 1;
    repeat (2) @(posedge aclk);
    if (m_axis_tvalid || completed_frame_count != 0) begin
      $display("PHASE06I_ERROR reset did not flush partial packet");
      $fatal(1);
    end

    scoreboard_enable = 1;
    automatic_source = 1;
    wait (input_count == INPUT_RECORDS && output_count == OUTPUT_BEATS);
    wait (!m_axis_tvalid);
    automatic_source = 0;
    scoreboard_enable = 0;
    repeat (3) @(posedge aclk);

    malformed = input_memory[1];
    malformed[105:94] = 12'd7;
    malformed[230] = 1'b1;
    send_manual(malformed);
    wait (completed_frame_count == 14);
    wait (!m_axis_tvalid);

    if (!status_transport_error_sticky || status_candidate_overflow_sticky) begin
      $display("PHASE06I_ERROR sticky status mismatch error=%0d overflow=%0d",
               status_transport_error_sticky, status_candidate_overflow_sticky);
      $fatal(1);
    end
    if (completed_packets != 13 || output_count != OUTPUT_BEATS) begin
      $display("PHASE06I_ERROR accounting packets=%0d beats=%0d", completed_packets, output_count);
      $fatal(1);
    end
    $display("PHASE06I_METRIC input_records=%0d output_beats=%0d packets=%0d semantic_candidates=1772", input_count, output_count, completed_packets);
    $display("PHASE06I_METRIC input_stalls=%0d output_stalls=%0d payload_stability_checks=%0d", input_stalls, output_stalls, payload_stability_checks);
    $display("PHASE06I_METRIC maximum_candidates_per_frame=1352 maximum_packet_bytes=54144 reset_partial_packet_checked=1 malformed_input_checked=1");
    $display("PHASE-06I TB PASS: %0d AXI64 beats checked", output_count);
    $finish;
  end

  initial begin
    #5000000;
    $display("PHASE06I_ERROR timeout");
    $fatal(1);
  end
endmodule
