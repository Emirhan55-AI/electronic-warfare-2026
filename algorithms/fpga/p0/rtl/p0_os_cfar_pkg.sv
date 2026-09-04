`timescale 1ns/1ps

package p0_os_cfar_pkg;
  localparam int FRAME_LENGTH = 4096;
  localparam int POWER_WIDTH = 58;
  localparam int REFERENCE_PER_SIDE = 16;
  localparam int GUARD_PER_SIDE = 4;
  localparam int RADIUS = REFERENCE_PER_SIDE + GUARD_PER_SIDE;
  localparam int ORDER_STATISTIC_RANK = 24;
  localparam int COEFFICIENT_FRACTION_BITS = 32;
  localparam logic [35:0] ALPHA_Q32 = 36'd36851433755;
  localparam logic [33:0] WEAK_ALPHA_Q32 = 34'd17098572778;
  localparam logic [3:0] OUTPUT_MARKER = 4'hA;
endpackage
