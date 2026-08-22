`timescale 1ns/1ps

module tb_axis_fft_linear_power;
  localparam integer EDGE_COUNT = 12;
  localparam integer REAL_COUNT = 45056;
  localparam integer TOTAL_COUNT = EDGE_COUNT + REAL_COUNT;

  logic aclk = 1'b0;
  logic aresetn = 1'b0;
  logic s_axis_tvalid = 1'b0;
  logic s_axis_tready;
  logic [63:0] s_axis_tdata = '0;
  logic s_axis_tlast = 1'b0;
  logic [11:0] s_axis_tuser_index = '0;
  logic m_axis_tvalid;
  logic m_axis_tready = 1'b0;
  logic [57:0] m_axis_tdata;
  logic m_axis_tlast;
  logic [11:0] m_axis_tuser_index;

  logic [63:0] edge_input [0:EDGE_COUNT-1];
  logic [57:0] edge_expected [0:EDGE_COUNT-1];
  logic [63:0] real_input [0:REAL_COUNT-1];
  logic [57:0] real_expected [0:REAL_COUNT-1];

  integer sent = 0;
  integer received = 0;
  integer cycles = 0;
  integer input_stalls = 0;
  integer output_stalls = 0;
  integer timeout = 0;
  integer latency_cycles = -1;
  time first_accept_time = 0;
  logic first_accept_seen = 1'b0;
  logic first_valid_seen = 1'b0;
  logic checking_enabled = 1'b0;
  logic reset_clock_seen = 1'b0;
  logic held_valid = 1'b0;
  logic [70:0] held_payload = '0;

  always #5 aclk = ~aclk;

  axis_fft_linear_power dut (
    .aclk(aclk),
    .aresetn(aresetn),
    .s_axis_tvalid(s_axis_tvalid),
    .s_axis_tready(s_axis_tready),
    .s_axis_tdata(s_axis_tdata),
    .s_axis_tlast(s_axis_tlast),
    .s_axis_tuser_index(s_axis_tuser_index),
    .m_axis_tvalid(m_axis_tvalid),
    .m_axis_tready(m_axis_tready),
    .m_axis_tdata(m_axis_tdata),
    .m_axis_tlast(m_axis_tlast),
    .m_axis_tuser_index(m_axis_tuser_index)
  );

  function automatic logic [63:0] input_word(input integer position);
    if (position < EDGE_COUNT) input_word = edge_input[position];
    else input_word = real_input[position - EDGE_COUNT];
  endfunction

  function automatic logic [57:0] expected_power(input integer position);
    if (position < EDGE_COUNT) expected_power = edge_expected[position];
    else expected_power = real_expected[position - EDGE_COUNT];
  endfunction

  function automatic logic [11:0] expected_index(input integer position);
    if (position < EDGE_COUNT) begin
      expected_index = position == EDGE_COUNT - 1 ? 12'd4095 : position[11:0];
    end else begin
      expected_index = (position - EDGE_COUNT) % 4096;
    end
  endfunction

  function automatic logic expected_last(input integer position);
    if (position < EDGE_COUNT) expected_last = position == EDGE_COUNT - 1;
    else expected_last = ((position - EDGE_COUNT) % 4096) == 4095;
  endfunction

  always @(posedge aclk) begin
    cycles = cycles + 1;
    if (!aresetn) begin
      held_valid <= 1'b0;
      if (reset_clock_seen && m_axis_tvalid !== 1'b0) $fatal(1, "output valid asserted after reset clock edge");
      reset_clock_seen <= 1'b1;
    end else begin
      reset_clock_seen <= 1'b0;
      if (checking_enabled) begin
        if (held_valid && {m_axis_tlast, m_axis_tuser_index, m_axis_tdata} !== held_payload)
          $fatal(1, "output payload changed under backpressure");
        held_valid <= m_axis_tvalid && !m_axis_tready;
        if (m_axis_tvalid && !m_axis_tready)
          held_payload <= {m_axis_tlast, m_axis_tuser_index, m_axis_tdata};

        if (s_axis_tvalid && !s_axis_tready) input_stalls = input_stalls + 1;
        if (m_axis_tvalid && !m_axis_tready) output_stalls = output_stalls + 1;

        if (s_axis_tvalid && s_axis_tready && !first_accept_seen) begin
          first_accept_seen = 1'b1;
          first_accept_time = $time;
        end

        if (m_axis_tvalid && m_axis_tready) begin
          if (received >= TOTAL_COUNT) $fatal(1, "duplicated output sample");
          if (m_axis_tdata !== expected_power(received))
            $fatal(1, "power mismatch at sample %0d: got %h expected %h", received, m_axis_tdata, expected_power(received));
          if (m_axis_tuser_index !== expected_index(received))
            $fatal(1, "XK_INDEX mismatch at sample %0d", received);
          if (m_axis_tlast !== expected_last(received))
            $fatal(1, "TLAST mismatch at sample %0d", received);
          received = received + 1;
        end
      end
    end
  end

  always @(negedge aclk) begin
    if (checking_enabled && first_accept_seen && !first_valid_seen && m_axis_tvalid) begin
      first_valid_seen = 1'b1;
      latency_cycles = ($time - first_accept_time - 5) / 10;
      if (latency_cycles != 2) $fatal(1, "pipeline latency %0d, expected 2", latency_cycles);
    end
    if (!aresetn || !checking_enabled) begin
      m_axis_tready <= 1'b0;
    end else if (received < 8) begin
      m_axis_tready <= 1'b1;
    end else begin
      m_axis_tready <= ((cycles % 13) != 3) && ((cycles % 13) != 4) && ((cycles % 17) != 9);
    end
  end

  task automatic reset_pipeline;
    begin
      @(negedge aclk);
      aresetn <= 1'b0;
      s_axis_tvalid <= 1'b0;
      repeat (3) @(negedge aclk);
      aresetn <= 1'b1;
      @(negedge aclk);
    end
  endtask

  initial begin
    $readmemh("datasets/fixtures/phase06f/edge-input.mem", edge_input);
    $readmemh("datasets/fixtures/phase06f/edge-expected.mem", edge_expected);
    $readmemh("datasets/fixtures/phase06d/cmodel-expected.mem", real_input);
    $readmemh("datasets/fixtures/phase06f/real-power-expected.mem", real_expected);

    // Put one value in flight, then prove synchronous reset flushes the pipeline.
    reset_pipeline();
    @(negedge aclk);
    s_axis_tvalid <= 1'b1;
    s_axis_tdata <= edge_input[6];
    s_axis_tlast <= 1'b1;
    s_axis_tuser_index <= 12'd4095;
    do @(posedge aclk); while (!s_axis_tready);
    @(negedge aclk);
    s_axis_tvalid <= 1'b0;
    aresetn <= 1'b0;
    repeat (3) @(negedge aclk);
    if (m_axis_tvalid !== 1'b0) $fatal(1, "mid-pipeline reset did not flush valid state");
    aresetn <= 1'b1;
    checking_enabled <= 1'b1;

    while (sent < TOTAL_COUNT) begin
      @(negedge aclk);
      s_axis_tvalid <= 1'b1;
      s_axis_tdata <= input_word(sent);
      s_axis_tlast <= expected_last(sent);
      s_axis_tuser_index <= expected_index(sent);
      do @(posedge aclk); while (!s_axis_tready);
      sent = sent + 1;
    end
    @(negedge aclk);
    s_axis_tvalid <= 1'b0;
    s_axis_tdata <= '0;
    s_axis_tlast <= 1'b0;
    s_axis_tuser_index <= '0;

    while (received < TOTAL_COUNT && timeout < 200000) begin
      @(posedge aclk);
      timeout = timeout + 1;
    end
    if (received != TOTAL_COUNT) $fatal(1, "timeout: received %0d/%0d", received, TOTAL_COUNT);
    if (input_stalls == 0 || output_stalls == 0) $fatal(1, "backpressure coverage missing");
    if (!first_valid_seen || latency_cycles != 2) $fatal(1, "latency coverage missing");
    $display("PHASE06F_METRIC latency_cycles=%0d", latency_cycles);
    $display("PHASE06F_METRIC input_stalls=%0d output_stalls=%0d", input_stalls, output_stalls);
    $display("PHASE-06F TB PASS: %0d power results checked", received);
    $finish;
  end
endmodule
