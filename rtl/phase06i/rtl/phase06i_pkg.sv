package phase06i_pkg;
  localparam logic [31:0] HEADER_MAGIC = 32'h48493650;
  localparam logic [31:0] TRAILER_MAGIC = 32'h54493650;
  localparam int ABI_VERSION = 1;
  localparam int HEADER_BYTES = 32;
  localparam int RECORD_BYTES = 40;
  localparam int TRAILER_BYTES = 32;
  localparam int MAX_CANDIDATES = 1352;
endpackage
