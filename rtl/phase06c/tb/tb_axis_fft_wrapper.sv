`timescale 1ns/1ps

module tb_axis_fft_wrapper;
  localparam integer MAIN_SAMPLE_COUNT = 40960;
  localparam integer EXPECTED_CHECKED_SAMPLES = 45074;

  logic clk = 1'b0;
  logic resetn = 1'b0;
  logic input_valid = 1'b0;
  logic input_ready;
  logic [31:0] input_data = '0;
  logic input_last = 1'b0;
  logic output_valid;
  logic output_ready = 1'b0;
  logic [63:0] output_data;
  logic output_last;
  logic [11:0] output_index;

  logic config_valid;
  logic config_ready;
  logic [7:0] config_data;
  logic fft_input_valid;
  logic fft_input_ready;
  logic [31:0] fft_input_data;
  logic fft_input_last;
  logic fft_output_valid;
  logic fft_output_ready;
  logic [63:0] fft_output_data;
  logic fft_output_last;
  logic [11:0] fft_output_index;
  logic configuration_done;
  logic [5:0] status_events;
  logic [5:0] inject_events = '0;
  logic stub_event_frame_started;
  logic stub_event_tlast_unexpected;
  logic stub_event_tlast_missing;
  logic stub_event_status_channel_halt;
  logic stub_event_data_in_channel_halt;
  logic stub_event_data_out_channel_halt;
  logic allow_config_ready = 1'b0;
  logic configuration_seen;

  logic [31:0] fixture_input [0:MAIN_SAMPLE_COUNT-1];
  logic [63:0] fixture_stub_expected [0:MAIN_SAMPLE_COUNT-1];
  logic [31:0] lfsr = 32'h06c2_0263;
  logic random_ready_enable = 1'b0;
  logic force_output_stall = 1'b0;
  logic input_stalled = 1'b0;
  logic output_stalled = 1'b0;
  logic config_stalled = 1'b0;
  logic [32:0] held_input;
  logic [76:0] held_output;
  logic [7:0] held_config;
  integer cycle_counter = 0;
  integer watchdog = 0;
  integer checked_samples = 0;
  integer checked_tlast = 0;
  integer input_stall_cycles = 0;
  integer output_stall_cycles = 0;
  integer config_handshakes = 0;
  integer measured_latency = -1;
  logic event_injected_while_output_stalled = 1'b0;

  axis_fft_wrapper dut (
    .aclk                              (clk),
    .aresetn                           (resetn),
    .s_axis_tvalid                     (input_valid),
    .s_axis_tready                     (input_ready),
    .s_axis_tdata                      (input_data),
    .s_axis_tlast                      (input_last),
    .m_axis_tvalid                     (output_valid),
    .m_axis_tready                     (output_ready),
    .m_axis_tdata                      (output_data),
    .m_axis_tlast                      (output_last),
    .m_axis_tuser_index                (output_index),
    .fft_s_axis_config_tvalid          (config_valid),
    .fft_s_axis_config_tready          (config_ready),
    .fft_s_axis_config_tdata           (config_data),
    .fft_s_axis_data_tvalid            (fft_input_valid),
    .fft_s_axis_data_tready            (fft_input_ready),
    .fft_s_axis_data_tdata             (fft_input_data),
    .fft_s_axis_data_tlast             (fft_input_last),
    .fft_m_axis_data_tvalid            (fft_output_valid),
    .fft_m_axis_data_tready            (fft_output_ready),
    .fft_m_axis_data_tdata             (fft_output_data),
    .fft_m_axis_data_tlast             (fft_output_last),
    .fft_m_axis_data_tuser_index       (fft_output_index),
    .fft_event_frame_started           (stub_event_frame_started),
    .fft_event_tlast_unexpected        (stub_event_tlast_unexpected),
    .fft_event_tlast_missing           (stub_event_tlast_missing),
    .fft_event_status_channel_halt     (stub_event_status_channel_halt),
    .fft_event_data_in_channel_halt    (stub_event_data_in_channel_halt),
    .fft_event_data_out_channel_halt   (stub_event_data_out_channel_halt),
    .configuration_done                (configuration_done),
    .status_events_sticky              (status_events)
  );

  fft_ip_transport_stub stub (
    .aclk                     (clk),
    .aresetn                  (resetn),
    .allow_config_ready       (allow_config_ready),
    .inject_events            (inject_events),
    .s_axis_config_tvalid     (config_valid),
    .s_axis_config_tready     (config_ready),
    .s_axis_config_tdata      (config_data),
    .s_axis_data_tvalid       (fft_input_valid),
    .s_axis_data_tready       (fft_input_ready),
    .s_axis_data_tdata        (fft_input_data),
    .s_axis_data_tlast        (fft_input_last),
    .m_axis_data_tvalid       (fft_output_valid),
    .m_axis_data_tready       (fft_output_ready),
    .m_axis_data_tdata        (fft_output_data),
    .m_axis_data_tlast        (fft_output_last),
    .m_axis_data_tuser_index  (fft_output_index),
    .event_frame_started      (stub_event_frame_started),
    .event_tlast_unexpected   (stub_event_tlast_unexpected),
    .event_tlast_missing      (stub_event_tlast_missing),
    .event_status_channel_halt(stub_event_status_channel_halt),
    .event_data_in_channel_halt(stub_event_data_in_channel_halt),
    .event_data_out_channel_halt(stub_event_data_out_channel_halt),
    .configuration_seen       (configuration_seen)
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

  task automatic wait_for_configuration;
    begin
      while (!configuration_done) @(posedge clk);
      if (!configuration_seen) begin
        $fatal(1, "Wrapper ve stub konfigurasyon durumu uyusmuyor");
      end
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
        if (output_data !== fixture_stub_expected[offset + local_index]) begin
          $fatal(1, "Stub transport uyusmazligi sample=%0d got=%016h expected=%016h", local_index, output_data, fixture_stub_expected[offset + local_index]);
        end
        if (output_index !== local_index[11:0]) begin
          $fatal(1, "XK_INDEX uyusmazligi sample=%0d got=%0d", local_index, output_index);
        end
        if (output_last !== expected_last) begin
          $fatal(1, "TLAST uyusmazligi sample=%0d got=%b expected=%b", local_index, output_last, expected_last);
        end
        checked_samples = checked_samples + 1;
        if (output_last) checked_tlast = checked_tlast + 1;
      end
    end
  endtask

  always @(posedge clk) begin
    if (!resetn) begin
      output_ready <= 1'b0;
      lfsr <= 32'h06c2_0263;
      watchdog <= 0;
    end else begin
      lfsr <= {lfsr[30:0], lfsr[31] ^ lfsr[21] ^ lfsr[1] ^ lfsr[0]};
      if (force_output_stall) output_ready <= 1'b0;
      else if (random_ready_enable) output_ready <= lfsr[2] | lfsr[5];
      else output_ready <= 1'b1;
      watchdog <= watchdog + 1;
      if (watchdog > 2000000) $fatal(1, "PHASE-06C testbench watchdog zaman asimi");
    end
    cycle_counter <= cycle_counter + 1;
  end

  always @(posedge clk) begin
    if (!resetn) begin
      input_stalled <= 1'b0;
      output_stalled <= 1'b0;
      config_stalled <= 1'b0;
    end else begin
      if (input_stalled && {input_last, input_data} !== held_input) $fatal(1, "AXI giris payload'u stall sirasinda degisti");
      if (output_stalled && {output_index, output_last, output_data} !== held_output) $fatal(1, "AXI cikis payload'u stall sirasinda degisti");
      if (config_stalled && config_data !== held_config) $fatal(1, "AXI config payload'u stall sirasinda degisti");
      if (output_valid && (^{output_index, output_last, output_data} === 1'bx)) $fatal(1, "Wrapper cikisinda X/Z bulundu");
      input_stalled <= input_valid && !input_ready;
      output_stalled <= output_valid && !output_ready;
      config_stalled <= config_valid && !config_ready;
      if (input_valid && !input_ready) input_stall_cycles <= input_stall_cycles + 1;
      if (output_valid && !output_ready) output_stall_cycles <= output_stall_cycles + 1;
      if (config_valid && config_ready) begin
        config_handshakes <= config_handshakes + 1;
        if (config_data !== 8'h01) $fatal(1, "Forward config payload'u 0x01 degil");
      end
      held_input <= {input_last, input_data};
      held_output <= {output_index, output_last, output_data};
      held_config <= config_data;
    end
  end

  initial begin
    integer accepted_cycle;
    $readmemh("datasets/fixtures/phase06c/axis-input.mem", fixture_input);
    $readmemh("datasets/fixtures/phase06c/stub-expected.mem", fixture_stub_expected);

    apply_reset();
    @(negedge clk);
    input_data = fixture_input[0];
    input_valid = 1'b1;
    repeat (3) begin
      @(posedge clk);
      if (input_ready || configuration_done) $fatal(1, "Konfigurasyon tamamlanmadan giris kabul edildi");
    end
    @(negedge clk);
    allow_config_ready = 1'b1;
    wait_for_configuration();
    if (!input_ready) $fatal(1, "Latency probe konfigurasyon sonrasi kabul edilmedi");
    #1 accepted_cycle = cycle_counter;
    @(negedge clk);
    input_valid = 1'b0;
    do begin @(posedge clk); #1; end while (!output_valid);
    measured_latency = cycle_counter - accepted_cycle;
    if (output_data !== fixture_stub_expected[0] || output_index !== 0 || output_last !== 0) $fatal(1, "Latency probe payload hatasi");
    @(posedge clk);
    checked_samples = checked_samples + 1;
    apply_reset();
    wait_for_configuration();

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
      begin
        while (!output_valid) @(posedge clk);
        repeat (3) @(posedge clk);
        @(negedge clk);
        if (!(output_valid && !output_ready)) $fatal(1, "Event plumbing output stall sirasinda uyarilmadi");
        event_injected_while_output_stalled = 1'b1;
        inject_events = 6'h3f;
        @(negedge clk);
        inject_events = '0;
      end
    join
    if (status_events !== 6'h3f) $fatal(1, "AMD event/status sticky plumbing eksik: %02h", status_events);
    if (!event_injected_while_output_stalled) $fatal(1, "Event stall kapsami gerceklesmedi");

    @(negedge clk);
    random_ready_enable = 1'b0;
    force_output_stall = 1'b0;
    fork
      drive_words(0, 17);
      check_words(0, 17);
    join

    @(negedge clk);
    force_output_stall = 1'b1;
    drive_words(17, 1);
    while (!output_valid) @(posedge clk);
    apply_reset();
    if (output_valid || status_events != 0) $fatal(1, "Reset pending output veya status durumunu temizlemedi");
    @(negedge clk);
    force_output_stall = 1'b0;
    wait_for_configuration();

    fork
      drive_words(0, 4096);
      check_words(0, 4096);
    join

    repeat (3) @(posedge clk);
    if (measured_latency != 2) $fatal(1, "Wrapper-boundary latency beklenen 2 degil: %0d", measured_latency);
    if (checked_samples != EXPECTED_CHECKED_SAMPLES) $fatal(1, "Kontrol edilen ornek sayisi yanlis: %0d", checked_samples);
    if (checked_tlast != 11) $fatal(1, "Kontrol edilen TLAST sayisi yanlis: %0d", checked_tlast);
    if (config_handshakes != 3) $fatal(1, "Config handshake sayisi yanlis: %0d", config_handshakes);
    if (input_stall_cycles == 0 || output_stall_cycles == 0) $fatal(1, "Backpressure gerceklesmedi");

    $display("PHASE-06C TB LATENCY: wrapper_boundary=%0d cycles", measured_latency);
    $display("PHASE-06C TB COVERAGE: input_stalls=%0d output_stalls=%0d tlast=%0d configs=%0d events=%0d", input_stall_cycles, output_stall_cycles, checked_tlast, config_handshakes, 63);
    $display("PHASE-06C TB PASS: %0d samples checked", checked_samples);
    $finish;
  end
endmodule
