package phase06g_pkg;
  localparam int FRAME_LENGTH = 4096;
  localparam int REGION_SIZE = 256;
  localparam int REGION_COUNT = 16;
  localparam int POWER_WIDTH = 58;
  localparam int COEFFICIENT_FRACTION_BITS = 24;
  localparam logic [25:0] C_NOISE_Q24 = 26'd24204406;
  localparam logic [28:0] C_COMBINED_PFA_1E3_Q24 = 29'd167198116;
  localparam logic [28:0] C_COMBINED_PFA_1E4_Q24 = 29'd222930821;
  localparam logic [28:0] C_COMBINED_PFA_1E5_Q24 = 29'd278663526;
endpackage
