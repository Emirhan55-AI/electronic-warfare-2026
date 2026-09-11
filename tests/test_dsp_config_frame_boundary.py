"""Whole-path frame admission check with a transport-only FFT stand-in.

The FFT stand-in does not validate spectral math; this test covers quiescence.
"""
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_whole_dsp_quiescence(tmp_path):
    fft = r'''
module amd_xfft_adapter (
input logic aclk,aresetn,s_axis_config_tvalid,
output logic s_axis_config_tready,
input logic [7:0] s_axis_config_tdata,
input logic s_axis_data_tvalid,
output logic s_axis_data_tready,
input logic [31:0] s_axis_data_tdata,
input logic s_axis_data_tlast,
output logic m_axis_data_tvalid,
input logic m_axis_data_tready,
output logic [63:0] m_axis_data_tdata,
output logic m_axis_data_tlast,
output logic [11:0] m_axis_data_tuser_index,
output logic event_frame_started,event_tlast_unexpected,event_tlast_missing,
event_status_channel_halt,event_data_in_channel_halt,event_data_out_channel_halt);
logic [11:0] index;
assign s_axis_config_tready=1;
assign s_axis_data_tready=!m_axis_data_tvalid || m_axis_data_tready;
assign {event_frame_started,event_tlast_unexpected,event_tlast_missing,
event_status_channel_halt,event_data_in_channel_halt,event_data_out_channel_halt}=0;
always_ff @(posedge aclk) begin
 if(!aresetn) begin index<=0; m_axis_data_tvalid<=0; m_axis_data_tdata<=0;
 m_axis_data_tlast<=0; m_axis_data_tuser_index<=0; end
 else if(s_axis_data_tready) begin
  m_axis_data_tvalid<=s_axis_data_tvalid;
  if(s_axis_data_tvalid) begin
   m_axis_data_tdata<=0; m_axis_data_tlast<=s_axis_data_tlast;
   m_axis_data_tuser_index<=index;
   index<=s_axis_data_tlast ? 0 : index+1'b1;
  end
 end
end
endmodule
'''
    tb = r'''
module tb;
reg clk=0; always #5 clk=~clk;
reg rst=0,sv=0,sl=0,mr=0,hold_in=0,cv=0;
wire sr,mv,ml,idle,cr,ap,rj; wire [63:0] md; wire [7:0] keep;
wire [35:0] aa; wire [33:0] wa;
integer n,outputs=0,cycles=0;
p0_dsp_runtime_top #(.RUNTIME_CONFIG(1)) dut(
.aclk(clk),.aresetn(rst),.s_axis_tvalid(sv),.s_axis_tready(sr),.s_axis_tdata(16'd0),
.s_axis_tlast(sl),.s_axis_tkeep(2'b11),.m_axis_tvalid(mv),.m_axis_tready(mr),
.m_axis_tdata(md),.m_axis_tlast(ml),.m_axis_tkeep(keep),.hold_input(hold_in),
.pipeline_idle(idle),.config_valid(cv),.config_ready(cr),
.config_alpha_q32(36'd8589934592),.config_weak_alpha_q32(34'd4294967296),
.config_applied(ap),.config_rejected(rj),.active_alpha_q32(aa),.active_weak_alpha_q32(wa),
.m_axis_bin_index(),.configuration_done(),.status_events_sticky(),
.input_keep_error_sticky(),.detector_frame_error_sticky());
always @(posedge clk) begin
 cycles=cycles+1; if(cycles>180000) $fatal(1,"timeout");
 if(rst && mv && mr) begin
  if(idle) $fatal(1,"idle before final output consumption");
  outputs=outputs+1;
 end
end
initial begin
 repeat(4) @(negedge clk); rst=1; hold_in=1; sv=1;
 repeat(12) begin @(negedge clk); if(sr || !idle) $fatal(1,"hold admission"); end
 hold_in=0; sv=0;
 for(n=0;n<4096;n=n+1) begin
  @(negedge clk); sv=1; sl=(n==4095);
  if(n==5) hold_in=1; // must finish the admitted frame
  do @(posedge clk); while(!sr);
 end
 @(negedge clk); sv=0; sl=0;
 if(idle) $fatal(1,"FFT/CFAR work outstanding");
 wait(mv); repeat(8) begin @(negedge clk); if(idle) $fatal(1,"output stall not idle"); end
 // A second frame cannot enter while the previous output is draining.
 sv=1; hold_in=0; mr=1;
 while(outputs<4096) begin @(negedge clk); if(outputs<4096 && sr) $fatal(1,"second frame entered early"); end
 sv=0; hold_in=1; @(negedge clk);
 if(!idle || !cr) $fatal(1,"did not become quiescent");
 cv=1; @(negedge clk);
 if(!ap || aa!=36'd8589934592 || wa!=34'd4294967296) $fatal(1,"idle apply");
 cv=0;
 $display("DSP_FRAME_BOUNDARY_PASS"); $finish;
end
endmodule
'''
    (tmp_path/'fft.sv').write_text(fft)
    (tmp_path/'tb.sv').write_text(tb)
    shutil.copyfile(ROOT/'datasets/fixtures/phase06b/hann-coefficients.mem', tmp_path/'hann-coefficients.mem')
    sources = ['phase06a/rtl/axis_skid_buffer.sv', 'phase06b/rtl/phase06b_pkg.sv',
               'phase06b/rtl/axis_hann_window.sv', 'phase06c/rtl/phase06c_pkg.sv',
               'phase06c/rtl/axis_fft_wrapper.sv', 'phase06f/rtl/axis_fft_linear_power.sv',
               'p0/rtl/p0_os_cfar_pkg.sv', 'p0/rtl/axis_p0_os_cfar.sv', 'p0/rtl/p0_dsp_runtime_top.sv']
    compiler = shutil.which('iverilog') or 'C:/msys64/ucrt64/bin/iverilog.exe'
    runtime = str(Path(compiler).with_name('vvp.exe' if compiler.lower().endswith('.exe') else 'vvp'))
    built = subprocess.run([compiler, '-g2012', '-s', 'tb', '-o', str(tmp_path/'test.vvp'),
        *(str(ROOT/'algorithms/fpga'/s) for s in sources), str(tmp_path/'fft.sv'), str(tmp_path/'tb.sv')],
        capture_output=True, text=True)
    assert built.returncode == 0, built.stderr
    run = subprocess.run([runtime, str(tmp_path/'test.vvp')], cwd=tmp_path, capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stdout+run.stderr
    assert 'DSP_FRAME_BOUNDARY_PASS' in run.stdout
