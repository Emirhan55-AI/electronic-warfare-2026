`timescale 1ns/1ps

module tb_axis_candidate_grouping;
  localparam int FRAME_LENGTH = 4096;
  localparam int TOTAL_INPUT_RECORDS = 53248;
  localparam int TOTAL_OUTPUT_RECORDS = 1773;

  logic aclk = 1'b0;
  always #5 aclk = ~aclk;
  logic aresetn = 1'b0;

  logic [266:0] input_memory [0:TOTAL_INPUT_RECORDS-1];
  logic [230:0] expected_memory [0:TOTAL_OUTPUT_RECORDS-1];
  integer input_count = 0;
  integer output_count = 0;
  integer cycle_count = 0;
  integer input_stalls = 0;
  integer output_stalls = 0;
  integer payload_stability_checks = 0;
  integer semantic_candidates = 0;
  integer current_frame_records = 0;
  integer maximum_candidate_count = 0;
  integer completed_frames = 0;
  integer first_frame_last_cycle = -1;
  integer first_output_cycle = -1;
  integer malformed_output_count = 0;

  logic automatic_source = 1'b0;
  logic scoreboard_enable = 1'b0;
  logic manual_valid = 1'b0;
  logic [266:0] manual_word = '0;
  wire [266:0] source_word = automatic_source ?
      ((input_count < TOTAL_INPUT_RECORDS) ? input_memory[input_count] : 267'd0) : manual_word;
  wire source_valid = automatic_source ? (input_count < TOTAL_INPUT_RECORDS) : manual_valid;

  wire s_axis_tready;
  wire m_axis_tvalid;
  logic m_axis_tready;
  wire [57:0] m_axis_tdata;
  wire m_axis_tlast;
  wire [11:0] m_axis_tuser_start_shifted_bin;
  wire [11:0] m_axis_tuser_end_shifted_bin;
  wire [11:0] m_axis_tuser_peak_shifted_bin;
  wire [11:0] m_axis_tuser_coarse_span_bins;
  wire [57:0] m_axis_tuser_noise;
  wire [61:0] m_axis_tuser_threshold;
  wire [1:0] m_axis_tuser_pfa_select;
  wire m_axis_tuser_evaluate_center;
  wire m_axis_tuser_candidate_valid;
  wire status_frame_error_sticky;
  wire status_candidate_overflow_sticky;

  wire [230:0] observed_payload = {
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
  logic stalled_previous = 1'b0;
  logic [230:0] stalled_payload = '0;

  axis_candidate_grouping dut (
    .aclk,
    .aresetn,
    .s_axis_tvalid(source_valid),
    .s_axis_tready,
    .s_axis_tdata(source_word[57:0]),
    .s_axis_tlast(source_word[266]),
    .s_axis_tuser_natural_index(source_word[69:58]),
    .s_axis_tuser_shifted_index(source_word[81:70]),
    .s_axis_tuser_median_twice(source_word[140:82]),
    .s_axis_tuser_noise(source_word[198:141]),
    .s_axis_tuser_threshold(source_word[260:199]),
    .s_axis_tuser_evaluated(source_word[261]),
    .s_axis_tuser_detected(source_word[262]),
    .s_axis_tuser_pfa_select(source_word[264:263]),
    .s_axis_tuser_evaluate_center(source_word[265]),
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
    .status_frame_error_sticky,
    .status_candidate_overflow_sticky
  );

  always_comb begin
    m_axis_tready = ((cycle_count % 11) != 3) && ((cycle_count % 17) != 8);
  end

  always @(posedge aclk) begin
    if (!aresetn) begin
      input_count <= 0;
      output_count <= 0;
      cycle_count <= 0;
      input_stalls <= 0;
      output_stalls <= 0;
      payload_stability_checks <= 0;
      semantic_candidates <= 0;
      current_frame_records <= 0;
      maximum_candidate_count <= 0;
      completed_frames <= 0;
      first_frame_last_cycle <= -1;
      first_output_cycle <= -1;
      malformed_output_count <= 0;
      stalled_previous <= 1'b0;
    end else begin
      cycle_count <= cycle_count + 1;
      if (automatic_source && source_valid && s_axis_tready) begin
        if (input_count == FRAME_LENGTH - 1)
          first_frame_last_cycle <= cycle_count;
        input_count <= input_count + 1;
      end
      if (automatic_source && source_valid && !s_axis_tready)
        input_stalls <= input_stalls + 1;
      if (m_axis_tvalid && !m_axis_tready)
        output_stalls <= output_stalls + 1;

      if (stalled_previous) begin
        if (!m_axis_tvalid || observed_payload !== stalled_payload) begin
          $display("PHASE06H_ERROR stalled payload changed");
          $fatal(1);
        end
        payload_stability_checks <= payload_stability_checks + 1;
      end
      stalled_previous <= m_axis_tvalid && !m_axis_tready;
      if (m_axis_tvalid && !m_axis_tready)
        stalled_payload <= observed_payload;

      if (m_axis_tvalid && m_axis_tready) begin
        if (scoreboard_enable) begin
          if (first_output_cycle < 0)
            first_output_cycle <= cycle_count;
          if (output_count >= TOTAL_OUTPUT_RECORDS || observed_payload !== expected_memory[output_count]) begin
            $display("PHASE06H_ERROR mismatch result=%0d observed=%058x expected=%058x",
                     output_count, observed_payload, expected_memory[output_count]);
            $fatal(1);
          end
          output_count <= output_count + 1;
          current_frame_records <= current_frame_records + (m_axis_tuser_candidate_valid ? 1 : 0);
          if (m_axis_tuser_candidate_valid)
            semantic_candidates <= semantic_candidates + 1;
          if (m_axis_tlast) begin
            if (current_frame_records + (m_axis_tuser_candidate_valid ? 1 : 0) > maximum_candidate_count)
              maximum_candidate_count <= current_frame_records + (m_axis_tuser_candidate_valid ? 1 : 0);
            current_frame_records <= 0;
            completed_frames <= completed_frames + 1;
          end
        end else begin
          malformed_output_count <= malformed_output_count + 1;
        end
      end
    end
  end

  task automatic send_manual(input logic [266:0] word);
    begin
      @(negedge aclk);
      manual_word = word;
      manual_valid = 1'b1;
      while (!s_axis_tready)
        @(negedge aclk);
      @(negedge aclk);
      manual_valid = 1'b0;
      manual_word = '0;
    end
  endtask

  integer index;
  logic [266:0] corrupted;
  initial begin
    $readmemh("datasets/fixtures/phase06h/axis-detector-input.mem", input_memory);
    $readmemh("datasets/fixtures/phase06h/candidate-expected.mem", expected_memory);

    repeat (4) @(posedge aclk);
    aresetn = 1'b1;

    for (index = 0; index < 9; index = index + 1)
      send_manual(input_memory[FRAME_LENGTH + index]);
    @(negedge aclk);
    aresetn = 1'b0;
    repeat (3) @(posedge aclk);
    aresetn = 1'b1;
    repeat (2) @(posedge aclk);
    if (m_axis_tvalid) begin
      $display("PHASE06H_ERROR reset did not flush partial frame");
      $fatal(1);
    end

    scoreboard_enable = 1'b1;
    automatic_source = 1'b1;
    wait (input_count == TOTAL_INPUT_RECORDS && output_count == TOTAL_OUTPUT_RECORDS);
    wait (!m_axis_tvalid);
    automatic_source = 1'b0;
    scoreboard_enable = 1'b0;
    repeat (3) @(posedge aclk);

    corrupted = input_memory[4];
    corrupted[266] = 1'b1;
    for (index = 0; index < 4; index = index + 1)
      send_manual(input_memory[index]);
    send_manual(corrupted);

    for (index = 0; index < FRAME_LENGTH; index = index + 1) begin
      corrupted = input_memory[FRAME_LENGTH + index];
      if (index == FRAME_LENGTH - 1)
        corrupted[266] = 1'b0;
      send_manual(corrupted);
    end
    send_manual(input_memory[FRAME_LENGTH - 1]);
    repeat (10) @(posedge aclk);

    if (!status_frame_error_sticky || status_candidate_overflow_sticky || malformed_output_count != 0) begin
      $display("PHASE06H_ERROR malformed/reset status mismatch frame_error=%0d overflow=%0d outputs=%0d",
               status_frame_error_sticky, status_candidate_overflow_sticky, malformed_output_count);
      $fatal(1);
    end
    if (completed_frames != 13 || semantic_candidates != 1772 || maximum_candidate_count != 1352) begin
      $display("PHASE06H_ERROR accounting frames=%0d semantic=%0d maximum=%0d",
               completed_frames, semantic_candidates, maximum_candidate_count);
      $fatal(1);
    end
    $display("PHASE06H_METRIC last_input_to_first_output_cycles=%0d",
             first_output_cycle - first_frame_last_cycle);
    $display("PHASE06H_METRIC input_records=%0d output_records=%0d semantic_candidates=%0d maximum_candidates_per_frame=%0d",
             input_count, output_count, semantic_candidates, maximum_candidate_count);
    $display("PHASE06H_METRIC input_stalls=%0d output_stalls=%0d payload_stability_checks=%0d",
             input_stalls, output_stalls, payload_stability_checks);
    $display("PHASE06H_METRIC malformed_frames_checked=3 reset_partial_frame_checked=1 frame_error_sticky=1 overflow_sticky=0");
    $display("PHASE-06H TB PASS: %0d candidate records checked", output_count);
    $finish;
  end

  initial begin
    #30000000;
    $display("PHASE06H_ERROR timeout");
    $fatal(1);
  end
endmodule
