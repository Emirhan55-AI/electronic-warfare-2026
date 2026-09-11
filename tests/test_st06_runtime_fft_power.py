from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def _lane(value: int) -> int:
    return value & 0xFFFFFFFF


def test_runtime_fft_power_is_exact_and_backpressure_stable(tmp_path: Path) -> None:
    compiler = shutil.which("iverilog") or "C:/msys64/ucrt64/bin/iverilog.exe"
    runtime = str(Path(compiler).with_name("vvp.exe" if compiler.lower().endswith(".exe") else "vvp"))
    pairs = [
        (0, 0), (1, -1), (1234567, -7654321),
        ((1 << 30) - 1, -(1 << 30)), (-(1 << 30), -(1 << 30)),
    ]
    words = [(_lane(q) << 32) | _lane(i) for i, q in pairs]
    powers = [i * i + q * q for i, q in pairs]
    (tmp_path / "input.mem").write_text("".join(f"{word:016x}\n" for word in words), encoding="ascii")
    (tmp_path / "expected.mem").write_text("".join(f"{value:016x}\n" for value in powers), encoding="ascii")
    tb = r'''
module tb;
reg clk=0; always #5 clk=~clk;
reg rst=0,sv=0,sl=0,mr=1; reg [63:0] sd=0; reg [13:0] si=0;
wire sr,mv,ml; wire [61:0] md; wire [13:0] mi;
reg [63:0] inputs[0:4],expected[0:4]; integer n,out_count=0,cycles=0;
reg stalled=0; reg [76:0] stalled_payload;
axis_fft_runtime_linear_power dut(.aclk(clk),.aresetn(rst),.s_axis_tvalid(sv),
 .s_axis_tready(sr),.s_axis_tdata(sd),.s_axis_tlast(sl),.s_axis_tuser_index(si),
 .m_axis_tvalid(mv),.m_axis_tready(mr),.m_axis_tdata(md),.m_axis_tlast(ml),
 .m_axis_tuser_index(mi));
always @(negedge clk) mr=(cycles%5!=2);
always @(posedge clk) begin
 cycles=cycles+1; if(cycles>200) $fatal(1,"timeout");
 if(stalled && (!mv || {mi,ml,md}!==stalled_payload)) $fatal(1,"backpressure");
 stalled=mv&&!mr; stalled_payload={mi,ml,md};
 if(mv&&mr) begin
  if(md!==expected[out_count][61:0] || mi!==out_count || ml!==(out_count==4))
   $fatal(1,"mismatch %0d got=%h expected=%h",out_count,md,expected[out_count]);
  out_count=out_count+1;
 end
end
initial begin
 $readmemh("input.mem",inputs); $readmemh("expected.mem",expected);
 repeat(3) @(negedge clk); rst=1;
 for(n=0;n<5;n=n+1) begin
  @(negedge clk); sv=1; sd=inputs[n]; si=n; sl=(n==4);
  do @(posedge clk); while(!sr);
 end
 @(negedge clk); sv=0; sl=0; wait(out_count==5);
 $display("RUNTIME_FFT_POWER_PASS"); $finish;
end
endmodule
'''
    (tmp_path / "tb.sv").write_text(tb, encoding="ascii")
    source = ROOT / "algorithms/fpga/p0/rtl/axis_fft_runtime_linear_power.sv"
    build = subprocess.run([compiler, "-g2012", "-s", "tb", "-o", str(tmp_path / "test.vvp"),
                            str(source), str(tmp_path / "tb.sv")], capture_output=True, text=True)
    assert build.returncode == 0, build.stderr
    run = subprocess.run([runtime, str(tmp_path / "test.vvp")], cwd=tmp_path,
                         capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "RUNTIME_FFT_POWER_PASS" in run.stdout
