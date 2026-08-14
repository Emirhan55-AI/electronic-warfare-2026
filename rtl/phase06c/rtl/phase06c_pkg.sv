package phase06c_pkg;
  localparam int unsigned PHASE06C_FRAME_LENGTH           = 4096;
  localparam int unsigned PHASE06C_INPUT_WIDTH            = 32;
  localparam int unsigned PHASE06C_INPUT_COMPONENT_WIDTH  = 16;
  localparam int unsigned PHASE06C_INPUT_FRAC_BITS        = 15;
  localparam int unsigned PHASE06C_OUTPUT_WIDTH           = 64;
  localparam int unsigned PHASE06C_OUTPUT_COMPONENT_WIDTH = 29;
  localparam int unsigned PHASE06C_OUTPUT_CONTAINER_WIDTH = 32;
  localparam int unsigned PHASE06C_OUTPUT_FRAC_BITS       = 15;
  localparam int unsigned PHASE06C_INDEX_WIDTH            = 12;
  localparam int unsigned PHASE06C_CONFIG_WIDTH           = 8;
  localparam logic [7:0] PHASE06C_FORWARD_CONFIG          = 8'h01;
  localparam int unsigned PHASE06C_STATUS_WIDTH           = 6;
endpackage
