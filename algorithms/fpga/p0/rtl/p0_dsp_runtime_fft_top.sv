module p0_dsp_runtime_fft_top (
  input  logic        aclk,
  input  logic        aresetn,
  input  logic        s_axis_tvalid,
  output logic        s_axis_tready,
  input  logic [15:0] s_axis_tdata,
  input  logic [1:0]  s_axis_tkeep,
  input  logic        s_axis_tlast,
  output logic        m_axis_tvalid,
  input  logic        m_axis_tready,
  output logic [63:0] m_axis_tdata,
  output logic [7:0]  m_axis_tkeep,
  output logic        m_axis_tlast,
  output logic [13:0] m_axis_bin_index,

  input  logic        hold_input,
  output logic        pipeline_idle,
  input  logic        config_valid,
  output logic        config_ready,
  input  logic [3:0]  config_fft_log2,
  input  logic [35:0] config_alpha_q32,
  input  logic [33:0] config_weak_alpha_q32,
  output logic        config_applied,
  output logic        config_rejected,
  output logic [3:0]  active_fft_log2,
  output logic [35:0] active_alpha_q32,
  output logic [33:0] active_weak_alpha_q32,
  output logic        configuration_done,
  output logic [9:0]  status_events_sticky
);
  logic input_ready, input_enabled, input_in_frame, frame_in_flight;
  logic transaction_active, launch_config, fft_seen, cfar_seen;
  logic [3:0] pending_fft_log2;
  logic [35:0] pending_alpha_q32;
  logic [33:0] pending_weak_alpha_q32;
  logic fft_config_ready, fft_config_applied, fft_config_rejected;
  logic cfar_config_ready, cfar_config_applied, cfar_config_rejected;

  logic hann_valid, hann_ready, hann_last, hann_error;
  logic [31:0] hann_data;
  logic fft_valid, fft_ready, fft_last;
  logic [63:0] fft_data;
  logic [13:0] fft_index;
  logic wide_power_valid, wide_power_ready, wide_power_last;
  logic [61:0] wide_power_data;
  logic [13:0] wide_power_index;
  logic power_valid, power_ready, power_last, power_config_error;
  logic [57:0] power_data;
  logic [13:0] power_index;
  logic detector_valid, detector_last, detector_error;
  logic input_keep_error;
  logic [63:0] detector_data;
  logic [13:0] detector_index;
  logic [5:0] fft_events;

  logic fft_s_axis_config_tvalid, fft_s_axis_config_tready;
  logic [15:0] fft_s_axis_config_tdata;
  logic fft_s_axis_data_tvalid, fft_s_axis_data_tready, fft_s_axis_data_tlast;
  logic [31:0] fft_s_axis_data_tdata;
  logic fft_m_axis_data_tvalid, fft_m_axis_data_tready, fft_m_axis_data_tlast;
  logic [63:0] fft_m_axis_data_tdata;
  logic [13:0] fft_m_axis_data_tuser_index;
  logic fft_event_frame_started, fft_event_tlast_unexpected, fft_event_tlast_missing;
  logic fft_event_status_channel_halt, fft_event_data_in_channel_halt;
  logic fft_event_data_out_channel_halt;

  function automatic logic valid_profile(
    input logic [3:0] fft_log2,
    input logic [35:0] alpha,
    input logic [33:0] weak_alpha
  );
    valid_profile = (fft_log2 == 4'd12 || fft_log2 == 4'd13 || fft_log2 == 4'd14) &&
                    alpha >= 36'd4294967296 && weak_alpha >= 34'd4294967296 &&
                    {2'b00, weak_alpha} <= alpha;
  endfunction

  assign pipeline_idle = !frame_in_flight && !input_in_frame && !transaction_active;
  assign config_ready = !frame_in_flight && !input_in_frame && !transaction_active &&
                        fft_config_ready && cfar_config_ready;
  assign input_enabled = input_in_frame ||
                         (!frame_in_flight && !hold_input && !config_valid && !transaction_active);
  assign s_axis_tready = input_ready && input_enabled;

  always_ff @(posedge aclk) begin
    if (!aresetn) begin
      input_in_frame <= 1'b0;
      frame_in_flight <= 1'b0;
      transaction_active <= 1'b0;
      launch_config <= 1'b0;
      fft_seen <= 1'b0;
      cfar_seen <= 1'b0;
      pending_fft_log2 <= 4'd12;
      pending_alpha_q32 <= 36'd36851433755;
      pending_weak_alpha_q32 <= 34'd17098572778;
      config_applied <= 1'b0;
      config_rejected <= 1'b0;
    end else begin
      config_applied <= 1'b0;
      config_rejected <= 1'b0;
      launch_config <= 1'b0;
      if (m_axis_tvalid && m_axis_tready && m_axis_tlast)
        frame_in_flight <= 1'b0;
      if (s_axis_tvalid && s_axis_tready) begin
        input_in_frame <= !s_axis_tlast;
        frame_in_flight <= 1'b1;
      end
      if (config_valid && config_ready) begin
        if (!valid_profile(config_fft_log2, config_alpha_q32, config_weak_alpha_q32)) begin
          config_rejected <= 1'b1;
        end else begin
          pending_fft_log2 <= config_fft_log2;
          pending_alpha_q32 <= config_alpha_q32;
          pending_weak_alpha_q32 <= config_weak_alpha_q32;
          transaction_active <= 1'b1;
          launch_config <= 1'b1;
          fft_seen <= 1'b0;
          cfar_seen <= 1'b0;
        end
      end
      if (transaction_active) begin
        if (fft_config_applied) fft_seen <= 1'b1;
        if (cfar_config_applied) cfar_seen <= 1'b1;
        if (fft_config_rejected || cfar_config_rejected) begin
          transaction_active <= 1'b0;
          config_rejected <= 1'b1;
        end else if ((fft_seen || fft_config_applied) &&
                     (cfar_seen || cfar_config_applied)) begin
          transaction_active <= 1'b0;
          config_applied <= 1'b1;
        end
      end
    end
  end

  axis_hann_window_runtime hann (
    .aclk(aclk), .aresetn(aresetn), .active_fft_log2(active_fft_log2),
    .s_axis_tvalid(s_axis_tvalid && input_enabled), .s_axis_tready(input_ready),
    .s_axis_tdata(s_axis_tdata), .s_axis_tlast(s_axis_tlast),
    .m_axis_tvalid(hann_valid), .m_axis_tready(hann_ready),
    .m_axis_tdata(hann_data), .m_axis_tlast(hann_last),
    .status_frame_error_sticky(hann_error)
  );

  axis_fft_runtime_wrapper fft_wrapper (
    .aclk(aclk), .aresetn(aresetn),
    .config_valid(launch_config), .config_ready(fft_config_ready),
    .config_fft_log2(pending_fft_log2), .config_applied(fft_config_applied),
    .config_rejected(fft_config_rejected), .active_fft_log2(active_fft_log2),
    .s_axis_tvalid(hann_valid), .s_axis_tready(hann_ready),
    .s_axis_tdata(hann_data), .s_axis_tlast(hann_last),
    .m_axis_tvalid(fft_valid), .m_axis_tready(fft_ready),
    .m_axis_tdata(fft_data), .m_axis_tlast(fft_last), .m_axis_tuser_index(fft_index),
    .fft_s_axis_config_tvalid(fft_s_axis_config_tvalid),
    .fft_s_axis_config_tready(fft_s_axis_config_tready),
    .fft_s_axis_config_tdata(fft_s_axis_config_tdata),
    .fft_s_axis_data_tvalid(fft_s_axis_data_tvalid),
    .fft_s_axis_data_tready(fft_s_axis_data_tready),
    .fft_s_axis_data_tdata(fft_s_axis_data_tdata),
    .fft_s_axis_data_tlast(fft_s_axis_data_tlast),
    .fft_m_axis_data_tvalid(fft_m_axis_data_tvalid),
    .fft_m_axis_data_tready(fft_m_axis_data_tready),
    .fft_m_axis_data_tdata(fft_m_axis_data_tdata),
    .fft_m_axis_data_tlast(fft_m_axis_data_tlast),
    .fft_m_axis_data_tuser_index(fft_m_axis_data_tuser_index),
    .fft_event_frame_started(fft_event_frame_started),
    .fft_event_tlast_unexpected(fft_event_tlast_unexpected),
    .fft_event_tlast_missing(fft_event_tlast_missing),
    .fft_event_status_channel_halt(fft_event_status_channel_halt),
    .fft_event_data_in_channel_halt(fft_event_data_in_channel_halt),
    .fft_event_data_out_channel_halt(fft_event_data_out_channel_halt),
    .configuration_done(configuration_done), .status_events_sticky(fft_events)
  );

  amd_xfft_runtime_adapter fft (
    .aclk(aclk), .aresetn(aresetn),
    .s_axis_config_tvalid(fft_s_axis_config_tvalid),
    .s_axis_config_tready(fft_s_axis_config_tready),
    .s_axis_config_tdata(fft_s_axis_config_tdata),
    .s_axis_data_tvalid(fft_s_axis_data_tvalid),
    .s_axis_data_tready(fft_s_axis_data_tready),
    .s_axis_data_tdata(fft_s_axis_data_tdata),
    .s_axis_data_tlast(fft_s_axis_data_tlast),
    .m_axis_data_tvalid(fft_m_axis_data_tvalid),
    .m_axis_data_tready(fft_m_axis_data_tready),
    .m_axis_data_tdata(fft_m_axis_data_tdata),
    .m_axis_data_tlast(fft_m_axis_data_tlast),
    .m_axis_data_tuser_index(fft_m_axis_data_tuser_index),
    .event_frame_started(fft_event_frame_started),
    .event_tlast_unexpected(fft_event_tlast_unexpected),
    .event_tlast_missing(fft_event_tlast_missing),
    .event_status_channel_halt(fft_event_status_channel_halt),
    .event_data_in_channel_halt(fft_event_data_in_channel_halt),
    .event_data_out_channel_halt(fft_event_data_out_channel_halt)
  );

  axis_fft_runtime_linear_power power_wide (
    .aclk(aclk), .aresetn(aresetn), .s_axis_tvalid(fft_valid),
    .s_axis_tready(fft_ready), .s_axis_tdata(fft_data), .s_axis_tlast(fft_last),
    .s_axis_tuser_index(fft_index), .m_axis_tvalid(wide_power_valid),
    .m_axis_tready(wide_power_ready), .m_axis_tdata(wide_power_data),
    .m_axis_tlast(wide_power_last), .m_axis_tuser_index(wide_power_index)
  );

  axis_fft_power_normalizer power_normalizer (
    .aclk(aclk), .aresetn(aresetn), .active_fft_log2(active_fft_log2),
    .s_axis_tvalid(wide_power_valid), .s_axis_tready(wide_power_ready),
    .s_axis_tdata(wide_power_data), .s_axis_tlast(wide_power_last),
    .s_axis_tuser_index(wide_power_index), .m_axis_tvalid(power_valid),
    .m_axis_tready(power_ready), .m_axis_tdata(power_data),
    .m_axis_tlast(power_last), .m_axis_tuser_index(power_index),
    .status_config_error_sticky(power_config_error)
  );

  axis_p0_runtime_os_cfar #(.RUNTIME_CONFIG(1'b1)) detector (
    .aclk(aclk), .aresetn(aresetn), .active_fft_log2(active_fft_log2),
    .s_axis_tvalid(power_valid), .s_axis_tready(power_ready),
    .s_axis_tdata(power_data), .s_axis_tlast(power_last),
    .s_axis_tuser_index(power_index), .m_axis_tvalid(detector_valid),
    .m_axis_tready(m_axis_tready), .m_axis_tdata(detector_data),
    .m_axis_tlast(detector_last), .m_axis_tuser_index(detector_index),
    .status_frame_error_sticky(detector_error), .config_valid(launch_config),
    .config_ready(cfar_config_ready), .config_alpha_q32(pending_alpha_q32),
    .config_weak_alpha_q32(pending_weak_alpha_q32),
    .config_applied(cfar_config_applied), .config_rejected(cfar_config_rejected),
    .active_alpha_q32(active_alpha_q32), .active_weak_alpha_q32(active_weak_alpha_q32)
  );

  assign m_axis_tvalid = detector_valid;
  assign m_axis_tdata = detector_data;
  assign m_axis_tkeep = 8'hff;
  assign m_axis_tlast = detector_last;
  assign m_axis_bin_index = detector_index;
  assign status_events_sticky = {input_keep_error, power_config_error,
                                 detector_error, hann_error, fft_events};

  always_ff @(posedge aclk) begin
    if (!aresetn)
      input_keep_error <= 1'b0;
    else if (s_axis_tvalid && s_axis_tready && s_axis_tkeep != 2'b11)
      input_keep_error <= 1'b1;
  end
endmodule
