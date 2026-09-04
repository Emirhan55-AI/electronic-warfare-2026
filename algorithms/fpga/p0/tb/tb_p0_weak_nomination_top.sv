`timescale 1ns/1ps

module tb_p0_weak_nomination_top;
  localparam int FRAME_LENGTH = 4096;
  logic aclk = 1'b0;
  logic aresetn = 1'b0;
  always #5 aclk = ~aclk;
  logic s_valid;
  wire s_ready;
  logic [57:0] s_data;
  logic s_last;
  logic [11:0] s_index;
  wire m_valid;
  logic m_ready;
  wire [57:0] m_data;
  wire m_last;
  wire [11:0] m_start;
  wire [11:0] m_end;
  wire [11:0] m_peak;
  wire [57:0] m_noise;
  wire [61:0] m_threshold;
  wire [1:0] m_pfa;
  wire m_center;
  wire m_weak;
  wire m_strong;
  wire m_candidate_valid;
  wire [15:0] completed;
  wire [1:0] status;
  integer input_index;
  integer candidates;
  logic [221:0] stalled_payload;
  logic stalled;

  p0_weak_nomination_top dut (
    .aclk, .aresetn,
    .s_axis_tvalid(s_valid), .s_axis_tready(s_ready),
    .s_axis_tdata(s_data), .s_axis_tlast(s_last),
    .s_axis_tuser_index(s_index),
    .m_axis_tvalid(m_valid), .m_axis_tready(m_ready),
    .m_axis_tdata(m_data), .m_axis_tlast(m_last),
    .m_axis_tuser_start_shifted_bin(m_start),
    .m_axis_tuser_end_shifted_bin(m_end),
    .m_axis_tuser_peak_shifted_bin(m_peak),
    .m_axis_tuser_order_statistic(m_noise),
    .m_axis_tuser_threshold(m_threshold),
    .m_axis_tuser_pfa_select(m_pfa),
    .m_axis_tuser_evaluate_center(m_center),
    .m_axis_tuser_weak_evidence(m_weak),
    .m_axis_tuser_single_frame_confident(m_strong),
    .m_axis_tuser_candidate_valid(m_candidate_valid),
    .completed_frame_count(completed), .status_sticky(status)
  );

  always @(posedge aclk) begin
    if (aresetn) begin
      m_ready <= ($time % 70) != 0;
      if (stalled && (!m_valid || {m_last, m_candidate_valid, m_start, m_end,
                                   m_peak, m_data, m_noise} !== stalled_payload)) begin
        $display("WEAK_GROUP_ERROR stalled payload changed");
        $fatal(1);
      end
      stalled <= m_valid && !m_ready;
      if (m_valid && !m_ready)
        stalled_payload <= {m_last, m_candidate_valid, m_start, m_end,
                            m_peak, m_data, m_noise};
      if (m_valid && m_ready && m_candidate_valid) begin
        if (candidates == 0 && (m_start != 1000 || m_end != 1000 || m_peak != 1000 ||
                                !m_weak || m_strong))
          $fatal(1, "WEAK_GROUP_ERROR first candidate");
        if (candidates == 1 && (m_start != 3000 || m_end != 3000 || m_peak != 3000 ||
                                !m_weak || !m_strong))
          $fatal(1, "WEAK_GROUP_ERROR second candidate");
        candidates <= candidates + 1;
      end
    end
  end

  initial begin
    s_valid = 0;
    s_data = 0;
    s_last = 0;
    s_index = 0;
    m_ready = 1;
    candidates = 0;
    stalled = 0;
    stalled_payload = 0;
    repeat (4) @(posedge aclk);
    @(negedge aclk);
    aresetn = 1;
    for (input_index = 0; input_index < FRAME_LENGTH; input_index = input_index + 1) begin
      @(negedge aclk);
      s_valid = 1;
      s_index = input_index[11:0];
      s_last = input_index == FRAME_LENGTH - 1;
      if (input_index == (1000 ^ 12'h800))
        s_data = 58'd5368709120;
      else if (input_index == (3000 ^ 12'h800))
        s_data = 58'd10737418240;
      else
        s_data = 58'd1073741824;
      do @(posedge aclk); while (!s_ready);
    end
    @(negedge aclk);
    s_valid = 0;
    wait (completed == 1);
    repeat (3) @(posedge aclk);
    if (status != 0 || candidates != 2)
      $fatal(1, "WEAK_GROUP_ERROR status=%0d candidates=%0d", status, candidates);
    $display("P0 WEAK NOMINATION TOP PASS candidates=%0d", candidates);
    $finish;
  end

  initial begin
    #10000000;
    $fatal(1, "WEAK_GROUP_ERROR timeout");
  end
endmodule
