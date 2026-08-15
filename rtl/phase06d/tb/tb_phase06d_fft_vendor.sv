`timescale 1ns/1ps

module tb_phase06d_fft_vendor;
  localparam int FRAME_LENGTH = 4096;
  localparam int FRAME_COUNT = 11;
  localparam int TOTAL_SAMPLES = FRAME_LENGTH * FRAME_COUNT;

  logic aclk = 1'b0;
  logic aresetn = 1'b0;
  logic s_axis_tvalid = 1'b0;
  logic s_axis_tready;
  logic [31:0] s_axis_tdata = '0;
  logic s_axis_tlast = 1'b0;
  logic m_axis_tvalid;
  logic m_axis_tready = 1'b0;
  logic [63:0] m_axis_tdata;
  logic m_axis_tlast;
  logic [11:0] m_axis_tuser_index;
  logic configuration_done;
  logic [5:0] status_events_sticky;

  logic fft_config_valid;
  logic fft_config_ready;
  logic [7:0] fft_config_data;
  logic fft_input_valid;
  logic fft_input_ready;
  logic [31:0] fft_input_data;
  logic fft_input_last;
  logic fft_output_valid;
  logic fft_output_ready;
  logic [63:0] fft_output_data;
  logic fft_output_last;
  logic [11:0] fft_output_index;
  logic event_frame_started;
  logic event_tlast_unexpected;
  logic event_tlast_missing;
  logic event_status_channel_halt;
  logic event_data_in_channel_halt;
  logic event_data_out_channel_halt;

  logic [31:0] input_words [0:TOTAL_SAMPLES-1];
  logic [63:0] expected_words [0:TOTAL_SAMPLES-1];
  string input_path;
  string expected_path;
  string capture_path;
  integer capture_file;

  integer cycle_count = 0;
  integer output_count = 0;
  integer mismatch_count = 0;
  integer index_mismatch_count = 0;
  integer tlast_mismatch_count = 0;
  integer padding_mismatch_count = 0;
  integer stability_mismatch_count = 0;
  integer frame_started_count = 0;
  integer unexpected_count = 0;
  integer missing_count = 0;
  integer status_halt_count = 0;
  integer input_halt_count = 0;
  integer output_halt_count = 0;
  integer first_external_input_cycle = -1;
  integer first_core_input_cycle = -1;
  integer first_core_output_cycle = -1;
  integer first_external_output_cycle = -1;
  integer final_external_input_cycle = -1;
  integer final_core_input_cycle = -1;
  integer final_external_output_cycle = -1;
  integer final_external_output_valid_cycle = -1;
  integer final_core_output_valid_cycle = -1;
  integer main_input_transfers = 0;
  integer main_core_input_transfers = 0;
  integer main_core_output_transfers = 0;
  integer main_output_transfers = 0;
  integer main_input_stall_cycles = 0;
  integer main_core_input_wait_cycles = 0;
  integer main_output_stall_cycles = 0;
  integer main_current_input_run = 0;
  integer main_max_input_run = 0;
  integer main_input_tlast_count = 0;
  integer main_output_tlast_count = 0;
  integer main_core_output_frame_count = 0;
  integer early_unexpected_cycle = -1;
  integer missing_event_cycle = -1;
  integer late_missing_cycle = -1;
  integer late_unexpected_cycle = -1;
  integer event_width_mismatch_count = 0;
  integer control_mismatch_count = 0;
  integer configuration_handshake_count = 0;
  integer main_configuration_cycle = -1;
  integer test_mode = 0;
  integer post_reset_output_count = 0;
  integer post_reset_input_index;
  integer timeout_counter;
  logic [15:0] ready_lfsr = 16'h1;
  logic held_output_valid = 1'b0;
  logic [76:0] held_output_payload = '0;
  logic held_input_valid = 1'b0;
  logic [32:0] held_input_payload = '0;
  logic previous_unexpected = 1'b0;
  logic previous_missing = 1'b0;

  always #5 aclk = ~aclk;

  axis_fft_wrapper wrapper (
    .aclk(aclk), .aresetn(aresetn),
    .s_axis_tvalid(s_axis_tvalid), .s_axis_tready(s_axis_tready),
    .s_axis_tdata(s_axis_tdata), .s_axis_tlast(s_axis_tlast),
    .m_axis_tvalid(m_axis_tvalid), .m_axis_tready(m_axis_tready),
    .m_axis_tdata(m_axis_tdata), .m_axis_tlast(m_axis_tlast),
    .m_axis_tuser_index(m_axis_tuser_index),
    .fft_s_axis_config_tvalid(fft_config_valid),
    .fft_s_axis_config_tready(fft_config_ready),
    .fft_s_axis_config_tdata(fft_config_data),
    .fft_s_axis_data_tvalid(fft_input_valid),
    .fft_s_axis_data_tready(fft_input_ready),
    .fft_s_axis_data_tdata(fft_input_data),
    .fft_s_axis_data_tlast(fft_input_last),
    .fft_m_axis_data_tvalid(fft_output_valid),
    .fft_m_axis_data_tready(fft_output_ready),
    .fft_m_axis_data_tdata(fft_output_data),
    .fft_m_axis_data_tlast(fft_output_last),
    .fft_m_axis_data_tuser_index(fft_output_index),
    .fft_event_frame_started(event_frame_started),
    .fft_event_tlast_unexpected(event_tlast_unexpected),
    .fft_event_tlast_missing(event_tlast_missing),
    .fft_event_status_channel_halt(event_status_channel_halt),
    .fft_event_data_in_channel_halt(event_data_in_channel_halt),
    .fft_event_data_out_channel_halt(event_data_out_channel_halt),
    .configuration_done(configuration_done),
    .status_events_sticky(status_events_sticky)
  );

  amd_xfft_adapter adapter (
    .aclk(aclk), .aresetn(aresetn),
    .s_axis_config_tvalid(fft_config_valid),
    .s_axis_config_tready(fft_config_ready),
    .s_axis_config_tdata(fft_config_data),
    .s_axis_data_tvalid(fft_input_valid),
    .s_axis_data_tready(fft_input_ready),
    .s_axis_data_tdata(fft_input_data),
    .s_axis_data_tlast(fft_input_last),
    .m_axis_data_tvalid(fft_output_valid),
    .m_axis_data_tready(fft_output_ready),
    .m_axis_data_tdata(fft_output_data),
    .m_axis_data_tlast(fft_output_last),
    .m_axis_data_tuser_index(fft_output_index),
    .event_frame_started(event_frame_started),
    .event_tlast_unexpected(event_tlast_unexpected),
    .event_tlast_missing(event_tlast_missing),
    .event_status_channel_halt(event_status_channel_halt),
    .event_data_in_channel_halt(event_data_in_channel_halt),
    .event_data_out_channel_halt(event_data_out_channel_halt)
  );

  always @(posedge aclk) begin
    cycle_count <= cycle_count + 1;
    if (aresetn) begin
      if (!configuration_done && s_axis_tready !== 1'b0)
        control_mismatch_count <= control_mismatch_count + 1;
      if (fft_config_valid && fft_config_data !== 8'h01)
        control_mismatch_count <= control_mismatch_count + 1;
      if (fft_config_valid && fft_config_ready) begin
        configuration_handshake_count <= configuration_handshake_count + 1;
        if (configuration_handshake_count == 0) main_configuration_cycle <= cycle_count;
      end
      if (event_frame_started) frame_started_count <= frame_started_count + 1;
      if (event_tlast_unexpected) unexpected_count <= unexpected_count + 1;
      if (event_tlast_missing) missing_count <= missing_count + 1;
      if (event_status_channel_halt) status_halt_count <= status_halt_count + 1;
      if (event_data_in_channel_halt) input_halt_count <= input_halt_count + 1;
      if (event_data_out_channel_halt) output_halt_count <= output_halt_count + 1;
      if (event_tlast_unexpected && previous_unexpected) event_width_mismatch_count <= event_width_mismatch_count + 1;
      if (event_tlast_missing && previous_missing) event_width_mismatch_count <= event_width_mismatch_count + 1;
      previous_unexpected <= event_tlast_unexpected;
      previous_missing <= event_tlast_missing;
      if (test_mode == 2 && event_tlast_unexpected && early_unexpected_cycle < 0)
        early_unexpected_cycle <= cycle_count;
      if (test_mode == 3 && event_tlast_missing && missing_event_cycle < 0)
        missing_event_cycle <= cycle_count;
      if (test_mode == 4 && event_tlast_missing && late_missing_cycle < 0)
        late_missing_cycle <= cycle_count;
      if (test_mode == 4 && event_tlast_unexpected && late_unexpected_cycle < 0)
        late_unexpected_cycle <= cycle_count;
      if (test_mode == 1 && s_axis_tvalid && s_axis_tready) begin
        if (first_external_input_cycle < 0) first_external_input_cycle <= cycle_count;
        final_external_input_cycle <= cycle_count;
        main_input_transfers <= main_input_transfers + 1;
        main_current_input_run <= main_current_input_run + 1;
        if (main_current_input_run + 1 > main_max_input_run)
          main_max_input_run <= main_current_input_run + 1;
        if (s_axis_tlast) main_input_tlast_count <= main_input_tlast_count + 1;
      end else if (test_mode == 1) begin
        main_current_input_run <= 0;
      end
      if (test_mode == 1 && s_axis_tvalid && !s_axis_tready)
        main_input_stall_cycles <= main_input_stall_cycles + 1;
      if (test_mode == 1 && fft_input_valid && !fft_input_ready)
        main_core_input_wait_cycles <= main_core_input_wait_cycles + 1;
      if (test_mode == 1 && m_axis_tvalid && !m_axis_tready)
        main_output_stall_cycles <= main_output_stall_cycles + 1;
      if (test_mode == 1 && fft_input_valid && fft_input_ready) begin
        main_core_input_transfers <= main_core_input_transfers + 1;
        if (first_core_input_cycle < 0) first_core_input_cycle <= cycle_count;
        final_core_input_cycle <= cycle_count;
      end
      if (test_mode == 1 && fft_output_valid && first_core_output_cycle < 0)
        first_core_output_cycle <= cycle_count;
      if (test_mode == 1 && fft_output_valid && fft_output_index == 12'd4095 &&
          main_core_output_frame_count == FRAME_COUNT-1 && final_core_output_valid_cycle < 0)
        final_core_output_valid_cycle <= cycle_count;
      if (test_mode == 1 && fft_output_valid && fft_output_ready) begin
        main_core_output_transfers <= main_core_output_transfers + 1;
        if (fft_output_last) main_core_output_frame_count <= main_core_output_frame_count + 1;
      end
      if (test_mode == 1 && m_axis_tvalid && m_axis_tuser_index == 12'd4095 &&
          main_output_tlast_count == FRAME_COUNT-1 && final_external_output_valid_cycle < 0)
        final_external_output_valid_cycle <= cycle_count;
      if (test_mode == 1 && m_axis_tvalid && m_axis_tready) begin
        if (first_external_output_cycle < 0) first_external_output_cycle <= cycle_count;
        final_external_output_cycle <= cycle_count;
        if (m_axis_tdata !== expected_words[output_count]) begin
          mismatch_count <= mismatch_count + 1;
          if (mismatch_count < 8)
            $display("MISMATCH sample=%0d actual=%016x expected=%016x", output_count, m_axis_tdata, expected_words[output_count]);
        end
        if (m_axis_tuser_index !== (output_count % FRAME_LENGTH)) index_mismatch_count <= index_mismatch_count + 1;
        if (m_axis_tlast !== ((output_count % FRAME_LENGTH) == FRAME_LENGTH-1)) tlast_mismatch_count <= tlast_mismatch_count + 1;
        $fdisplay(capture_file, "%016x", m_axis_tdata);
        output_count <= output_count + 1;
        main_output_transfers <= main_output_transfers + 1;
        if (m_axis_tlast) main_output_tlast_count <= main_output_tlast_count + 1;
      end
      if (test_mode == 5 && m_axis_tvalid && m_axis_tready) begin
        if (m_axis_tdata !== 64'b0 || m_axis_tuser_index !== post_reset_output_count[11:0] ||
            m_axis_tlast !== (post_reset_output_count == FRAME_LENGTH-1)) begin
          mismatch_count <= mismatch_count + 1;
        end
        post_reset_output_count <= post_reset_output_count + 1;
      end
      if (fft_output_valid) begin
        if (adapter.amd_m_axis_data_tuser[15:12] !== 4'b0000) padding_mismatch_count <= padding_mismatch_count + 1;
        if (adapter.amd_m_axis_data_tdata[31:29] !== {3{adapter.amd_m_axis_data_tdata[28]}} ||
            adapter.amd_m_axis_data_tdata[63:61] !== {3{adapter.amd_m_axis_data_tdata[60]}})
          padding_mismatch_count <= padding_mismatch_count + 1;
      end
    end
  end

  always @(negedge aclk) begin
    if (!aresetn) begin
      held_output_valid <= 1'b0;
      held_input_valid <= 1'b0;
    end else begin
      if (held_output_valid && {m_axis_tuser_index, m_axis_tlast, m_axis_tdata} !== held_output_payload)
        stability_mismatch_count <= stability_mismatch_count + 1;
      if (held_input_valid && {s_axis_tlast, s_axis_tdata} !== held_input_payload)
        stability_mismatch_count <= stability_mismatch_count + 1;
      held_output_valid <= m_axis_tvalid && !m_axis_tready;
      held_output_payload <= {m_axis_tuser_index, m_axis_tlast, m_axis_tdata};
      held_input_valid <= s_axis_tvalid && !s_axis_tready;
      held_input_payload <= {s_axis_tlast, s_axis_tdata};
    end
  end

  task automatic reset_core;
    begin
      @(negedge aclk);
      aresetn = 1'b0;
      s_axis_tvalid = 1'b0;
      s_axis_tlast = 1'b0;
      m_axis_tready = 1'b0;
      repeat (5) @(posedge aclk);
      @(negedge aclk);
      aresetn = 1'b1;
      timeout_counter = 0;
      while (!configuration_done && timeout_counter < 100) begin
        @(posedge aclk);
        timeout_counter = timeout_counter + 1;
      end
      if (!configuration_done) $fatal(1, "configuration handshake timeout");
      if (fft_config_data !== 8'h01) $fatal(1, "forward configuration payload mismatch");
    end
  endtask

  task automatic send_word(input logic [31:0] word, input logic last_value);
    logic accepted;
    begin
      accepted = 1'b0;
      while (!accepted) begin
        @(negedge aclk);
        s_axis_tvalid = 1'b1;
        s_axis_tdata = word;
        s_axis_tlast = last_value;
        @(posedge aclk);
        accepted = s_axis_tready;
      end
      @(negedge aclk);
      s_axis_tvalid = 1'b0;
      s_axis_tlast = 1'b0;
    end
  endtask

  task automatic send_main_frames;
    integer sample;
    logic accepted;
    begin
      for (sample = 0; sample < TOTAL_SAMPLES; sample = sample + 1) begin
        accepted = 1'b0;
        while (!accepted) begin
          @(negedge aclk);
          s_axis_tvalid = 1'b1;
          s_axis_tdata = input_words[sample];
          s_axis_tlast = ((sample % FRAME_LENGTH) == FRAME_LENGTH-1);
          @(posedge aclk);
          accepted = s_axis_tready;
        end
      end
      @(negedge aclk);
      s_axis_tvalid = 1'b0;
      s_axis_tlast = 1'b0;
    end
  endtask

  task automatic drive_output_ready;
    begin
      while (test_mode == 1) begin
        @(negedge aclk);
        ready_lfsr = {ready_lfsr[14:0], ready_lfsr[15] ^ ready_lfsr[13] ^ ready_lfsr[12] ^ ready_lfsr[10]};
        m_axis_tready = ready_lfsr[0] | ready_lfsr[3];
      end
    end
  endtask

  task automatic send_malformed_frame(input integer mode);
    integer sample;
    logic last_value;
    begin
      for (sample = 0; sample < (mode == 3 ? FRAME_LENGTH+1 : FRAME_LENGTH); sample = sample + 1) begin
        last_value = 1'b0;
        if (mode == 1 && (sample == 100 || sample == FRAME_LENGTH-1)) last_value = 1'b1;
        if (mode == 3 && sample == FRAME_LENGTH) last_value = 1'b1;
        send_word(32'b0, last_value);
      end
    end
  endtask

  initial begin
    if (!$value$plusargs("INPUT_MEM=%s", input_path)) $fatal(1, "INPUT_MEM plusarg missing");
    if (!$value$plusargs("EXPECTED_MEM=%s", expected_path)) $fatal(1, "EXPECTED_MEM plusarg missing");
    if (!$value$plusargs("CAPTURE_MEM=%s", capture_path)) $fatal(1, "CAPTURE_MEM plusarg missing");
    $readmemh(input_path, input_words);
    $readmemh(expected_path, expected_words);
    capture_file = $fopen(capture_path, "w");
    if (capture_file == 0) $fatal(1, "capture file open failed");

    reset_core();
    test_mode = 1;
    fork
      send_main_frames();
      drive_output_ready();
    join_none
    timeout_counter = 0;
    while (output_count < TOTAL_SAMPLES && timeout_counter < 250000) begin
      @(posedge aclk);
      timeout_counter = timeout_counter + 1;
    end
    if (output_count != TOTAL_SAMPLES) $fatal(1, "main output timeout count=%0d", output_count);
    test_mode = 0;
    @(negedge aclk); m_axis_tready = 1'b1;
    wait fork;

    reset_core();
    test_mode = 2;
    send_malformed_frame(1);
    repeat (20) @(posedge aclk);
    if (!status_events_sticky[1]) $fatal(1, "early TLAST event not observed");

    reset_core();
    test_mode = 3;
    send_malformed_frame(2);
    repeat (20) @(posedge aclk);
    if (!status_events_sticky[2]) $fatal(1, "missing TLAST event not observed");

    reset_core();
    test_mode = 4;
    send_malformed_frame(3);
    repeat (20) @(posedge aclk);
    if (!status_events_sticky[2] || !status_events_sticky[1]) $fatal(1, "late TLAST events not observed");

    reset_core();
    test_mode = 5;
    repeat (127) send_word(32'h00000000, 1'b0);
    @(negedge aclk); aresetn = 1'b0; s_axis_tvalid = 1'b0; m_axis_tready = 1'b0;
    repeat (5) @(posedge aclk);
    if (configuration_done !== 1'b0 || status_events_sticky !== 6'b0) $fatal(1, "reset state not cleared");
    @(negedge aclk); aresetn = 1'b1;
    wait (configuration_done);
    @(negedge aclk); m_axis_tready = 1'b1;
    for (post_reset_input_index = 0; post_reset_input_index < FRAME_LENGTH; post_reset_input_index = post_reset_input_index + 1)
      send_word(32'h00000000, post_reset_input_index == FRAME_LENGTH-1);
    timeout_counter = 0;
    while (post_reset_output_count < FRAME_LENGTH && timeout_counter < 30000) begin
      @(posedge aclk);
      timeout_counter = timeout_counter + 1;
    end
    if (post_reset_output_count != FRAME_LENGTH) $fatal(1, "post-reset frame timeout");

    $fclose(capture_file);
    if (mismatch_count != 0 || index_mismatch_count != 0 || tlast_mismatch_count != 0 ||
        padding_mismatch_count != 0 || stability_mismatch_count != 0 || event_width_mismatch_count != 0 ||
        control_mismatch_count != 0 || configuration_handshake_count != 6 ||
        first_external_input_cycle <= main_configuration_cycle) begin
      $fatal(1, "verification mismatch data=%0d index=%0d tlast=%0d padding=%0d stability=%0d",
             mismatch_count, index_mismatch_count, tlast_mismatch_count, padding_mismatch_count, stability_mismatch_count);
    end else begin
      $display("PHASE06D_METRIC total_samples=%0d", output_count);
      $display("PHASE06D_METRIC configuration_handshakes=%0d", configuration_handshake_count);
      $display("PHASE06D_METRIC core_latency_cycles=%0d", first_core_output_cycle-first_core_input_cycle);
      $display("PHASE06D_METRIC wrapper_latency_cycles=%0d", first_external_output_cycle-first_external_input_cycle);
      $display("PHASE06D_METRIC final_drain_cycles=%0d", final_external_output_cycle-final_external_input_cycle);
      $display("PHASE06D_METRIC final_output_valid_cycles=%0d", final_external_output_valid_cycle-final_external_input_cycle);
      $display("PHASE06D_METRIC final_core_output_valid_cycles=%0d", final_core_output_valid_cycle-final_core_input_cycle);
      $display("PHASE06D_METRIC throughput input=%0d core_input=%0d core_output=%0d output=%0d input_stalls=%0d core_wait=%0d output_stalls=%0d max_input_run=%0d input_tlast=%0d output_tlast=%0d",
               main_input_transfers, main_core_input_transfers, main_core_output_transfers, main_output_transfers,
               main_input_stall_cycles, main_core_input_wait_cycles, main_output_stall_cycles,
               main_max_input_run, main_input_tlast_count, main_output_tlast_count);
      $display("PHASE06D_METRIC events frame_started=%0d unexpected=%0d missing=%0d status_halt=%0d input_halt=%0d output_halt=%0d",
               frame_started_count, unexpected_count, missing_count, status_halt_count, input_halt_count, output_halt_count);
      $display("PHASE06D_METRIC event_cycles early_unexpected=%0d missing=%0d late_missing=%0d late_unexpected=%0d pulse_width_cycles=1",
               early_unexpected_cycle, missing_event_cycle, late_missing_cycle, late_unexpected_cycle);
      $display("PHASE-06D XSIM PASS: 45056 vendor FFT results checked");
    end
    $finish;
  end
endmodule
