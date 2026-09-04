`timescale 1ns/1ps

module tb_p0_candidate_reducer;
  localparam int FRAME_COUNT = 8;
  localparam int FRAME_LENGTH = 4096;
  localparam int TOTAL_INPUT_RECORDS = FRAME_COUNT * FRAME_LENGTH;
  localparam int TOTAL_OUTPUT_RECORDS = 115;
  localparam int MAX_PROCESSING_CYCLES = 50000;

  logic aclk = 1'b0;
  logic aresetn = 1'b0;
  logic s_axis_tvalid = 1'b0;
  logic s_axis_tready;
  logic [57:0] s_axis_tdata = 58'd0;
  logic s_axis_tlast = 1'b0;
  logic [11:0] s_axis_tuser_index = 12'd0;
  logic m_axis_tvalid;
  logic m_axis_tready;
  logic [57:0] m_axis_tdata;
  logic m_axis_tlast;
  logic [11:0] m_axis_tuser_start_shifted_bin;
  logic [11:0] m_axis_tuser_end_shifted_bin;
  logic [11:0] m_axis_tuser_peak_shifted_bin;
  logic [11:0] m_axis_tuser_coarse_span_bins;
  logic [57:0] m_axis_tuser_noise;
  logic [61:0] m_axis_tuser_threshold;
  logic [1:0] m_axis_tuser_pfa_select;
  logic m_axis_tuser_evaluate_center;
  logic m_axis_tuser_candidate_valid;
  logic [15:0] completed_frame_count;
  logic [8:0] status_sticky;

  logic [70:0] input_memory [0:TOTAL_INPUT_RECORDS-1];
  logic [230:0] expected_memory [0:TOTAL_OUTPUT_RECORDS-1];
  logic [15:0] expected_record_counts [0:FRAME_COUNT-1];
  logic [230:0] observed_payload;
  logic [230:0] stalled_payload = 231'd0;
  logic stalled_previous = 1'b0;
  integer cycle_count = 0;
  integer output_count = 0;
  integer semantic_candidates = 0;
  integer payload_stability_checks = 0;
  integer maximum_processing_cycles = 0;
  integer processing_start;
  integer processing_cycles;
  integer expected_frame_output;
  integer frame;
  integer sample;

  always #5 aclk = ~aclk;
  always @(posedge aclk) cycle_count <= cycle_count + 1;
  always_comb m_axis_tready = ((cycle_count % 11) != 3) && ((cycle_count % 17) != 8);

  assign observed_payload = {
    m_axis_tlast,
    m_axis_tuser_candidate_valid,
    m_axis_tuser_evaluate_center,
    m_axis_tuser_pfa_select,
    m_axis_tuser_threshold,
    m_axis_tuser_noise,
    m_axis_tuser_coarse_span_bins,
    m_axis_tuser_peak_shifted_bin,
    m_axis_tuser_end_shifted_bin,
    m_axis_tuser_start_shifted_bin,
    m_axis_tdata
  };

  p0_candidate_reducer_top dut (
    .aclk,
    .aresetn,
    .s_axis_tvalid,
    .s_axis_tready,
    .s_axis_tdata,
    .s_axis_tlast,
    .s_axis_tuser_index,
    .m_axis_tvalid,
    .m_axis_tready,
    .m_axis_tdata,
    .m_axis_tlast,
    .m_axis_tuser_start_shifted_bin,
    .m_axis_tuser_end_shifted_bin,
    .m_axis_tuser_peak_shifted_bin,
    .m_axis_tuser_coarse_span_bins,
    .m_axis_tuser_noise,
    .m_axis_tuser_threshold,
    .m_axis_tuser_pfa_select,
    .m_axis_tuser_evaluate_center,
    .m_axis_tuser_candidate_valid,
    .completed_frame_count,
    .status_sticky
  );

  always @(posedge aclk) begin
    if (!aresetn) begin
      output_count <= 0;
      semantic_candidates <= 0;
      payload_stability_checks <= 0;
      stalled_previous <= 1'b0;
    end else begin
      if (stalled_previous) begin
        if (!m_axis_tvalid || observed_payload !== stalled_payload)
          $fatal(1, "Final candidate output changed while stalled");
        payload_stability_checks <= payload_stability_checks + 1;
      end
      stalled_previous <= m_axis_tvalid && !m_axis_tready;
      if (m_axis_tvalid && !m_axis_tready)
        stalled_payload <= observed_payload;
      if (m_axis_tvalid && m_axis_tready && output_count < TOTAL_OUTPUT_RECORDS) begin
        if (observed_payload !== expected_memory[output_count])
          $fatal(
            1,
            "Final candidate mismatch record=%0d observed=%058x expected=%058x",
            output_count,
            observed_payload,
            expected_memory[output_count]
          );
        output_count <= output_count + 1;
        if (m_axis_tuser_candidate_valid)
          semantic_candidates <= semantic_candidates + 1;
      end
    end
  end

  task automatic drive_sample(input logic [70:0] word);
    begin
      @(negedge aclk);
      s_axis_tvalid = 1'b1;
      s_axis_tdata = word[57:0];
      s_axis_tuser_index = word[69:58];
      s_axis_tlast = word[70];
      while (!s_axis_tready)
        @(negedge aclk);
      @(negedge aclk);
      s_axis_tvalid = 1'b0;
      s_axis_tlast = 1'b0;
    end
  endtask

  logic [70:0] corrupted;
  integer range_output_seen;
  initial begin
    $readmemh("datasets/fixtures/p0_wideband_recovery/axis-power-input.mem", input_memory);
    $readmemh("datasets/fixtures/p0_final_candidate/candidate-expected.mem", expected_memory);
    $readmemh(
      "datasets/fixtures/p0_final_candidate/expected-record-counts.mem",
      expected_record_counts
    );
    repeat (4) @(posedge aclk);
    aresetn = 1'b1;

    for (frame = 0; frame < FRAME_COUNT; frame = frame + 1) begin
      for (sample = 0; sample < FRAME_LENGTH; sample = sample + 1) begin
        if (((sample + frame) % 43) == 0) begin
          @(negedge aclk);
          s_axis_tvalid = 1'b0;
        end
        drive_sample(input_memory[frame * FRAME_LENGTH + sample]);
      end
      processing_start = cycle_count;
      expected_frame_output = output_count + expected_record_counts[frame];
      wait (output_count == expected_frame_output);
      processing_cycles = cycle_count - processing_start;
      if (processing_cycles > maximum_processing_cycles)
        maximum_processing_cycles = processing_cycles;
      if (processing_cycles > MAX_PROCESSING_CYCLES)
        $fatal(1, "Final candidate processing exceeded cycle budget: %0d", processing_cycles);
    end

    if (output_count != TOTAL_OUTPUT_RECORDS || semantic_candidates != 113)
      $fatal(1, "Final candidate accounting mismatch outputs=%0d semantic=%0d", output_count, semantic_candidates);
    if (completed_frame_count != FRAME_COUNT || status_sticky != 9'd0)
      $fatal(1, "Final candidate completion/status mismatch count=%0d status=%b", completed_frame_count, status_sticky);

    range_output_seen = 0;
    for (sample = 0; sample < FRAME_LENGTH; sample = sample + 1) begin
      corrupted = input_memory[sample];
      if (sample == 0)
        corrupted[57:0] = 58'h200000000000001;
      drive_sample(corrupted);
    end
    while (!range_output_seen) begin
      @(posedge aclk);
      if (m_axis_tvalid && m_axis_tready) begin
        if (m_axis_tuser_candidate_valid || !m_axis_tlast)
          $fatal(1, "Out-of-range final frame did not fail closed");
        range_output_seen = 1;
      end
    end

    corrupted = input_memory[0];
    corrupted[70] = 1'b1;
    drive_sample(corrupted);
    repeat (4) @(posedge aclk);
    if (status_sticky != 9'b000011101)
      $fatal(1, "Final candidate malformed status mismatch: %b", status_sticky);

    $display(
      "P0_FINAL_CANDIDATE_PASS frames=%0d records=%0d semantic=%0d max_processing_cycles=%0d stability_checks=%0d",
      FRAME_COUNT,
      TOTAL_OUTPUT_RECORDS,
      semantic_candidates,
      maximum_processing_cycles,
      payload_stability_checks
    );
    $finish;
  end

  initial begin
    #30000000;
    $fatal(1, "P0 final candidate reducer timeout");
  end
endmodule
