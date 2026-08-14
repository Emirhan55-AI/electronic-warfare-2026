module axis_fft_wrapper (
  input  logic        aclk,
  input  logic        aresetn,

  input  logic        s_axis_tvalid,
  output logic        s_axis_tready,
  input  logic [31:0] s_axis_tdata,
  input  logic        s_axis_tlast,

  output logic        m_axis_tvalid,
  input  logic        m_axis_tready,
  output logic [63:0] m_axis_tdata,
  output logic        m_axis_tlast,
  output logic [11:0] m_axis_tuser_index,

  output logic        fft_s_axis_config_tvalid,
  input  logic        fft_s_axis_config_tready,
  output logic [7:0]  fft_s_axis_config_tdata,

  output logic        fft_s_axis_data_tvalid,
  input  logic        fft_s_axis_data_tready,
  output logic [31:0] fft_s_axis_data_tdata,
  output logic        fft_s_axis_data_tlast,

  input  logic        fft_m_axis_data_tvalid,
  output logic        fft_m_axis_data_tready,
  input  logic [63:0] fft_m_axis_data_tdata,
  input  logic        fft_m_axis_data_tlast,
  input  logic [11:0] fft_m_axis_data_tuser_index,

  input  logic        fft_event_frame_started,
  input  logic        fft_event_tlast_unexpected,
  input  logic        fft_event_tlast_missing,
  input  logic        fft_event_status_channel_halt,
  input  logic        fft_event_data_in_channel_halt,
  input  logic        fft_event_data_out_channel_halt,

  output logic        configuration_done,
  output logic [5:0]  status_events_sticky
);
  import phase06c_pkg::*;

  logic        input_ready_internal;
  logic        input_valid_buffered;
  logic [32:0] input_payload_buffered;
  logic        output_valid_buffered;
  logic [76:0] output_payload_buffered;

  assign fft_s_axis_config_tvalid = !configuration_done;
  assign fft_s_axis_config_tdata  = PHASE06C_FORWARD_CONFIG;

  assign s_axis_tready = configuration_done && input_ready_internal;

  axis_skid_buffer #(
    .PAYLOAD_WIDTH(33)
  ) input_boundary_buffer (
    .aclk      (aclk),
    .aresetn   (aresetn),
    .s_valid   (s_axis_tvalid && configuration_done),
    .s_ready   (input_ready_internal),
    .s_payload ({s_axis_tlast, s_axis_tdata}),
    .m_valid   (input_valid_buffered),
    .m_ready   (fft_s_axis_data_tready),
    .m_payload (input_payload_buffered)
  );

  assign fft_s_axis_data_tvalid = input_valid_buffered;
  assign fft_s_axis_data_tdata  = input_payload_buffered[31:0];
  assign fft_s_axis_data_tlast  = input_payload_buffered[32];

  axis_skid_buffer #(
    .PAYLOAD_WIDTH(77)
  ) output_boundary_buffer (
    .aclk      (aclk),
    .aresetn   (aresetn),
    .s_valid   (fft_m_axis_data_tvalid),
    .s_ready   (fft_m_axis_data_tready),
    .s_payload ({fft_m_axis_data_tuser_index, fft_m_axis_data_tlast, fft_m_axis_data_tdata}),
    .m_valid   (output_valid_buffered),
    .m_ready   (m_axis_tready),
    .m_payload (output_payload_buffered)
  );

  assign m_axis_tvalid      = output_valid_buffered;
  assign m_axis_tdata       = output_payload_buffered[63:0];
  assign m_axis_tlast       = output_payload_buffered[64];
  assign m_axis_tuser_index = output_payload_buffered[76:65];

  always_ff @(posedge aclk) begin
    if (!aresetn) begin
      configuration_done  <= 1'b0;
      status_events_sticky <= '0;
    end else begin
      if (fft_s_axis_config_tvalid && fft_s_axis_config_tready) begin
        configuration_done <= 1'b1;
      end
      status_events_sticky <= status_events_sticky | {
        fft_event_data_out_channel_halt,
        fft_event_data_in_channel_halt,
        fft_event_status_channel_halt,
        fft_event_tlast_missing,
        fft_event_tlast_unexpected,
        fft_event_frame_started
      };
    end
  end
endmodule
