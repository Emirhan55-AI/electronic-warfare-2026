module axis_skid_buffer #(
  parameter int unsigned PAYLOAD_WIDTH = 17
) (
  input  logic                     aclk,
  input  logic                     aresetn,
  input  logic                     s_valid,
  output logic                     s_ready,
  input  logic [PAYLOAD_WIDTH-1:0] s_payload,
  output logic                     m_valid,
  input  logic                     m_ready,
  output logic [PAYLOAD_WIDTH-1:0] m_payload
);
  logic full;
  logic [PAYLOAD_WIDTH-1:0] payload;

  assign s_ready   = !full || m_ready;
  assign m_valid   = full;
  assign m_payload = payload;

  always_ff @(posedge aclk) begin
    if (!aresetn) begin
      full    <= 1'b0;
      payload <= '0;
    end else if (s_ready) begin
      full <= s_valid;
      if (s_valid) begin
        payload <= s_payload;
      end
    end
  end
endmodule
