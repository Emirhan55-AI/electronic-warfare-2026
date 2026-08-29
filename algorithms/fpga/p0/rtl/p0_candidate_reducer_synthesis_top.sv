module p0_candidate_reducer_synthesis_top (
  input  logic        aclk,
  input  logic        aresetn,
  input  logic        s_axis_tvalid,
  input  logic [57:0] s_axis_tdata,
  input  logic        s_axis_tlast,
  input  logic [11:0] s_axis_tuser_index,
  // Synthesis-only observability bus.  The complete internal record is folded
  // into 124 pins so the wrapper remains placeable on the Zynq-7020 package
  // without implying a board-level interface definition.
  output logic [123:0] observable
);
  logic        s_axis_tready;
  logic        m_axis_tvalid;
  logic        m_axis_tready;
  logic [57:0] m_axis_tdata;
  logic        m_axis_tlast;
  logic [11:0] m_axis_tuser_start_shifted_bin;
  logic [11:0] m_axis_tuser_end_shifted_bin;
  logic [11:0] m_axis_tuser_peak_shifted_bin;
  logic [11:0] m_axis_tuser_coarse_span_bins;
  logic [57:0] m_axis_tuser_noise;
  logic [61:0] m_axis_tuser_threshold;
  logic [1:0]  m_axis_tuser_pfa_select;
  logic        m_axis_tuser_evaluate_center;
  logic        m_axis_tuser_candidate_valid;
  logic [15:0] completed_frame_count;
  logic [8:0]  status_sticky;

  assign m_axis_tready = 1'b1;

  p0_candidate_reducer_top reducer_i (
    .aclk,
    .aresetn,
    .s_axis_tvalid,
    .s_axis_tready,
    .s_axis_tdata,
    .s_axis_tlast,
    .s_axis_tuser_index,
    .m_axis_tvalid,
    .m_axis_tready,
    .m_axis_tdata,
    .m_axis_tlast,
    .m_axis_tuser_start_shifted_bin,
    .m_axis_tuser_end_shifted_bin,
    .m_axis_tuser_peak_shifted_bin,
    .m_axis_tuser_coarse_span_bins,
    .m_axis_tuser_noise,
    .m_axis_tuser_threshold,
    .m_axis_tuser_pfa_select,
    .m_axis_tuser_evaluate_center,
    .m_axis_tuser_candidate_valid,
    .completed_frame_count,
    .status_sticky
  );

  logic [255:0] observable_full;

  assign observable_full = {
    status_sticky,
    completed_frame_count,
    m_axis_tuser_candidate_valid,
    m_axis_tuser_pfa_select,
    m_axis_tuser_threshold,
    m_axis_tuser_noise,
    m_axis_tuser_coarse_span_bins,
    m_axis_tuser_peak_shifted_bin,
    m_axis_tuser_end_shifted_bin,
    m_axis_tuser_start_shifted_bin,
    m_axis_tlast,
    m_axis_tvalid,
    m_axis_tdata
  };

  assign observable = observable_full[123:0] ^ observable_full[247:124]
                    ^ {116'b0, observable_full[255:248]};
endmodule
