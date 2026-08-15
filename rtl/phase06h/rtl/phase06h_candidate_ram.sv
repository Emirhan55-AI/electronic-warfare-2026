module phase06h_candidate_ram #(
  parameter int WIDTH = 94,
  parameter int DEPTH = 676,
  parameter int ADDRESS_WIDTH = 10
) (
  input  logic                     aclk,
  input  logic                     write_enable,
  input  logic [ADDRESS_WIDTH-1:0] write_address,
  input  logic [WIDTH-1:0]         write_data,
  input  logic [ADDRESS_WIDTH-1:0] read_address,
  output logic [WIDTH-1:0]         read_data
);
  (* ram_style = "block" *) logic [WIDTH-1:0] memory [0:DEPTH-1];

  always_ff @(posedge aclk) begin
    if (write_enable)
      memory[write_address] <= write_data;
    read_data <= memory[read_address];
  end
endmodule
