`timescale 1ns/1ps

module p0_os_candidate_ram (
  input  logic         aclk,
  input  logic         write_enable,
  input  logic [10:0]  write_address,
  input  logic [151:0] write_data,
  input  logic [10:0]  read_address,
  output logic [151:0] read_data
);
  import p0_sparse_os_candidate_pkg::*;

  (* ram_style = "block" *) logic [151:0] memory [0:MAXIMUM_OS_CANDIDATES-1];

  always_ff @(posedge aclk) begin
    if (write_enable)
      memory[write_address] <= write_data;
    read_data <= memory[read_address];
  end
endmodule
