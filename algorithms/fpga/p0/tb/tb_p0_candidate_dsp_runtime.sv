`timescale 1ns/1ps

// Boundary smoke test for the complete CI8-to-packet path.  The vendor FFT
// is replaced only at this test boundary; the Hann, power, reducer and
// packetizer RTL remain the production modules under test.
module phase06d_fft_4096 (
  input  logic        aclk,
  input  logic        aresetn,
  input  logic [7:0]  s_axis_config_tdata,
  input  logic        s_axis_config_tvalid,
  output logic        s_axis_config_tready,
  input  logic [31:0] s_axis_data_tdata,
  input  logic        s_axis_data_tvalid,
  output logic        s_axis_data_tready,
  input  logic        s_axis_data_tlast,
  output logic [63:0] m_axis_data_tdata,
  output logic [15:0] m_axis_data_tuser,
  output logic        m_axis_data_tvalid,
  input  logic        m_axis_data_tready,
  output logic        m_axis_data_tlast,
  output logic        event_frame_started,
  output logic        event_tlast_unexpected,
  output logic        event_tlast_missing,
  output logic        event_status_channel_halt,
  output logic        event_data_in_channel_halt,
  output logic        event_data_out_channel_halt
);
  logic configured;
  logic [11:0] sample_index;

  assign s_axis_config_tready = !configured;
  assign s_axis_data_tready = configured && (!m_axis_data_tvalid || m_axis_data_tready);
  assign event_frame_started = 1'b0;
  assign event_tlast_unexpected = 1'b0;
  assign event_tlast_missing = 1'b0;
  assign event_status_channel_halt = 1'b0;
  assign event_data_in_channel_halt = 1'b0;
  assign event_data_out_channel_halt = 1'b0;

  always_ff @(posedge aclk) begin
    if (!aresetn) begin
      configured <= 1'b0;
      sample_index <= '0;
      m_axis_data_tvalid <= 1'b0;
      m_axis_data_tdata <= '0;
      m_axis_data_tuser <= '0;
      m_axis_data_tlast <= 1'b0;
    end else begin
      if (s_axis_config_tvalid && s_axis_config_tready) begin
        if (s_axis_config_tdata !== 8'h01)
          $fatal(1, "FFT konfigurasyonu beklenmeyen deger");
        configured <= 1'b1;
      end
      if (m_axis_data_tvalid && m_axis_data_tready)
        m_axis_data_tvalid <= 1'b0;
      if (s_axis_data_tvalid && s_axis_data_tready) begin
        // A zero FFT frame is the deterministic negative control.  The
        // natural index and frame boundary still exercise the real wrapper.
        m_axis_data_tvalid <= 1'b1;
        m_axis_data_tdata <= '0;
        m_axis_data_tuser <= {4'd0, sample_index};
        m_axis_data_tlast <= s_axis_data_tlast;
        if (s_axis_data_tlast || sample_index == 12'd4095)
          sample_index <= '0;
        else
          sample_index <= sample_index + 12'd1;
      end
    end
  end
endmodule

module tb_p0_candidate_dsp_runtime;
  logic clk = 1'b0;
  logic resetn = 1'b0;
  logic input_valid = 1'b0;
  logic input_ready;
  logic [15:0] input_data = 16'd0;
  logic [1:0] input_keep = 2'b11;
  logic input_last = 1'b0;
  logic output_valid;
  logic output_ready = 1'b1;
  logic [63:0] output_data;
  logic [7:0] output_keep;
  logic output_last;
  logic configuration_done;
  logic [5:0] status_events;
  logic input_keep_error;
  logic [8:0] reducer_status;
  logic transport_error;
  logic candidate_overflow;
  logic [31:0] completed_frames;
  integer output_beats = 0;
  integer watchdog = 0;
  integer sample = 0;

  p0_candidate_dsp_runtime_top dut (
    .aclk(clk),
    .aresetn(resetn),
    .s_axis_tvalid(input_valid),
    .s_axis_tready(input_ready),
    .s_axis_tdata(input_data),
    .s_axis_tkeep(input_keep),
    .s_axis_tlast(input_last),
    .m_axis_tvalid(output_valid),
    .m_axis_tready(output_ready),
    .m_axis_tdata(output_data),
    .m_axis_tkeep(output_keep),
    .m_axis_tlast(output_last),
    .configuration_done(configuration_done),
    .status_events_sticky(status_events),
    .input_keep_error_sticky(input_keep_error),
    .status_reducer_sticky(reducer_status),
    .status_transport_error_sticky(transport_error),
    .status_candidate_overflow_sticky(candidate_overflow),
    .completed_frame_count(completed_frames)
  );

  always #5 clk = ~clk;

  initial begin
    repeat (3) @(posedge clk);
    resetn = 1'b1;
    while (!configuration_done) @(posedge clk);
    for (sample = 0; sample < 4096; sample = sample + 1) begin
      @(negedge clk);
      input_valid = 1'b1;
      input_last = (sample == 4095);
      do @(posedge clk); while (!input_ready);
    end
    @(negedge clk);
    input_valid = 1'b0;
    input_last = 1'b0;

    while (completed_frames < 1) begin
      @(posedge clk);
      watchdog = watchdog + 1;
      if (watchdog > 500000)
        $fatal(1, "tam aday yolu smoke testi zaman asimi");
    end
    repeat (8) begin
      do @(posedge clk); while (!output_valid);
      if (output_keep !== 8'hFF)
        $fatal(1, "AXI TKEEP beklenmeyen deger");
      if (output_last && output_beats != 7)
        $fatal(1, "bos pakette TLAST sirasi beklenmeyen deger");
      output_beats = output_beats + 1;
    end
    if (output_beats != 8 || !output_last)
      $fatal(1, "bos paket beat sayisi beklenmeyen deger");
    if (status_events !== 0 || input_keep_error || reducer_status !== 0 || transport_error || candidate_overflow)
      $fatal(1, "tam aday yolunda sticky durum hatasi");
    $display("P0_CANDIDATE_DSP_RUNTIME_PASS frames=%0d beats=%0d", completed_frames, output_beats);
    $finish;
  end
endmodule
