module p0_dsp_runtime_fft_bd (
  (* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 aclk CLK" *)
  (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME aclk, ASSOCIATED_BUSIF S_AXIS:M_AXIS:S_AXI, ASSOCIATED_RESET aresetn, FREQ_HZ 50000000" *)
  input wire aclk,
  (* X_INTERFACE_INFO = "xilinx.com:signal:reset:1.0 aresetn RST" *)
  (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME aresetn, POLARITY ACTIVE_LOW" *)
  input wire aresetn,
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 S_AXIS TVALID" *) input wire s_axis_tvalid,
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 S_AXIS TREADY" *) output wire s_axis_tready,
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 S_AXIS TDATA" *) input wire [15:0] s_axis_tdata,
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 S_AXIS TKEEP" *) input wire [1:0] s_axis_tkeep,
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 S_AXIS TLAST" *) input wire s_axis_tlast,
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 M_AXIS TVALID" *) output wire m_axis_tvalid,
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 M_AXIS TREADY" *) input wire m_axis_tready,
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 M_AXIS TDATA" *) output wire [63:0] m_axis_tdata,
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 M_AXIS TKEEP" *) output wire [7:0] m_axis_tkeep,
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 M_AXIS TLAST" *) output wire m_axis_tlast,
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWADDR" *) input wire [7:0] s_axi_awaddr,
  (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME S_AXI, PROTOCOL AXI4LITE, DATA_WIDTH 32, ADDR_WIDTH 8, READ_WRITE_MODE READ_WRITE" *)
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWVALID" *) input wire s_axi_awvalid,
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWREADY" *) output wire s_axi_awready,
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI WDATA" *) input wire [31:0] s_axi_wdata,
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI WSTRB" *) input wire [3:0] s_axi_wstrb,
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI WVALID" *) input wire s_axi_wvalid,
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI WREADY" *) output wire s_axi_wready,
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI BRESP" *) output wire [1:0] s_axi_bresp,
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI BVALID" *) output wire s_axi_bvalid,
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI BREADY" *) input wire s_axi_bready,
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARADDR" *) input wire [7:0] s_axi_araddr,
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARVALID" *) input wire s_axi_arvalid,
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARREADY" *) output wire s_axi_arready,
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *) output wire [31:0] s_axi_rdata,
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RRESP" *) output wire [1:0] s_axi_rresp,
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RVALID" *) output wire s_axi_rvalid,
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RREADY" *) input wire s_axi_rready
);
  wire hold_input, pipeline_idle, config_valid, config_ready, config_applied, config_rejected;
  wire [3:0] config_fft_log2, active_fft_log2;
  wire [35:0] config_alpha_q32, active_alpha_q32;
  wire [33:0] config_weak_alpha_q32, active_weak_alpha_q32;

  p0_detection_profile_control control (
    .aclk(aclk),.aresetn(aresetn),.s_axi_awaddr(s_axi_awaddr),
    .s_axi_awvalid(s_axi_awvalid),.s_axi_awready(s_axi_awready),
    .s_axi_wdata(s_axi_wdata),.s_axi_wstrb(s_axi_wstrb),
    .s_axi_wvalid(s_axi_wvalid),.s_axi_wready(s_axi_wready),
    .s_axi_bresp(s_axi_bresp),.s_axi_bvalid(s_axi_bvalid),.s_axi_bready(s_axi_bready),
    .s_axi_araddr(s_axi_araddr),.s_axi_arvalid(s_axi_arvalid),.s_axi_arready(s_axi_arready),
    .s_axi_rdata(s_axi_rdata),.s_axi_rresp(s_axi_rresp),.s_axi_rvalid(s_axi_rvalid),
    .s_axi_rready(s_axi_rready),.pipeline_idle(pipeline_idle),.hold_input(hold_input),
    .config_valid(config_valid),.config_ready(config_ready),.config_fft_log2(config_fft_log2),
    .config_alpha_q32(config_alpha_q32),.config_weak_alpha_q32(config_weak_alpha_q32),
    .config_applied(config_applied),.config_rejected(config_rejected),
    .active_fft_log2(active_fft_log2),.active_alpha_q32(active_alpha_q32),
    .active_weak_alpha_q32(active_weak_alpha_q32)
  );

  p0_dsp_runtime_fft_top core (
    .aclk(aclk),.aresetn(aresetn),.s_axis_tvalid(s_axis_tvalid),.s_axis_tready(s_axis_tready),
    .s_axis_tdata(s_axis_tdata),.s_axis_tkeep(s_axis_tkeep),.s_axis_tlast(s_axis_tlast),
    .m_axis_tvalid(m_axis_tvalid),.m_axis_tready(m_axis_tready),.m_axis_tdata(m_axis_tdata),
    .m_axis_tkeep(m_axis_tkeep),.m_axis_tlast(m_axis_tlast),.m_axis_bin_index(),
    .hold_input(hold_input),.pipeline_idle(pipeline_idle),.config_valid(config_valid),
    .config_ready(config_ready),.config_fft_log2(config_fft_log2),
    .config_alpha_q32(config_alpha_q32),.config_weak_alpha_q32(config_weak_alpha_q32),
    .config_applied(config_applied),.config_rejected(config_rejected),
    .active_fft_log2(active_fft_log2),.active_alpha_q32(active_alpha_q32),
    .active_weak_alpha_q32(active_weak_alpha_q32),.configuration_done(),.status_events_sticky()
  );
endmodule
