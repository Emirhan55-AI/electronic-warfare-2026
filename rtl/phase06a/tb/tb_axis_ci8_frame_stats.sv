`timescale 1ns/1ps

module tb_axis_ci8_frame_stats;
  import phase06a_pkg::*;

  logic clk = 1'b0;
  logic resetn = 1'b0;
  logic input_valid = 1'b0;
  logic input_ready;
  logic [15:0] input_data = '0;
  logic input_last = 1'b0;
  logic result_valid;
  logic result_ready = 1'b0;
  logic [27:0] result_energy;
  logic [15:0] result_peak;
  logic [11:0] result_peak_index;
  logic [12:0] result_count;
  logic result_protocol_error;
  logic [1:0] result_error_code;

  logic [15:0] fixture_words [0:16383];
  logic [71:0] fixture_expected [0:3];
  logic [31:0] lfsr = 32'h06a2_0261;
  logic [16:0] held_input;
  logic [71:0] held_result;
  logic input_stalled = 1'b0;
  logic result_stalled = 1'b0;
  logic force_result_stall = 1'b0;
  logic reset_at_edge;
  logic accept_at_edge;
  logic [11:0] index_at_edge;
  integer watchdog = 0;
  integer result_number = 0;
  integer input_stall_cycles = 0;
  integer result_stall_cycles = 0;

  axis_ci8_frame_stats dut (
    .aclk                    (clk),
    .aresetn                 (resetn),
    .s_axis_tvalid           (input_valid),
    .s_axis_tready           (input_ready),
    .s_axis_tdata            (input_data),
    .s_axis_tlast            (input_last),
    .m_result_tvalid         (result_valid),
    .m_result_tready         (result_ready),
    .m_result_total_energy   (result_energy),
    .m_result_peak_power     (result_peak),
    .m_result_peak_index     (result_peak_index),
    .m_result_sample_count   (result_count),
    .m_result_protocol_error (result_protocol_error),
    .m_result_error_code     (result_error_code)
  );

  always #5 clk = ~clk;

  function automatic [71:0] packed_result;
    packed_result = {
      result_energy,
      result_peak,
      result_peak_index,
      result_count,
      result_protocol_error,
      result_error_code
    };
  endfunction

  task automatic drive_word(input logic [15:0] word, input logic last_word);
    begin
      repeat (lfsr[1:0] == 2'b00) @(posedge clk);
      input_data  <= word;
      input_last  <= last_word;
      input_valid <= 1'b1;
      do @(posedge clk); while (!input_ready);
      input_valid <= 1'b0;
      input_last  <= 1'b0;
    end
  endtask

  task automatic wait_result(input logic [71:0] expected);
    begin
      while (!result_valid) @(posedge clk);
      if (packed_result() !== expected) begin
        $error("Sonuc uyusmazligi: got=%018h expected=%018h", packed_result(), expected);
        $fatal(1);
      end
      do @(posedge clk); while (!result_ready);
      @(negedge clk);
      result_number = result_number + 1;
    end
  endtask

  task automatic drive_constant_frame(input logic [15:0] word);
    integer index;
    begin
      for (index = 0; index < 4096; index = index + 1) begin
        drive_word(word, index == 4095);
      end
    end
  endtask

  task automatic drive_fixture_frames_contiguous;
    integer word_index;
    begin
      for (word_index = 0; word_index < 16384; word_index = word_index + 1) begin
        input_data  <= fixture_words[word_index];
        input_last  <= word_index[11:0] == 12'd4095;
        input_valid <= 1'b1;
        do @(posedge clk); while (!input_ready);
      end
      input_valid <= 1'b0;
      input_last  <= 1'b0;
    end
  endtask

  task automatic wait_fixture_results;
    integer expected_index;
    begin
      for (expected_index = 0; expected_index < 4; expected_index = expected_index + 1) begin
        wait_result(fixture_expected[expected_index]);
      end
    end
  endtask

  always @(posedge clk) begin
    if (!resetn) begin
      lfsr <= 32'h06a2_0261;
      result_ready <= 1'b0;
      watchdog <= 0;
    end else begin
      lfsr <= {lfsr[30:0], lfsr[31] ^ lfsr[21] ^ lfsr[1] ^ lfsr[0]};
      result_ready <= force_result_stall ? 1'b0 : lfsr[2] | lfsr[5];
      watchdog <= watchdog + 1;
      if (watchdog > 1000000) begin
        $fatal(1, "Testbench watchdog zaman asimi");
      end
    end
  end

  always @(posedge clk) begin
    reset_at_edge = resetn;
    accept_at_edge = dut.accepted_transfer;
    index_at_edge = dut.sample_index;
    #1;
    if (!reset_at_edge) begin
      if (dut.sample_index !== 0 || dut.energy_accumulator !== 0
          || dut.peak_power_accumulator !== 0 || dut.dropping_late_frame !== 0
          || result_valid !== 0) begin
        $fatal(1, "Reset sonrasinda temiz durum saglanmadi");
      end
    end else if (!accept_at_edge && dut.sample_index !== index_at_edge) begin
      $fatal(1, "Kabul edilen transfer olmadan ornek sayaci ilerledi");
    end
  end

  always @(posedge clk) begin
    if (!resetn) begin
      input_stalled <= 1'b0;
      result_stalled <= 1'b0;
    end else begin
      if (input_stalled && {input_last, input_data} !== held_input) begin
        $fatal(1, "AXI giris payload'u backpressure sirasinda degisti");
      end
      if (result_stalled && packed_result() !== held_result) begin
        $fatal(1, "Sonuc payload'u backpressure sirasinda degisti");
      end
      if (result_valid && (^ {
        result_energy,
        result_peak,
        result_peak_index,
        result_count,
        result_protocol_error,
        result_error_code
      } === 1'bx)) begin
        $fatal(
          1,
          "Sonuc payload'unda X/Z bulundu: energy=%h peak=%h index=%h count=%h protocol=%b code=%b",
          result_energy,
          result_peak,
          result_peak_index,
          result_count,
          result_protocol_error,
          result_error_code
        );
      end
      input_stalled <= input_valid && !input_ready;
      result_stalled <= result_valid && !result_ready;
      if (input_valid && !input_ready) begin
        input_stall_cycles <= input_stall_cycles + 1;
      end
      if (result_valid && !result_ready) begin
        result_stall_cycles <= result_stall_cycles + 1;
      end
      held_input <= {input_last, input_data};
      held_result <= packed_result();
    end
  end

  integer sample_index;
  initial begin
    $readmemh("datasets/fixtures/phase06a/axis-input.hex", fixture_words);
    $readmemh("datasets/fixtures/phase06a/axis-expected.mem", fixture_expected);

    repeat (5) @(posedge clk);
    resetn <= 1'b1;
    repeat (2) @(posedge clk);

    force_result_stall <= 1'b1;
    fork
      drive_fixture_frames_contiguous();
      wait_fixture_results();
      begin
        while (!result_valid) @(posedge clk);
        repeat (7) @(posedge clk);
        force_result_stall <= 1'b0;
      end
    join

    fork
      drive_constant_frame(16'h0000);
      wait_result({28'd0, 16'd0, 12'd0, 13'd4096, 1'b0, PHASE06A_ERROR_NONE});
    join

    fork
      drive_constant_frame(16'h8080);
      wait_result({28'd134217728, 16'd32768, 12'd0, 13'd4096, 1'b0, PHASE06A_ERROR_NONE});
    join

    fork
      drive_constant_frame(16'h7f7f);
      wait_result({28'd132128768, 16'd32258, 12'd0, 13'd4096, 1'b0, PHASE06A_ERROR_NONE});
    join

    fork
      begin
        for (sample_index = 0; sample_index < 4096; sample_index = sample_index + 1) begin
          drive_word(sample_index[0] ? 16'h7f7f : 16'h8080, sample_index == 4095);
        end
      end
      wait_result({28'd133173248, 16'd32768, 12'd0, 13'd4096, 1'b0, PHASE06A_ERROR_NONE});
    join

    fork
      begin
        for (sample_index = 0; sample_index < 4096; sample_index = sample_index + 1) begin
          drive_word(sample_index == 137 ? 16'h8080 : 16'h0000, sample_index == 4095);
        end
      end
      wait_result({28'd32768, 16'd32768, 12'd137, 13'd4096, 1'b0, PHASE06A_ERROR_NONE});
    join

    fork
      begin
        for (sample_index = 0; sample_index < 4096; sample_index = sample_index + 1) begin
          drive_word(
            (sample_index == 23 || sample_index == 99) ? 16'h7f7f : 16'h0000,
            sample_index == 4095
          );
        end
      end
      wait_result({28'd64516, 16'd32258, 12'd23, 13'd4096, 1'b0, PHASE06A_ERROR_NONE});
    join

    drive_word(16'h0001, 1'b0);
    drive_word(16'h0001, 1'b0);
    drive_word(16'h0001, 1'b1);
    wait_result({28'd3, 16'd1, 12'd0, 13'd3, 1'b1, PHASE06A_ERROR_EARLY_TLAST});

    for (sample_index = 0; sample_index < 4096; sample_index = sample_index + 1) begin
      drive_word(16'h0000, 1'b0);
    end
    wait_result({28'd0, 16'd0, 12'd0, 13'd4096, 1'b1, PHASE06A_ERROR_MISSING_TLAST});
    drive_word(16'h0000, 1'b0);
    drive_word(16'h0000, 1'b1);

    fork
      drive_constant_frame(16'h0001);
      wait_result({28'd4096, 16'd1, 12'd0, 13'd4096, 1'b0, PHASE06A_ERROR_NONE});
    join

    input_data <= 16'h8080;
    input_valid <= 1'b1;
    input_last <= 1'b0;
    repeat (17) @(posedge clk);
    resetn <= 1'b0;
    repeat (3) @(posedge clk);
    input_valid <= 1'b0;
    resetn <= 1'b1;
    repeat (2) @(posedge clk);

    fork
      drive_constant_frame(16'h0000);
      wait_result({28'd0, 16'd0, 12'd0, 13'd4096, 1'b0, PHASE06A_ERROR_NONE});
    join

    if (result_number != 14) begin
      $fatal(1, "Frame basina tek sonuc sozlesmesi bozuldu: %0d", result_number);
    end
    if (input_stall_cycles == 0 || result_stall_cycles == 0) begin
      $fatal(
        1,
        "Backpressure senaryosu gerceklesmedi: input=%0d result=%0d",
        input_stall_cycles,
        result_stall_cycles
      );
    end
    $display(
      "PHASE-06A TB COVERAGE: input_stalls=%0d result_stalls=%0d",
      input_stall_cycles,
      result_stall_cycles
    );
    $display("PHASE-06A TB PASS: %0d result checked", result_number);
    $finish;
  end
endmodule
