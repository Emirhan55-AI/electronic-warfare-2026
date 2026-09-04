`timescale 1ns/1ps

module tb_axis_candidate_packetizer_classes;
  logic aclk = 1'b0;
  logic aresetn = 1'b0;
  always #5 aclk = ~aclk;
  logic s_valid = 1'b0;
  wire s_ready;
  logic s_last = 1'b0;
  logic s_weak = 1'b0;
  logic s_strong = 1'b0;
  wire m_valid;
  logic m_ready = 1'b1;
  wire [63:0] m_data;
  wire [7:0] m_keep;
  wire m_last;
  integer beat = 0;

  axis_candidate_packetizer dut (
    .aclk, .aresetn,
    .s_axis_tvalid(s_valid), .s_axis_tready(s_ready),
    .s_axis_tdata(58'd5368709120), .s_axis_tlast(s_last),
    .s_axis_tuser_start_shifted_bin(s_strong ? 12'd200 : 12'd100),
    .s_axis_tuser_end_shifted_bin(s_strong ? 12'd200 : 12'd100),
    .s_axis_tuser_peak_shifted_bin(s_strong ? 12'd200 : 12'd100),
    .s_axis_tuser_coarse_span_bins(12'd1),
    .s_axis_tuser_noise(58'd1073741824),
    .s_axis_tuser_threshold(s_strong ? 62'd9212858439 : 62'd4274643195),
    .s_axis_tuser_pfa_select(2'd1),
    .s_axis_tuser_evaluate_center(1'b0),
    .s_axis_tuser_weak_evidence(s_weak),
    .s_axis_tuser_single_frame_confident(s_strong),
    .s_axis_tuser_candidate_valid(1'b1),
    .m_axis_tvalid(m_valid), .m_axis_tready(m_ready),
    .m_axis_tdata(m_data), .m_axis_tkeep(m_keep), .m_axis_tlast(m_last),
    .completed_frame_count(), .status_transport_error_sticky(),
    .status_candidate_overflow_sticky()
  );

  always @(posedge aclk) begin
    if (aresetn && m_valid && m_ready) begin
      if (beat == 5 && m_data[15:8] != 8'h05)
        $fatal(1, "PACKET_CLASS_ERROR weak flags=%02x", m_data[15:8]);
      if (beat == 10 && m_data[15:8] != 8'h0d)
        $fatal(1, "PACKET_CLASS_ERROR strong flags=%02x", m_data[15:8]);
      beat <= beat + 1;
    end
  end

  task automatic send(input logic weak_value, input logic strong_value, input logic last_value);
    begin
      @(negedge aclk);
      s_weak = weak_value;
      s_strong = strong_value;
      s_last = last_value;
      s_valid = 1'b1;
      do @(posedge aclk); while (!s_ready);
      @(negedge aclk);
      s_valid = 1'b0;
    end
  endtask

  initial begin
    repeat (4) @(posedge aclk);
    @(negedge aclk);
    aresetn = 1'b1;
    send(1'b1, 1'b0, 1'b0);
    send(1'b1, 1'b1, 1'b1);
    wait (m_last && m_valid);
    @(posedge aclk);
    @(negedge aclk);
    if (beat != 18)
      $fatal(1, "PACKET_CLASS_ERROR beats=%0d", beat);
    $display("P0 PACKET CLASS FLAGS PASS beats=%0d", beat);
    $finish;
  end

  initial begin
    #100000;
    $fatal(1, "PACKET_CLASS_ERROR timeout");
  end
endmodule
