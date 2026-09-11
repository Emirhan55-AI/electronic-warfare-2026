// AXI-Lite control for the atomic FFT-length and CFAR profile.
module p0_detection_profile_control (
  input logic aclk, aresetn,
  input logic [7:0] s_axi_awaddr,
  input logic s_axi_awvalid,
  output logic s_axi_awready,
  input logic [31:0] s_axi_wdata,
  input logic [3:0] s_axi_wstrb,
  input logic s_axi_wvalid,
  output logic s_axi_wready,
  output logic [1:0] s_axi_bresp,
  output logic s_axi_bvalid,
  input logic s_axi_bready,
  input logic [7:0] s_axi_araddr,
  input logic s_axi_arvalid,
  output logic s_axi_arready,
  output logic [31:0] s_axi_rdata,
  output logic [1:0] s_axi_rresp,
  output logic s_axi_rvalid,
  input logic s_axi_rready,
  input logic pipeline_idle,
  output logic hold_input,
  output logic config_valid,
  input logic config_ready,
  output logic [3:0] config_fft_log2,
  output logic [35:0] config_alpha_q32,
  output logic [33:0] config_weak_alpha_q32,
  input logic config_applied, config_rejected,
  input logic [3:0] active_fft_log2,
  input logic [35:0] active_alpha_q32,
  input logic [33:0] active_weak_alpha_q32
);
  import p0_os_cfar_pkg::*;
  logic aw_pending, w_pending, commit_pending;
  logic [7:0] address;
  logic [31:0] data;
  logic [3:0] strobe;
  logic [3:0] draft_fft_log2;
  logic [35:0] draft_alpha;
  logic [33:0] draft_weak;
  logic [31:0] generation;
  wire write_pending = aw_pending && w_pending && !s_axi_bvalid && !commit_pending;
  wire valid_draft = (draft_fft_log2 == 4'd12 || draft_fft_log2 == 4'd13 ||
                      draft_fft_log2 == 4'd14) &&
                     draft_alpha >= 36'd4294967296 &&
                     draft_weak >= 34'd4294967296 &&
                     {2'b00, draft_weak} <= draft_alpha;

  assign hold_input = commit_pending || (write_pending && address == 8'h08);
  assign s_axi_awready = aresetn && !aw_pending && !s_axi_bvalid && !commit_pending;
  assign s_axi_wready = aresetn && !w_pending && !s_axi_bvalid && !commit_pending;
  assign s_axi_arready = aresetn && !s_axi_rvalid;

  always_ff @(posedge aclk) begin
    if (!aresetn) begin
      aw_pending <= 0; w_pending <= 0; commit_pending <= 0;
      address <= 0; data <= 0; strobe <= 0;
      draft_fft_log2 <= 4'd12; draft_alpha <= ALPHA_Q32; draft_weak <= WEAK_ALPHA_Q32;
      config_fft_log2 <= 4'd12; config_alpha_q32 <= ALPHA_Q32;
      config_weak_alpha_q32 <= WEAK_ALPHA_Q32;
      config_valid <= 0; generation <= 0;
      s_axi_bvalid <= 0; s_axi_bresp <= 0;
      s_axi_rvalid <= 0; s_axi_rresp <= 0; s_axi_rdata <= 0;
    end else begin
      if (s_axi_awvalid && s_axi_awready) begin address <= s_axi_awaddr; aw_pending <= 1; end
      if (s_axi_wvalid && s_axi_wready) begin data <= s_axi_wdata; strobe <= s_axi_wstrb; w_pending <= 1; end
      if (s_axi_bvalid && s_axi_bready) s_axi_bvalid <= 0;
      if (config_valid && config_ready) config_valid <= 0;
      if (commit_pending && (config_applied || config_rejected)) begin
        commit_pending <= 0; s_axi_bvalid <= 1;
        s_axi_bresp <= config_rejected ? 2'b10 : 2'b00;
        if (config_applied && !config_rejected) generation <= generation + 1'b1;
      end
      if (write_pending) begin
        aw_pending <= 0; w_pending <= 0; s_axi_bvalid <= 1; s_axi_bresp <= 2'b00;
        if (strobe != 4'hf || address[1:0] != 0) s_axi_bresp <= 2'b10;
        else case (address)
          8'h0c: if (data != 32'd12 && data != 32'd13 && data != 32'd14) s_axi_bresp <= 2'b10;
                   else draft_fft_log2 <= data[3:0];
          8'h10: draft_alpha[31:0] <= data;
          8'h14: if (data[31:4] != 0) s_axi_bresp <= 2'b10;
                   else draft_alpha[35:32] <= data[3:0];
          8'h18: draft_weak[31:0] <= data;
          8'h1c: if (data[31:2] != 0) s_axi_bresp <= 2'b10;
                   else draft_weak[33:32] <= data[1:0];
          8'h08: begin
            if (data != 1 || !pipeline_idle || !config_ready || !valid_draft)
              s_axi_bresp <= 2'b10;
            else begin
              config_fft_log2 <= draft_fft_log2;
              config_alpha_q32 <= draft_alpha;
              config_weak_alpha_q32 <= draft_weak;
              config_valid <= 1; commit_pending <= 1; s_axi_bvalid <= 0;
            end
          end
          default: s_axi_bresp <= 2'b10;
        endcase
      end
      if (s_axi_rvalid && s_axi_rready) s_axi_rvalid <= 0;
      if (s_axi_arvalid && s_axi_arready) begin
        s_axi_rvalid <= 1; s_axi_rresp <= 0; s_axi_rdata <= 0;
        case (s_axi_araddr)
          8'h00: s_axi_rdata <= 32'h53540602;
          8'h04: s_axi_rdata <= {29'd0,commit_pending,config_ready,pipeline_idle};
          8'h0c: s_axi_rdata <= {28'd0,draft_fft_log2};
          8'h10: s_axi_rdata <= draft_alpha[31:0];
          8'h14: s_axi_rdata <= {28'd0,draft_alpha[35:32]};
          8'h18: s_axi_rdata <= draft_weak[31:0];
          8'h1c: s_axi_rdata <= {30'd0,draft_weak[33:32]};
          8'h20: s_axi_rdata <= active_alpha_q32[31:0];
          8'h24: s_axi_rdata <= {28'd0,active_alpha_q32[35:32]};
          8'h28: s_axi_rdata <= active_weak_alpha_q32[31:0];
          8'h2c: s_axi_rdata <= {30'd0,active_weak_alpha_q32[33:32]};
          8'h30: s_axi_rdata <= generation;
          8'h34: s_axi_rdata <= {28'd0,active_fft_log2};
          default: s_axi_rresp <= 2'b10;
        endcase
      end
    end
  end
endmodule
