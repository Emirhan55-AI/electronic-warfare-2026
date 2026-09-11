from pathlib import Path
import shutil
import subprocess

from algorithms.rtl.runtime_hann import SUPPORTED_FFT_SIZES, window_words


ROOT = Path(__file__).resolve().parents[1]


def test_runtime_hann_roms_are_reproducible() -> None:
    result = subprocess.run(
        ["python", "scripts/generate_st06_runtime_hann.py", "--check"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_runtime_hann_matches_reference_for_all_lengths(tmp_path: Path) -> None:
    compiler = shutil.which("iverilog") or "C:/msys64/ucrt64/bin/iverilog.exe"
    if not Path(compiler).exists():
        raise AssertionError("Icarus Verilog gerekli.")
    runtime = str(Path(compiler).with_name("vvp.exe" if compiler.lower().endswith(".exe") else "vvp"))
    all_inputs = []
    all_expected = []
    for size in SUPPORTED_FFT_SIZES:
        words = tuple((((index * 29) & 0xFF) << 8) | ((index * 17) & 0xFF) for index in range(size))
        all_inputs.extend(words)
        all_expected.extend(window_words(size, words))
    (tmp_path / "input.mem").write_text("".join(f"{word:04x}\n" for word in all_inputs), encoding="ascii")
    (tmp_path / "expected.mem").write_text("".join(f"{word:08x}\n" for word in all_expected), encoding="ascii")
    for size in SUPPORTED_FFT_SIZES:
        source = ROOT / "datasets/fixtures/phase06b" / (
            f"hann-runtime-coefficients-{size}.mem"
        )
        shutil.copyfile(source, tmp_path / source.name)
    tb = r'''
module tb;
reg clk=0; always #5 clk=~clk;
reg rst=0,sv=0,sl=0,mr=0; reg [15:0] sd=0; reg [3:0] nfft=12;
wire sr,mv,ml,err; wire [31:0] md;
reg [15:0] inputs[0:28671]; reg [31:0] expected[0:28671];
integer base=0,n,out_count=0,cycles=0;
axis_hann_window_runtime dut(.aclk(clk),.aresetn(rst),.active_fft_log2(nfft),
 .s_axis_tvalid(sv),.s_axis_tready(sr),.s_axis_tdata(sd),.s_axis_tlast(sl),
 .m_axis_tvalid(mv),.m_axis_tready(mr),.m_axis_tdata(md),.m_axis_tlast(ml),
 .status_frame_error_sticky(err));
always @(negedge clk) mr=(cycles%7!=2);
always @(posedge clk) begin
 cycles=cycles+1; if(cycles>100000) $fatal(1,"timeout");
 if(rst && err) $fatal(1,"frame error");
 if(mv&&mr) begin
  if(md!==expected[out_count]) $fatal(1,"data mismatch %0d got=%h expected=%h",out_count,md,expected[out_count]);
  if(ml!==((out_count==4095)||(out_count==12287)||(out_count==28671)))
   $fatal(1,"last mismatch %0d",out_count);
  out_count=out_count+1;
 end
end
task frame(input integer log2n,input integer size);
 begin
  nfft=log2n;
  for(n=0;n<size;n=n+1) begin
   @(negedge clk); sv=1; sd=inputs[base+n]; sl=(n==size-1);
   do @(posedge clk); while(!sr);
  end
  @(negedge clk); sv=0; sl=0; base=base+size;
  wait(out_count==base);
 end
endtask
initial begin
 $readmemh("input.mem",inputs); $readmemh("expected.mem",expected);
 repeat(4) @(negedge clk); rst=1;
 frame(12,4096); frame(13,8192); frame(14,16384);
 $display("RUNTIME_HANN_PASS words=%0d",out_count); $finish;
end
endmodule
'''
    (tmp_path / "tb.sv").write_text(tb, encoding="ascii")
    sources = [
        ROOT / "algorithms/fpga/phase06a/rtl/axis_skid_buffer.sv",
        ROOT / "algorithms/fpga/p0/rtl/axis_hann_window_runtime.sv",
        tmp_path / "tb.sv",
    ]
    build = subprocess.run(
        [compiler, "-g2012", "-s", "tb", "-o", str(tmp_path / "test.vvp"), *(str(path) for path in sources)],
        capture_output=True, text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run([runtime, str(tmp_path / "test.vvp")], cwd=tmp_path,
                         capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "RUNTIME_HANN_PASS words=28672" in run.stdout
