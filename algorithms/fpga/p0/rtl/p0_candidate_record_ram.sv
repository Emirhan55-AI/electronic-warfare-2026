`timescale 1ns/1ps

module p0_candidate_record_ram #(
  parameter int DEPTH = 1352,
  parameter int ADDRESS_WIDTH = 11
) (
  input  logic                       aclk,
  input  logic                       write_enable,
  input  logic [ADDRESS_WIDTH-1:0]   write_address,
  input  logic [213:0]               write_data,
  input  logic [ADDRESS_WIDTH-1:0]   read_address,
  output logic [213:0]               read_data
);
  (* ram_style = "block" *) logic [213:0] memory [0:DEPTH-1];

  always_ff @(posedge aclk) begin
    if (write_enable)
      memory[write_address] <= write_data;
    read_data <= memory[read_address];
  end
endmodule
