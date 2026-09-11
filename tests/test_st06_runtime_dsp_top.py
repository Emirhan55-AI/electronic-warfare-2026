from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def test_runtime_dsp_top_applies_fft_and_cfar_as_one_profile(tmp_path: Path) -> None:
    compiler = shutil.which("iverilog") or "C:/msys64/ucrt64/bin/iverilog.exe"
    runtime = str(Path(compiler).with_name("vvp.exe" if compiler.lower().endswith(".exe") else "vvp"))
    fft_stub = r'''
module amd_xfft_runtime_adapter(input logic aclk,aresetn,s_axis_config_tvalid,
 output logic s_axis_config_tready,input logic [15:0] s_axis_config_tdata,
 input logic s_axis_data_tvalid,output logic s_axis_data_tready,input logic [31:0] s_axis_data_tdata,
 input logic s_axis_data_tlast,output logic m_axis_data_tvalid,input logic m_axis_data_tready,
 output logic [63:0] m_axis_data_tdata,output logic m_axis_data_tlast,
 output logic [13:0] m_axis_data_tuser_index,output logic event_frame_started,
 output logic event_tlast_unexpected,event_tlast_missing,event_status_channel_halt,
 event_data_in_channel_halt,event_data_out_channel_halt);
logic [13:0] index; assign s_axis_config_tready=1;
assign s_axis_data_tready=!m_axis_data_tvalid||m_axis_data_tready;
assign {event_frame_started,event_tlast_unexpected,event_tlast_missing,event_status_channel_halt,
 event_data_in_channel_halt,event_data_out_channel_halt}=0;
always_ff @(posedge aclk) begin
 if(!aresetn) begin index<=0;m_axis_data_tvalid<=0;m_axis_data_tdata<=0;m_axis_data_tlast<=0;m_axis_data_tuser_index<=0;end
 else if(s_axis_data_tready) begin
  m_axis_data_tvalid<=s_axis_data_tvalid;
  if(s_axis_data_tvalid) begin m_axis_data_tdata<=0;m_axis_data_tlast<=s_axis_data_tlast;
   m_axis_data_tuser_index<=index;index<=s_axis_data_tlast?0:index+1'b1;end
 end
end
endmodule
'''
    tb = r'''
module tb;
reg clk=0;always #5 clk=~clk;
reg rst=0,cv=0,sv=0,sl=0,mr=1,hold=0;reg [3:0] cfg_n=12;
wire sr,mv,ml,idle,cr,ap,rj,done;wire [63:0] md;wire [7:0] keep;wire [13:0] mi;
wire [3:0] active_n;wire [35:0] active_a;wire [33:0] active_w;wire [9:0] events;
integer n,outputs=0,cycles=0;
p0_dsp_runtime_fft_top dut(.aclk(clk),.aresetn(rst),.s_axis_tvalid(sv),.s_axis_tready(sr),
 .s_axis_tdata(0),.s_axis_tkeep(2'b11),.s_axis_tlast(sl),.m_axis_tvalid(mv),
 .m_axis_tready(mr),.m_axis_tdata(md),.m_axis_tkeep(keep),.m_axis_tlast(ml),
 .m_axis_bin_index(mi),.hold_input(hold),.pipeline_idle(idle),.config_valid(cv),
 .config_ready(cr),.config_fft_log2(cfg_n),.config_alpha_q32(36'd8589934592),
 .config_weak_alpha_q32(34'd4294967296),.config_applied(ap),.config_rejected(rj),
 .active_fft_log2(active_n),.active_alpha_q32(active_a),.active_weak_alpha_q32(active_w),
 .configuration_done(done),.status_events_sticky(events));
always @(posedge clk) begin cycles=cycles+1;if(cycles>400000)$fatal(1,"timeout");if(mv&&mr)outputs=outputs+1;end
task apply(input [3:0] log2n,input accepted);
 begin wait(cr);@(negedge clk);cfg_n=log2n;cv=1;@(negedge clk);cv=0;
  if(accepted) begin wait(ap);@(negedge clk);if(active_n!=log2n||active_a!=36'd8589934592||active_w!=34'd4294967296)$fatal(1,"apply state");end
  else begin wait(rj);@(negedge clk);end
 end
endtask
initial begin
 repeat(3)@(negedge clk);rst=1;wait(done);@(negedge clk);
 if(active_n!=12||!idle||!cr)$fatal(1,"default state");
 apply(11,0);if(active_n!=12)$fatal(1,"invalid changed state");
 apply(13,1);if(!idle)$fatal(1,"post apply idle");
 for(n=0;n<8192;n=n+1)begin @(negedge clk);sv=1;sl=(n==8191);do @(posedge clk);while(!sr);end
 @(negedge clk);sv=0;sl=0;wait(outputs==8192);@(negedge clk);
 if(!idle||events!=0)$fatal(1,"frame result idle=%b events=%h ml=%b mi=%0d",idle,events,ml,mi);
 $display("RUNTIME_DSP_TOP_PASS outputs=%0d",outputs);$finish;
end
endmodule
'''
    (tmp_path / "fft_stub.sv").write_text(fft_stub, encoding="ascii")
    (tmp_path / "tb.sv").write_text(tb, encoding="ascii")
    for size in (4096, 8192, 16384):
        name = f"hann-runtime-coefficients-{size}.mem"
        shutil.copyfile(ROOT / "datasets/fixtures/phase06b" / name, tmp_path / name)
    sources = [
        "phase06a/rtl/axis_skid_buffer.sv",
        "p0/rtl/axis_hann_window_runtime.sv",
        "p0/rtl/axis_fft_runtime_wrapper.sv",
        "p0/rtl/axis_fft_runtime_linear_power.sv",
        "p0/rtl/axis_fft_power_normalizer.sv",
        "p0/rtl/p0_os_cfar_pkg.sv",
        "p0/rtl/axis_p0_runtime_os_cfar.sv",
        "p0/rtl/p0_dsp_runtime_fft_top.sv",
    ]
    build = subprocess.run([compiler, "-g2012", "-s", "tb", "-o", str(tmp_path / "test.vvp"),
                            *(str(ROOT / "algorithms/fpga" / path) for path in sources),
                            str(tmp_path / "fft_stub.sv"), str(tmp_path / "tb.sv")],
                           capture_output=True, text=True)
    assert build.returncode == 0, build.stderr
    run = subprocess.run([runtime, str(tmp_path / "test.vvp")], cwd=tmp_path,
                         capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "RUNTIME_DSP_TOP_PASS outputs=8192" in run.stdout
