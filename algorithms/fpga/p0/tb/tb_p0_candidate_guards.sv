`timescale 1ns/1ps

module tb_p0_candidate_guards;
  localparam int MAXIMUM_OS_CANDIDATES = 1352;

  logic aclk = 1'b0;
  logic aresetn = 1'b0;
  always #5 aclk = ~aclk;

  logic group_s_valid = 1'b0;
  logic group_s_ready;
  logic [57:0] group_s_power = 58'd0;
  logic group_s_last = 1'b0;
  logic [11:0] group_s_index = 12'd0;
  logic [57:0] group_s_noise = 58'd0;
  logic group_s_detected = 1'b0;
  logic group_m_valid;
  logic [57:0] group_m_power;
  logic group_m_last;
  logic [11:0] group_m_start;
  logic [11:0] group_m_end;
  logic [11:0] group_m_peak;
  logic [11:0] group_m_span;
  logic [57:0] group_m_noise;
  logic [61:0] group_m_threshold;
  logic [1:0] group_m_pfa;
  logic group_m_evaluate_center;
  logic group_m_candidate_valid;
  logic [15:0] group_completed;
  logic group_frame_error;
  logic group_overflow;
  integer group_output_count = 0;

  p0_os_candidate_grouping grouping_i (
    .aclk,
    .aresetn,
    .s_axis_tvalid(group_s_valid),
    .s_axis_tready(group_s_ready),
    .s_axis_tdata(group_s_power),
    .s_axis_tlast(group_s_last),
    .s_axis_tuser_shifted_index(group_s_index),
    .s_axis_tuser_order_statistic(group_s_noise),
    .s_axis_tuser_detected(group_s_detected),
    .m_axis_tvalid(group_m_valid),
    .m_axis_tready(1'b1),
    .m_axis_tdata(group_m_power),
    .m_axis_tlast(group_m_last),
    .m_axis_tuser_start_shifted_bin(group_m_start),
    .m_axis_tuser_end_shifted_bin(group_m_end),
    .m_axis_tuser_peak_shifted_bin(group_m_peak),
    .m_axis_tuser_coarse_span_bins(group_m_span),
    .m_axis_tuser_noise(group_m_noise),
    .m_axis_tuser_threshold(group_m_threshold),
    .m_axis_tuser_pfa_select(group_m_pfa),
    .m_axis_tuser_evaluate_center(group_m_evaluate_center),
    .m_axis_tuser_candidate_valid(group_m_candidate_valid),
    .completed_frame_count(group_completed),
    .status_frame_error_sticky(group_frame_error),
    .status_candidate_overflow_sticky(group_overflow)
  );

  always @(posedge aclk) begin
    if (group_m_valid) begin
      if (!group_m_candidate_valid || group_m_start != 20 + group_output_count * 3 ||
          group_m_end != group_m_start || group_m_peak != group_m_start ||
          group_m_span != 12'd1 || group_m_power != group_m_start + 1000 ||
          group_m_noise != group_m_start + 500 || group_m_pfa != 2'd1 ||
          group_m_evaluate_center ||
          group_m_last != (group_output_count == MAXIMUM_OS_CANDIDATES - 1))
        $fatal(1, "OS candidate capacity record mismatch: %0d", group_output_count);
      group_output_count <= group_output_count + 1;
    end
  end

  task automatic drive_group_cell(input integer index);
    begin
      @(negedge aclk);
      group_s_valid = 1'b1;
      group_s_power = index + 1000;
      group_s_last = index == 4075;
      group_s_index = index;
      group_s_noise = index + 500;
      group_s_detected = ((index - 20) % 3) == 0;
      while (!group_s_ready)
        @(negedge aclk);
      @(negedge aclk);
      group_s_valid = 1'b0;
      group_s_last = 1'b0;
    end
  endtask

  logic fusion_os_valid = 1'b0;
  logic fusion_os_ready;
  logic [57:0] fusion_os_power = 58'd0;
  logic fusion_os_last = 1'b0;
  logic [11:0] fusion_os_start = 12'd0;
  logic fusion_recovery_valid = 1'b0;
  logic fusion_recovery_ready;
  logic fusion_recovery_last = 1'b0;
  logic fusion_m_valid;
  logic fusion_m_last;
  logic fusion_m_candidate_valid;
  logic [15:0] fusion_completed;
  logic fusion_input_error;
  logic fusion_overflow;

  p0_candidate_fusion fusion_i (
    .aclk,
    .aresetn,
    .s_os_tvalid(fusion_os_valid),
    .s_os_tready(fusion_os_ready),
    .s_os_tdata(fusion_os_power),
    .s_os_tlast(fusion_os_last),
    .s_os_start(fusion_os_start),
    .s_os_end(fusion_os_start),
    .s_os_peak(fusion_os_start),
    .s_os_noise(58'd100),
    .s_os_threshold(62'd200),
    .s_os_pfa_select(2'd1),
    .s_os_evaluate_center(1'b0),
    .s_os_weak_evidence(1'b0),
    .s_os_single_frame_confident(1'b0),
    .s_os_candidate_valid(1'b1),
    .s_recovery_tvalid(fusion_recovery_valid),
    .s_recovery_tready(fusion_recovery_ready),
    .s_recovery_tdata(58'd300),
    .s_recovery_tlast(fusion_recovery_last),
    .s_recovery_start(12'd4095),
    .s_recovery_end(12'd4095),
    .s_recovery_peak(12'd4095),
    .s_recovery_noise(58'd100),
    .s_recovery_threshold(62'd200),
    .s_recovery_pfa_select(2'd1),
    .s_recovery_evaluate_center(1'b0),
    .s_recovery_candidate_valid(1'b1),
    .s_recovery_frame_invalid(1'b0),
    .m_axis_tvalid(fusion_m_valid),
    .m_axis_tready(1'b1),
    .m_axis_tdata(),
    .m_axis_tlast(fusion_m_last),
    .m_axis_tuser_start_shifted_bin(),
    .m_axis_tuser_end_shifted_bin(),
    .m_axis_tuser_peak_shifted_bin(),
    .m_axis_tuser_coarse_span_bins(),
    .m_axis_tuser_noise(),
    .m_axis_tuser_threshold(),
    .m_axis_tuser_pfa_select(),
    .m_axis_tuser_evaluate_center(),
    .m_axis_tuser_weak_evidence(),
    .m_axis_tuser_single_frame_confident(),
    .m_axis_tuser_candidate_valid(fusion_m_candidate_valid),
    .completed_frame_count(fusion_completed),
    .status_input_error_sticky(fusion_input_error),
    .status_candidate_overflow_sticky(fusion_overflow)
  );

  task automatic drive_fusion_os(input integer candidate_index);
    begin
      @(negedge aclk);
      fusion_os_valid = 1'b1;
      fusion_os_power = candidate_index + 100;
      fusion_os_start = candidate_index * 3;
      fusion_os_last = candidate_index == MAXIMUM_OS_CANDIDATES - 1;
      while (!fusion_os_ready)
        @(negedge aclk);
      @(negedge aclk);
      fusion_os_valid = 1'b0;
      fusion_os_last = 1'b0;
    end
  endtask

  task automatic drive_fusion_recovery(input integer candidate_index);
    begin
      @(negedge aclk);
      fusion_recovery_valid = 1'b1;
      fusion_recovery_last = candidate_index == 95;
      while (!fusion_recovery_ready)
        @(negedge aclk);
      @(negedge aclk);
      fusion_recovery_valid = 1'b0;
      fusion_recovery_last = 1'b0;
    end
  endtask

  integer index;
  initial begin
    repeat (4) @(posedge aclk);
    aresetn = 1'b1;

    for (index = 20; index <= 4075; index = index + 1)
      drive_group_cell(index);
    wait (group_completed == 1);
    if (group_output_count != MAXIMUM_OS_CANDIDATES || group_frame_error || group_overflow)
      $fatal(
        1,
        "OS candidate capacity mismatch count=%0d frame=%0d overflow=%0d",
        group_output_count,
        group_frame_error,
        group_overflow
      );

    for (index = 0; index < MAXIMUM_OS_CANDIDATES; index = index + 1)
      drive_fusion_os(index);
    for (index = 0; index < 96; index = index + 1)
      drive_fusion_recovery(index);
    wait (fusion_m_valid);
    if (fusion_m_candidate_valid || !fusion_m_last || !fusion_overflow || fusion_input_error)
      $fatal(
        1,
        "Fusion overflow policy mismatch valid=%0d last=%0d overflow=%0d input=%0d",
        fusion_m_candidate_valid,
        fusion_m_last,
        fusion_overflow,
        fusion_input_error
      );
    @(posedge aclk);
    #1;
    if (fusion_completed != 1)
      $fatal(1, "Fusion overflow frame did not complete");

    $display(
      "P0_CANDIDATE_GUARDS_PASS os_records=%0d fusion_overflow=%0d",
      group_output_count,
      fusion_overflow
    );
    $finish;
  end

  initial begin
    #10000000;
    $fatal(1, "P0 candidate guard timeout");
  end
endmodule
