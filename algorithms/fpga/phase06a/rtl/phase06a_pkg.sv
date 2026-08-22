package phase06a_pkg;
  localparam int unsigned PHASE06A_FRAME_LENGTH       = 4096;
  localparam int unsigned PHASE06A_POWER_WIDTH        = 16;
  localparam int unsigned PHASE06A_ENERGY_WIDTH       = 28;
  localparam int unsigned PHASE06A_INDEX_WIDTH        = 12;
  localparam int unsigned PHASE06A_SAMPLE_COUNT_WIDTH = 13;
  localparam int unsigned PHASE06A_RESULT_WIDTH       = 72;

  localparam logic [1:0] PHASE06A_ERROR_NONE          = 2'd0;
  localparam logic [1:0] PHASE06A_ERROR_EARLY_TLAST   = 2'd1;
  localparam logic [1:0] PHASE06A_ERROR_MISSING_TLAST = 2'd2;

  typedef struct packed {
    logic [PHASE06A_ENERGY_WIDTH-1:0]       total_energy;
    logic [PHASE06A_POWER_WIDTH-1:0]        peak_power;
    logic [PHASE06A_INDEX_WIDTH-1:0]        peak_index;
    logic [PHASE06A_SAMPLE_COUNT_WIDTH-1:0] sample_count;
    logic                                    protocol_error;
    logic [1:0]                              error_code;
  } phase06a_result_t;
endpackage
