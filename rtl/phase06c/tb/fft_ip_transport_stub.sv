module fft_ip_transport_stub (
  input  logic        aclk,
  input  logic        aresetn,
  input  logic        allow_config_ready,
  input  logic [5:0]  inject_events,

  input  logic        s_axis_config_tvalid,
  output logic        s_axis_config_tready,
  input  logic [7:0]  s_axis_config_tdata,

  input  logic        s_axis_data_tvalid,
  output logic        s_axis_data_tready,
  input  logic [31:0] s_axis_data_tdata,
  input  logic        s_axis_data_tlast,

  output logic        m_axis_data_tvalid,
  input  logic        m_axis_data_tready,
  output logic [63:0] m_axis_data_tdata,
  output logic        m_axis_data_tlast,
  output logic [11:0] m_axis_data_tuser_index,

  output logic        event_frame_started,
  output logic        event_tlast_unexpected,
  output logic        event_tlast_missing,
  output logic        event_status_channel_halt,
  output logic        event_data_in_channel_halt,
  output logic        event_data_out_channel_halt,
  output logic        configuration_seen
);
  logic [11:0] sample_index;

  assign s_axis_config_tready = allow_config_ready && !configuration_seen;
  assign s_axis_data_tready = configuration_seen && (!m_axis_data_tvalid || m_axis_data_tready);

  assign event_frame_started          = inject_events[0];
  assign event_tlast_unexpected       = inject_events[1];
  assign event_tlast_missing          = inject_events[2];
  assign event_status_channel_halt    = inject_events[3];
  assign event_data_in_channel_halt   = inject_events[4];
  assign event_data_out_channel_halt  = inject_events[5];

  always_ff @(posedge aclk) begin
    if (!aresetn) begin
      configuration_seen     <= 1'b0;
      sample_index           <= '0;
      m_axis_data_tvalid     <= 1'b0;
      m_axis_data_tdata      <= '0;
      m_axis_data_tlast      <= 1'b0;
      m_axis_data_tuser_index <= '0;
    end else begin
      if (s_axis_config_tvalid && s_axis_config_tready) begin
        if (s_axis_config_tdata !== 8'h01) begin
          $fatal(1, "PHASE-06C stub yalniz 0x01 forward konfigurasyonunu kabul eder");
        end
        configuration_seen <= 1'b1;
      end
      if (m_axis_data_tvalid && m_axis_data_tready) begin
        m_axis_data_tvalid <= 1'b0;
      end
      if (s_axis_data_tvalid && s_axis_data_tready) begin
        m_axis_data_tvalid <= 1'b1;
        m_axis_data_tdata <= {
          {{16{s_axis_data_tdata[31]}}, s_axis_data_tdata[31:16]},
          {{16{s_axis_data_tdata[15]}}, s_axis_data_tdata[15:0]}
        };
        m_axis_data_tlast <= s_axis_data_tlast;
        m_axis_data_tuser_index <= sample_index;
        // PG109 input TLAST is event-only and does not define the FFT frame.
        // Keep this non-FFT transport index on the fixed-N sample count so an
        // early TLAST cannot masquerade as real AMD frame-boundary behavior.
        if (sample_index == 12'd4095) begin
          sample_index <= '0;
        end else begin
          sample_index <= sample_index + 12'd1;
        end
      end
    end
  end
endmodule
