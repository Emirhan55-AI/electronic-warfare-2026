package p0_wideband_recovery_pkg;
  timeunit 1ns;
  timeprecision 1ps;
  localparam int FIXED_COEFFICIENT_BITS = 48;
  localparam int INTEGRATION_BINS = 32;
  localparam int INTEGRATION_LEFT = 15;
  localparam int INTEGRATION_RIGHT = 16;
  localparam int MINIMUM_RECOVERY_SPAN = 41;
  localparam int MAXIMUM_GAP_BINS = 1;
  localparam int MAXIMUM_RECOVERY_CANDIDATES = 96;
  localparam logic [57:0] POWER_MAX_REACHABLE = 58'h200000000000000;
  localparam logic [47:0] NOISE_Q48 = 48'hb8aa3b295c18;
  localparam logic [48:0] REGIONAL_THRESHOLD_Q48 = 49'h1cda993e7663c;
  localparam logic [53:0] INTEGRATED_THRESHOLD_Q48 = 54'h39b5327cecc77c;
endpackage
