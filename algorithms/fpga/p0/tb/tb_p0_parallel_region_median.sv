`timescale 1ns/1ps

module tb_p0_parallel_region_median;
  localparam int FRAME_COUNT = 5;
  localparam int FRAME_LENGTH = 4096;
  localparam int REGION_COUNT = 16;
  localparam int TOTAL_SAMPLES = FRAME_COUNT * FRAME_LENGTH;
  localparam int MAX_PROCESSING_CYCLES = 30000;

  logic aclk = 1'b0;
  logic aresetn = 1'b0;
  logic s_axis_tvalid = 1'b0;
  logic s_axis_tready;
  logic [57:0] s_axis_tdata = '0;
  logic s_axis_tlast = 1'b0;
  logic [11:0] s_axis_tuser_index = '0;
  logic result_valid;
  logic [58:0] region_median_twice [0:REGION_COUNT-1];
  logic [15:0] completed_frame_count;
  logic status_frame_error_sticky;

  logic [70:0] input_memory [0:TOTAL_SAMPLES-1];
  logic [58:0] expected_memory [0:FRAME_COUNT*REGION_COUNT-1];
  integer cycle_count = 0;
  integer maximum_processing_cycles = 0;
  integer frame;
  integer sample;
  integer region;
  integer processing_started;
  integer processing_cycles;

  always #5 aclk = ~aclk;
  always @(posedge aclk) cycle_count <= cycle_count + 1;

  p0_parallel_region_median dut (
    .aclk(aclk),
    .aresetn(aresetn),
    .s_axis_tvalid(s_axis_tvalid),
    .s_axis_tready(s_axis_tready),
    .s_axis_tdata(s_axis_tdata),
    .s_axis_tlast(s_axis_tlast),
    .s_axis_tuser_index(s_axis_tuser_index),
    .result_valid(result_valid),
    .region_median_twice(region_median_twice),
    .completed_frame_count(completed_frame_count),
    .status_frame_error_sticky(status_frame_error_sticky)
  );

  task automatic drive_sample(input logic [70:0] word);
    begin
      @(negedge aclk);
      s_axis_tvalid = 1'b1;
      s_axis_tdata = word[57:0];
      s_axis_tuser_index = word[69:58];
      s_axis_tlast = word[70];
      do @(posedge aclk); while (!s_axis_tready);
      @(negedge aclk);
      s_axis_tvalid = 1'b0;
      s_axis_tlast = 1'b0;
    end
  endtask

  initial begin
    $readmemh("datasets/fixtures/p0_candidate_reducer/axis-power-input.mem", input_memory);
    $readmemh(
      "datasets/fixtures/p0_candidate_reducer/region-median-twice-expected.mem",
      expected_memory
    );

    repeat (4) @(posedge aclk);
    aresetn = 1'b1;

    for (frame = 0; frame < FRAME_COUNT; frame = frame + 1) begin
      for (sample = 0; sample < FRAME_LENGTH; sample = sample + 1) begin
        if (((sample + frame) % 31) == 0) begin
          @(negedge aclk);
          s_axis_tvalid = 1'b0;
          @(posedge aclk);
        end
        drive_sample(input_memory[frame * FRAME_LENGTH + sample]);
      end
      processing_started = cycle_count;
      while (!result_valid) @(posedge aclk);
      #1;
      processing_cycles = cycle_count - processing_started;
      if (processing_cycles > maximum_processing_cycles)
        maximum_processing_cycles = processing_cycles;
      if (processing_cycles > MAX_PROCESSING_CYCLES)
        $fatal(1, "Median processing exceeded cycle budget: %0d", processing_cycles);
      for (region = 0; region < REGION_COUNT; region = region + 1) begin
        if (region_median_twice[region] !== expected_memory[frame * REGION_COUNT + region])
          $fatal(
            1,
            "Median mismatch frame=%0d region=%0d observed=%h expected=%h",
            frame,
            region,
            region_median_twice[region],
            expected_memory[frame * REGION_COUNT + region]
          );
      end
      if (completed_frame_count != frame + 1)
        $fatal(1, "Completed frame count mismatch: %0d", completed_frame_count);
      @(posedge aclk);
    end

    drive_sample({1'b1, 12'd0, 58'd1});
    @(posedge aclk);
    if (!status_frame_error_sticky)
      $fatal(1, "Malformed frame did not set the sticky error");

    $display(
      "P0_PARALLEL_MEDIAN_PASS frames=%0d max_processing_cycles=%0d",
      FRAME_COUNT,
      maximum_processing_cycles
    );
    $finish;
  end
endmodule
