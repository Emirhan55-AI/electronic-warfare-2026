`timescale 1ns/1ps

module tb_p0_os_cfar_weak_nomination;
  localparam int FRAME_LENGTH = 4096;
  localparam int WEAK_SHIFTED_BIN = 1000;
  localparam int STRONG_SHIFTED_BIN = 3000;

  logic aclk = 1'b0;
  logic aresetn = 1'b0;
  always #5 aclk = ~aclk;

  logic s_valid;
  wire s_ready;
  logic [57:0] s_data;
  logic s_last;
  logic [11:0] s_index;
  wire m_valid;
  logic m_ready = 1'b1;
  wire [57:0] m_data;
  wire m_last;
  wire [11:0] m_index;
  wire [57:0] m_noise;
  wire m_detected;
  wire m_weak;
  wire [15:0] completed;
  wire frame_error;
  integer input_index;
  integer output_count;
  integer weak_hits;
  integer strong_hits;

  p0_os_cfar_decision_engine dut (
    .aclk, .aresetn,
    .s_axis_tvalid(s_valid), .s_axis_tready(s_ready),
    .s_axis_tdata(s_data), .s_axis_tlast(s_last),
    .s_axis_tuser_index(s_index),
    .m_axis_tvalid(m_valid), .m_axis_tready(m_ready),
    .m_axis_tdata(m_data), .m_axis_tlast(m_last),
    .m_axis_tuser_shifted_index(m_index),
    .m_axis_tuser_order_statistic(m_noise),
    .m_axis_tuser_detected(m_detected),
    .m_axis_tuser_weak_nominated(m_weak),
    .completed_frame_count(completed),
    .status_frame_error_sticky(frame_error)
  );

  always @(posedge aclk) begin
    if (aresetn && m_valid && m_ready) begin
      output_count <= output_count + 1;
      if (m_weak) weak_hits <= weak_hits + 1;
      if (m_detected) strong_hits <= strong_hits + 1;
      if (m_detected && !m_weak) begin
        $display("WEAK_RTL_ERROR strict decision lacked weak nomination");
        $fatal(1);
      end
      if (m_index == WEAK_SHIFTED_BIN && (!m_weak || m_detected)) begin
        $display("WEAK_RTL_ERROR 5x cell classification weak=%0d strict=%0d",
                 m_weak, m_detected);
        $fatal(1);
      end
      if (m_index == STRONG_SHIFTED_BIN && (!m_weak || !m_detected)) begin
        $display("WEAK_RTL_ERROR 10x cell classification weak=%0d strict=%0d",
                 m_weak, m_detected);
        $fatal(1);
      end
    end
  end

  initial begin
    s_valid = 1'b0;
    s_data = 58'd0;
    s_last = 1'b0;
    s_index = 12'd0;
    output_count = 0;
    weak_hits = 0;
    strong_hits = 0;
    repeat (4) @(posedge aclk);
    @(negedge aclk);
    aresetn = 1'b1;
    for (input_index = 0; input_index < FRAME_LENGTH; input_index = input_index + 1) begin
      @(negedge aclk);
      s_valid = 1'b1;
      s_index = input_index[11:0];
      s_last = input_index == FRAME_LENGTH - 1;
      if (input_index == (WEAK_SHIFTED_BIN ^ 12'h800))
        s_data = 58'd5368709120;
      else if (input_index == (STRONG_SHIFTED_BIN ^ 12'h800))
        s_data = 58'd10737418240;
      else
        s_data = 58'd1073741824;
      do @(posedge aclk); while (!s_ready);
    end
    @(negedge aclk);
    s_valid = 1'b0;
    wait (completed == 1);
    repeat (2) @(posedge aclk);
    if (frame_error || output_count != FRAME_LENGTH - 40 ||
        weak_hits != 2 || strong_hits != 1) begin
      $display("WEAK_RTL_ERROR summary error=%0d outputs=%0d weak=%0d strong=%0d",
               frame_error, output_count, weak_hits, strong_hits);
      $fatal(1);
    end
    $display("P0 WEAK NOMINATION RTL PASS outputs=%0d weak=%0d strong=%0d",
             output_count, weak_hits, strong_hits);
    $finish;
  end

  initial begin
    #10000000;
    $display("WEAK_RTL_ERROR timeout");
    $fatal(1);
  end
endmodule
