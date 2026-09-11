"""Exercise configurable RTL against the integer model, including frame isolation."""
from pathlib import Path
import shutil
import subprocess

import pytest

from algorithms.rtl.p0_os_cfar import ALPHA_Q32, WEAK_ALPHA_Q32, detect_frame

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("normal,weak", [(True, 1 << 32), (0, 1 << 32),
    (1 << 36, 1 << 32), (8 << 32, 4 << 32), (2 << 32, 3 << 32)])
def test_model_rejects_invalid_coefficients(normal, weak):
    with pytest.raises(ValueError):
        detect_frame([100] * 4096, alpha_q32=normal, weak_alpha_q32=weak)


def test_runtime_thresholds_and_frame_isolation(tmp_path):
    compiler = shutil.which("iverilog") or "C:/msys64/ucrt64/bin/iverilog.exe"
    if not Path(compiler).exists():
        pytest.fail("Icarus Verilog gerekli.")
    runtime = str(Path(compiler).with_name("vvp.exe" if compiler.lower().endswith(".exe") else "vvp"))
    shifted = [100 + (i % 7) for i in range(4096)]
    for index, value in [(200, 220), (1000, 500), (2000, 1000), (3000, 1600)]:
        shifted[index] = value
    natural = [shifted[n ^ 2048] for n in range(4096)]
    profiles = [(ALPHA_Q32, WEAK_ALPHA_Q32), (2 << 32, 1 << 32),
                (12 << 32, 3 << 32), (ALPHA_Q32, WEAK_ALPHA_Q32)]
    (tmp_path / "power.mem").write_text("".join(f"{v:015x}\n" for v in natural))
    expected = [word for a, w in profiles for word in detect_frame(
        natural, alpha_q32=a, weak_alpha_q32=w).dma_words_natural]
    (tmp_path / "expected.mem").write_text("".join(f"{v:016x}\n" for v in expected))
    tb = r'''
module tb;
 reg clk=0; always #5 clk=~clk;
 reg rst=0, valid=0, ready=1, last=0, cv=0;
 reg [57:0] data=0; reg [11:0] idx=0;
 reg [35:0] ca=0; reg [33:0] cw=0;
 wire sr,mv,ml,cr,ap,rj,err; wire [63:0] md; wire [11:0] mi;
 wire [35:0] aa; wire [33:0] aw;
 reg [57:0] power_mem[0:4095]; reg [63:0] expected[0:16383];
 integer out_count=0; integer n; integer cycles=0;
 reg stalled=0; reg [76:0] stalled_payload;
 always @(negedge clk) ready=(cycles % 11 != 5 && cycles % 11 != 6);
 axis_p0_os_cfar #(.RUNTIME_CONFIG(1)) dut(
  .aclk(clk),.aresetn(rst),.s_axis_tvalid(valid),.s_axis_tready(sr),
  .s_axis_tdata(data),.s_axis_tlast(last),.s_axis_tuser_index(idx),
  .m_axis_tvalid(mv),.m_axis_tready(ready),.m_axis_tdata(md),
  .m_axis_tlast(ml),.m_axis_tuser_index(mi),.status_frame_error_sticky(err),
  .config_valid(cv),.config_ready(cr),.config_alpha_q32(ca),
  .config_weak_alpha_q32(cw),.config_applied(ap),.config_rejected(rj),
  .active_alpha_q32(aa),.active_weak_alpha_q32(aw));
 always @(posedge clk) if (rst) begin
  cycles=cycles+1;
  if(cycles>400000) $fatal(1,"timeout");
  if(err) $fatal(1,"frame error");
  if(stalled && (!mv || {mi,ml,md} !== stalled_payload)) $fatal(1,"backpressure stability");
  stalled=mv && !ready; stalled_payload={mi,ml,md};
  if(mv && ready) begin
   if(md !== expected[out_count] || mi !== (out_count % 4096) || ml !== ((out_count%4096)==4095))
    $fatal(1,"mismatch word=%0d got=%h expected=%h",out_count,md,expected[out_count]);
   out_count=out_count+1;
  end
 end
 task configure(input [35:0] a, input [33:0] w, input accepted);
  begin
   @(negedge clk); ca=a; cw=w; cv=1;
   if(!cr) $fatal(1,"not idle");
   @(negedge clk);
   if(ap !== accepted || rj !== !accepted) $fatal(1,"configuration acknowledgement");
   if(accepted && (aa !== a || aw !== w)) $fatal(1,"readback");
   cv=0;
  end
 endtask
 task frame(input integer target);
  begin
   for(n=0;n<4096;n=n+1) begin
    @(negedge clk); valid=1; data=power_mem[n]; idx=n; last=(n==4095);
    // A simultaneous first sample and a mid-frame request must not apply.
    cv=(n==0 || n==100); ca=36'd4294967296; cw=34'd4294967296;
    #1; if(cr || !sr) $fatal(1,"frame/config isolation");
   end
   @(negedge clk); valid=0; last=0; cv=0;
   // Request while the detector computes: no acknowledgement or change.
   repeat(20) begin
    @(negedge clk); cv=1;
    if(cr || ap || rj) $fatal(1,"busy configuration");
   end
   @(negedge clk); cv=0;
   wait(out_count==target);
   @(negedge clk);
  end
 endtask
 initial begin
  $readmemh("power.mem",power_mem); $readmemh("expected.mem",expected);
  repeat(3) @(negedge clk); rst=1;
  if(aa !== 36'd36851433755 || aw !== 34'd17098572778) $fatal(1,"defaults");
  frame(4096);
  configure(36'd8589934592,34'd4294967296,1);
  configure(36'd4294967296,34'd12884901888,0);
  configure(36'd0,34'd4294967296,0);
  if(aa !== 36'd8589934592 || aw !== 34'd4294967296) $fatal(1,"invalid modified state");
  frame(8192);
  configure(36'd51539607552,34'd12884901888,1);
  frame(12288);
  @(negedge clk); rst=0; repeat(2) @(negedge clk); rst=1;
  frame(16384);
  $display("RUNTIME_CFAR_PASS words=%0d",out_count); $finish;
 end
endmodule
'''
    (tmp_path / "tb.sv").write_text(tb)
    rtl = ROOT / "algorithms/fpga/p0/rtl"
    subprocess.run([compiler, "-g2012", "-s", "tb", "-o", str(tmp_path / "test.vvp"),
        str(rtl / "p0_os_cfar_pkg.sv"), str(rtl / "axis_p0_os_cfar.sv"), str(tmp_path / "tb.sv")],
        check=True, capture_output=True, text=True)
    result = subprocess.run([runtime, str(tmp_path / "test.vvp")], cwd=tmp_path,
                            check=True, capture_output=True, text=True, timeout=120)
    assert "RUNTIME_CFAR_PASS words=16384" in result.stdout
