`timescale 1ns/1ps

module tb_axis_hann_window;
  import phase06b_pkg::*;

  localparam integer MAIN_SAMPLE_COUNT = 40960;
  localparam integer ZERO_FRAME_OFFSET = 4 * 4096;
  localparam integer MINIMUM_FRAME_OFFSET = 5 * 4096;
  localparam integer EXPECTED_CHECKED_SAMPLES = 45074;

  logic clk = 1'b0;
  logic resetn = 1'b0;
  logic input_valid = 1'b0;
  logic input_ready;
  logic [15:0] input_data = '0;
  logic input_last = 1'b0;
  logic output_valid;
  logic output_ready = 1'b0;
  logic [31:0] output_data;
  logic output_last;

  logic [15:0] fixture_input [0:MAIN_SAMPLE_COUNT-1];
  logic [31:0] fixture_expected [0:MAIN_SAMPLE_COUNT-1];
  logic [31:0] lfsr = 32'h06b2_0262;
  logic random_ready_enable = 1'b0;
  logic force_output_stall = 1'b0;
  logic input_stalled = 1'b0;
  logic output_stalled = 1'b0;
  logic [16:0] held_input;
  logic [32:0] held_output;
  logic reset_at_edge;
  logic processing_at_edge;
  logic [11:0] index_at_edge;
  integer cycle_counter = 0;
  integer watchdog = 0;
  integer checked_samples = 0;
  integer checked_tlast = 0;
  integer input_stall_cycles = 0;
  integer output_stall_cycles = 0;
  integer measured_latency = -1;

  axis_hann_window dut (
    .aclk          (clk),
    .aresetn       (resetn),
    .s_axis_tvalid (input_valid),
    .s_axis_tready (input_ready),
    .s_axis_tdata  (input_data),
    .s_axis_tlast  (input_last),
    .m_axis_tvalid (output_valid),
    .m_axis_tready (output_ready),
    .m_axis_tdata  (output_data),
    .m_axis_tlast  (output_last)
  );

  always #5 clk = ~clk;

  task automatic apply_reset;
    begin
      @(negedge clk);
      resetn = 1'b0;
      input_valid = 1'b0;
      input_last = 1'b0;
      repeat (3) @(posedge clk);
      @(negedge clk);
      resetn = 1'b1;
      repeat (2) @(posedge clk);
    end
  endtask

  task automatic drive_words(input integer offset, input integer count);
    integer local_index;
    begin
      for (local_index = 0; local_index < count; local_index = local_index + 1) begin
        @(negedge clk);
        input_data = fixture_input[offset + local_index];
        input_last = local_index[11:0] == 12'd4095;
        input_valid = 1'b1;
        do @(posedge clk); while (!input_ready);
      end
      @(negedge clk);
      input_valid = 1'b0;
      input_last = 1'b0;
    end
  endtask

  task automatic check_words(input integer offset, input integer count);
    integer local_index;
    logic expected_last;
    begin
      for (local_index = 0; local_index < count; local_index = local_index + 1) begin
        do @(posedge clk); while (!(output_valid && output_ready));
        expected_last = local_index[11:0] == 12'd4095;
        if (output_data !== fixture_expected[offset + local_index]) begin
          $fatal(
            1,
            "Golden uyusmazligi sample=%0d got=%08h expected=%08h",
            local_index,
            output_data,
            fixture_expected[offset + local_index]
          );
        end
        if (output_last !== expected_last) begin
          $fatal(1, "TLAST uyusmazligi sample=%0d got=%b expected=%b", local_index, output_last, expected_last);
        end
        checked_samples = checked_samples + 1;
        if (output_last) begin
          checked_tlast = checked_tlast + 1;
        end
      end
    end
  endtask

  always @(posedge clk) begin
    if (!resetn) begin
      output_ready <= 1'b0;
      lfsr <= 32'h06b2_0262;
      watchdog <= 0;
    end else begin
      lfsr <= {lfsr[30:0], lfsr[31] ^ lfsr[21] ^ lfsr[1] ^ lfsr[0]};
      if (force_output_stall) begin
        output_ready <= 1'b0;
      end else if (random_ready_enable) begin
        output_ready <= lfsr[2] | lfsr[5];
      end else begin
        output_ready <= 1'b1;
      end
      watchdog <= watchdog + 1;
      if (watchdog > 2000000) begin
        $fatal(1, "PHASE-06B testbench watchdog zaman asimi");
      end
    end
    cycle_counter <= cycle_counter + 1;
  end

  always @(posedge clk) begin
    reset_at_edge = resetn;
    processing_at_edge = dut.processing_transfer;
    index_at_edge = dut.sample_index;
    #1;
    if (!reset_at_edge) begin
      if (dut.sample_index !== 0 || output_valid !== 0) begin
        $fatal(1, "Reset Hann indeksini veya bekleyen cikisi temizlemedi");
      end
    end else if (!processing_at_edge && dut.sample_index !== index_at_edge) begin
      $fatal(1, "Gercek transfer olmadan Hann ornek indisi ilerledi");
    end
  end

  always @(posedge clk) begin
    if (!resetn) begin
      input_stalled <= 1'b0;
      output_stalled <= 1'b0;
    end else begin
      if (input_stalled && {input_last, input_data} !== held_input) begin
        $fatal(1, "AXI giris payload'u backpressure sirasinda degisti");
      end
      if (output_stalled && {output_last, output_data} !== held_output) begin
        $fatal(1, "AXI cikis payload'u backpressure sirasinda degisti");
      end
      if (output_valid && (^{output_last, output_data} === 1'bx)) begin
        $fatal(1, "Hann cikis payload'unda X/Z bulundu");
      end
      input_stalled <= input_valid && !input_ready;
      output_stalled <= output_valid && !output_ready;
      if (input_valid && !input_ready) begin
        input_stall_cycles <= input_stall_cycles + 1;
      end
      if (output_valid && !output_ready) begin
        output_stall_cycles <= output_stall_cycles + 1;
      end
      held_input <= {input_last, input_data};
      held_output <= {output_last, output_data};
    end
  end

  initial begin
    $readmemh("datasets/fixtures/phase06b/axis-input.hex", fixture_input);
    $readmemh("datasets/fixtures/phase06b/axis-expected.mem", fixture_expected);

    apply_reset();
    if (dut.coefficient_rom[0] !== 16'h0000
        || dut.coefficient_rom[1] !== 16'h0000
        || dut.coefficient_rom[2048] !== 16'h8000) begin
      $fatal(1, "Ilk/son/merkez Hann katsayilari sozlesmeyle uyusmuyor");
    end

    @(negedge clk);
    input_data = 16'h7f7f;
    input_last = 1'b0;
    input_valid = 1'b1;
    @(posedge clk);
    if (!input_ready) begin
      $fatal(1, "Latency probe girisi kabul edilmedi");
    end
    #1;
    if (output_valid) begin
      $fatal(1, "Hann cikisi kabul kenarinda erken valid oldu");
    end
    @(negedge clk);
    input_valid = 1'b0;
    @(posedge clk);
    #1;
    measured_latency = 1;
    if (!output_valid || measured_latency != 1 || output_data !== 32'h00000000 || output_last !== 1'b0) begin
      $fatal(1, "Latency probe basarisiz: latency=%0d data=%08h", measured_latency, output_data);
    end
    @(posedge clk);
    checked_samples = checked_samples + 1;
    apply_reset();

    random_ready_enable = 1'b1;
    force_output_stall = 1'b1;
    fork
      drive_words(0, MAIN_SAMPLE_COUNT);
      check_words(0, MAIN_SAMPLE_COUNT);
      begin
        while (!output_valid) @(posedge clk);
        repeat (9) @(posedge clk);
        @(negedge clk);
        force_output_stall = 1'b0;
      end
    join

    @(negedge clk);
    random_ready_enable = 1'b0;
    force_output_stall = 1'b0;
    fork
      drive_words(MINIMUM_FRAME_OFFSET, 17);
      check_words(MINIMUM_FRAME_OFFSET, 17);
    join

    @(negedge clk);
    force_output_stall = 1'b1;
    drive_words(MINIMUM_FRAME_OFFSET + 17, 1);
    while (!output_valid) @(posedge clk);
    apply_reset();
    @(negedge clk);
    force_output_stall = 1'b0;

    fork
      drive_words(ZERO_FRAME_OFFSET, 4096);
      check_words(ZERO_FRAME_OFFSET, 4096);
    join

    repeat (3) @(posedge clk);
    if (checked_samples != EXPECTED_CHECKED_SAMPLES) begin
      $fatal(1, "Kontrol edilen ornek sayisi yanlis: %0d", checked_samples);
    end
    if (checked_tlast != 11) begin
      $fatal(1, "Kontrol edilen TLAST sayisi yanlis: %0d", checked_tlast);
    end
    if (input_stall_cycles == 0 || output_stall_cycles == 0) begin
      $fatal(
        1,
        "Backpressure gerceklesmedi: input=%0d output=%0d",
        input_stall_cycles,
        output_stall_cycles
      );
    end
    $display("PHASE-06B TB LATENCY: %0d cycle", measured_latency);
    $display(
      "PHASE-06B TB COVERAGE: input_stalls=%0d output_stalls=%0d tlast=%0d",
      input_stall_cycles,
      output_stall_cycles,
      checked_tlast
    );
    $display("PHASE-06B TB PASS: %0d samples checked", checked_samples);
    $finish;
  end
endmodule
