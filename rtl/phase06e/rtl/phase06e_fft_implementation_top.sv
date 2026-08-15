module phase06e_axis_input_register_slice (
  input  logic        aclk,
  input  logic        aresetn,
  input  logic        enable,
  input  logic        s_axis_tvalid,
  (* IOB = "TRUE" *) output logic s_axis_tready,
  input  logic [31:0] s_axis_tdata,
  input  logic        s_axis_tlast,
  output logic        m_axis_tvalid,
  input  logic        m_axis_tready,
  output logic [31:0] m_axis_tdata,
  output logic        m_axis_tlast
);
  logic [1:0]  occupancy;
  logic [32:0] payload_0;
  logic [32:0] payload_1;
  logic        push;
  logic        pop;
  logic [1:0]  next_occupancy;

  assign push = s_axis_tvalid && s_axis_tready;
  assign pop = m_axis_tvalid && m_axis_tready;
  assign m_axis_tvalid = occupancy != 0;
  assign {m_axis_tlast, m_axis_tdata} = payload_0;

  always_comb begin
    next_occupancy = occupancy;
    case ({push, pop})
      2'b10: next_occupancy = occupancy + 1'b1;
      2'b01: next_occupancy = occupancy - 1'b1;
      default: next_occupancy = occupancy;
    endcase
  end

  always_ff @(posedge aclk) begin
    if (!aresetn) begin
      occupancy   <= '0;
      payload_0   <= '0;
      payload_1   <= '0;
      s_axis_tready <= 1'b0;
    end else begin
      occupancy <= next_occupancy;
      s_axis_tready <= enable && (next_occupancy < 2);
      case ({push, pop})
        2'b10: begin
          if (occupancy == 0) payload_0 <= {s_axis_tlast, s_axis_tdata};
          else payload_1 <= {s_axis_tlast, s_axis_tdata};
        end
        2'b01: begin
          if (occupancy == 2) payload_0 <= payload_1;
        end
        2'b11: begin
          payload_0 <= {s_axis_tlast, s_axis_tdata};
        end
        default: begin
          payload_0 <= payload_0;
          payload_1 <= payload_1;
        end
      endcase
    end
  end
endmodule

module phase06e_fft_implementation_top (
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

  output logic        configuration_done,
  output logic [5:0]  status_events_sticky
);
  logic        fft_s_axis_config_tvalid;
  logic        fft_s_axis_config_tready;
  logic [7:0]  fft_s_axis_config_tdata;
  logic        fft_s_axis_data_tvalid;
  logic        fft_s_axis_data_tready;
  logic [31:0] fft_s_axis_data_tdata;
  logic        fft_s_axis_data_tlast;
  logic        fft_m_axis_data_tvalid;
  logic        fft_m_axis_data_tready;
  logic [63:0] fft_m_axis_data_tdata;
  logic        fft_m_axis_data_tlast;
  logic [11:0] fft_m_axis_data_tuser_index;
  logic        fft_event_frame_started;
  logic        fft_event_tlast_unexpected;
  logic        fft_event_tlast_missing;
  logic        fft_event_status_channel_halt;
  logic        fft_event_data_in_channel_halt;
  logic        fft_event_data_out_channel_halt;
  logic        wrapper_s_axis_tvalid;
  logic        wrapper_s_axis_tready;
  logic [31:0] wrapper_s_axis_tdata;
  logic        wrapper_s_axis_tlast;

  phase06e_axis_input_register_slice input_timing_boundary (
    .aclk(aclk),
    .aresetn(aresetn),
    .enable(configuration_done),
    .s_axis_tvalid(s_axis_tvalid),
    .s_axis_tready(s_axis_tready),
    .s_axis_tdata(s_axis_tdata),
    .s_axis_tlast(s_axis_tlast),
    .m_axis_tvalid(wrapper_s_axis_tvalid),
    .m_axis_tready(wrapper_s_axis_tready),
    .m_axis_tdata(wrapper_s_axis_tdata),
    .m_axis_tlast(wrapper_s_axis_tlast)
  );

  axis_fft_wrapper wrapper (
    .aclk(aclk),
    .aresetn(aresetn),
    .s_axis_tvalid(wrapper_s_axis_tvalid),
    .s_axis_tready(wrapper_s_axis_tready),
    .s_axis_tdata(wrapper_s_axis_tdata),
    .s_axis_tlast(wrapper_s_axis_tlast),
    .m_axis_tvalid(m_axis_tvalid),
    .m_axis_tready(m_axis_tready),
    .m_axis_tdata(m_axis_tdata),
    .m_axis_tlast(m_axis_tlast),
    .m_axis_tuser_index(m_axis_tuser_index),
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
    .configuration_done(configuration_done),
    .status_events_sticky(status_events_sticky)
  );

  amd_xfft_adapter adapter (
    .aclk(aclk),
    .aresetn(aresetn),
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
endmodule
