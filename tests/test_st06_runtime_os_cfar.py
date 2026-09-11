from pathlib import Path
import shutil
import subprocess

from algorithms.rtl.runtime_hann import SUPPORTED_FFT_SIZES
from algorithms.rtl.runtime_os_cfar import detect_words


ROOT = Path(__file__).resolve().parents[1]


def test_runtime_os_cfar_matches_all_supported_lengths(tmp_path: Path) -> None:
    compiler = shutil.which("iverilog") or "C:/msys64/ucrt64/bin/iverilog.exe"
    runtime = str(Path(compiler).with_name("vvp.exe" if compiler.lower().endswith(".exe") else "vvp"))
    inputs = []
    expected = []
    for size in SUPPORTED_FFT_SIZES:
        frame = [1000 + (index % 17) for index in range(size)]
        for index, scale in ((size // 8, 8), (size // 2 + 73, 12), (size - 100, 5)):
            frame[index] *= scale
        inputs.extend(frame)
        expected.extend(detect_words(frame))
    (tmp_path / "power.mem").write_text("".join(f"{word:015x}\n" for word in inputs), encoding="ascii")
    (tmp_path / "expected.mem").write_text("".join(f"{word:016x}\n" for word in expected), encoding="ascii")
    tb = r'''
module tb;
reg clk=0; always #5 clk=~clk;
reg rst=0,sv=0,sl=0,mr=1; reg [57:0] sd=0; reg [13:0] si=0; reg [3:0] nfft=12;
wire sr,mv,ml,err,cr,ap,rj; wire [63:0] md; wire [13:0] mi;
wire [35:0] aa; wire [33:0] aw;
reg [57:0] power[0:28671]; reg [63:0] expected[0:28671];
integer base=0,n,out_count=0,cycles=0;
reg stalled=0; reg [78:0] stalled_payload;
axis_p0_runtime_os_cfar dut(.aclk(clk),.aresetn(rst),.active_fft_log2(nfft),
 .s_axis_tvalid(sv),.s_axis_tready(sr),.s_axis_tdata(sd),.s_axis_tlast(sl),
 .s_axis_tuser_index(si),.m_axis_tvalid(mv),.m_axis_tready(mr),.m_axis_tdata(md),
 .m_axis_tlast(ml),.m_axis_tuser_index(mi),.status_frame_error_sticky(err),
 .config_valid(1'b0),.config_ready(cr),.config_alpha_q32(36'd36851433755),
 .config_weak_alpha_q32(34'd17098572778),.config_applied(ap),.config_rejected(rj),
 .active_alpha_q32(aa),.active_weak_alpha_q32(aw));
always @(negedge clk) mr=(cycles%13!=4 && cycles%13!=5);
always @(posedge clk) begin
 cycles=cycles+1; if(cycles>1000000) $fatal(1,"timeout");
 if(rst&&err) $fatal(1,"frame error");
 if(stalled&&(!mv||{mi,ml,md}!==stalled_payload)) $fatal(1,"backpressure");
 stalled=mv&&!mr; stalled_payload={mi,ml,md};
 if(mv&&mr) begin
  if(md!==expected[out_count] || mi!==(out_count-base))
   $fatal(1,"mismatch global=%0d local=%0d got=%h expected=%h",out_count,out_count-base,md,expected[out_count]);
  if(ml!==((out_count-base)==((1<<nfft)-1))) $fatal(1,"last mismatch %0d",out_count);
  out_count=out_count+1;
 end
end
task frame(input integer log2n,input integer size);
 integer start;
 begin
  nfft=log2n; start=base;
  for(n=0;n<size;n=n+1) begin
   @(negedge clk); sv=1; sd=power[start+n]; si=n; sl=(n==size-1);
   do @(posedge clk); while(!sr);
  end
  @(negedge clk); sv=0; sl=0;
  wait(out_count==start+size); base=start+size;
 end
endtask
initial begin
 $readmemh("power.mem",power); $readmemh("expected.mem",expected);
 repeat(3) @(negedge clk); rst=1;
 frame(12,4096); frame(13,8192); frame(14,16384);
 $display("RUNTIME_OS_CFAR_PASS words=%0d",out_count); $finish;
end
endmodule
'''
    (tmp_path / "tb.sv").write_text(tb, encoding="ascii")
    sources = [
        ROOT / "algorithms/fpga/p0/rtl/p0_os_cfar_pkg.sv",
        ROOT / "algorithms/fpga/p0/rtl/axis_p0_runtime_os_cfar.sv",
        tmp_path / "tb.sv",
    ]
    build = subprocess.run([compiler, "-g2012", "-s", "tb", "-o", str(tmp_path / "test.vvp"),
                            *(str(path) for path in sources)], capture_output=True, text=True)
    assert build.returncode == 0, build.stderr
    run = subprocess.run([runtime, str(tmp_path / "test.vvp")], cwd=tmp_path,
                         capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "RUNTIME_OS_CFAR_PASS words=28672" in run.stdout
