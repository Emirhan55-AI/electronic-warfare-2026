module axis_fft_runtime_wrapper (
  input  logic        aclk,
  input  logic        aresetn,

  input  logic        config_valid,
  output logic        config_ready,
  input  logic [3:0]  config_fft_log2,
  output logic        config_applied,
  output logic        config_rejected,
  output logic [3:0]  active_fft_log2,

  input  logic        s_axis_tvalid,
  output logic        s_axis_tready,
  input  logic [31:0] s_axis_tdata,
  input  logic        s_axis_tlast,

  output logic        m_axis_tvalid,
  input  logic        m_axis_tready,
  output logic [63:0] m_axis_tdata,
  output logic        m_axis_tlast,
  output logic [13:0] m_axis_tuser_index,

  output logic        fft_s_axis_config_tvalid,
  input  logic        fft_s_axis_config_tready,
  output logic [15:0] fft_s_axis_config_tdata,
  output logic        fft_s_axis_data_tvalid,
  input  logic        fft_s_axis_data_tready,
  output logic [31:0] fft_s_axis_data_tdata,
  output logic        fft_s_axis_data_tlast,
  input  logic        fft_m_axis_data_tvalid,
  output logic        fft_m_axis_data_tready,
  input  logic [63:0] fft_m_axis_data_tdata,
  input  logic        fft_m_axis_data_tlast,
  input  logic [13:0] fft_m_axis_data_tuser_index,

  input  logic        fft_event_frame_started,
  input  logic        fft_event_tlast_unexpected,
  input  logic        fft_event_tlast_missing,
  input  logic        fft_event_status_channel_halt,
  input  logic        fft_event_data_in_channel_halt,
  input  logic        fft_event_data_out_channel_halt,
  output logic        configuration_done,
  output logic [5:0]  status_events_sticky
);
  logic config_pending;
  logic [3:0] pending_fft_log2;
  logic input_ready_internal;
  logic input_valid_buffered;
  logic [32:0] input_payload_buffered;
  logic output_valid_buffered;
  logic [78:0] output_payload_buffered;

  function automatic logic supported(input logic [3:0] value);
    supported = value == 4'd12 || value == 4'd13 || value == 4'd14;
  endfunction

  assign config_ready = configuration_done && !config_pending &&
                        !input_valid_buffered && !output_valid_buffered &&
                        !s_axis_tvalid && !fft_m_axis_data_tvalid;
  assign fft_s_axis_config_tvalid = !configuration_done || config_pending;
  assign fft_s_axis_config_tdata = {7'd0, 1'b1, 4'd0,
                                    config_pending ? pending_fft_log2 : 4'd12};
  assign s_axis_tready = configuration_done && !config_pending && input_ready_internal;

  axis_skid_buffer #(.PAYLOAD_WIDTH(33)) input_boundary_buffer (
    .aclk(aclk), .aresetn(aresetn),
    .s_valid(s_axis_tvalid && configuration_done && !config_pending),
    .s_ready(input_ready_internal),
    .s_payload({s_axis_tlast, s_axis_tdata}),
    .m_valid(input_valid_buffered), .m_ready(fft_s_axis_data_tready),
    .m_payload(input_payload_buffered)
  );
  assign fft_s_axis_data_tvalid = input_valid_buffered;
  assign fft_s_axis_data_tdata = input_payload_buffered[31:0];
  assign fft_s_axis_data_tlast = input_payload_buffered[32];

  axis_skid_buffer #(.PAYLOAD_WIDTH(79)) output_boundary_buffer (
    .aclk(aclk), .aresetn(aresetn),
    .s_valid(fft_m_axis_data_tvalid), .s_ready(fft_m_axis_data_tready),
    .s_payload({fft_m_axis_data_tuser_index, fft_m_axis_data_tlast, fft_m_axis_data_tdata}),
    .m_valid(output_valid_buffered), .m_ready(m_axis_tready),
    .m_payload(output_payload_buffered)
  );
  assign m_axis_tvalid = output_valid_buffered;
  assign m_axis_tdata = output_payload_buffered[63:0];
  assign m_axis_tlast = output_payload_buffered[64];
  assign m_axis_tuser_index = output_payload_buffered[78:65];

  always_ff @(posedge aclk) begin
    if (!aresetn) begin
      configuration_done <= 1'b0;
      config_pending <= 1'b0;
      pending_fft_log2 <= 4'd12;
      active_fft_log2 <= 4'd12;
      config_applied <= 1'b0;
      config_rejected <= 1'b0;
      status_events_sticky <= '0;
    end else begin
      config_applied <= 1'b0;
      config_rejected <= 1'b0;
      if (config_valid && config_ready) begin
        if (!supported(config_fft_log2)) begin
          config_rejected <= 1'b1;
        end else if (config_fft_log2 == active_fft_log2) begin
          config_applied <= 1'b1;
        end else begin
          pending_fft_log2 <= config_fft_log2;
          config_pending <= 1'b1;
        end
      end
      if (fft_s_axis_config_tvalid && fft_s_axis_config_tready) begin
        configuration_done <= 1'b1;
        if (config_pending) begin
          active_fft_log2 <= pending_fft_log2;
          config_pending <= 1'b0;
          config_applied <= 1'b1;
        end
      end
      status_events_sticky <= status_events_sticky | {
        fft_event_data_out_channel_halt, fft_event_data_in_channel_halt,
        fft_event_status_channel_halt, fft_event_tlast_missing,
        fft_event_tlast_unexpected, fft_event_frame_started
      };
    end
  end
endmodule
