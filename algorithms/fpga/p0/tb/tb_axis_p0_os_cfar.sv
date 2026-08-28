`timescale 1ns/1ps

module tb_axis_p0_os_cfar;
  localparam int FRAME_LENGTH = 4096;
  localparam int FRAME_COUNT = 11;
  localparam int TOTAL_RESULTS = FRAME_LENGTH * FRAME_COUNT;
  localparam int FRAME_CYCLE_BUDGET_50MHZ = 102400;

  logic aclk = 1'b0;
  logic aresetn = 1'b0;
  always #5 aclk = ~aclk;

  logic [70:0] input_memory [0:TOTAL_RESULTS-1];
  logic [63:0] expected_memory [0:TOTAL_RESULTS-1];
  integer input_count;
  integer output_count;
  integer cycle_count;
  integer input_stalls;
  integer output_stalls;
  integer payload_stability_checks;
  integer first_input_cycle;
  integer first_frame_last_input_cycle;
  integer first_frame_first_output_cycle;
  integer first_frame_last_output_cycle;
  integer malformed_output_count;
  logic automatic_source;
  logic scoreboard_enable;
  logic manual_valid;
  logic [57:0] manual_data;
  logic manual_last;
  logic [11:0] manual_index;
  logic [76:0] stalled_payload;
  logic stalled_previous;

  wire source_valid = automatic_source ? (input_count < TOTAL_RESULTS) : manual_valid;
  wire [57:0] source_data = automatic_source ? input_memory[input_count][57:0] : manual_data;
  wire [11:0] source_index = automatic_source ? input_memory[input_count][69:58] : manual_index;
  wire source_last = automatic_source ? input_memory[input_count][70] : manual_last;

  wire s_axis_tready;
  wire m_axis_tvalid;
  logic m_axis_tready;
  wire [63:0] m_axis_tdata;
  wire m_axis_tlast;
  wire [11:0] m_axis_tuser_index;
  wire status_frame_error_sticky;
  wire [76:0] observed_payload = {m_axis_tlast, m_axis_tuser_index, m_axis_tdata};

  axis_p0_os_cfar dut (
    .aclk(aclk), .aresetn(aresetn),
    .s_axis_tvalid(source_valid), .s_axis_tready(s_axis_tready),
    .s_axis_tdata(source_data), .s_axis_tlast(source_last),
    .s_axis_tuser_index(source_index),
    .m_axis_tvalid(m_axis_tvalid), .m_axis_tready(m_axis_tready),
    .m_axis_tdata(m_axis_tdata), .m_axis_tlast(m_axis_tlast),
    .m_axis_tuser_index(m_axis_tuser_index),
    .status_frame_error_sticky(status_frame_error_sticky)
  );

  always_comb begin
    if (scoreboard_enable && output_count < FRAME_LENGTH)
      m_axis_tready = 1'b1;
    else
      m_axis_tready = ((cycle_count % 13) != 4) && ((cycle_count % 17) != 9);
  end

  always @(posedge aclk) begin
    if (!aresetn) begin
      input_count <= 0;
      output_count <= 0;
      cycle_count <= 0;
      input_stalls <= 0;
      output_stalls <= 0;
      payload_stability_checks <= 0;
      first_input_cycle <= -1;
      first_frame_last_input_cycle <= -1;
      first_frame_first_output_cycle <= -1;
      first_frame_last_output_cycle <= -1;
      malformed_output_count <= 0;
      stalled_previous <= 1'b0;
      stalled_payload <= '0;
    end else begin
      cycle_count <= cycle_count + 1;
      if (automatic_source && source_valid && s_axis_tready) begin
        if (scoreboard_enable && input_count == 0)
          first_input_cycle <= cycle_count;
        if (scoreboard_enable && input_count == FRAME_LENGTH - 1)
          first_frame_last_input_cycle <= cycle_count;
        input_count <= input_count + 1;
      end
      if (source_valid && !s_axis_tready)
        input_stalls <= input_stalls + 1;
      if (m_axis_tvalid && !m_axis_tready)
        output_stalls <= output_stalls + 1;

      if (stalled_previous) begin
        if (!m_axis_tvalid || observed_payload !== stalled_payload) begin
          $display("P0_OS_CFAR_ERROR stalled payload changed");
          $fatal(1);
        end
        payload_stability_checks <= payload_stability_checks + 1;
      end
      stalled_previous <= m_axis_tvalid && !m_axis_tready;
      if (m_axis_tvalid && !m_axis_tready)
        stalled_payload <= observed_payload;

      if (m_axis_tvalid && m_axis_tready) begin
        if (scoreboard_enable) begin
          if (output_count == 0)
            first_frame_first_output_cycle <= cycle_count;
          if (output_count == FRAME_LENGTH - 1)
            first_frame_last_output_cycle <= cycle_count;
          if (output_count >= TOTAL_RESULTS || m_axis_tdata !== expected_memory[output_count]) begin
            $display("P0_OS_CFAR_ERROR mismatch result=%0d observed=%016x expected=%016x",
                     output_count, m_axis_tdata, expected_memory[output_count]);
            $fatal(1);
          end
          if (m_axis_tuser_index !== (output_count % FRAME_LENGTH) ||
              m_axis_tlast !== ((output_count % FRAME_LENGTH) == FRAME_LENGTH - 1)) begin
            $display("P0_OS_CFAR_ERROR output framing mismatch result=%0d", output_count);
            $fatal(1);
          end
          output_count <= output_count + 1;
        end else begin
          malformed_output_count <= malformed_output_count + 1;
        end
      end
    end
  end

  task automatic send_manual(
    input logic [57:0] power,
    input logic [11:0] index,
    input logic last
  );
    begin
      @(negedge aclk);
      manual_data = power;
      manual_index = index;
      manual_last = last;
      manual_valid = 1'b1;
      do @(posedge aclk); while (!s_axis_tready);
      @(negedge aclk);
      manual_valid = 1'b0;
    end
  endtask

  integer malformed_index;
  integer frame_completion_cycles;
  initial begin
    $readmemh("datasets/fixtures/p0_os_cfar/axis-power-input.mem", input_memory);
    $readmemh("datasets/fixtures/p0_os_cfar/dma-expected.mem", expected_memory);
    automatic_source = 1'b0;
    scoreboard_enable = 1'b0;
    manual_valid = 1'b0;
    manual_data = '0;
    manual_index = '0;
    manual_last = 1'b0;

    repeat (4) @(posedge aclk);
    aresetn = 1'b1;
    automatic_source = 1'b1;
    wait (input_count == 137);
    @(negedge aclk);
    aresetn = 1'b0;
    automatic_source = 1'b0;
    repeat (3) @(posedge aclk);
    @(negedge aclk);
    aresetn = 1'b1;
    scoreboard_enable = 1'b1;
    automatic_source = 1'b1;

    wait (output_count == TOTAL_RESULTS);
    @(negedge aclk);
    automatic_source = 1'b0;
    scoreboard_enable = 1'b0;
    repeat (4) @(posedge aclk);

    send_manual(58'd1, 12'd0, 1'b1);
    for (malformed_index = 0; malformed_index < FRAME_LENGTH; malformed_index = malformed_index + 1)
      send_manual(58'd2, malformed_index[11:0], 1'b0);
    send_manual(58'd3, 12'd5, 1'b1);
    repeat (20) @(posedge aclk);

    if (!status_frame_error_sticky || malformed_output_count != 0) begin
      $display("P0_OS_CFAR_ERROR malformed-frame policy failed sticky=%0d outputs=%0d",
               status_frame_error_sticky, malformed_output_count);
      $fatal(1);
    end
    if (first_input_cycle < 0 || first_frame_last_input_cycle < first_input_cycle ||
        first_frame_first_output_cycle <= first_frame_last_input_cycle ||
        first_frame_last_output_cycle <= first_frame_first_output_cycle) begin
      $display("P0_OS_CFAR_ERROR latency measurement failed");
      $fatal(1);
    end
    frame_completion_cycles = first_frame_last_output_cycle - first_input_cycle;
    if (frame_completion_cycles >= FRAME_CYCLE_BUDGET_50MHZ) begin
      $display("P0_OS_CFAR_ERROR frame budget exceeded cycles=%0d", frame_completion_cycles);
      $fatal(1);
    end

    $display("P0_OS_CFAR_METRIC frame_completion_cycles=%0d", frame_completion_cycles);
    $display("P0_OS_CFAR_METRIC last_input_to_first_output_cycles=%0d",
             first_frame_first_output_cycle - first_frame_last_input_cycle);
    $display("P0_OS_CFAR_METRIC input_stalls=%0d output_stalls=%0d payload_stability_checks=%0d",
             input_stalls, output_stalls, payload_stability_checks);
    $display("P0_OS_CFAR_METRIC malformed_frames_checked=3 frame_error_sticky=1");
    $display("P0 OS-CFAR TB PASS: %0d DMA words checked", TOTAL_RESULTS);
    $finish;
  end

  initial begin
    #200000000;
    $display("P0_OS_CFAR_ERROR timeout");
    $fatal(1);
  end
endmodule
