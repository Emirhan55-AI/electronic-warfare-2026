`timescale 1ns/1ps

module tb_p0_wideband_recovery;
  localparam int FRAME_COUNT = 5;
  localparam int FRAME_LENGTH = 4096;
  localparam int TOTAL_INPUT_RECORDS = FRAME_COUNT * FRAME_LENGTH;
  localparam int TOTAL_OUTPUT_RECORDS = 24;
  localparam int MAX_PROCESSING_CYCLES = 50000;

  logic aclk = 1'b0;
  logic aresetn = 1'b0;
  logic source_valid = 1'b0;
  logic [70:0] source_word = 71'd0;
  logic median_ready;
  logic recovery_ready;
  logic shared_ready;
  logic shared_valid;
  logic median_valid;
  logic [58:0] region_median_twice [0:15];
  logic [15:0] median_completed_frame_count;
  logic median_frame_error;

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
  logic status_frame_error_sticky;
  logic status_input_range_error_sticky;
  logic status_candidate_overflow_sticky;

  logic [70:0] input_memory [0:TOTAL_INPUT_RECORDS-1];
  logic [230:0] expected_memory [0:TOTAL_OUTPUT_RECORDS-1];
  logic [7:0] expected_record_counts [0:FRAME_COUNT-1];
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

  assign shared_ready = median_ready && recovery_ready;
  assign shared_valid = source_valid && shared_ready;
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

  always_comb begin
    m_axis_tready = ((cycle_count % 11) != 3) && ((cycle_count % 17) != 8);
  end

  p0_parallel_region_median median_i (
    .aclk,
    .aresetn,
    .s_axis_tvalid(shared_valid),
    .s_axis_tready(median_ready),
    .s_axis_tdata(source_word[57:0]),
    .s_axis_tlast(source_word[70]),
    .s_axis_tuser_index(source_word[69:58]),
    .result_valid(median_valid),
    .region_median_twice,
    .completed_frame_count(median_completed_frame_count),
    .status_frame_error_sticky(median_frame_error)
  );

  p0_wideband_recovery dut (
    .aclk,
    .aresetn,
    .s_axis_tvalid(shared_valid),
    .s_axis_tready(recovery_ready),
    .s_axis_tdata(source_word[57:0]),
    .s_axis_tlast(source_word[70]),
    .s_axis_tuser_index(source_word[69:58]),
    .median_valid,
    .region_median_twice,
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
    .status_frame_error_sticky,
    .status_input_range_error_sticky,
    .status_candidate_overflow_sticky
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
          $fatal(1, "Wideband output changed while stalled");
        payload_stability_checks <= payload_stability_checks + 1;
      end
      stalled_previous <= m_axis_tvalid && !m_axis_tready;
      if (m_axis_tvalid && !m_axis_tready)
        stalled_payload <= observed_payload;
      if (m_axis_tvalid && m_axis_tready && output_count < TOTAL_OUTPUT_RECORDS) begin
        if (observed_payload !== expected_memory[output_count])
          $fatal(
            1,
            "Wideband mismatch record=%0d observed=%058x expected=%058x",
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
      source_valid = 1'b1;
      source_word = word;
      while (!shared_ready)
        @(negedge aclk);
      @(negedge aclk);
      source_valid = 1'b0;
      source_word = 71'd0;
    end
  endtask

  logic [70:0] corrupted;
  integer range_output_seen;
  initial begin
    $readmemh("datasets/fixtures/p0_wideband_recovery/axis-power-input.mem", input_memory);
    $readmemh("datasets/fixtures/p0_wideband_recovery/candidate-expected.mem", expected_memory);
    $readmemh(
      "datasets/fixtures/p0_wideband_recovery/expected-record-counts.mem",
      expected_record_counts
    );

    repeat (4) @(posedge aclk);
    aresetn = 1'b1;

    for (frame = 0; frame < FRAME_COUNT; frame = frame + 1) begin
      for (sample = 0; sample < FRAME_LENGTH; sample = sample + 1) begin
        if (((sample + frame) % 37) == 0) begin
          @(negedge aclk);
          source_valid = 1'b0;
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
        $fatal(1, "Wideband processing exceeded cycle budget: %0d", processing_cycles);
    end

    if (output_count != TOTAL_OUTPUT_RECORDS || semantic_candidates != 22)
      $fatal(1, "Wideband accounting mismatch outputs=%0d semantic=%0d", output_count, semantic_candidates);
    if (completed_frame_count != FRAME_COUNT || median_completed_frame_count != FRAME_COUNT)
      $fatal(
        1,
        "Wideband completed-frame mismatch recovery=%0d median=%0d",
        completed_frame_count,
        median_completed_frame_count
      );

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
          $fatal(1, "Out-of-range frame did not fail closed");
        range_output_seen = 1;
      end
    end

    corrupted = input_memory[0];
    corrupted[70] = 1'b1;
    drive_sample(corrupted);
    repeat (4) @(posedge aclk);
    if (!status_input_range_error_sticky || !status_frame_error_sticky || !median_frame_error)
      $fatal(
        1,
        "Wideband sticky status mismatch range=%0d frame=%0d median=%0d",
        status_input_range_error_sticky,
        status_frame_error_sticky,
        median_frame_error
      );
    if (status_candidate_overflow_sticky)
      $fatal(1, "Unexpected wideband candidate overflow");

    $display(
      "P0_WIDEBAND_RECOVERY_PASS frames=%0d records=%0d semantic=%0d max_processing_cycles=%0d stability_checks=%0d",
      FRAME_COUNT,
      TOTAL_OUTPUT_RECORDS,
      semantic_candidates,
      maximum_processing_cycles,
      payload_stability_checks
    );
    $finish;
  end

  initial begin
    #20000000;
    $fatal(1, "P0 wideband recovery timeout");
  end
endmodule
