from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def test_runtime_fft_wrapper_serializes_length_changes(tmp_path: Path) -> None:
    compiler = shutil.which("iverilog") or "C:/msys64/ucrt64/bin/iverilog.exe"
    runtime = str(Path(compiler).with_name("vvp.exe" if compiler.lower().endswith(".exe") else "vvp"))
    tb = r'''
module tb;
reg clk=0; always #5 clk=~clk;
reg rst=0,cv=0,sv=0,sl=0,mr=1,fc_ready=0,fd_ready=1,fm_valid=0,fm_last=0;
reg [3:0] requested=12; reg [31:0] sd=0; reg [63:0] fm_data=0; reg [13:0] fm_index=0;
wire cr,ap,rj,sr,mv,ml,fc_valid,fd_valid,fd_last,fm_ready,done;
wire [3:0] active; wire [15:0] fc_data; wire [31:0] fd_data; wire [63:0] md;
wire [13:0] mi; wire [5:0] events;
axis_fft_runtime_wrapper dut(.aclk(clk),.aresetn(rst),.config_valid(cv),.config_ready(cr),
 .config_fft_log2(requested),.config_applied(ap),.config_rejected(rj),.active_fft_log2(active),
 .s_axis_tvalid(sv),.s_axis_tready(sr),.s_axis_tdata(sd),.s_axis_tlast(sl),
 .m_axis_tvalid(mv),.m_axis_tready(mr),.m_axis_tdata(md),.m_axis_tlast(ml),
 .m_axis_tuser_index(mi),.fft_s_axis_config_tvalid(fc_valid),
 .fft_s_axis_config_tready(fc_ready),.fft_s_axis_config_tdata(fc_data),
 .fft_s_axis_data_tvalid(fd_valid),.fft_s_axis_data_tready(fd_ready),
 .fft_s_axis_data_tdata(fd_data),.fft_s_axis_data_tlast(fd_last),
 .fft_m_axis_data_tvalid(fm_valid),.fft_m_axis_data_tready(fm_ready),
 .fft_m_axis_data_tdata(fm_data),.fft_m_axis_data_tlast(fm_last),
 .fft_m_axis_data_tuser_index(fm_index),.fft_event_frame_started(1'b0),
 .fft_event_tlast_unexpected(1'b0),.fft_event_tlast_missing(1'b0),
 .fft_event_status_channel_halt(1'b0),.fft_event_data_in_channel_halt(1'b0),
 .fft_event_data_out_channel_halt(1'b0),.configuration_done(done),
 .status_events_sticky(events));
initial begin
 repeat(3) @(negedge clk); rst=1;
 if(!fc_valid || fc_data!==16'h010c || done || sr) $fatal(1,"default config");
 fc_ready=1; @(negedge clk); fc_ready=0; #1;
 if(!done || active!=12 || !cr) $fatal(1,"default apply");
 requested=11; cv=1; @(negedge clk); cv=0; #1;
 if(!rj || active!=12) $fatal(1,"invalid rejection");
 @(negedge clk); requested=14; cv=1; @(negedge clk); cv=0; #1;
 if(!fc_valid || fc_data!==16'h010e || sr || active!=12) $fatal(1,"pending config");
 fc_ready=1; @(negedge clk); fc_ready=0; #1;
 if(!ap || active!=14 || !sr) $fatal(1,"runtime apply");
 @(negedge clk); sv=1; sd=32'h12345678; sl=1; @(negedge clk); sv=0; sl=0;
 if(!fd_valid || fd_data!==32'h12345678 || !fd_last || cr) $fatal(1,"input bridge");
 @(negedge clk); fm_valid=1; fm_data=64'habcdef0123456789; fm_index=14'h3ffe; fm_last=1;
 @(negedge clk); fm_valid=0; #1;
 if(!mv || md!==64'habcdef0123456789 || mi!=14'h3ffe || !ml) $fatal(1,"output bridge");
 $display("RUNTIME_FFT_WRAPPER_PASS"); $finish;
end
endmodule
'''
    (tmp_path / "tb.sv").write_text(tb, encoding="ascii")
    sources = [
        ROOT / "algorithms/fpga/phase06a/rtl/axis_skid_buffer.sv",
        ROOT / "algorithms/fpga/p0/rtl/axis_fft_runtime_wrapper.sv",
        tmp_path / "tb.sv",
    ]
    build = subprocess.run([compiler, "-g2012", "-s", "tb", "-o", str(tmp_path / "test.vvp"),
                            *(str(path) for path in sources)], capture_output=True, text=True)
    assert build.returncode == 0, build.stderr
    run = subprocess.run([runtime, str(tmp_path / "test.vvp")], cwd=tmp_path,
                         capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "RUNTIME_FFT_WRAPPER_PASS" in run.stdout


def test_runtime_adapter_uses_full_dynamic_core_widths() -> None:
    source = (ROOT / "algorithms/fpga/p0/rtl/amd_xfft_runtime_adapter.sv").read_text(encoding="utf-8")
    assert "input  logic [15:0] s_axis_config_tdata" in source
    assert "output logic [13:0] m_axis_data_tuser_index" in source
    assert "amd_m_axis_data_tdata[62:32]" in source
    assert "amd_m_axis_data_tdata[30:0]" in source
