`timescale 1ns/1ps

module tb_phase06e_axis_input_register_slice;
  localparam integer SAMPLE_COUNT = 20;
  logic aclk = 1'b0;
  logic aresetn = 1'b0;
  logic enable = 1'b0;
  logic s_axis_tvalid = 1'b0;
  logic s_axis_tready;
  logic [31:0] s_axis_tdata = '0;
  logic s_axis_tlast = 1'b0;
  logic m_axis_tvalid;
  logic m_axis_tready = 1'b0;
  logic [31:0] m_axis_tdata;
  logic m_axis_tlast;
  integer sent = 0;
  integer received = 0;
  integer timeout = 0;
  logic [32:0] held_payload;
  logic held_valid = 1'b0;
  logic [7:0] ready_pattern = 8'b10110100;

  always #5 aclk = ~aclk;

  phase06e_axis_input_register_slice dut (
    .aclk(aclk),
    .aresetn(aresetn),
    .enable(enable),
    .s_axis_tvalid(s_axis_tvalid),
    .s_axis_tready(s_axis_tready),
    .s_axis_tdata(s_axis_tdata),
    .s_axis_tlast(s_axis_tlast),
    .m_axis_tvalid(m_axis_tvalid),
    .m_axis_tready(m_axis_tready),
    .m_axis_tdata(m_axis_tdata),
    .m_axis_tlast(m_axis_tlast)
  );

  always @(posedge aclk) begin
    if (!aresetn) begin
      received <= 0;
      held_valid <= 1'b0;
    end else begin
      if (m_axis_tvalid && !m_axis_tready) begin
        if (held_valid && held_payload !== {m_axis_tlast, m_axis_tdata})
          $fatal(1, "output payload changed under backpressure");
        held_payload <= {m_axis_tlast, m_axis_tdata};
        held_valid <= 1'b1;
      end else begin
        held_valid <= 1'b0;
      end
      if (m_axis_tvalid && m_axis_tready) begin
        if (m_axis_tdata !== received[31:0]) $fatal(1, "payload order mismatch");
        if (m_axis_tlast !== ((received == 7) || (received == 15)))
          $fatal(1, "TLAST mismatch");
        received <= received + 1;
      end
    end
  end

  always @(negedge aclk) begin
    if (aresetn) begin
      ready_pattern <= {ready_pattern[6:0], ready_pattern[7] ^ ready_pattern[5]};
      m_axis_tready <= ready_pattern[0];
    end
  end

  initial begin
    repeat (4) @(posedge aclk);
    @(negedge aclk);
    aresetn = 1'b1;
    s_axis_tvalid = 1'b1;
    s_axis_tdata = 32'hdeadbeef;
    repeat (3) begin
      @(posedge aclk);
      if (s_axis_tready !== 1'b0) $fatal(1, "input accepted before configuration enable");
    end
    @(negedge aclk);
    s_axis_tvalid = 1'b0;
    enable = 1'b1;

    for (sent = 0; sent < SAMPLE_COUNT; sent = sent + 1) begin
      @(negedge aclk);
      s_axis_tvalid = 1'b1;
      s_axis_tdata = sent[31:0];
      s_axis_tlast = (sent == 7) || (sent == 15);
      while (!s_axis_tready) @(negedge aclk);
    end
    @(negedge aclk);
    s_axis_tvalid = 1'b0;
    s_axis_tlast = 1'b0;

    while (received < SAMPLE_COUNT && timeout < 200) begin
      @(posedge aclk);
      timeout = timeout + 1;
    end
    if (received != SAMPLE_COUNT) $fatal(1, "output timeout");
    $display("PHASE-06E AXI REGISTER SLICE TB PASS: %0d results checked", received);
    $finish;
  end
endmodule
